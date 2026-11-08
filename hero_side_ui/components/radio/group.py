"""RadioGroup 互斥单选组：统一下发样式并实现互斥，聚合 value_changed。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS
from ..text import Text
from ._base import RadioBase
from .radio import VALID_COLORS, VALID_SIZES, VALID_VARIANTS, Radio


class RadioGroup(QWidget):
    """单选组：统一管理子 Radio，value_changed 汇报当前 value。"""

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
        default_value: str | None = None,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """初始化单选组，校验样式参数并搭建界面。

        Args:
            label: 组标题文本。
            description: 辅助说明文本。
            error_message: 非法状态下显示的错误文本。
            orientation: 排列方向，vertical 或 horizontal。
            color: 颜色主题名。
            size: 尺寸名。
            variant: 变体名。
            is_disabled: 是否禁用整组。
            is_invalid: 是否显示非法状态。
            is_required: 是否在标题显示必填标记。
            default_value: 初始选中的 value。
            disable_animation: 是否关闭选中动画。
            theme: 主题模式，auto/light/dark。
            parent: Qt 父对象。

        Note:
            color、size、variant、orientation 取非法值时抛 ValueError；
            theme 为 auto 时注册到 ThemeProvider 以跟随系统主题。
        """
        super().__init__(parent)

        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}, got {size!r}")
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}, got {variant!r}")
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

        self._radios: list[RadioBase] = []
        self._suppress = False  # 互斥时防止 toggled 风暴

        self._setup_ui()
        self._apply_styles()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # UI
    # ============================================================
    def _setup_ui(self):
        """搭建根布局、标题、子项容器与辅助文本控件。"""
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
        """按主题与状态刷新标题及辅助文本的颜色和显隐。"""
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
        """添加一个 Radio，统一下发样式并接入互斥逻辑。

        Args:
            radio: 要加入组的单选控件。

        Note:
            注入 toggle_guard 使已选中项再次点击被忽略；
            default_value 命中时自动勾选该项。
        """
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
        radio.toggled.connect(lambda checked, r=radio: self._on_radio_toggled(r, checked))

        self._radios.append(radio)
        self._wrapper_layout.addWidget(radio)

    def create_radio(
        self,
        text: str,
        value: str | None = None,
        description: str = "",
    ) -> Radio:
        """创建 Radio 并按组样式配置后加入 group。

        Args:
            text: 显示文本。
            value: 选中时汇报的值。
            description: 辅助说明文本。

        Returns:
            新建并已加入组的 Radio。
        """
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
        """已选中时返回 True，供互斥守卫忽略重复点击。"""
        return radio.isChecked()

    def _on_radio_toggled(self, source: RadioBase, checked: bool):
        """处理子项选中事件，取消其他项并广播 value_changed。

        Args:
            source: 触发选中的单选控件。
            checked: 是否变为选中；未选中时直接忽略。

        Note:
            批量取消选中期间用 _suppress 抑制互斥回调递归。
        """
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
    def value(self) -> str | None:
        """返回当前选中项的 value。

        Returns:
            选中项的 value；无选中时返回 None。
        """
        for r in self._radios:
            if r.isChecked():
                return r.value()
        return None

    def set_value(self, value: str | None):
        """按 value 选中对应项并广播 value_changed。

        Args:
            value: 要选中的值；无匹配项时全部取消选中。

        Note:
            批量改选中期间用 _suppress 抑制互斥回调，结束后统一广播一次。
        """
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
        """对所有子 Radio 依次执行 fn。

        Args:
            fn: 接受单个 RadioBase 的回调。
        """
        for r in self._radios:
            fn(r)

    def set_color(self, color: str):
        """统一设置颜色并下发到各子项。

        Args:
            color: 颜色主题名，须为 VALID_COLORS 中的值。

        Note:
            非法 color 抛 ValueError。
        """
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        self._color = color
        self._broadcast(lambda r: r.set_color(color))

    def set_size(self, size: str):
        """统一设置尺寸并下发到各子项。

        Args:
            size: 尺寸名，须为 VALID_SIZES 中的值。

        Note:
            非法 size 抛 ValueError。
        """
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        self._size = size
        self._broadcast(lambda r: r.set_size(size))

    def set_variant(self, variant: str):
        """统一设置变体并下发到各子项。

        Args:
            variant: 变体名，须为 VALID_VARIANTS 中的值。

        Note:
            非法 variant 抛 ValueError。
        """
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        self._variant = variant
        self._broadcast(lambda r: r.set_variant(variant))

    def variant(self) -> str:
        """返回当前变体名。"""
        return self._variant

    def set_theme(self, theme: str):
        """切换主题模式并向子项广播。

        Args:
            theme: auto 时注册到 ThemeProvider，其余值作为固定主题下发。

        Note:
            由 auto 切到固定主题时会从 ThemeProvider 注销。
        """
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
        """响应 ThemeProvider 广播，向子项下发主题并重绘样式。"""
        self._theme = theme
        self._broadcast(lambda r: r._apply_provider_theme(theme))
        self._apply_styles()

    def set_is_disabled(self, disabled: bool):
        """统一设置禁用状态并下发到各子项。"""
        self._is_disabled = disabled
        self._broadcast(lambda r: r.set_is_disabled(disabled))

    def set_is_invalid(self, invalid: bool):
        """统一设置非法状态，下发到子项并刷新样式。"""
        self._is_invalid = invalid
        self._broadcast(lambda r: r.set_is_invalid(invalid))
        self._apply_styles()

    def set_is_required(self, required: bool):
        """设置必填标记并刷新样式。"""
        self._is_required = required
        self._apply_styles()

    def set_label(self, label: str):
        """设置组标题并刷新样式。"""
        self._label_text = label
        self._apply_styles()

    def set_description(self, desc: str):
        """设置辅助说明并刷新样式。"""
        self._description = desc
        self._apply_styles()

    def set_error_message(self, msg: str):
        """设置错误文本并刷新样式。"""
        self._error_message = msg
        self._apply_styles()

    def set_disable_animation(self, disable: bool):
        """统一下发是否关闭选中动画。"""
        self._disable_animation = disable
        self._broadcast(lambda r: r.set_disable_animation(disable))

    def set_orientation(self, orientation: str):
        """切换排列方向并重建子项容器布局。

        Args:
            orientation: vertical 或 horizontal。

        Note:
            非法 orientation 抛 ValueError；同值直接返回不重建；
            重建时仅从旧布局移除子项、不解除父子关系，避免 Windows 闪原生窗口框。
        """
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
