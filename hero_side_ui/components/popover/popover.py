"""HeroSideUI Popover Component — 弹出层容器（trigger + 浮层）。

基于 HeroUI v2 popover。trigger 任意 QWidget，浮层自动定位并避让屏幕边界。

子组件 / mixin 拆分：
    - ``_GlobalClickCatcher`` → ``_click_catcher.py``
    - ``PopoverContent``      → ``content.py``
    - ``_Backdrop``           → ``_backdrop.py``
    - ``_PopoverPaintMixin``    → ``_paint.py``
    - ``_PopoverGeometryMixin`` → ``_geometry.py``
    - ``_PopoverTriggerMixin``  → ``_trigger.py``
    - ``_PopoverScrollMixin``   → ``_scroll.py`` （滚动跟随/关闭/wheel 转发）
    - ``_PopoverApiMixin``      → ``_api.py``    （动态 setter/theme/状态查询）
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

from ._api import _PopoverApiMixin
from ._backdrop import _Backdrop
from ._click_catcher import _GlobalClickCatcher
from ._constants import ARROW_INSET, ARROW_SIZE, DEFAULT_PADDING, VALID_PLACEMENTS
from ._geometry import _PopoverGeometryMixin
from ._paint import _PopoverPaintMixin
from ._scroll import _PopoverScrollMixin
from ._trigger import _PopoverTriggerMixin
from .content import PopoverContent


# ============================================================
# Popover — 主组件
# ============================================================
class Popover(
    _PopoverApiMixin,
    _PopoverScrollMixin,
    _PopoverPaintMixin,
    _PopoverGeometryMixin,
    _PopoverTriggerMixin,
    QWidget,
):
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
        close_on_scroll: bool = True,
        blur_quality: str = "fast",
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
        self._close_on_scroll = bool(close_on_scroll)
        # backdrop='blur' 滚动重抓质量档位（4 档）：
        #   low(2级) / fast(3级,默认) / great(4级) / high(QGraphicsBlurEffect)。
        # 初始 snapshot 永远是 QGraphicsBlurEffect，不受此参数影响；此值仅控制滚动节流
        # 帧重抓的路径。非法档位会在 _Backdrop 构造时 raise ValueError。
        self._blur_quality = blur_quality
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
        # 关闭中（fade-out 进行中、_finalize_close 还未触发）。
        # 用于在 fade-out 中途用户再次 hover/click 时正确"取消关闭并重新打开"，
        # 而不是 bail（bail 会留下 popover 在旧位置，trigger 可能因滚动变了位）。
        self._closing = False

        # 全局外部点击监听（open 时 install，close 时 remove）
        self._global_filter = _GlobalClickCatcher(self)

        # 滚动监听：open 时连接祖先链的 scrollbar，close 时断开。
        # 默认 close_on_scroll=True：滚动即关闭（带 fade-out 动画）；
        # 设 close_on_scroll=False 才切换为"跟随 reposition"。
        self._scroll_bars: list = []
        # reposition 节流：合并同一帧多个 scrollbar.valueChanged，避免重复 move。
        self._scroll_reposition_pending = False
        # popover 相对 trigger 全局坐标的固定偏移（open() 时记录）。
        # 滚动跟随只做"trigger_global + offset"平移，不再调用 _calc_position
        # 避免 fade-out 期间 sizeHint() 缩水导致的右下大幅偏移 / auto-flip 突变。
        self._scroll_anchor_offset: Optional[QPoint] = None

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
    # open / close API （is_open / toggle → _api.py，开关核心仍在主类）
    # ============================================================
    def open(self, near: Optional[QWidget] = None):
        # disabled 忽略
        if self._is_disabled:
            return
        target = near or self._trigger
        if target is None:
            return

        # 三种入场情况：
        #   A) 完全关闭（_is_open=False）→ 标准首次打开
        #   B) 正在 fade-out（_closing=True）→ 取消关闭 + 重算位置 + play_in 续接
        #   C) 已稳定 open（_is_open=True 且 _closing=False）→ bail
        if self._is_open and not self._closing:
            return  # 情况 C

        reopening = self._is_open and self._closing  # 情况 B
        # 取消"关闭中"标记；scroll watchers / global filter 在 reopening 路径下仍连着，无需重连
        self._closing = False

        # reopening 时必须先 end 旧 scale_proxy：_do_close 已 begin 截图 + hide content，
        # 否则下面 adjustSize / sizeHint 拿不到真实内容尺寸，_calc_position 会用 mini
        # sizeHint 算出严重错位的位置（向右下大幅偏移）。仅纯文字模式启用了 proxy。
        if reopening and self._scale_proxy.is_active():
            self._scale_proxy.end()

        if not reopening:
            # 1) backdrop —— 作为 trigger 所在 window 的子 widget，
            # 只覆盖应用客户区，不影响其他屏幕 / 其他应用。
            if self._backdrop_kind != "transparent":
                host = target.window() if hasattr(target, "window") else None
                if host is not None:
                    self._backdrop = _Backdrop(
                        self._backdrop_kind,
                        host=host,
                        blur_quality=self._blur_quality,
                    )
                    self._backdrop.setGeometry(0, 0, host.width(), host.height())
                    if self._backdrop_kind == "blur":
                        self._backdrop.prepare_blur_snapshot()
                    self._backdrop.clicked.connect(self.close)
                    self._backdrop.wheel_scrolled.connect(self._on_backdrop_wheel)
                    self._backdrop.raise_()
                    self._backdrop.show()
                    # 渐入
                    self._backdrop.play_in()
        else:
            # reopening: backdrop 在 _do_close 里已经 play_out，在这里重新 play_in 续接
            if self._backdrop is not None:
                self._backdrop.play_in()

        # 2) 布局 + 位置：严格按内容 sizeHint 撅开，不受 trigger 宽度限制
        # reopening 时也要重算 trigger 位置（可能因滚动而变）
        self.adjustSize()
        # adjustSize 在某些平台上仅采用当前可用宽度，这里显式 resize 到 sizeHint
        self.resize(self.sizeHint())
        pos = self._calc_position(target)
        self.move(pos)
        # 记录 popover 相对 trigger 全局坐标的偏移量。后续滚动跟随
        # （_do_scroll_reposition）只需 trigger_global + offset，不再调用
        # _calc_position / _compute_pos_for —— 否则会用受 _scale_proxy 影响
        # 后的 mini sizeHint() 算出严重右下偏移的位置。
        try:
            self._scroll_anchor_offset = pos - target.mapToGlobal(QPoint(0, 0))
        except RuntimeError:
            self._scroll_anchor_offset = QPoint(0, 0)

        # 3) trigger 视觉反馈
        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(True)

        if not reopening:
            # 4) 监听 popover 自己的 Enter/Leave（hover 模式用）
            self.installEventFilter(self)

            # 5) 全局点击监听（代替 Qt.Popup 的自动外部点击关闭）
            app = QApplication.instance()
            if app is not None:
                app.installEventFilter(self._global_filter)

            # 5b) 滚动跟随：监听 trigger 祖先链上的所有 QAbstractScrollArea
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
                # reopening 时也重新 begin：上面已 end（content 恢复显示），现在用新位置 +
                # 新尺寸截一张新 pixmap，让 fade.play_in 从当前 progress 续接到 1.0
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

        # 标记"关闭中"。fade-out 期间用户再触发 open() 会走"取消关闭"分支。
        self._closing = True

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
        # 如果 _closing 已被 open() 重置为 False（用户中途又触发了打开），
        # 说明 finished_out 是"已被 play_in 抢占后的尾声"——不该真的关闭
        if not self._closing:
            return
        self._closing = False
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
            self._closing = False
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
