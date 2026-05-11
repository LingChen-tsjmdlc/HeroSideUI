"""
HeroSideUI Popover Component
基于 HeroUI v2 设计风格

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/popover.ts

结构:
    Popover  (顶层 QWidget, Qt.Tool; paintEvent 自绘背景 + 圆角 + 阴影 + 箭头)
        └── PopoverContent  (QWidget 插槽，用户随意 add)

    Popover.attach(trigger_widget) 让任意 QWidget 当触发器，点击切换显隐。
    支持 12 种 placement、auto flip、backdrop（transparent/opaque/blur）。

特性:
    - 7 种颜色（default 即白底；其他色为 solid 主色背景）
    - 3 种尺寸（控制内容字号 / 默认 padding）
    - 5 种圆角（none/sm/md/lg/full）
    - 4 种阴影（none/sm/md/lg）
    - 12 种 placement: top / top-start / top-end / bottom / bottom-start / bottom-end
                     left / left-start / left-end / right / right-start / right-end
    - backdrop: transparent / opaque(50% 黑) / blur(30% 黑 + 静态模糊)
    - trigger_scale_on_open: 打开/关闭时给 trigger 刷 `popoverOpen` 动态属性
    - 打开/关闭动画: windowOpacity 0↔1 + （纯文字内容时）pixmap scale 0.9↔1
      时长 in=280ms / out=200ms；backdrop 独立 fade（in=260ms / out=200ms）
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QRectF,
    QPoint,
    QEvent,
    QSize,
    QTimer,
    QElapsedTimer,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPainterPath,
)
from typing import Optional

from ..themes import HEROUI_COLORS, POPOVER_SHADOWS
from ..animation import FadeScaleAnimation, BackdropFade, PixmapScaleProxy
from ..core import ThemeProvider

ARROW_SIZE = 5  # 箭头一半边长（视觉像 5~6px 的小箭头）
ARROW_INSET = 2  # 箭头底边相对 content_rect 向内偏移，避免圆角缝隙
DEFAULT_PADDING = 10  # 内部内容默认 padding


# 合法 placement
VALID_PLACEMENTS = {
    "top",
    "top-start",
    "top-end",
    "bottom",
    "bottom-start",
    "bottom-end",
    "left",
    "left-start",
    "left-end",
    "right",
    "right-start",
    "right-end",
}


# ============================================================
# 全局外部点击监听（Tool 模式下用它代替 Popup 的自动外部关闭）
# ============================================================


class _GlobalClickCatcher(QObject):
    def __init__(self, owner: "Popover"):
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if not self._owner._is_open:
                return False
            # 全局坐标
            try:
                gp = event.globalPosition().toPoint()
            except AttributeError:
                gp = event.globalPos()
            # 点到 popover 自己 → 保持打开
            if self._owner.geometry().contains(gp):
                return False
            # 点到 trigger → 也保持（让 trigger 的 click 逻辑走 toggle，
            # 否则这里先关一次，用户点击再开一次，体感还是"点两次")
            if self._owner._trigger is not None:
                tr_top_left = self._owner._trigger.mapToGlobal(QPoint(0, 0))
                w = self._owner._trigger.width()
                h = self._owner._trigger.height()
                if (
                    tr_top_left.x() <= gp.x() <= tr_top_left.x() + w
                    and tr_top_left.y() <= gp.y() <= tr_top_left.y() + h
                ):
                    return False
            # 外部点击 → 关
            self._owner.close()
        return False


# ============================================================
# PopoverContent（插槽，类似 CardBody）
# ============================================================
class PopoverContent(QWidget):
    """Popover 内容插槽 — 任意 widget 都可以塞进来。

    用法::

        pc = PopoverContent()
        pc.layout().addWidget(QLabel("Hello"))
        pc.layout().addWidget(some_button)
        popover.set_content(pc)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroPopoverContent")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING
        )
        layout.setSpacing(8)


