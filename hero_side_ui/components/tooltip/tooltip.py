"""
HeroSideUI Tooltip Component
基于 HeroUI v2 设计风格

样式来源: https://v2.heroui.com/docs/components/tooltip
设计意图: Tooltip = Popover 的 hover-only 简化版，不带 Backdrop

两种模式:
    1. 顶层模式（默认 embedded=False）：
        Tooltip (顶层 QWidget, Qt.Tool; paintEvent 自绘背景 + 圆角 + 阴影 + 箭头)
        适合 hover 静态按钮 / 文字提示等不需要跟随父滚动的常规场景。

    2. embedded 模式（embedded=True）：
        Tooltip 作为 trigger.window() 的子 widget；不设 windowFlags，无独立顶层窗口。
        适合需要"跟随父滚动 / 父移动"或避免顶层窗口首帧闪烁的场景（如 Slider thumb tooltip）。父子坐标关系让其自动跟随，零代码。

    Tooltip.attach(trigger_widget) 让任意 QWidget 当触发器，hover 自动显隐。
    支持 12 种 placement、auto flip。

特性:
    - 7 种颜色（default 即白底；其他色为 solid 主色背景）
    - 3 种尺寸（控制内容字号 / 默认 padding）
    - 5 种圆角（none/sm/md/lg/full）
    - 4 种阴影（none/sm/md/lg）
    - 12 种 placement
    - offset: 控制 tooltip 与 trigger 的距离（默认 7px）
    - open_delay / close_delay: 打开/关闭延迟（默认 0ms / 150ms）
    - show_arrow: 是否显示箭头（默认 False）
    - trigger_scale_on_open: 打开时给 trigger 设动态属性
    - 打开/关闭动画: opacity 0 ↔ 1 + pixmap scale 0.9 ↔ 1 时长 in=200ms / out=150ms（顶层模式用 windowOpacity；embedded 模式用 QGraphicsOpacityEffect）
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QPoint,
    QTimer,
)
from typing import Optional, Union

from ...themes import TOOLTIP_SIZES
from ...animation import FadeScaleAnimation, PixmapScaleProxy
from ...core import ThemeProvider
from ..text import Text
from ._constants import VALID_PLACEMENTS
from ._scroll_follow import _TooltipScrollFollowMixin
from ._trigger import _TooltipTriggerMixin
from ._paint import _TooltipPaintMixin
from . import _position as _pos


class Tooltip(
    _TooltipPaintMixin,
    _TooltipTriggerMixin,
    _TooltipScrollFollowMixin,
    QWidget,
):
    """HeroUI 风格 Tooltip — hover 触发的轻量信息提示。

    用法::

        tooltip = Tooltip(content="Hello tooltip", placement="top")
        tooltip.attach(my_button)

    或自定义内容::

        custom_widget = QWidget()
        # ... 配置 custom_widget ...
        tooltip = Tooltip(placement="bottom")
        tooltip.set_content(custom_widget)
        tooltip.attach(my_button)
    """

    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        content: Union[str, QWidget, None] = None,
        color: str = "default",
        size: str = "md",
        radius: str = "md",
        shadow: str = "sm",
        placement: str = "top",
        offset: int = 7,
        open_delay: int = 0,
        close_delay: int = 150,
        show_arrow: bool = False,
        trigger_scale_on_open: bool = True,
        is_disabled: bool = False,
        disable_animation: bool = False,
        embedded: bool = False,
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
        self._actual_placement = placement
        self._offset = offset
        self._open_delay = open_delay
        self._close_delay = close_delay
        self._show_arrow = show_arrow
        self._trigger_scale = trigger_scale_on_open
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._embedded = embedded
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._trigger: Optional[QWidget] = None
        # embedded 模式下的共享坐标系父（通常是 trigger.window()）；
        # 顶层模式下始终为 None。在 attach() 里赋值。
        self._anchor_ancestor: Optional[QWidget] = None
        self._content: Optional[QWidget] = None
        self._is_open = False
        # 关闭中（fade-out 进行中，_finalize_close 未触发）。
        # fade-out 期间用户再次 hover/click 能正确"取消关闭并重新打开"。
        self._closing = False
        # 顶层模式滚动跟随：open 时连接祖先链 scrollbar、close 时断开。
        # embedded 不需要——子 widget 随父滚动是 Qt 原生能力。
        self._scroll_bars: list = []
        self._scroll_reposition_pending = False

        # 窗口模式分流：
        # - 顶层模式（默认）：Qt.Tool + Frameless + WA_TranslucentBackground。
        #   广常场景（hover 按钮、文字提示）走这里。
        # - embedded：不设 windowFlags，作为 trigger 顶层 ancestor 的子 widget。
        #   适用于需要"跟随迫选项移动 / 滚动"的场景（如 Slider thumb tooltip）。
        #   子 widget 跟随是 Qt 内置能力，不需代码；且避免顶层窗口首次 show 闪一帧原生装饰。
        if not embedded:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        else:
            # embedded 不需要顶层窗口那套 attribute，背景透明靠 paintEvent 自绘心控。
            # 为了让 paintEvent 能画阶梯（paddings、阴影），不设 AutoFillBackground。
            self.setAutoFillBackground(False)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        # Tooltip 不抢焦点
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # open_delay 计时器
        self._open_timer = QTimer(self)
        self._open_timer.setSingleShot(True)
        self._open_timer.timeout.connect(self._do_open)

        # close_delay 计时器
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._do_close)

        # 内层 layout
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(*self._frame_margins())
        self._outer.setSpacing(0)

        # 设置内容
        if content is not None:
            if isinstance(content, str):
                self._set_text_content(content)
            elif isinstance(content, QWidget):
                self._set_widget_content(content)
        else:
            self._set_empty_content()

        # 动画: opacity + pixmap scale
        # - 顶层模式用 windowOpacity（不会影响阶梯 paintEvent 的阴影/圈绘制）
        # - embedded 模式用 QGraphicsOpacityEffect（子 widget 不能设 windowOpacity）
        self._fade = FadeScaleAnimation(
            target=self,
            scale_min=0.9,
            duration_in=200,
            duration_out=150,
            apply_opacity_via="effect" if embedded else "window",
        )
        self._fade.finished_in.connect(self._on_anim_in_done)
        self._fade.finished_out.connect(self._finalize_close)

        # pixmap 缩放代理
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
    # 内容
    # ============================================================
    def _set_empty_content(self):
        empty = QWidget()
        empty.setLayout(QVBoxLayout())
        pad = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["padding"]
        empty.layout().setContentsMargins(pad, pad, pad, pad)
        self._content = empty
        self._outer.addWidget(empty)

    def _set_text_content(self, text: str):
        """设置纯文字内容。"""
        pad = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["padding"]
        font_size = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["font_size"]

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)

        label = Text(
            text,
            size=font_size,
            color=self._text_color().name(),
            selectable=False,
        )
        layout.addWidget(label)

        self._content = container
        self._outer.addWidget(container)

    def _set_widget_content(self, widget: QWidget):
        """设置自定义 widget 内容。"""
        self._content = widget
        self._outer.addWidget(widget)
        self._apply_content_text_color()

    def set_content(self, content: Union[str, QWidget]):
        """替换内容。如果 tooltip 正在显示，自动刷新尺寸和位置。"""
        if self._content is not None:
            self._outer.removeWidget(self._content)
            from ...utils import safe_delete
            safe_delete(self._content)
        if isinstance(content, str):
            self._set_text_content(content)
        else:
            self._set_widget_content(content)
        # 如果正在显示，延迟到下一帧刷新（等 trigger 布局更新完）
        if self._is_open and self._trigger is not None:
            QTimer.singleShot(0, self._refresh_geometry)

    def _refresh_geometry(self):
        """刷新 tooltip 尺寸和位置（在下一帧调用，确保 trigger 布局已更新）。"""
        if not self._is_open or self._trigger is None:
            return
        self.adjustSize()
        self.resize(self.sizeHint())
        pos = self._calc_position(self._trigger)
        self.move(pos)

    def _apply_content_text_color(self):
        """给内容里的裸 QLabel/Text 刷反色。

        Text 是 QLabel 子类，优先走 set_color（不需 setStyleSheet，不会覆盖 padding）；
        裸 QLabel 仍走 setStyleSheet 兑底。这里是为了兼容用户给 set_content() 传入的
        自定义 widget 中的裸 QLabel。
        """
        if self._content is None:
            return
        text_hex = self._text_color().name()
        layout = self._content.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None:
                continue
            if isinstance(w, Text):
                w.set_color(text_hex)
            elif isinstance(w, QLabel):
                w.setStyleSheet(f"color: {text_hex}; background: transparent;")

    # ============================================================
    # 触发器 / hover 调度 / 视觉反馈
    # —— attach / eventFilter / _schedule_open / _schedule_close /
    #     _apply_trigger_open_state 均由 _TooltipTriggerMixin 提供
    # ============================================================

    # ============================================================
    # open / close 内部实现
    # ============================================================
    def _do_open(self):
        """打开 tooltip。三种入场：A) 全关闭→首次打开；B) fade-out 中→取消关闭、
        重算位置（trigger 可能因滚动移动了）、play_in 续接；C) 已稳定 open→bail。
        """
        if self._is_disabled or self._trigger is None:
            return
        if self._is_open and not self._closing:
            return  # 情况 C
        reopening = self._is_open and self._closing  # 情况 B
        # 取消"关闭中"标记；scroll watcher 在 reopening 路径下仍连着，无需重连
        self._closing = False

        # reopening 时必须先 end 旧 scale_proxy：_do_close 已 begin 截图 + hide content，
        # 否则下面 adjustSize / sizeHint 拿不到真实内容尺寸，_calc_position 会用 mini
        # sizeHint 算出严重错位的位置（向右下大幅偏移）。
        if reopening and self._scale_proxy.is_active():
            self._scale_proxy.end()

        # 布局 + 位置（reopening 时也要重算：trigger 可能因滚动而移动了）
        self.adjustSize()
        self.resize(self.sizeHint())
        pos = self._calc_position(self._trigger)
        self.move(pos)

        # trigger 视觉反馈
        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(True)

        if not reopening:
            # 顶层模式：连接祖先 scrollbar.valueChanged 以跟随滚动
            if not self._embedded:
                self._connect_scroll_watchers(self._trigger)
            self.show()
            self.raise_()
            self._is_open = True
            self.opened.emit()

        if self._disable_animation:
            self._fade.play_in(instant=True)
        else:
            # reopening 时也要重新 begin：上面已 end（content 恢复显示），现在用新位置 +
            # 新尺寸截一张新 pixmap，让 fade.play_in 从当前 progress 续接到 1.0
            self._scale_proxy.begin()
            self._fade.play_in()  # 内部会 stop 当前 fade，从当前 progress 续接到 1.0

    def _do_close(self):
        """实际执行关闭逻辑。标记 _closing=True，fade-out 中途又 _do_open 会走 reopening 分支。"""
        if not self._is_open:
            return
        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(False)
        self._closing = True
        if self._disable_animation:
            self._fade.play_out(instant=True)
            self._finalize_close()
        else:
            self._scale_proxy.begin()
            self._fade.play_out()

    def _finalize_close(self):
        if not self._is_open:
            return
        # _closing 被 _do_open 重置为 False = reopening 已抢占，该信号是尾声，跳过
        if not self._closing:
            return
        self._closing = False
        self.hide()
        self._is_open = False
        self._scale_proxy.end()
        self._disconnect_scroll_watchers()
        self.closed.emit()

    # 公共 API
    def is_open(self) -> bool:
        return self._is_open

    def open(self):
        """手动打开 tooltip。"""
        self._close_timer.stop()
        self._do_open()

    def close(self):
        """手动关闭 tooltip。"""
        self._open_timer.stop()
        self._do_close()

    # ============================================================
    # 缩放动画辅助
    # ============================================================
    def _content_is_text_only(self) -> bool:
        if self._content is None:
            return True
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
        self._scale_proxy.end()

    def hideEvent(self, event):
        if self._is_open:
            self._is_open = False
            self._closing = False
            self._scale_proxy.end()
            self._disconnect_scroll_watchers()
            self.closed.emit()
        super().hideEvent(event)

    # ============================================================
    # 触发器视觉响应 —— _apply_trigger_open_state 由 _TooltipTriggerMixin 提供
    # ============================================================

    # ============================================================
    # 几何（thin wrapper：纯几何计算在 _position.py）
    # ============================================================
    def _frame_margins(self) -> tuple:
        return _pos.frame_margins(
            self._shadow, self._show_arrow, self._actual_placement
        )

    def _calc_position(self, trigger: QWidget) -> QPoint:
        """计算 tooltip 坐标（含 auto-flip）。

        重要：每次计算都从 self._placement 重新出发，不使用上次的 _actual_placement——
        避免上次 flip 后 margins/sizeHint 被污染留到这次的中间态。
        """
        # 先 reset 到用户设定的 placement，重置 margins + sizeHint。
        # 这是为了让 flip 检测基于清洁初始态，不被上次 flip 的状态干扰
        if self._actual_placement != self._placement:
            self._actual_placement = self._placement
            self._outer.setContentsMargins(*self._frame_margins())
            self.adjustSize()
            self.resize(self.sizeHint())
        sz = self.sizeHint()
        margins = self._frame_margins()
        pos, actual = _pos.calc_position(
            trigger=trigger,
            placement=self._placement,
            offset_gap=self._offset,
            my_size=(sz.width(), sz.height()),
            margins=margins,
            embedded=self._embedded,
            anchor_ancestor=self._anchor_ancestor,
        )
        # 发生 flip：同步 actual_placement + margins + adjustSize，并重新用新 margins/size 算 pos
        if actual != self._actual_placement:
            self._actual_placement = actual
            self._outer.setContentsMargins(*self._frame_margins())
            self.adjustSize()
            self.resize(self.sizeHint())
            # 第二次重算：用新 sizeHint/margins 直接算（绕过 calc_position 的 flip 检测，
            # 否则 trigger 同时贴近上下边界时会被反复 flip，导致 pos 与 actual_placement
            # 不一致——表现为：tooltip 显示在 bottom 位置但 paintEvent 按 top 画箭头朝下）
            sz2 = self.sizeHint()
            new_margins = self._frame_margins()
            if self._embedded and self._anchor_ancestor is not None:
                origin = trigger.mapTo(self._anchor_ancestor, QPoint(0, 0))
            else:
                origin = trigger.mapToGlobal(QPoint(0, 0))
            pos = _pos.compute_pos_for(
                actual,
                origin,
                trigger.width(),
                trigger.height(),
                sz2.width(),
                sz2.height(),
                new_margins,
                self._offset,
            )
        else:
            self._outer.setContentsMargins(*margins)
        return pos

    @staticmethod
    def _flip_placement(p: str) -> str:
        return _pos.flip_placement(p)

    # ============================================================
    # 颜色 / 圆角 / paintEvent / 箭头 —— 全部由 _TooltipPaintMixin 提供
    # ============================================================

    # ============================================================
    # 公共动态 API
    # ============================================================
    def set_color(self, color: str):
        self._color = color
        self.update()
        self._apply_content_text_color()

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

    def set_offset(self, offset: int):
        """设置 tooltip 与 trigger 的距离（px）。"""
        self._offset = offset

    def set_open_delay(self, delay: int):
        """设置打开延迟（ms）。"""
        self._open_delay = delay

    def set_close_delay(self, delay: int):
        """设置关闭延迟（ms）。"""
        self._close_delay = delay

    def set_show_arrow(self, enabled: bool):
        self._show_arrow = enabled
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

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
        # 主题切换后:内容里 QLabel 的文字色是创建时写死的 hex,不会自动跟随主题,
        # 必须显式重刷,否则 dark 模式下 default tooltip 仍显示亮模式的暗色文字。
        self._apply_content_text_color()
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        # 同 set_theme:必须刷新 QLabel 文字色以匹配新主题。
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
