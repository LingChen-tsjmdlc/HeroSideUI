"""RadioGroup — 互斥单选组。

统一应用 color / size / theme / orientation 到子 Radio，并实现单选互斥
语义：选中其中一个时其他自动取消。聚合 value_changed(str | None) 信号。
"""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS

from ..text import Text
from .radio import Radio, VALID_COLORS, VALID_SIZES, VALID_VARIANTS
from ._base import RadioBase


class RadioGroup(QWidget):
    """单选组

    统一管理多个 Radio，聚合 label / description / errorMessage /
    isRequired / isInvalid / orientation。通过 value_changed 汇报当前
    选中的 value（无选中时为 None）。

    用法:
        group = RadioGroup(label="Plan", color="primary")
        group.create_radio("Free", value="free")
        group.create_radio("Pro", value="pro")
        group.value_changed.connect(lambda v: print(v))
    """

    value_changed = Signal(object)  # str | None

    def __init__(
        self,
        label: str = "",
        description: str = "",
        error_message: str = "",
        orientation: str = "vertical",
        color: str = "primary",
        size: str = "md",
        variant: str = "default",
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        default_value: Optional[str] = None,
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
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("orientation must be 'vertical' or 'horizontal'")

        self._label_text = label
        self._description = description
        self._error_message = error_message
        self._orientation = orientation
        self._color = color
        self._size = size
        self._variant = variant
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_required = is_required
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = Radio._resolve_theme(theme)
        self._default_value = default_value

        self._radios: List[RadioBase] = []
        self._suppress = False  # 互斥时防止 toggled 风暴

        self._setup_ui()
        self._apply_styles()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # UI
    # ============================================================
    def _setup_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(8)

        # label
        self._label = Text("", size="sm", weight="normal", selectable=False)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._label, 0, Qt.AlignmentFlag.AlignLeft)

        # radios 容器
        self._wrapper = QWidget()
        if self._orientation == "horizontal":
            self._wrapper_layout = QHBoxLayout(self._wrapper)
        else:
            self._wrapper_layout = QVBoxLayout(self._wrapper)
        self._wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._wrapper_layout.setSpacing(8)
        self._wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._root.addWidget(self._wrapper)

        # helper (description / errorMessage)
        self._helper = Text("", size="xs", weight="normal", selectable=False)
        self._helper.setWordWrap(True)
        self._helper.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._helper.hide()
        self._root.addWidget(self._helper)

    def _apply_styles(self):
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]

        # label
        label_color = dc[400] if is_dark else dc[500]
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        display = self._label_text + req_mark if self._label_text else ""
        self._label.setText(display)
        self._label.set_color(label_color)
        self._label.setVisible(bool(self._label_text))

        # helper
        if self._is_invalid and self._error_message:
            self._helper.setText(self._error_message)
            self._helper.set_color(HEROUI_COLORS["danger"][500])
            self._helper.show()
        elif self._description:
            self._helper.setText(self._description)
            self._helper.set_color(dc[400] if is_dark else dc[400])
            self._helper.show()
        else:
            self._helper.hide()

    # ============================================================
    # 子 Radio 管理
    # ============================================================
    def add_radio(self, radio: RadioBase):
        """添加一个 Radio 到 group，继承样式并接入互斥逻辑"""
        radio.set_color(self._color)
        radio.set_size(self._size)
        radio.set_variant(self._variant)
        radio.set_theme(self._theme)
        radio.set_disable_animation(self._disable_animation)
        if self._is_disabled:
            radio.set_is_disabled(True)
        if self._is_invalid:
            radio.set_is_invalid(True)

        # 默认值回填
        if self._default_value is not None and radio.value() == self._default_value:
            radio.setChecked(True)

        # 互斥语义：HeroUI 的 radio 已选中再点忽略 —— 注入 toggle_guard
        radio._toggle_guard = self._guard_toggle  # type: ignore[attr-defined]
        radio.toggled.connect(
            lambda checked, r=radio: self._on_radio_toggled(r, checked)
        )

        self._radios.append(radio)
        self._wrapper_layout.addWidget(radio)

    def create_radio(
        self,
        text: str,
        value: Optional[str] = None,
        description: str = "",
    ) -> Radio:
        """便利方法：创建 Radio 并加入 group"""
        r = Radio(
            text=text,
            value=value,
            description=description,
            color=self._color,
            size=self._size,
            variant=self._variant,
            theme=self._theme,
            disable_animation=self._disable_animation,
        )
        self.add_radio(r)
        return r

    # 互斥守卫：已选中再点忽略
    def _guard_toggle(self, radio: RadioBase) -> bool:
        return radio.isChecked()

    def _on_radio_toggled(self, source: RadioBase, checked: bool):
        if self._suppress:
            return
        if not checked:
            return
        # 取消其他所有 radio 的选中
        self._suppress = True
        try:
            for r in self._radios:
                if r is not source and r.isChecked():
                    r.setChecked(False)
        finally:
            self._suppress = False
        self.value_changed.emit(source.value())

    # ============================================================
    # value API
    # ============================================================
    def value(self) -> Optional[str]:
        for r in self._radios:
            if r.isChecked():
                return r.value()
        return None

    def set_value(self, value: Optional[str]):
        self._suppress = True
        try:
            for r in self._radios:
                r.setChecked(r.value() == value)
        finally:
            self._suppress = False
        self.value_changed.emit(value)

    # ============================================================
    # 动态 API
    # ============================================================
    def _broadcast(self, fn):
        for r in self._radios:
            fn(r)

    def set_color(self, color: str):
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        self._color = color
        self._broadcast(lambda r: r.set_color(color))

    def set_size(self, size: str):
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        self._size = size
        self._broadcast(lambda r: r.set_size(size))

    def set_variant(self, variant: str):
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        self._variant = variant
        self._broadcast(lambda r: r.set_variant(variant))

    def variant(self) -> str:
        return self._variant

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = Radio._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._broadcast(lambda r: r.set_theme(theme))
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._broadcast(lambda r: r._apply_provider_theme(theme))
        self._apply_styles()

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._broadcast(lambda r: r.set_is_disabled(disabled))

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self._broadcast(lambda r: r.set_is_invalid(invalid))
        self._apply_styles()

    def set_is_required(self, required: bool):
        self._is_required = required
        self._apply_styles()

    def set_label(self, label: str):
        self._label_text = label
        self._apply_styles()

    def set_description(self, desc: str):
        self._description = desc
        self._apply_styles()

    def set_error_message(self, msg: str):
        self._error_message = msg
        self._apply_styles()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable
        self._broadcast(lambda r: r.set_disable_animation(disable))

    def set_orientation(self, orientation: str):
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("orientation must be 'vertical' or 'horizontal'")
        if orientation == self._orientation:
            return
        self._orientation = orientation
        # 重建 wrapper 布局；只从旧 layout 移除（removeWidget 不改父子关系，
        # radio 仍是 _wrapper 的子 widget），不调 setParent(None) —— 那会让 radio
        # 瞬间变顶层窗口在 Windows 闪原生 frame。销毁旧 layout 不会波及已 remove 的 widget。
        for r in self._radios:
            self._wrapper_layout.removeWidget(r)
        old = self._wrapper_layout
        new_layout = QHBoxLayout() if orientation == "horizontal" else QVBoxLayout()
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(8)
        new_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        QWidget().setLayout(old)  # 销毁旧 layout
        self._wrapper_layout = new_layout
        self._wrapper.setLayout(new_layout)
        for r in self._radios:
            new_layout.addWidget(r)
            r.show()
