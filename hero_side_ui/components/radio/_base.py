"""HeroSideUI Radio 基类 — 状态机 / 互斥钩子 / 数据 API（不含 paint）

提供共享的状态、动画、value/description/disabled/invalid 等数据 API，
以及与 RadioGroup 协作所需的 `_toggle_guard` 钩子和 `selected` 信号。

不实现 paintEvent —— 子类（如 `Radio`）负责自绘视觉。

适用场景:
    - 用户继承 `RadioBase` 自造视觉时，`RadioGroup` 仍能正常托管互斥
    - 任意 `RadioBase` 子类皆可被 `RadioGroup.add_radio` 接纳
"""

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIO_SIZES

VALID_COLORS = tuple(HEROUI_COLORS.keys())
VALID_SIZES = ("sm", "md", "lg")
VALID_VARIANTS = ("default", "card")


class RadioBase(QAbstractButton):
    """Radio 基类：仅承载状态机与数据 API，不含 paintEvent

    子类必须自行实现 paintEvent；本基类提供：
        - 标准 prop（color / size / variant / theme / disabled / invalid 等）
        - 动画驱动属性（control_progress / press_progress）
        - hover / press / theme 切换钩子
        - 与 RadioGroup 协作所需的 `_toggle_guard` / selected 信号
    """

    selected = Signal(str)

    def __init__(
        self,
        text: str = "",
        value: Optional[str] = None,
        description: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        variant: str = "default",
        is_disabled: bool = False,
        is_invalid: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}, got {size!r}")
        if variant not in VALID_VARIANTS:
            raise ValueError(
                f"variant must be one of {VALID_VARIANTS}, got {variant!r}"
            )

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

        if is_selected and not disable_animation:
            self._control_progress = 1.0

        # 动画
        self._control_anim = QPropertyAnimation(self, b"control_progress")
        self._control_anim.setDuration(180)
        self._control_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"press_progress")
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)
        self._refresh_geometry()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Qt 属性（驱动动画）
    # ============================================================
    def _get_control(self) -> float:
        return self._control_progress

    def _set_control(self, v: float):
        self._control_progress = v
        self.update()

    control_progress = Property(float, _get_control, _set_control)

    def _get_press(self) -> float:
        return self._press_progress

    def _set_press(self, v: float):
        self._press_progress = v
        self.update()

    press_progress = Property(float, _get_press, _set_press)

    # ============================================================
    # 状态变化
    # ============================================================
    def _on_toggled(self, checked: bool):
        if self._disable_animation:
            self._control_progress = 1.0 if checked else 0.0
            self.update()
        else:
            self._control_anim.stop()
            self._control_anim.setStartValue(self._control_progress)
            self._control_anim.setEndValue(1.0 if checked else 0.0)
            self._control_anim.start()
        if checked:
            self.selected.emit(self._value)

    # ============================================================
    # 鼠标 / 焦点事件
    # ============================================================
    def mousePressEvent(self, event):
        if self.isEnabled() and not self._disable_animation:
            self._press_anim.stop()
            self._press_anim.setStartValue(self._press_progress)
            self._press_anim.setEndValue(1.0)
            self._press_anim.setDuration(80)
            self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and not self._disable_animation:
            self._press_anim.stop()
            self._press_anim.setStartValue(self._press_progress)
            self._press_anim.setEndValue(0.0)
            self._press_anim.setDuration(150)
            self._press_anim.start()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # 已选中再点击时由 RadioGroup 注入的守卫拦截，避免反向取消
    def nextCheckState(self):
        guard = getattr(self, "_toggle_guard", None)
        if callable(guard) and guard(self):
            return
        super().nextCheckState()

    # ============================================================
    # 几何 / 子类可覆写
    # ============================================================
    def _size_config(self) -> dict:
        return RADIO_SIZES.get(self._size, RADIO_SIZES["md"])

    def _refresh_geometry(self):
        """子类可覆写：当 size/text/description/variant 改变时调用"""
        self.updateGeometry()
        self.update()

    def setText(self, text: str):  # type: ignore[override]
        super().setText(text)
        self._refresh_geometry()

    def sizeHint(self) -> QSize:
        # 基类提供默认实现避免 Qt 报警；子类应根据自身画法覆写
        cfg = self._size_config()
        wrapper = cfg["wrapper"]
        return QSize(wrapper * 4, wrapper + 8)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ============================================================
    # 公共 API（运行时切换）
    # ============================================================
    def set_color(self, color: str):
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        self._color = color
        self.update()

    def set_size(self, size: str):
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        self._size = size
        self._refresh_geometry()

    def set_variant(self, variant: str):
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        self._variant = variant
        self._refresh_geometry()

    def variant(self) -> str:
        return self._variant

    def set_description(self, description: str):
        self._description = description
        self._refresh_geometry()

    def description(self) -> str:
        return self._description

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self.update()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable

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

    def is_selected(self) -> bool:
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        self.setChecked(selected)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str):
        self._value = value
