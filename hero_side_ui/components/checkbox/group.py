"""CheckboxGroup：统一下发样式并聚合 value_changed(list[str])。"""

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
    """多选组：统一管理子 Checkbox 样式与状态。

    通过 value_changed 汇报已选值列表；label/description/errorMessage
    齐备，适合表单场景。
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
        radius: str | None = None,
        line_through: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        default_value: list[str] | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建多选组容器。

        Args:
            label: 组标签文本。
            description: 组描述。
            error_message: 错误提示文本（invalid 时优先显示）。
            orientation: vertical / horizontal 排列方向。
            color: 组级语义色，下发给子 Checkbox。
            size: 组级尺寸档位。
            radius: 组级圆角；None 不下发。
            line_through: 选中时文字是否加删除线。
            is_disabled: 组级禁用。
            is_invalid: 组级错误态。
            is_required: 是否显示必填星号。
            default_value: 初始选中的 value 列表。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。
        """
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

        self._checkboxes: list[Checkbox] = []

        self._setup_ui()
        self._apply_styles()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    def _setup_ui(self):
        """构建组标签、子项容器与 helper 文本三层结构。

        Note:
            子项容器按 orientation 选横/纵布局；label 与 helper
            都透明化鼠标事件，避免挡住子 Checkbox 交互。
        """
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
        """刷新 label（含必填星号）与 helper（错误 / 描述）的文案与配色。"""
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
        """添加一个已有 Checkbox 并继承组级样式。

        Args:
            checkbox: 待加入的子 Checkbox。

        Note:
            统一下发 color / size / radius / theme / line_through /
            disabled / invalid，回填 default_value，并接上 stateChanged。
        """
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

    def create_checkbox(self, text: str, value: str | None = None) -> Checkbox:
        """便利方法：创建一个 Checkbox 并加入组。

        Args:
            text: 显示文字。
            value: 该选项的值；None 时由 Checkbox 自行决定。

        Returns:
            已加入组的新 Checkbox。
        """
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
        """子项状态变化回调：聚合已选值并发出信号。

        Args:
            _state: Qt stateChanged 的整数状态（未使用）。
        """
        vals = [cb.value() for cb in self._checkboxes if cb.isChecked()]
        self.value_changed.emit(vals)

    def value(self) -> list[str]:
        """返回当前已选值列表。

        Returns:
            所有 isChecked 子项的 value。
        """
        return [cb.value() for cb in self._checkboxes if cb.isChecked()]

    def set_value(self, values: list[str]):
        """按值列表批量设置子项勾选态。

        Args:
            values: 应被勾选的 value 集合。
        """
        for cb in self._checkboxes:
            cb.setChecked(cb.value() in values)

    # ------------------------------------------------------------
    # 动态 API
    # ------------------------------------------------------------
    def _broadcast(self, fn):
        """把操作广播到全部子 Checkbox。

        Args:
            fn: 接受单个 Checkbox 的可调用对象。
        """
        for cb in self._checkboxes:
            fn(cb)

    def set_color(self, color: str):
        """切换组级语义色并广播。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._broadcast(lambda c: c.set_color(color))

    def set_size(self, size: str):
        """切换组级尺寸并广播。

        Args:
            size: 尺寸档位名。
        """
        self._size = size
        self._broadcast(lambda c: c.set_size(size))

    def set_radius(self, radius: str | None):
        """切换组级圆角并广播。

        Args:
            radius: 圆角档位；None 恢复子项默认。
        """
        self._radius = radius
        self._broadcast(lambda c: c.set_radius(radius))

    def set_theme(self, theme: str):
        """切换主题并广播给全部子项。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
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
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._broadcast(lambda c: c._apply_provider_theme(theme))
        self._apply_styles()

    def set_line_through(self, enabled: bool):
        """切换选中文字删除线并广播。

        Args:
            enabled: True 启用删除线。
        """
        self._line_through = enabled
        self._broadcast(lambda c: c.set_line_through(enabled))

    def set_is_disabled(self, disabled: bool):
        """切换组级禁用并广播。

        Args:
            disabled: True 表示禁用全部子项。
        """
        self._is_disabled = disabled
        self._broadcast(lambda c: c.set_is_disabled(disabled))

    def set_is_invalid(self, invalid: bool):
        """切换组级错误态并广播，同时刷新 helper。

        Args:
            invalid: True 显示错误提示与红框。
        """
        self._is_invalid = invalid
        self._broadcast(lambda c: c.set_is_invalid(invalid))
        self._apply_styles()

    def set_is_required(self, required: bool):
        """切换必填星号。

        Args:
            required: True 时在 label 后加红色星号。
        """
        self._is_required = required
        self._apply_styles()

    def set_label(self, label: str):
        """更新组标签。

        Args:
            label: 新标签文本；空串时隐藏 label。
        """
        self._label_text = label
        self._apply_styles()

    def set_description(self, desc: str):
        """更新组描述。

        Args:
            desc: 新描述文本。
        """
        self._description = desc
        self._apply_styles()

    def set_error_message(self, msg: str):
        """更新错误提示文本。

        Args:
            msg: 新错误文本。
        """
        self._error_message = msg
        self._apply_styles()

    def set_orientation(self, orientation: str):
        """切换子项排列方向并重建布局。

        Args:
            orientation: vertical / horizontal；同值直接返回。

        Note:
            重建时先把子项从旧 layout 摘出、把旧 layout 挂到临时
            QWidget 上释放，再挂新 layout 并重新加入子项。
        """
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
