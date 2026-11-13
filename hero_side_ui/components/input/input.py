"""Input 单行输入组件；外框、清除按钮与样式决策来自 _shared.fields。"""

from PySide6.QtCore import (
    QEvent,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..._shared.fields import ClearButton, InputLayoutMixin, InputStylingMixin, InputWrapper
from ...animation import LabelFloatAnimation, UnderlineBar
from ...core import ThemeProvider
from ..text import Text
from ._line_edit import _LineEdit


# ============================================================
# Input 主体
# ============================================================
class Input(InputStylingMixin, InputLayoutMixin, QWidget):
    """HeroUI 风格输入框，内嵌 QLineEdit。

    四变体、六色、三尺寸、四 label 位置；start/end_content 与 clear 按钮；
    浮动 label 与下划线展开动画。原生 API 经 .line_edit 直调。
    """

    # 代理信号（与 QLineEdit 对齐）
    text_changed = Signal(str)
    editing_finished = Signal()
    returned = Signal()
    cleared = Signal()

    # QSS objectName；子类（如 NumberInput）可覆写
    _object_name = "heroInput"

    def __init__(
        self,
        label: str = "",
        value: str = "",
        placeholder: str = "",
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str | None = None,
        label_placement: str = "inside",
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        is_clearable: bool = False,
        full_width: bool = True,
        description: str = "",
        error_message: str = "",
        start_content=None,
        end_content=None,
        on_start_content_click=None,
        on_end_content_click=None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建单行输入框。

        Args:
            label: 标签文本。
            value: 初始文本。
            placeholder: 占位符。
            variant: flat / faded / bordered / underlined。
            color: 语义色。
            size: 尺寸档位。
            radius: 圆角档位；None 跟随尺寸默认。
            label_placement: inside / outside / outside-left / outside-top。
            is_disabled: 禁用。
            is_invalid: 错误态。
            is_required: 必填星号。
            is_readonly: 只读。
            is_clearable: 显示清除按钮。
            full_width: 是否横向撑满。
            description: 描述文本。
            error_message: 错误提示文本。
            start_content: 前置内容（图标名 / SVG 路径 / QWidget）。
            end_content: 后置内容（图标名 / SVG 路径 / QWidget）。
            on_start_content_click: 前置图标点击回调。
            on_end_content_click: 后置图标点击回调。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Note:
            label 初始浮起状态瞬切不走动画，避免与 placeholder 挤在一起；
            auto 注册会立即触发一次 _apply_provider_theme，但 palette.Base
            已在 _apply_styles 里设透明，不会复发「挖空」问题。
        """
        super().__init__(parent)

        # ---- 状态 ----
        self._label_text = label
        self._placeholder = placeholder
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._label_placement = label_placement
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_required = is_required
        self._is_readonly = is_readonly
        self._is_clearable = is_clearable
        self._full_width = full_width
        self._description = description
        self._error_message = error_message
        # start / end content: 可以是 str（图标名/路径）或任意 QWidget
        # on_*_click: 字符串图标时挂点击回调，会自动包成可点击按钮
        self._start_content = start_content
        self._end_content = end_content
        self._on_start_click = on_start_content_click
        self._on_end_click = on_end_content_click
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._is_hover = False
        self._is_focused = False

        # 用户是否显式接管了宽度（调用过 setFixedWidth/setMinimumWidth/
        # setMaximumWidth 或 set_width）。一旦置 True，_apply_styles() 不再
        # 用 size_config 的 min_width 覆盖用户宽度，避免点击/聚焦/setText 等
        # 触发的样式重算把 setFixedWidth(80) 这类硬约束悄悄涨破。
        self._user_width_locked = False

        self._setup_ui()
        self._bind_events()
        self._apply_styles()

        # 初始值
        if value:
            self.line_edit.setText(value)
        self._update_filled_state()
        # 初始化 label 浮起状态（瞬切，不走动画）——避免有 placeholder 时
        # 组件显示瞬间 label 还在中心和 placeholder 文字挤在一起
        self._update_label_animation(animate=False)

        # auto 模式：注册到 ThemeProvider
        # 注意：register() 会立即调一次 _apply_provider_theme()，但 Input 的
        # palette.Base = transparent 已经在 _apply_styles() 里设好；
        # _apply_provider_theme 重新走一遍 _apply_styles，会再次设置 palette
        # 保持透明，所以"挖空"问题不会复发（_apply_styles 已经在上面调过一次了）。
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # UI 结构
    # ============================================================
    def _setup_ui(self):
        """构建 Input 子控件树与布局。

        Note:
            创建 wrapper / line_edit / 浮动 label / 前后槽位 / 清除按钮 /
            下划线；内部 label 绝对定位，由 _apply_label_progress 动画驱动。
        """
        self.setObjectName(self._object_name)

        # --- 根布局 ---
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        # --- outside label (仅 outside / outside-top 模式显示) ---
        self._outside_label = Text(self._label_text, weight="medium", selectable=False)
        self._outside_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._outside_label.setContentsMargins(0, 0, 0, 0)
        self._outside_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._outside_label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._outside_label, 0, Qt.AlignmentFlag.AlignLeft)

        # --- outside-left 需要一个横向行：[label | inputWrapper] ---
        self._outside_left_row = QWidget()
        _row = QHBoxLayout(self._outside_left_row)
        _row.setContentsMargins(0, 0, 0, 0)
        _row.setSpacing(8)

        # outside-left label
        self._outside_left_label = Text(self._label_text, weight="medium", selectable=False)
        self._outside_left_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._outside_left_label.setContentsMargins(0, 0, 0, 0)
        self._outside_left_label.setTextFormat(Qt.TextFormat.RichText)
        _row.addWidget(
            self._outside_left_label,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )

        # --- inputWrapper (背景容器) ---
        self._wrapper = InputWrapper()
        self._wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        wrap_layout = QHBoxLayout(self._wrapper)
        wrap_layout.setContentsMargins(12, 6, 12, 6)
        wrap_layout.setSpacing(8)

        # start_content 槽位：容器，内部可放 icon QLabel 或任意 QWidget
        self._start_slot = QWidget()
        self._start_slot_layout = QHBoxLayout(self._start_slot)
        self._start_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._start_slot_layout.setSpacing(0)
        self._start_slot.hide()
        wrap_layout.addWidget(self._start_slot, 0, Qt.AlignmentFlag.AlignVCenter)

        # innerWrapper: 浮动 label + line_edit
        self._inner = QWidget()
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # inner 用 Qt 默认布局，但 label 是绝对定位（手动 setGeometry）
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

        # 浮动 label（覆盖在 line_edit 上方，手动定位）
        # parent 设为 self（Input 根），这样在 outside 模式下可以飞出 inputWrapper 到达 Input 顶部
        # 文字颜色由 _layout._apply_label_progress() 动画插值后用 RichText <span> 覆写，
        # Text 本身的 set_color 不介入 inside-label 的动画路径。
        self._inside_label = Text(self._label_text, parent=self, selectable=False)
        self._inside_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._inside_label.setContentsMargins(0, 0, 0, 0)
        self._inside_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._inside_label.raise_()

        # 真正的输入框
        self.line_edit = _LineEdit()
        self.line_edit.setPlaceholderText(self._placeholder)
        if self._is_readonly:
            self.line_edit.setReadOnly(True)
        self._inner_layout.addWidget(self.line_edit)

        wrap_layout.addWidget(self._inner, 1)

        # end_content 槽位
        self._end_slot = QWidget()
        self._end_slot_layout = QHBoxLayout(self._end_slot)
        self._end_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._end_slot_layout.setSpacing(0)
        self._end_slot.hide()
        wrap_layout.addWidget(self._end_slot, 0, Qt.AlignmentFlag.AlignVCenter)

        # clear 按钮
        self._clear_btn = ClearButton()
        self._clear_btn.hide()
        wrap_layout.addWidget(self._clear_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # underline bar（仅 underlined 变体显示，其他隐藏）
        # 用 child-widget 方式放在 wrapper 底部，通过 resizeEvent 摆放
        self._underline = UnderlineBar(parent=self._wrapper)
        self._underline.hide()

        _row.addWidget(self._wrapper, 1)

        self._root.addWidget(self._outside_left_row)

        # --- helper 区域 ---
        self._helper_label = Text("", weight="normal", selectable=False)
        self._helper_label.setWordWrap(True)
        self._helper_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._helper_label.hide()
        self._root.addWidget(self._helper_label)

        # --- label 浮动动画 ---
        self._label_anim = LabelFloatAnimation(
            on_progress=self._on_label_progress,
            duration=200,
        )

        # --- 静态 label 颜色（动画时插值需要记住起止色）---
        self._label_color_resting = QColor("#a1a1aa")
        self._label_color_floated = QColor("#71717a")

        # 适配不同 label placement 的显示/隐藏
        self._relayout_for_label_placement()

    # ============================================================
    # 事件绑定
    # ============================================================
    def _bind_events(self):
        """连接 line_edit 信号、焦点与悬浮事件过滤器，以及 wrapper 点击聚焦。

        Note:
            wrapper 的 mousePressEvent 被替换为 _on_wrapper_clicked 以转发焦点。
        """
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.editingFinished.connect(self.editing_finished.emit)
        self.line_edit.returnPressed.connect(self.returned.emit)
        self._clear_btn.clicked.connect(self._on_clear_clicked)

        # 焦点事件（通过事件过滤器捕获）
        self.line_edit.installEventFilter(self)
        # hover 事件在 wrapper 上
        self._wrapper.installEventFilter(self)
        self._wrapper.setMouseTracking(True)

        # 点击 wrapper 区域聚焦到 line_edit
        self._wrapper.mousePressEvent = self._on_wrapper_clicked

        # inside label 点击也应聚焦
        self._inside_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        """拦截 line_edit 焦点、wrapper 悬浮与 inside_label 点击。

        Args:
            obj: 被监视的对象。
            event: 当前事件。

        Returns:
            bool: 已处理返回 True，否则交给父类。
        """
        if obj is self.line_edit:
            if event.type() == QEvent.Type.FocusIn:
                self._is_focused = True
                self._update_label_animation()
                self._apply_styles()
                if self._variant == "underlined":
                    self._underline.expand()
            elif event.type() == QEvent.Type.FocusOut:
                self._is_focused = False
                self._update_label_animation()
                self._apply_styles()
                if self._variant == "underlined":
                    self._underline.collapse()
        elif obj is self._wrapper:
            if event.type() == QEvent.Type.Enter:
                self._is_hover = True
                self._apply_styles()
            elif event.type() == QEvent.Type.Leave:
                self._is_hover = False
                self._apply_styles()
        elif obj is self._inside_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.line_edit.setFocus()
                return True
        return super().eventFilter(obj, event)

    def _on_wrapper_clicked(self, event):
        """点击 wrapper 任意位置把焦点交给 line_edit。

        Args:
            event: 鼠标按下事件。
        """
        # 点击 inputWrapper 任意位置让 line_edit 获得焦点
        self.line_edit.setFocus()
        QFrame.mousePressEvent(self._wrapper, event)

    def _on_text_changed(self, text: str):
        """文本变化回调。

        Args:
            text: 变化后的文本。
        """
        self._update_filled_state()
        self._update_label_animation()
        self.text_changed.emit(text)

    def _on_clear_clicked(self):
        """清除按钮点击处理。

        Note:
            清空 line_edit 文本、重新聚焦，并发射 cleared 信号。
        """
        self.line_edit.clear()
        self.line_edit.setFocus()
        self.cleared.emit()

    # ============================================================
    # 状态计算
    # ============================================================
    def _qcolor(self, s) -> QColor:
        """把颜色表示转换为 QColor。

        Args:
            s: 颜色值，支持 hex / rgba() / transparent / QColor。

        Returns:
            QColor: 转换后的颜色；无效值返回全透明黑。
        """
        if isinstance(s, QColor):
            return QColor(s)
        if s is None or s == "" or s == "transparent":
            return QColor(0, 0, 0, 0)
        s = s.strip()
        if s.startswith("rgba"):
            # rgba(r, g, b, a)
            inner = s[s.index("(") + 1 : s.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            r = int(float(parts[0]))
            g = int(float(parts[1]))
            b = int(float(parts[2]))
            a = int(float(parts[3]) * 255) if len(parts) == 4 else 255
            return QColor(r, g, b, a)
        # hex 或颜色名
        c = QColor(s)
        if not c.isValid():
            return QColor(0, 0, 0, 0)
        return c

    def _has_label(self) -> bool:
        """是否有标签文本。

        Returns:
            bool: 标签文本非空时为 True。
        """
        return bool(self._label_text)

    def _has_value(self) -> bool:
        """line_edit 当前是否非空。

        Returns:
            bool: 文本非空时为 True。
        """
        return bool(self.line_edit.text())

    def _filled_within(self) -> bool:
        """当前是否处于 filled-within 状态（驱动 label 浮起）。

        Returns:
            bool: 聚焦、有值、有占位符或前导内容时为真。
        """
        return (
            self._is_focused
            or self._has_value()
            or bool(self._placeholder)
            or bool(self._start_content)
        )

    def _update_filled_state(self):
        """刷新清除按钮显隐。

        Note:
            clearable 且非禁用、非只读时按当前是否有值显隐清除按钮。
        """
        # 控制 clear 按钮显隐
        if self._is_clearable and not self._is_disabled and not self._is_readonly:
            self._clear_btn.set_visible(self._has_value())
        else:
            self._clear_btn.set_visible(False, animate=False)

    def _update_label_animation(self, animate: bool = True):
        """按 filled_within 状态驱动浮动 label 动画。

        Args:
            animate: False 用于初始瞬切，不走补间。
        """
        if self._label_placement not in ("inside", "outside"):
            return
        if not self._has_label():
            return

        should_float = self._filled_within()
        self._label_anim.set_state(should_float, animate=animate)

    # ============================================================
    # 公共 API
    # ============================================================
    def is_readonly(self) -> bool:
        """返回当前是否只读。"""
        return self._is_readonly

    def click_targets(self) -> tuple[QWidget, ...]:
        """返回构成输入框点击区域的控件，供外部统一监听鼠标事件。

        Returns:
            原生输入框、外框与内置浮动标签。
        """
        return (self.line_edit, self._wrapper, self._inside_label)

    def refresh_filled_state(self, animate: bool = True):
        """按当前文本刷新清除按钮与浮动标签，供外部直接写入文本后调用。

        Args:
            animate: False 时标签直接就位，不播放过渡。
        """
        self._update_filled_state()
        self._update_label_animation(animate=animate)

    def text(self) -> str:
        """返回当前文本。

        Returns:
            str: line_edit 的当前文本。
        """
        return self.line_edit.text()

    def set_text(self, text: str):
        """设置文本。

        Args:
            text: 要设置的文本。
        """
        self.line_edit.setText(text)

    def clear(self):
        """清空文本。

        Note:
            等价于 line_edit.clear()，并触发 filled 状态刷新。
        """
        self.line_edit.clear()

    def set_value(self, value: str):
        """设置输入框的值（文本）。

        Args:
            value: 要设置的文本。
        """
        self.line_edit.setText(value)

    def set_placeholder(self, placeholder: str):
        """设置占位符文本。

        Args:
            placeholder: 占位提示文本。

        Note:
            占位符变化会触发 label 浮起状态刷新。
        """
        self._placeholder = placeholder
        self.line_edit.setPlaceholderText(placeholder)
        self._update_label_animation()

    def set_label(self, label: str):
        """设置标签文本。

        Args:
            label: 新标签文本。

        Note:
            会重算样式与 label 浮起状态。
        """
        self._label_text = label
        self._apply_styles()
        self._update_label_animation()

    def set_color(self, color: str):
        """设置语义色。

        Args:
            color: 语义色名称（如 default / primary / danger）。

        Note:
            仅接受校验过的色值，非法值被忽略。
        """
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        """设置外观变体。

        Args:
            variant: flat / faded / bordered / underlined。
        """
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        """设置尺寸档位。

        Args:
            size: 尺寸名称（sm / md / lg 等）。
        """
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: str | None):
        """设置圆角档位。

        Args:
            radius: 圆角名称；None 跟随尺寸默认。
        """
        self._radius = radius
        self._apply_styles()

    # ============================================================
    # 宽度接管：用户一旦显式设宽，_apply_styles 就不再覆盖
    # ============================================================
    def setFixedWidth(self, w: int):
        """拦截原生 setFixedWidth：标记用户接管宽度。

        Args:
            w: 固定宽度（像素）。

        Note:
            标记后 _apply_styles 不再覆盖，并立即重算释放 wrapper 守卫。
        """
        self._user_width_locked = True
        super().setFixedWidth(w)
        # 立即让 wrapper 的 min_width 守卫释放，否则 wrapper 仍守
        # 构造期写入的 260，导致 chevron 被推出 Input 视口
        self._apply_styles()

    def setMinimumWidth(self, w: int):
        """拦截原生 setMinimumWidth：标记用户接管宽度。

        Args:
            w: 最小宽度（像素）。

        Note:
            标记后 _apply_styles 不再用尺寸 token 覆盖，并立即重算。
        """
        self._user_width_locked = True
        super().setMinimumWidth(w)
        self._apply_styles()

    def setMaximumWidth(self, w: int):
        """拦截原生 setMaximumWidth：标记用户接管宽度。

        Args:
            w: 最大宽度（像素）。

        Note:
            标记后 _apply_styles 不再用尺寸 token 覆盖，并立即重算。
        """
        self._user_width_locked = True
        super().setMaximumWidth(w)
        self._apply_styles()

    def set_width(self, w: int):
        """高层宽度接管 API。

        Args:
            w: 固定宽度（像素）。

        Note:
            等价于 setFixedWidth，推荐用这个接管 Input 宽度。
        """
        self.setFixedWidth(w)

    def set_label_placement(self, placement: str):
        """设置标签位置。

        Args:
            placement: inside / outside / outside-left / outside-top。

        Note:
            会重排 label 布局、重算样式并刷新浮起状态。
        """
        self._label_placement = placement
        self._relayout_for_label_placement()
        self._apply_styles()
        self._update_label_animation()

    def set_theme(self, theme: str):
        """设置主题。

        Args:
            theme: auto / light / dark。auto 注册 ThemeProvider 跟随全局。

        Note:
            light/dark 会注销 auto 注册，硬锁主题。
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
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播回调。

        Args:
            theme: 广播下发的实际主题（light/dark）。

        Note:
            只更新实际主题，不改 _theme_mode 注册状态。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """将主题模式解析为实际 light 或 dark。

        Args:
            mode: 主题模式字符串。

        Returns:
            str: "light" 或 "dark"。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_disabled(self, disabled: bool):
        """设置禁用态。

        Args:
            disabled: 是否禁用。
        """
        self._is_disabled = disabled
        self._apply_styles()

    def set_is_invalid(self, invalid: bool):
        """设置错误态。

        Args:
            invalid: 是否进入错误态（影响边框/文字/helper 配色）。
        """
        self._is_invalid = invalid
        self._apply_styles()

    def set_is_required(self, required: bool):
        """设置必填态（显示星号）。

        Args:
            required: 是否必填。
        """
        self._is_required = required
        self._apply_styles()

    def set_is_readonly(self, readonly: bool):
        """设置只读态。

        Args:
            readonly: 是否只读。

        Note:
            会同步 line_edit 的只读属性。
        """
        self._is_readonly = readonly
        self.line_edit.setReadOnly(readonly)
        self._apply_styles()

    def set_is_clearable(self, clearable: bool):
        """设置是否显示清除按钮。

        Args:
            clearable: 是否可清除。

        Note:
            改变后立即刷新清除按钮显隐。
        """
        self._is_clearable = clearable
        self._apply_styles()
        self._update_filled_state()

    def set_description(self, description: str):
        """设置描述文本。

        Args:
            description: 描述文本。
        """
        self._description = description
        self._apply_styles()

    def set_error_message(self, message: str):
        """设置错误提示文本。

        Args:
            message: 错误提示文本。
        """
        self._error_message = message
        self._apply_styles()

    def set_start_content(self, content, on_click=None):
        """设置左侧（前导）内容。

        Args:
            content: 图标名 / SVG 路径字符串，或任意 QWidget。
            on_click: 字符串模式下挂点击回调，自动包成可点击按钮。
        """
        self._start_content = content
        if on_click is not None:
            self._on_start_click = on_click
        self._apply_styles()

    def set_end_content(self, content, on_click=None):
        """设置右侧（后导）内容。

        Args:
            content: 图标名 / SVG 路径字符串，或任意 QWidget。
            on_click: 字符串模式下挂点击回调，自动包成可点击按钮。

        Note:
            典型用途：密码框眼睛切换
            set_end_content('heroicons--eye-solid', on_click=toggle)。
        """
        self._end_content = content
        if on_click is not None:
            self._on_end_click = on_click
        self._apply_styles()

    def set_on_start_content_click(self, callback):
        """单独更新左侧点击回调。

        Args:
            callback: 点击回调，content 保持不变。
        """
        self._on_start_click = callback
        self._apply_styles()

    def set_on_end_content_click(self, callback):
        """单独更新右侧点击回调。

        Args:
            callback: 点击回调，content 保持不变。
        """
        self._on_end_click = callback
        self._apply_styles()
