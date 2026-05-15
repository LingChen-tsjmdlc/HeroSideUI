"""HeroSideUI Input Component — 单行文本输入。

基于 HeroUI v2 设计，QLineEdit 派生（保留信号/槽兼容）。

子组件：
    - ``_LineEdit``  → ``_line_edit.py``
    - ``_ClearButton`` → ``_clear_button.py``
    - ``_InputWrapper`` → ``_wrapper.py``
"""

from PySide6.QtWidgets import QFrame, QPushButton

from typing import Callable, Optional

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import LabelFloatAnimation, UnderlineBar
from ...core import ThemeProvider
from ...themes import FONT_FAMILY, HEROUI_COLORS, INPUT_SIZES, RADIUS
from ...utils import hex_to_rgba, load_svg_icon

from ._clear_button import _ClearButton
from ._layout import _InputLayoutMixin
from ._line_edit import _LineEdit
from ._styling import _InputStylingMixin
from ._wrapper import _InputWrapper




# ============================================================
# Input 主体
# ============================================================
class Input(_InputStylingMixin, _InputLayoutMixin, QWidget):
    """HeroUI 风格的输入框组件

    特性：
    - 4 种变体 (flat / faded / bordered / underlined)
    - 6 种颜色 (default / primary / secondary / success / warning / danger)
    - 3 种尺寸 (sm / md / lg)
    - 4 种 label 位置 (inside / outside / outside-left / outside-top)
    - 支持 clear 按钮、start_content、end_content
    - 支持禁用、无效、必填、只读
    - 浮动 label 动画 (对齐 HeroUI 的 200ms ease-out)
    - underlined 变体下划线从中心展开动画
    - 亮暗双主题

    对外也暴露 line_edit 属性和常用代理方法（text/setText/textChanged 等），
    Qt 原生用法（setValidator/setEchoMode/setMaxLength）可通过 .line_edit 直接调用。

    用法:
        input = Input(label="Email", placeholder="you@example.com",
                      color="primary", variant="flat", size="md")
        input.text_changed.connect(lambda t: print(t))
    """

    # 代理信号（与 QLineEdit 对齐）
    text_changed = Signal(str)
    editing_finished = Signal()
    returned = Signal()
    cleared = Signal()

    def __init__(
        self,
        label: str = "",
        value: str = "",
        placeholder: str = "",
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
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
        parent: Optional[QWidget] = None,
    ):
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
        self.setObjectName("heroInput")

        # --- 根布局 ---
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        # --- outside label (仅 outside / outside-top 模式显示) ---
        self._outside_label = QLabel(self._label_text)
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
        self._outside_left_label = QLabel(self._label_text)
        self._outside_left_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._outside_left_label.setContentsMargins(0, 0, 0, 0)
        self._outside_left_label.setTextFormat(Qt.TextFormat.RichText)
        _row.addWidget(self._outside_left_label, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # --- inputWrapper (背景容器) ---
        self._wrapper = _InputWrapper()
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
        self._inside_label = QLabel(self._label_text, self)
        self._inside_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
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
        self._clear_btn = _ClearButton()
        self._clear_btn.hide()
        wrap_layout.addWidget(self._clear_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # underline bar（仅 underlined 变体显示，其他隐藏）
        # 用 child-widget 方式放在 wrapper 底部，通过 resizeEvent 摆放
        self._underline = UnderlineBar(parent=self._wrapper)
        self._underline.hide()

        _row.addWidget(self._wrapper, 1)

        self._root.addWidget(self._outside_left_row)

        # --- helper 区域 ---
        self._helper_label = QLabel("")
        self._helper_label.setWordWrap(True)
        self._helper_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
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
        # 点击 inputWrapper 任意位置让 line_edit 获得焦点
        self.line_edit.setFocus()
        QFrame.mousePressEvent(self._wrapper, event)

    def _on_text_changed(self, text: str):
        self._update_filled_state()
        self._update_label_animation()
        self.text_changed.emit(text)

    def _on_clear_clicked(self):
        self.line_edit.clear()
        self.line_edit.setFocus()
        self.cleared.emit()

    # ============================================================
    # 状态计算
    # ============================================================
    def _qcolor(self, s) -> QColor:
        """把各种颜色表示（hex/rgba()/transparent/QColor）转换为 QColor"""
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
        return bool(self._label_text)

    def _has_value(self) -> bool:
        return bool(self.line_edit.text())

    def _filled_within(self) -> bool:
        """对应 HeroUI 的 data-filled-within: 聚焦 或 有值 或 有占位符"""
        return (
            self._is_focused
            or self._has_value()
            or bool(self._placeholder)
            or bool(self._start_content)
        )

    def _update_filled_state(self):
        # 控制 clear 按钮显隐
        if self._is_clearable and not self._is_disabled and not self._is_readonly:
            self._clear_btn.set_visible(self._has_value())
        else:
            self._clear_btn.set_visible(False, animate=False)

    def _update_label_animation(self, animate: bool = True):
        """根据 filled_within 状态驱动浮动动画（inside 与 outside 都用）

        animate=False 用于构造期或无需动画的瞬切场景（避免初始显示时 label
        从中央飞到顶部的那一瞬和 placeholder 重叠）。
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
    def text(self) -> str:
        return self.line_edit.text()

    def set_text(self, text: str):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()

    def set_value(self, value: str):
        self.line_edit.setText(value)

    def set_placeholder(self, placeholder: str):
        self._placeholder = placeholder
        self.line_edit.setPlaceholderText(placeholder)
        self._update_label_animation()

    def set_label(self, label: str):
        self._label_text = label
        self._apply_styles()
        self._update_label_animation()

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: Optional[str]):
        self._radius = radius
        self._apply_styles()

    def set_label_placement(self, placement: str):
        self._label_placement = placement
        self._relayout_for_label_placement()
        self._apply_styles()
        self._update_label_animation()

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
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用——只更新实际主题，不改 _theme_mode"""
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._apply_styles()

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self._apply_styles()

    def set_is_required(self, required: bool):
        self._is_required = required
        self._apply_styles()

    def set_is_readonly(self, readonly: bool):
        self._is_readonly = readonly
        self.line_edit.setReadOnly(readonly)
        self._apply_styles()

    def set_is_clearable(self, clearable: bool):
        self._is_clearable = clearable
        self._apply_styles()
        self._update_filled_state()

    def set_description(self, description: str):
        self._description = description
        self._apply_styles()

    def set_error_message(self, message: str):
        self._error_message = message
        self._apply_styles()

    def set_start_content(self, content, on_click=None):
        """设置左侧内容。content 可以是字符串图标名/路径或任意 QWidget；
        字符串模式下传入 on_click 会将图标包成可点击按钮。"""
        self._start_content = content
        if on_click is not None:
            self._on_start_click = on_click
        self._apply_styles()

    def set_end_content(self, content, on_click=None):
        """设置右侧内容。content 可以是字符串图标名/路径或任意 QWidget；
        字符串模式下传入 on_click 会将图标包成可点击按钮。
        典型用途：密码框的眼睛切换 —— set_end_content('heroicons--eye-solid', on_click=toggle)
        """
        self._end_content = content
        if on_click is not None:
            self._on_end_click = on_click
        self._apply_styles()

    def set_on_start_content_click(self, callback):
        """单独更新左侧点击回调（content 保持不变）"""
        self._on_start_click = callback
        self._apply_styles()

    def set_on_end_content_click(self, callback):
        """单独更新右侧点击回调"""
        self._on_end_click = callback
        self._apply_styles()
