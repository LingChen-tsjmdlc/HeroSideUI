"""HeroSideUI Popover Component — 弹出层容器（trigger + 浮层）。

基于 HeroUI v2 popover。trigger 任意 QWidget，浮层自动定位并避让屏幕边界。

子组件：
    - ``_GlobalClickCatcher`` → ``_click_catcher.py``
    - ``PopoverContent``      → ``content.py``
    - ``_Backdrop``           → ``_backdrop.py``
"""

from PySide6.QtCore import QElapsedTimer

from PySide6.QtCore import QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QPainterPath

from typing import Callable, Optional

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    QTimer,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import (
    BackdropFade,
    FadeScaleAnimation,
    PaddingSqueezeAnimation,
    PixmapScaleProxy,
)
from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, POPOVER_SHADOWS

from ._backdrop import _Backdrop
from ._click_catcher import _GlobalClickCatcher
from ._constants import ARROW_INSET, ARROW_SIZE, DEFAULT_PADDING, VALID_PLACEMENTS
from ._geometry import _PopoverGeometryMixin
from ._paint import _PopoverPaintMixin
from ._trigger import _PopoverTriggerMixin
from .content import PopoverContent




# ============================================================
# Popover — 主组件
# ============================================================
class Popover(_PopoverPaintMixin, _PopoverGeometryMixin, _PopoverTriggerMixin, QWidget):
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
        allow_flip: bool = True,
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
        self._allow_flip = bool(allow_flip)
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

        # padding 挤压扩张动画(复合组件场景下 transform-scale 的轻量替代):
        #   - 复合组件(Listbox/Input/...)走 pixmap_scale 会让子组件糊掉,只 fade
        #     缺乏"展开感";额外动画 _outer 的 contentsMargins 让内容"从锚点
        #     向外铺开",视觉补强
        #   - 纯文字仍走 pixmap scale(更整体感),不启用此动画
        # 启用与否在 open() 时根据 _content_is_text_only 决定。
        self._squeeze = PaddingSqueezeAnimation(
            layout=self._outer,
            base_margins=self._frame_margins(),
            # delta 20 + duration 280: 挤压幅度加大 20px,时长与 fade 对齐,
            # 视觉"展开"感明显。用 OutQuart(比 OutCubic 更有减速感,无过冲
            # 风险 —— OutBack 会 progress > 1.0 让 squeeze_extra 变负,
            # content_rect 反而超出 popover 外框,可能穿帮)
            delta=20,
            duration=280,
            easing=QEasingCurve.Type.OutQuart,
            easing_out=QEasingCurve.Type.InQuart,
            origin="center",  # open 时根据 placement 动态调,默认 center
            parent=self,
        )
        # 每帧 progress 变化触发重绘:paintEvent 会读 squeeze_extra() 让外框
        # 圆角/阴影跟着缩,实现"整个 popover(含底色)整体挤压"的效果,而不只是
        # 内容 layout 几何。否则边框不动只内容缩,视觉是"内容从中心铺开",
        # 不是"组件整体出现"。
        self._squeeze.progress_changed.connect(lambda _: self.update())

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

        # 动画分支:
        #   - 纯文字 popover: pixmap_scale + fade(整体感更强,字会被光栅化但短暂可接受)
        #   - 自定义插槽 / 复合组件: 只 fade,不做任何缩放/挤压(用户明确指定:
        #     使用透明度变化,不使用缩放或 padding squeeze。padding squeeze 在
        #     popover 含阴影 + 与 input 等宽的场景里视觉张力有限,且对子组件
        #     hover/ripple 没增益,fade 已足够)
        if self._disable_animation:
            self._fade.play_in(instant=True)
        else:
            if self._content_is_text_only():
                # 纯文字:抓取整窗 pixmap 作为缩放代理,隐藏真实内容
                self._scale_proxy.begin()
                self._fade.play_in()
            else:
                # 自定义插槽:只 fade
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
            if self._content_is_text_only():
                # 纯文字:关闭前也抓一次快照(内容可能变了),隐藏真实内容播 scale
                self._scale_proxy.begin()
                self._fade.play_out()
            else:
                # 自定义插槽:只 fade out
                self._fade.play_out()

    def _finalize_close(self):
        if not self._is_open:
            return
        self.hide()
        # squeeze 复位到展开(base margins),避免 popover 再次被 set_content/
        # adjustSize 时 layout 残留收起态影响 sizeHint 计算。
        self._squeeze.set_immediate(True)
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
        """把 popover 的 color/variant 同步给 trigger。

        6 种色（default / primary / secondary / success / warning / danger）全部透传。
        但**绝不调用 trigger.set_theme(self._theme)**：如果 trigger 原本是
        theme="auto" 的 Button，传入实际主题 "light" 会把它注销出 ThemeProvider，
        后续切 dark 时按钮文字仍停留在亮色规则，暗色背景下会变成低对比灰色。
        trigger 的主题应由它自己监听 ThemeProvider 自治刷新。
        """
        if self._trigger is None:
            return

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
        # 主题变化后:内容里的"裸 QLabel"文字色是我们 setStyleSheet 写死的 hex,
        # 不会自动跟主题切换 → 必须显式重刷。
        # 注意:不在这里 _sync_trigger_style() —— trigger(Button) 自己订阅了
        # ThemeProvider,会自治刷新 theme;popover 在 attach 时已做过一次性
        # color/variant 默认同步,主题切换不该再插手覆盖 trigger 状态。
        self._apply_content_text_color()
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        # 同 set_theme:只刷自家裸 QLabel,trigger 由它自己处理。
        self._apply_content_text_color()
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
