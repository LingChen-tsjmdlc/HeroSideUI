"""CheckboxGroup — 批量管理多个 Checkbox。

统一应用 color / size / radius / theme / orientation，聚合
selection_changed(List[str]) 信号，适合表单多选场景。
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
from .checkbox import Checkbox


# ============================================================
# CheckboxGroup
# ============================================================
class CheckboxGroup(QWidget):
    """多选组

    统一管理多个 Checkbox 的 color / size / radius / theme / orientation，
    提供 label / description / errorMessage / isRequired / isInvalid，
    并通过 value_changed 信号汇报已选值列表。

    用法:
        group = CheckboxGroup(label="Select your tech", color="primary")
        group.add_checkbox(Checkbox("React", value="react"))
        group.add_checkbox(Checkbox("Vue", value="vue"))
        group.value_changed.connect(lambda vals: print(vals))
    """

    value_changed = Signal(list)

    def __init__(
        self,
        label: str = "",
        description: str = "",
        error_message: str = "",
        orientation: str = "vertical",
        color: str = "primary",
        size: str = "md",
        radius: Optional[str] = None,
        line_through: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        default_value: Optional[List[str]] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._label_text = label
        self._description = description
        self._error_message = error_message
        self._orientation = orientation
        self._color = color
        self._size = size
        self._radius = radius
        self._line_through = line_through
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_required = is_required
        self._theme_mode = theme
        self._theme = Checkbox._resolve_theme(theme)
        self._default_value = default_value or []

        self._checkboxes: List[Checkbox] = []

        self._setup_ui()
        self._apply_styles()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    def _setup_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(8)

        # label
        self._label = Text(
            self._label_text,
            size="sm",
            weight="medium",
            selectable=False,
        )
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._label, 0, Qt.AlignmentFlag.AlignLeft)

        # checkbox 容器
        self._wrapper = QWidget()
        if self._orientation == "horizontal":
            self._wrapper_layout = QHBoxLayout(self._wrapper)
        else:
            self._wrapper_layout = QVBoxLayout(self._wrapper)
        self._wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._wrapper_layout.setSpacing(8)
        self._root.addWidget(self._wrapper)

        # helper (desc / error)
        self._helper = Text(
            "",
            size="xs",
            weight="normal",
            selectable=False,
        )
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
            desc_color = dc[400] if is_dark else dc[500]
            self._helper.setText(self._description)
            self._helper.set_color(desc_color)
            self._helper.show()
        else:
            self._helper.hide()

    # ------------------------------------------------------------
    # 管理子 Checkbox
    # ------------------------------------------------------------
    def add_checkbox(self, checkbox: Checkbox):
        """添加一个已有 Checkbox（继承 group 的样式属性）"""
        # 统一样式
        checkbox.set_color(self._color)
        checkbox.set_size(self._size)
        if self._radius is not None:
            checkbox.set_radius(self._radius)
        checkbox.set_theme(self._theme)
        checkbox.set_line_through(self._line_through)
        if self._is_disabled:
            checkbox.set_is_disabled(True)
        if self._is_invalid:
            checkbox.set_is_invalid(True)

        # 默认值回填
        if checkbox.value() in self._default_value:
            checkbox.setChecked(True)

        checkbox.stateChanged.connect(self._emit_value)
        self._checkboxes.append(checkbox)
        self._wrapper_layout.addWidget(checkbox)

    def create_checkbox(self, text: str, value: Optional[str] = None) -> Checkbox:
        """便利方法：创建一个 Checkbox 并加入 group"""
        cb = Checkbox(
            text=text,
            value=value,
            color=self._color,
            size=self._size,
            theme=self._theme,
            line_through=self._line_through,
        )
        if self._radius is not None:
            cb.set_radius(self._radius)
        self.add_checkbox(cb)
        return cb

    def _emit_value(self, _state):
        vals = [cb.value() for cb in self._checkboxes if cb.isChecked()]
        self.value_changed.emit(vals)

    def value(self) -> List[str]:
        return [cb.value() for cb in self._checkboxes if cb.isChecked()]

    def set_value(self, values: List[str]):
        for cb in self._checkboxes:
            cb.setChecked(cb.value() in values)

    # ------------------------------------------------------------
    # 动态 API
    # ------------------------------------------------------------
    def _broadcast(self, fn):
        for cb in self._checkboxes:
            fn(cb)

    def set_color(self, color: str):
        self._color = color
        self._broadcast(lambda c: c.set_color(color))

    def set_size(self, size: str):
        self._size = size
        self._broadcast(lambda c: c.set_size(size))

    def set_radius(self, radius: Optional[str]):
        self._radius = radius
        self._broadcast(lambda c: c.set_radius(radius))

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = Checkbox._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._broadcast(lambda c: c.set_theme(theme))
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._broadcast(lambda c: c._apply_provider_theme(theme))
        self._apply_styles()

    def set_line_through(self, enabled: bool):
        self._line_through = enabled
        self._broadcast(lambda c: c.set_line_through(enabled))

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._broadcast(lambda c: c.set_is_disabled(disabled))

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self._broadcast(lambda c: c.set_is_invalid(invalid))
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

    def set_orientation(self, orientation: str):
        if orientation == self._orientation:
            return
        self._orientation = orientation
        # 重建布局
        old = self._wrapper_layout
        new_layout = QHBoxLayout() if orientation == "horizontal" else QVBoxLayout()
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(8)
        for cb in self._checkboxes:
            old.removeWidget(cb)
        # 删除旧 layout
        QWidget().setLayout(old)
        self._wrapper_layout = new_layout
        self._wrapper.setLayout(new_layout)
        for cb in self._checkboxes:
            new_layout.addWidget(cb)