# ============================================================
# Backdrop
# ============================================================
class _Backdrop(QWidget):
    """遮罩层 — 作为 **host window 的子 widget**，只覆盖 host 的客户区；
    不会遮到其他应用、其他屏幕。

    kind:
        transparent — 透明遮罩（只用于拦截/不拦截点击）
        opaque      — 黑色 50% 遮罩
        blur        — 对 host 客户区做静态截屏 + 高斯模糊作为背景，再叠 30% 黑

    淡入淡出由 `BackdropFade` 驱动（paintEvent 里 `setOpacity(progress)`）。

    **static snapshot 说明**：`blur` 模式是在 `show()` 之前截图的，
    之后 host 内容变化不会反映到 backdrop 上。对 Popover 这种打开-关闭短期场景够用。
    """

    clicked = Signal()

    def __init__(self, kind: str = "transparent", host: Optional[QWidget] = None):
        # 关键：parent = host，不是独立顶层窗口
        super().__init__(host)
        self._kind = kind
        self._host = host
        self._blur_pixmap: Optional["QPixmap"] = None

        # 作为 host 的子 widget，不需要 window flags
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # transparent 模式不拦截点击（事件穿透）
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, kind == "transparent"
        )

        # 淡入淡出 —— 复用通用 BackdropFade 动画
        self._fade = BackdropFade(owner=self, duration_in=260, duration_out=200)

    def play_in(self):
        self._fade.play_in()

    def play_out(self):
        self._fade.play_out()

    def prepare_blur_snapshot(self):
        """在 show() 之前调用：抓取 host 客户区做高斯模糊快照。"""
        if self._host is None:
            return
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QGraphicsScene,
            QGraphicsPixmapItem,
            QGraphicsBlurEffect,
        )

        pm = self._host.grab()
        if pm.isNull():
            return

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pm)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(16)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)

        blurred = QPixmap(pm.size())
        blurred.fill(Qt.GlobalColor.transparent)
        painter = QPainter(blurred)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        scene.render(painter)
        painter.end()

        self._blur_pixmap = blurred

    def paintEvent(self, event):
        if self._kind == "transparent":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # 整体透明度随 BackdropFade.progress 渐变
        painter.setOpacity(self._fade.progress_value())

        if self._kind == "blur" and self._blur_pixmap is not None:
            painter.drawPixmap(self.rect(), self._blur_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))  # 30%
        elif self._kind == "opaque":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 128))  # 50%
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ============================================================
# Popover — 主组件
# ============================================================
class Popover(QWidget):
    """HeroUI 风格 Popover。

    用法::

        popover = Popover(placement="bottom", color="default")
        content = PopoverContent()
        content.layout().addWidget(QLabel("Hello popover"))
        popover.set_content(content)

        popover.attach(my_button)            # 默认 click 切换
        # 或手动: popover.open(near=my_button); popover.close()
    """

    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        color: str = "default",
        size: str = "md",
        radius: str = "md",
        shadow: str = "md",
        placement: str = "top",
        backdrop: str = "transparent",
        arrow: bool = False,
        trigger_scale_on_open: bool = True,
        trigger_variant: str = "flat",
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if placement not in VALID_PLACEMENTS:
            placement = "top"

        self._color = color
        self._size = size
        self._radius = radius
        self._shadow = shadow
        self._placement = placement
        self._actual_placement = placement  # auto-flip 后的真实方向
        self._backdrop_kind = backdrop
        self._arrow = arrow
        self._trigger_scale = trigger_scale_on_open
        self._trigger_variant = trigger_variant
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._trigger: Optional[QWidget] = None
        self._backdrop: Optional[_Backdrop] = None
        self._content: Optional[QWidget] = None
        self._is_open = False

        # 顶层窗口设置 —— 用 Tool 而不是 Popup：
        # Popup 会把点击 trigger 的 release 当作"外部点击"自动 hide
        # 我们自己的 _is_open 不知道，下一次 toggle 会走 close 分支，
        # 造成"点一次关了、点第二次才真的打开"的 bug。
        # 改用 Tool + 全局 mousePress 监听手动实现外部点击关闭。
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # hover 模式下延迟关闭，防闪烁
        self._hover_close_timer = QTimer(self)
        self._hover_close_timer.setSingleShot(True)
        self._hover_close_timer.setInterval(120)
        self._hover_close_timer.timeout.connect(self._hover_maybe_close)

        # 防止 Qt 自动关闭后立刻被 trigger click 重新打开造成"点两次才开"
        self._just_closed = QElapsedTimer()  # 上次 close 完成的时间

        # 全局外部点击监听（open 时 install，close 时 remove）
        self._global_filter = _GlobalClickCatcher(self)

        # 滚动监听：open 时连接祖先链的 scrollbar，close 时断开
        self._scroll_bars: list = []

        # 内层 layout: 留出 arrow + shadow 边距
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(*self._frame_margins())
        self._outer.setSpacing(0)

        # 默认空内容容器
        self._set_empty_content()

        # 动画: opacity（windowOpacity）+ pixmap-proxy scale 联动
        #
        # 打开/关闭期间:
        #   - FadeScaleAnimation 驱动 progress 0↔1；windowOpacity 随进度渐变；
        #     progress 同时暴露给 PixmapScaleProxy 换算出 0.9↔1 的缩放系数
        #   - PixmapScaleProxy 在动画开始时把整窗渲染成 QPixmap、隐藏真实
        #     content；paintEvent 里用缩放后的 pixmap 代替常规绘制，动画结束
        #     后恢复 content（见 `_content_is_text_only` 判断是否启用 scale）
        self._fade = FadeScaleAnimation(
            target=self,
            scale_min=0.9,
            duration_in=280,
            duration_out=200,
            apply_opacity_via="window",
        )
        self._fade.finished_in.connect(self._on_anim_in_done)
        self._fade.finished_out.connect(self._finalize_close)

        # pixmap 缩放代理（仅在纯文字内容时启用，避免复合组件位图模糊）
        self._scale_proxy = PixmapScaleProxy(
            owner=self,
            content_widget_getter=lambda: self._content,
            scale_getter=self._fade.scale_value,
            enable_predicate=self._content_is_text_only,
        )

        # 默认隐藏
        self.hide()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 内容插槽
    # ============================================================
    def _set_empty_content(self):
        empty = QWidget()
        empty.setLayout(QVBoxLayout())
        empty.layout().setContentsMargins(
            DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING
        )
        self._content = empty
        self._outer.addWidget(empty)

    def set_content(self, widget: QWidget):
        """替换内容控件。"""
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.setParent(None)
            self._content.deleteLater()
        self._content = widget
        self._outer.addWidget(widget)
        self._apply_content_text_color()

    def content(self) -> Optional[QWidget]:
        return self._content

    def _apply_content_text_color(self):
        """根据当前 color 给内容区里的"顶层裸 QLabel"刷反色。

        不对子控件（Input/Checkbox 等复合组件）级联 — 它们内部的 QLabel
        自己有样式逻辑。只遍历 `_content` 的直接子控件，命中是 `QLabel`
        且没设过 objectName 的（说明是用户手动 addWidget 的普通文字），
        给它 setStyleSheet 反色。
        """
        if self._content is None:
            return
        try:
            from PySide6.QtWidgets import QLabel
        except ImportError:
            return

        text_hex = self._text_color().name()
        # 清除 _content 上可能残留的级联 QSS
        self._content.setStyleSheet("")

        layout = self._content.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if isinstance(w, QLabel):
                # 仅给"裸 QLabel"刷色；复合组件内部的 QLabel 不动
                w.setStyleSheet(f"color: {text_hex}; background: transparent;")

    # ============================================================
    # 触发器
    # ============================================================
    def attach(
        self,
        trigger: QWidget,
        event: str = "click",
    ):
        """把任意 widget 设为触发器。

        - event="click"：触发器点击切换 open/close
        - event="hover"：进入时打开，离开时关闭（150ms 延迟防闪烁）
        - event="manual"：仅记录 trigger，使用方手动调用 open/close
        """
        if self._trigger is not None and self._trigger is not trigger:
            self._trigger.removeEventFilter(self)
        self._trigger = trigger

        if event == "manual":
            return

        trigger.installEventFilter(self)
        self._trigger_event_kind = event
        # 绑定时把颜色同步到 trigger（如果 trigger 支持 set_color）
        self._sync_trigger_color()

    def eventFilter(self, obj, event):
        # ---- trigger 的事件 ----
        if obj is self._trigger:
            kind = getattr(self, "_trigger_event_kind", "click")
            if kind == "click" and event.type() == QEvent.Type.MouseButtonRelease:
                if self._is_disabled:
                    return False
                # 如果刚关掉不久（<250ms），说明用户点到 trigger 的这一下同时
                # 被外部点击逻辑关闭了 popover，这里应忽略，避免立刻又开一遍
                if self._just_closed.isValid() and self._just_closed.elapsed() < 250:
                    return False
                self.toggle()
                return False

            if kind == "hover":
                if event.type() == QEvent.Type.Enter:
                    self._hover_close_timer.stop()
                    if not self._is_disabled:
                        self.open()
                    return False
                if event.type() == QEvent.Type.Leave:
                    # 延迟关闭：鼠标可能正在移向 popover
                    self._hover_close_timer.start()
                    return False

        # ---- popover 自己的 Enter/Leave（hover 模式下要能停掉关闭计时器）----
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self._hover_close_timer.stop()
            elif event.type() == QEvent.Type.Leave:
                if getattr(self, "_trigger_event_kind", "click") == "hover":
                    self._hover_close_timer.start()

        return super().eventFilter(obj, event)

    def _hover_maybe_close(self):
        """hover 模式下延迟关闭：如果鼠标已进入 popover 或 trigger 就取消。"""
        if not self._is_open:
            return
        gpos = self._cursor_global_pos()
        if gpos is None:
            self.close()
            return
        if self._point_inside_trigger_or_popover(gpos):
            return
        self.close()

    def _cursor_global_pos(self) -> Optional[QPoint]:
        try:
            from PySide6.QtGui import QCursor

            return QCursor.pos()
        except Exception:
            return None

    def _point_inside_trigger_or_popover(self, gp: QPoint) -> bool:
        # trigger
        if self._trigger is not None:
            tr_top_left = self._trigger.mapToGlobal(QPoint(0, 0))
            tr_rect = (
                tr_top_left.x(),
                tr_top_left.y(),
                self._trigger.width(),
                self._trigger.height(),
            )
            if (
                tr_rect[0] <= gp.x() <= tr_rect[0] + tr_rect[2]
                and tr_rect[1] <= gp.y() <= tr_rect[1] + tr_rect[3]
            ):
                return True
        # popover 自己（以 widget 几何为准）
        my_rect = self.geometry()
        if my_rect.contains(gp):
            return True
        return False

    # ============================================================
    # open / close API
    # ============================================================
    def is_open(self) -> bool:
        return self._is_open

    def toggle(self):
        if self._is_open:
            self.close()
        else:
            self.open()

    def open(self, near: Optional[QWidget] = None):
        # 已打开忽略；disabled 忽略
        if self._is_open or self._is_disabled:
            return
        target = near or self._trigger
        if target is None:
            return

        # 1) backdrop —— 作为 trigger 所在 window 的子 widget，
        # 只覆盖应用客户区，不影响其他屏幕 / 其他应用。
        if self._backdrop_kind != "transparent":
            host = target.window() if hasattr(target, "window") else None
            if host is not None:
                self._backdrop = _Backdrop(self._backdrop_kind, host=host)
                self._backdrop.setGeometry(0, 0, host.width(), host.height())
                if self._backdrop_kind == "blur":
                    self._backdrop.prepare_blur_snapshot()
                self._backdrop.clicked.connect(self.close)
                self._backdrop.raise_()
                self._backdrop.show()
                # 渐入
                self._backdrop.play_in()

        # 2) 布局 + 位置：严格按内容 sizeHint 撑开，不受 trigger 宽度限制
        self.adjustSize()
        # adjustSize 在某些平台上仅采用当前可用宽度，这里显式 resize 到 sizeHint
        self.resize(self.sizeHint())
        pos = self._calc_position(target)
        self.move(pos)

        # 3) trigger 视觉反馈
        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(True)

        # 4) 监听 popover 自己的 Enter/Leave（hover 模式用）
        self.installEventFilter(self)

        # 5) 全局点击监听（代替 Qt.Popup 的自动外部关闭）
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._global_filter)

        # 5b) 滚动即关闭：监听 trigger 祖先链上的所有 QAbstractScrollArea
        self._connect_scroll_watchers(target)

        # 6) 显示
        self.show()
        self.raise_()
        self._is_open = True
        self.opened.emit()

        if self._disable_animation:
            self._fade.play_in(instant=True)
        else:
            # 抓取整窗 pixmap 作为缩放代理，隐藏真实内容
            self._scale_proxy.begin()
            self._fade.play_in()

    def close(self):
        if not self._is_open:
            return

        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(False)

        # 移除全局点击监听
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._global_filter)

        # backdrop 渐出
        if self._backdrop is not None:
            self._backdrop.play_out()

        if self._disable_animation:
            self._fade.play_out(instant=True)
            self._finalize_close()
        else:
            # 关闭前也抓一次快照（内容可能变了），然后隐藏真实内容播 scale
            self._scale_proxy.begin()
            self._fade.play_out()

    def _finalize_close(self):
        if not self._is_open:
            return
        self.hide()
        # backdrop 的 hide 已由它自己的 fade 动画完成触发，这里只需 delete
        if self._backdrop is not None:
            self._backdrop.deleteLater()
            self._backdrop = None
        self._is_open = False
        self._just_closed.start()
        self._disconnect_scroll_watchers()
        self._scale_proxy.end()
        self.closed.emit()

    # ============================================================
    # 缩放动画辅助
    # ============================================================
    def _content_is_text_only(self) -> bool:
        """判断 _content 是否只包含 QLabel（纯文字）。

        - 没有 content / 没有 layout → True（空内容当文字处理）
        - layout 里所有直接子控件都是 QLabel → True
        - 否则 → False（包含 Input/Button/Checkbox 等复合组件）

        pixmap scale 对纯文字很合适，但对复合组件会：
        - 位图缩放让子组件变模糊
        - 子组件自己的 hover/focus 动画被冻结进 pixmap
        所以复合组件场景下只做 opacity fade。
        """
        if self._content is None:
            return True
        try:
            from PySide6.QtWidgets import QLabel
        except ImportError:
            return False
        layout = self._content.layout()
        if layout is None:
            return True
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None:
                continue
            if not isinstance(w, QLabel):
                return False
        return True

    def _on_anim_in_done(self):
        """play_in 结束 → 切换回真实内容（恢复交互）。"""
        self._scale_proxy.end()

    def hideEvent(self, event):
        """保险：无论出于什么原因 hide 了（Qt 内部的切窗口等），
        都把 _is_open 同步为 False，让 toggle 逻辑下次能正常开。"""
        if self._is_open:
            # 可能是 Qt 自动 hide（如切到其他应用），同步状态
            self._is_open = False
            self._just_closed.start()
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self._global_filter)
            if self._backdrop is not None:
                self._backdrop.hide()
                self._backdrop.deleteLater()
                self._backdrop = None
            self._disconnect_scroll_watchers()
            self._scale_proxy.end()
            self.closed.emit()
        super().hideEvent(event)

    # ============================================================
    # 触发器视觉响应
    # ============================================================
    def _apply_trigger_open_state(self, opened: bool):
        """打开/关闭时给 trigger 的视觉反馈。

        注意：不能用 setGraphicsEffect，会覆盖 trigger 自身的 effect
        （例如 Button 的 PressScaleEffect），一旦旧 effect 被替换 Qt
        C++ 端会立即析构 _ScaleEffect，后续 PressScaleEffect 动画回调
        再访问就会抛 "Internal C++ object already deleted"。

        改为通过动态属性 + Qt 的 styleSheet 刷新实现。如果触发器没有
        QSS 响应这个属性，则视觉上没变化，但不会崩。
        """
        if self._trigger is None:
            return
        self._trigger.setProperty("popoverOpen", opened)
        # 触发 style 刷新（很多控件的 QSS 会读 property）
        style = self._trigger.style()
        if style is not None:
            style.unpolish(self._trigger)
            style.polish(self._trigger)

    # ============================================================
    # 几何
    # ============================================================
    def _frame_margins(self) -> tuple:
        """内 layout 在四个方向需要让出多少空间给 arrow 和阴影。"""
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["md"])
        sm = cfg["blur"] + abs(cfg["offset_y"])
        # arrow 占用一边（仅在 self._arrow=True 时保留空间）
        arrow = ARROW_SIZE if self._arrow else 0
        place = self._actual_placement
        m = [sm, sm, sm, sm]  # left, top, right, bottom
        if place.startswith("top"):
            m[3] += arrow
        elif place.startswith("bottom"):
            m[1] += arrow
        elif place.startswith("left"):
            m[2] += arrow
        elif place.startswith("right"):
            m[0] += arrow
        return tuple(m)

    def _calc_position(self, trigger: QWidget) -> QPoint:
        """计算 popover 在屏幕坐标下的左上角位置（含 auto-flip）。"""
        tr_pos = trigger.mapToGlobal(QPoint(0, 0))
        tr_w = trigger.width()
        tr_h = trigger.height()

        screen = QApplication.primaryScreen().availableGeometry()

        # 先按用户指定方向算
        place = self._placement
        pos = self._compute_pos_for(place, tr_pos, tr_w, tr_h)

        # 检查是否越界，越界则反向
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        rect = (pos.x(), pos.y(), my_w, my_h)
        if (
            rect[0] < screen.left()
            or rect[1] < screen.top()
            or rect[0] + rect[2] > screen.right()
            or rect[1] + rect[3] > screen.bottom()
        ):
            flipped = self._flip_placement(place)
            new_pos = self._compute_pos_for(flipped, tr_pos, tr_w, tr_h)
            self._actual_placement = flipped
            self._outer.setContentsMargins(*self._frame_margins())
            self.adjustSize()
            return new_pos

        self._actual_placement = place
        self._outer.setContentsMargins(*self._frame_margins())
        return pos

    def _compute_pos_for(
        self, place: str, tr_pos: QPoint, tr_w: int, tr_h: int
    ) -> QPoint:
        """根据 placement 计算 popover 左上角（已扣掉 shadow 方向的 margin
        以保证 arrow 紧贴 trigger）。"""
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        x, y = tr_pos.x(), tr_pos.y()

        # frame_margins: (left, top, right, bottom)。我们 sizeHint 包含了
        # 这些 margin，但实际 content_rect 距离 widget 边缘还有 margin。
        # 为了让 arrow 紧贴 trigger，要把 widget 位置朝 trigger 的反方向 +margin。
        ml, mt, mr, mb = self._frame_margins()
        # arrow 尖与 trigger 之间保留 6px 空气
        gap = 6

        if place == "top":
            return QPoint(x + (tr_w - my_w) // 2, y - my_h + mb - gap)
        if place == "top-start":
            return QPoint(x - ml, y - my_h + mb - gap)
        if place == "top-end":
            return QPoint(x + tr_w - my_w + mr, y - my_h + mb - gap)

        if place == "bottom":
            return QPoint(x + (tr_w - my_w) // 2, y + tr_h - mt + gap)
        if place == "bottom-start":
            return QPoint(x - ml, y + tr_h - mt + gap)
        if place == "bottom-end":
            return QPoint(x + tr_w - my_w + mr, y + tr_h - mt + gap)

        if place == "left":
            return QPoint(x - my_w + mr - gap, y + (tr_h - my_h) // 2)
        if place == "left-start":
            # popover 顶对齐 trigger 顶（视觉左下方向延伸）
            return QPoint(x - my_w + mr - gap, y - mt)
        if place == "left-end":
            # popover 底对齐 trigger 底（视觉左上方向延伸）
            return QPoint(x - my_w + mr - gap, y + tr_h - my_h + mb)

        if place == "right":
            return QPoint(x + tr_w - ml + gap, y + (tr_h - my_h) // 2)
        if place == "right-start":
            return QPoint(x + tr_w - ml + gap, y - mt)
        if place == "right-end":
            return QPoint(x + tr_w - ml + gap, y + tr_h - my_h + mb)

        return QPoint(x, y + tr_h)

    @staticmethod
    def _flip_placement(p: str) -> str:
        if p.startswith("top"):
            return p.replace("top", "bottom")
        if p.startswith("bottom"):
            return p.replace("bottom", "top")
        if p.startswith("left"):
            return p.replace("left", "right")
        if p.startswith("right"):
            return p.replace("right", "left")
        return p

    # ============================================================
    # 颜色
    # ============================================================
    def _bg_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#ffffff" if not is_dark else "#27272a")
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        return QColor(c[500])

    def _text_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#11181c" if not is_dark else "#ecedee")
        if self._color == "warning":
            return QColor("#000000")
        return QColor("#ffffff")

    # ============================================================
    # 圆角
    # ============================================================
    def _resolve_radius(self) -> float:
        if self._radius == "none":
            return 0.0
        if self._radius == "full":
            # 半高
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 14))

    def _content_rect_size(self) -> QSize:
        m = self._frame_margins()
        return QSize(
            max(0, self.width() - m[0] - m[2]), max(0, self.height() - m[1] - m[3])
        )

    # ============================================================
    # 绘制：阴影 + 圆角主体 + 箭头
    # ============================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # ---- 动画期间：只画缩放后的 pixmap，跳过常规绘制 ----
        if self._scale_proxy.is_active():
            w, h = self.width(), self.height()
            # 缩放锚点：靠近 trigger 的那一侧（arrow 所在边的中点）
            # 这样 scale 动画的视觉是"从 trigger 方向展开/收回"，更贴合 HeroUI
            m = self._frame_margins()
            place = self._actual_placement
            content_rect = QRectF(m[0], m[1], w - m[0] - m[2], h - m[1] - m[3])
            if place.startswith("top"):
                cx, cy = content_rect.center().x(), content_rect.bottom()
            elif place.startswith("bottom"):
                cx, cy = content_rect.center().x(), content_rect.top()
            elif place.startswith("left"):
                cx, cy = content_rect.right(), content_rect.center().y()
            elif place.startswith("right"):
                cx, cy = content_rect.left(), content_rect.center().y()
            else:
                cx, cy = content_rect.center().x(), content_rect.center().y()
            self._scale_proxy.draw(painter, self.rect(), anchor=(cx, cy))
            return

        m = self._frame_margins()
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["md"])
        bg = self._bg_color()
        radius = self._resolve_radius()

        # 内容矩形（即 frame 内层）
        content_rect = QRectF(
            m[0], m[1], self.width() - m[0] - m[2], self.height() - m[1] - m[3]
        )

        # ---- 1) 阴影：多层半透明，越往外越透明 ----
        if cfg["layers"] > 0:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            # 从外到内画 layers 层，外层扩散大但透明度低
            for i in range(cfg["layers"]):
                t = (i + 1) / cfg["layers"]  # 0..1，内→外
                grow = cfg["blur"] * (1 - t) + 1
                off = cfg["offset_y"] * (1 - t)
                rect = content_rect.adjusted(-grow, -grow + off, grow, grow + off)
                # alpha 渐进：外层最淡（t 小），内层最浓（t→1）
                alpha = int(cfg["alpha"] * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(rect, radius, radius)
            painter.restore()

        # ---- 2) 主体背景 ----
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)

        # ---- 3) arrow（仅当 arrow=True）----
        if self._arrow:
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        place = self._actual_placement
        a = ARROW_SIZE
        path = QPainterPath()

        # arrow 基底向 content_rect **内部** 偏移 ARROW_INSET，
        # 让三角形底边被 content 盖住一小段，避免圆角在 start/end 时露缝隙。
        inset = ARROW_INSET

        if place.startswith("top"):
            # arrow 在底部（指向 trigger 方向 = 下）
            base_y = content_rect.bottom() - inset
            tip_y = content_rect.bottom() + a
            if "start" in place:
                cx = content_rect.left() + 14 + a
            elif "end" in place:
                cx = content_rect.right() - 14 - a
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("bottom"):
            base_y = content_rect.top() + inset
            tip_y = content_rect.top() - a
            if "start" in place:
                cx = content_rect.left() + 14 + a
            elif "end" in place:
                cx = content_rect.right() - 14 - a
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("left"):
            base_x = content_rect.right() - inset
            tip_x = content_rect.right() + a
            if "start" in place:
                # start 顶对齐 → 箭头在顶部 25%
                cy = content_rect.top() + max(14 + a, content_rect.height() * 0.25)
            elif "end" in place:
                # end 底对齐 → 箭头在底部 25%
                cy = content_rect.bottom() - max(14 + a, content_rect.height() * 0.25)
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        elif place.startswith("right"):
            base_x = content_rect.left() + inset
            tip_x = content_rect.left() - a
            if "start" in place:
                cy = content_rect.top() + max(14 + a, content_rect.height() * 0.25)
            elif "end" in place:
                cy = content_rect.bottom() - max(14 + a, content_rect.height() * 0.25)
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        else:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawPath(path)

    # ============================================================
    # 公共动态 API
    # ============================================================
    def set_color(self, color: str):
        self._color = color
        self.update()
        self._apply_content_text_color()
        self._sync_trigger_style()

    def set_trigger_variant(self, variant: str):
        self._trigger_variant = variant
        self._sync_trigger_style()

    def set_arrow(self, enabled: bool):
        self._arrow = enabled
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def _sync_trigger_style(self):
        """把 popover 的 color/variant/theme 同步给 trigger。

        6 种色（default / primary / secondary / success / warning / danger）全部透传：
        - `trigger.set_color(color)`
        - `trigger.set_theme(popover.theme)`
        - `trigger.set_variant(trigger_variant)`（默认 flat）
        """
        if self._trigger is None:
            return

        if hasattr(self._trigger, "set_theme"):
            try:
                self._trigger.set_theme(self._theme)
            except Exception:
                pass
        if hasattr(self._trigger, "set_color"):
            try:
                self._trigger.set_color(self._color)
            except Exception:
                pass
        if hasattr(self._trigger, "set_variant"):
            try:
                self._trigger.set_variant(self._trigger_variant)
            except Exception:
                pass

    # 兼容旧名
    def _sync_trigger_color(self):
        self._sync_trigger_style()

    # ============================================================
    # 滚动即关闭
    # ============================================================
    def _connect_scroll_watchers(self, trigger: QWidget):
        """沿 trigger 祖先链找所有 QAbstractScrollArea，监听其滚动条变化，
        一旦滚动就关闭 popover。"""
        from PySide6.QtWidgets import QAbstractScrollArea

        self._disconnect_scroll_watchers()
        w = trigger
        seen = set()
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                for bar in (w.verticalScrollBar(), w.horizontalScrollBar()):
                    if bar is not None and id(bar) not in seen:
                        seen.add(id(bar))
                        bar.valueChanged.connect(self._on_scroll_detected)
                        self._scroll_bars.append(bar)
            w = w.parentWidget()

    def _disconnect_scroll_watchers(self):
        for bar in self._scroll_bars:
            try:
                bar.valueChanged.disconnect(self._on_scroll_detected)
            except (RuntimeError, TypeError):
                pass
        self._scroll_bars.clear()

    def _on_scroll_detected(self, _value: int):
        """任何祖先 scroll area 滚动时 → **立即**关闭 popover（跳过淡出动画）。

        如果走正常 fade-out（200ms），popover 会跟着滚动条飘 200ms 才消失，
        视觉上像是 popover 位置和 trigger 脱钩了。
        """
        if not self._is_open:
            return

        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(False)

        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._global_filter)

        # 立即把 fade 动画置 0 + 隐藏
        self._fade.play_out(instant=True)
        if self._backdrop is not None:
            # backdrop 也立即隐藏（无淡出）
            self._backdrop.hide()
        self._scale_proxy.end()
        self._finalize_close()

    def set_size(self, size: str):
        self._size = size
        self.update()

    def set_radius(self, radius: str):
        self._radius = radius
        self.update()

    def set_shadow(self, shadow: str):
        self._shadow = shadow
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_placement(self, placement: str):
        if placement in VALID_PLACEMENTS:
            self._placement = placement
            self._actual_placement = placement
            self._outer.setContentsMargins(*self._frame_margins())
            self.update()

    def set_backdrop(self, kind: str):
        self._backdrop_kind = kind

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        if disabled and self._is_open:
            self.close()
