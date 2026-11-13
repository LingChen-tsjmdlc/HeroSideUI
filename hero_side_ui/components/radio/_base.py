"""RadioBase 基类：状态机/动画/互斥钩子/数据 API 全托管，不含 paintEvent。
任意子类可被 RadioGroup.add_radio 接纳。
"""

from PySide6.QtCore import (
    Property,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from ...animation import tween_property
from ...core import FontProvider, ThemeProvider
from ...themes import HEROUI_COLORS, RADIO_SIZES

VALID_COLORS = tuple(HEROUI_COLORS.keys())
VALID_SIZES = ("sm", "md", "lg")
VALID_VARIANTS = ("default", "card")


class RadioBase(QAbstractButton):
    """Radio 基类：承载状态机、动画属性与数据 API。

    Note:
        子类必须实现 paintEvent；selected 信号在勾选时携带 value，
        _toggle_guard 由 RadioGroup 注入以阻止反向取消。
    """

    selected = Signal(str)

    def __init__(
        self,
        text: str = "",
        value: str | None = None,
        description: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        variant: str = "default",
        is_disabled: bool = False,
        is_invalid: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构造单选按钮基类。

        Args:
            text: 显示文字。
            value: 选中时随信号发出的值；None 时回退到 text。
            description: 副说明文字。
            is_selected: 初始是否选中。
            color: 语义色名，须在 VALID_COLORS 内。
            size: sm/md/lg，须在 VALID_SIZES 内。
            variant: default/card，须在 VALID_VARIANTS 内。
            is_disabled: 初始是否禁用。
            is_invalid: 初始是否为校验失败态。
            disable_animation: 关闭选中与按压过渡。
            theme: light/dark/auto。
            parent: 父控件。

        Note:
            color/size/variant 会在构造期校验，非法值直接抛 ValueError；
            auto 模式注册到 ThemeProvider。
        """
        super().__init__(parent)

        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}, got {size!r}")
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}, got {variant!r}")

        self._color = color
        self._size = size
        self._variant = variant
        self._description = description
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._value = value if value is not None else text

        # 动画驱动值
        self._control_progress = 0.0  # 0 = hidden, 1 = full
        self._press_progress = 0.0  # 0 = 1.0 倍, 1 = 0.95 倍
        self._hover = False

        self.setText(text)
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setEnabled(not is_disabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        if is_selected:
            self._control_progress = 1.0

        # 动画
        self._control_anim = None

        self._press_anim = None

        self.toggled.connect(self._on_toggled)
        self._refresh_geometry()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)
        FontProvider.instance().register(self)

    # ============================================================
    # Qt 属性（驱动动画）
    # ============================================================
    def _get_control(self) -> float:
        """读取选中圆点的绘制进度。

        Returns:
            float: 0 隐藏、1 完全显示。
        """
        return self._control_progress

    def _set_control(self, v: float):
        """更新选中圆点绘制进度并触发重绘。

        Args:
            v: 新的进度值（0..1）。
        """
        self._control_progress = v
        self.update()

    control_progress = Property(float, _get_control, _set_control)

    def _get_press(self) -> float:
        """读取按压缩放进度。

        Returns:
            float: 0 为原始尺寸、1 为 0.95 倍。
        """
        return self._press_progress

    def _set_press(self, v: float):
        """更新按压缩放进度并触发重绘。

        Args:
            v: 新的进度值（0..1）。
        """
        self._press_progress = v
        self.update()

    press_progress = Property(float, _get_press, _set_press)

    # ============================================================
    # 状态变化
    # ============================================================
    def _on_toggled(self, checked: bool):
        """勾选状态变化时播放圆点过渡并派发选中信号。

        Args:
            checked: 当前是否已勾选。

        Note:
            过渡写入 control_progress Qt 属性；仅勾选时发 selected 信号。
        """
        tween_property(
            self,
            "_control_anim",
            b"control_progress",
            1.0 if checked else 0.0,
            duration=180,
            animated=not self._disable_animation,
        )
        if checked:
            self.selected.emit(self._value)

    # ============================================================
    # 鼠标 / 焦点事件
    # ============================================================
    def mousePressEvent(self, event):
        """按下时播放缩放反馈。

        Args:
            event: Qt 鼠标事件。

        Note:
            禁用态或关闭动画时不启动过渡，事件仍交由基类处理。
        """
        if self.isEnabled() and not self._disable_animation:
            tween_property(self, "_press_anim", b"press_progress", 1.0, duration=80)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """松开时恢复原始尺寸。

        Args:
            event: Qt 鼠标事件。
        """
        if self.isEnabled() and not self._disable_animation:
            tween_property(self, "_press_anim", b"press_progress", 0.0, duration=150)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """进入控件时置 hover 态并重绘。

        Args:
            event: Qt 进入事件。
        """
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """离开控件时清除 hover 态并重绘。

        Args:
            event: Qt 离开事件。
        """
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # 已选中再点击时由 RadioGroup 注入的守卫拦截，避免反向取消
    def nextCheckState(self):
        """切换勾选态前先经过互斥守卫。

        Note:
            _toggle_guard 由 RadioGroup 注入；命中时直接返回，避免已选中项
            被再次点击后取消选中。
        """
        guard = getattr(self, "_toggle_guard", None)
        if callable(guard) and guard(self):
            return
        super().nextCheckState()

    # ============================================================
    # 几何 / 子类可覆写
    # ============================================================
    def _size_config(self) -> dict:
        """返回当前 size 档位的几何配置。

        Returns:
            dict: 尺寸配置；未知档位回退到 md。
        """
        return RADIO_SIZES.get(self._size, RADIO_SIZES["md"])

    def _apply_font(self):
        """全局字体变化后刷新几何与绘制。"""
        self._refresh_geometry()

    def _refresh_geometry(self):
        """在尺寸或文本变化后刷新几何与绘制。

        Note:
            子类可覆写此钩子，以按自身画法重算布局。
        """
        self.updateGeometry()
        self.update()

    def setText(self, text: str):  # type: ignore[override]
        """设置显示文字并刷新几何。

        Args:
            text: 新的显示文字。
        """
        super().setText(text)
        self._refresh_geometry()

    def sizeHint(self) -> QSize:
        """返回建议尺寸。

        Returns:
            QSize: 由 wrapper 尺寸推导的基类默认尺寸。
        """
        # 基类提供默认实现避免 Qt 报警；子类应根据自身画法覆写
        cfg = self._size_config()
        wrapper = cfg["wrapper"]
        return QSize(wrapper * 4, wrapper + 8)

    def minimumSizeHint(self) -> QSize:
        """返回最小建议尺寸。

        Returns:
            QSize: 与 sizeHint 相同。
        """
        return self.sizeHint()

    # ============================================================
    # 公共 API（运行时切换）
    # ============================================================
    def set_color(self, color: str):
        """设置语义色并立即重绘。

        Args:
            color: 语义色名。

        Note:
            非法值抛 ValueError，与构造期校验一致。
        """
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        self._color = color
        self.update()

    def set_size(self, size: str):
        """设置尺寸档位并刷新几何。

        Args:
            size: sm/md/lg。

        Note:
            非法值抛 ValueError。
        """
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        self._size = size
        self._refresh_geometry()

    def set_variant(self, variant: str):
        """设置视觉变体并刷新几何。

        Args:
            variant: default/card。

        Note:
            非法值抛 ValueError。
        """
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        self._variant = variant
        self._refresh_geometry()

    def variant(self) -> str:
        """返回当前视觉变体。

        Returns:
            str: default 或 card。
        """
        return self._variant

    def set_description(self, description: str):
        """设置副说明文字并刷新几何。

        Args:
            description: 新的说明文字。
        """
        self._description = description
        self._refresh_geometry()

    def description(self) -> str:
        """返回当前副说明文字。

        Returns:
            str: 说明文字。
        """
        return self._description

    def set_is_disabled(self, disabled: bool):
        """设置禁用状态。

        Args:
            disabled: True 禁用交互。
        """
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_invalid(self, invalid: bool):
        """设置校验失败态并立即重绘。

        Args:
            invalid: True 显示错误配色。
        """
        self._is_invalid = invalid
        self.update()

    def set_disable_animation(self, disable: bool):
        """开启或关闭过渡动画。

        Args:
            disable: True 关闭动画。

        Note:
            关闭时立即把圆点与按压进度归位到当前状态，避免停在中间帧。
        """
        self._disable_animation = disable
        if disable:
            tween_property(
                self,
                "_control_anim",
                b"control_progress",
                1.0 if self.isChecked() else 0.0,
                duration=0,
            )
            tween_property(self, "_press_anim", b"press_progress", 0.0, duration=0)

    def set_theme(self, theme: str):
        """设置主题模式并立即重绘。

        Args:
            theme: auto 订阅 ThemeProvider 广播；light/dark 固定。

        Note:
            从 auto 切到固定主题时注销注册，避免继续接收广播。
        """
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
        """应用 ThemeProvider 广播的主题。

        Args:
            theme: 广播的目标主题（light/dark）。

        Note:
            由 Provider 回调触发，不走 set_theme 以免重复注册。
        """
        self._theme = theme
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析为实际主题。

        Args:
            mode: auto/light/dark。

        Returns:
            str: light 或 dark；auto 取 Provider 当前值。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def is_selected(self) -> bool:
        """返回当前是否选中。

        Returns:
            bool: 等同于 QAbstractButton 的勾选状态。
        """
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        """设置选中状态。

        Args:
            selected: True 勾选。

        Note:
            走 setChecked，因而会触发 _on_toggled 的过渡与信号。
        """
        self.setChecked(selected)

    def value(self) -> str:
        """返回选中信号携带的值。

        Returns:
            str: 当前 value。
        """
        return self._value

    def set_value(self, value: str):
        """设置选中信号携带的值。

        Args:
            value: 新的值。
        """
        self._value = value
