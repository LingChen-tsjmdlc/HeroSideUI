"""HeroSideUI Textarea Component — 多行文本输入。

子组件：
    - ``_TextEdit``  → ``_text_edit.py``
    - ``_ResizeGrip`` → ``_resize_grip.py``
"""

from PySide6.QtWidgets import QPushButton

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

from ...animation import LabelFloatAnimation
from ...core import ScrollStyle, SmoothScroll, ThemeProvider
from ...themes import FONT_FAMILY, HEROUI_COLORS, RADIUS, TEXTAREA_SIZES
from ...utils import hex_to_rgba, load_svg_icon

from ..input._clear_button import _ClearButton
from ..input._wrapper import _InputWrapper

from ._autosize import _TextareaAutosizeMixin
from ._layout import _TextareaLayoutMixin
from ._resize_grip import _ResizeGrip
from ._styling import _TextareaStylingMixin
from ._text_edit import _TextEdit




# ============================================================
# Textarea 主体
# ============================================================
class Textarea(
    _TextareaStylingMixin,
    _TextareaLayoutMixin,
    _TextareaAutosizeMixin,
    QWidget,
):
    """HeroUI 风格的多行输入框组件

    特性：
    - 3 种变体 (flat / faded / bordered)，**不支持 underlined**
    - 6 种颜色 (default / primary / secondary / success / warning / danger)
    - 3 种尺寸 (sm / md / lg)
    - 4 种 label 位置 (inside / outside / outside-left / outside-top)
    - 支持 clear 按钮、top_right / center_right / bottom_right 三个内容槽
    - 支持禁用、无效、必填、只读
    - **auto-resize**: 内容驱动高度，[min_rows, max_rows] 范围内自动伸缩；
      超过 max_rows 出现滚动条
    - disable_autosize=True 时高度固定在 min_rows
    - 浮动 label 动画 (200ms ease-out)
    - 亮暗双主题

    用法:
        ta = Textarea(label="Description", placeholder="Tell us a bit about yourself...",
                      min_rows=3, max_rows=8, color="primary")
        ta.text_changed.connect(lambda t: print(t))

    底层 QTextEdit 通过 .text_edit 属性暴露，可直接调用 Qt 原生 API。
    """

    # 信号（与 HeroUI Textarea 对齐）
    text_changed = Signal(str)        # onValueChange
    cleared = Signal()                 # onClear
    height_changed = Signal(int, int)  # onHeightChange(height, row_height)
    focus_in = Signal()
    focus_out = Signal()

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
        min_rows: int = 3,
        max_rows: int = 8,
        disable_autosize: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        is_clearable: bool = False,
        full_width: bool = True,
        resizable=False,    # 用户能否手动拖动 grip 改变高度。默认 False（与 HeroUI 风格保持简洁）；可选: True/"vertical"/"horizontal"/"both"
        description: str = "",
        error_message: str = "",
        # ---- 三槽内容 API（绝对定位 + layout 混合实现）----
        # top_right_content: wrapper 右上角（layout 内 AlignTop）
        # center_right_content: wrapper 垂直居中（绝对定位，随高度实时居中）
        # bottom_right_content: wrapper 右下角（绝对定位，距右/底 = bottom_right_offset）
        top_right_content=None,
        center_right_content=None,
        bottom_right_content=None,
        on_top_right_content_click=None,
        on_center_right_content_click=None,
        on_bottom_right_content_click=None,
        bottom_right_offset=(8, 8),   # (right_px, bottom_px) —— 类似 Tailwind absolute right-X bottom-X
        center_right_offset=8,         # 距 wrapper 右边的像素
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---- 校验 variant ----
        if variant == "underlined":
            # HeroUI Textarea 没有 underlined，静默降级到 flat
            variant = "flat"

        # ---- 状态 ----
        self._label_text = label
        self._placeholder = placeholder
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._label_placement = label_placement
        self._min_rows = max(1, int(min_rows))
        self._max_rows = max(self._min_rows, int(max_rows))
        self._disable_autosize = disable_autosize
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_required = is_required
        self._is_readonly = is_readonly
        self._is_clearable = is_clearable
        self._full_width = full_width
        # ---- 手动 resize ----
        # resizable: True/False/"vertical"/"horizontal"/"both"
        self._resize_mode = self._normalize_resize(resizable)
        self._manual_height: Optional[int] = None  # 用户拖动设置的目标高度（None = 走 auto-resize）
        self._description = description
        self._error_message = error_message
        self._top_right_content = top_right_content
        self._center_right_content = center_right_content
        self._bottom_right_content = bottom_right_content
        self._on_top_right_click = on_top_right_content_click
        self._on_center_right_click = on_center_right_content_click
        self._on_bottom_right_click = on_bottom_right_content_click
        self._bottom_right_offset = bottom_right_offset
        self._center_right_offset = center_right_offset
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._is_hover = False
        self._is_focused = False

        # 上一次发出的高度，用于触发 height_changed
        self._last_emitted_height = -1
        # 缓存上次计算的 row_height
        self._cached_row_height = 0

        self._setup_ui()
        self._bind_events()
        self._apply_styles()

        # 初始值（先设值，再算高度）
        if value:
            self.text_edit.setPlainText(value)
        self._update_filled_state()
        self._update_label_animation(animate=False)
        # 初始计算一次高度
        self._update_textarea_height()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        # 平滑滚动 —— Qt 默认整行跳跃太生硬，attach 后变成丝滑过渡
        try:
            from ...core import SmoothScroll
            SmoothScroll.attach(self.text_edit)
        except Exception:
            pass

    @staticmethod
    def _normalize_resize(value) -> Optional[str]:
        """把 resizable 参数转成内部字符串 mode

        True / "vertical" / "v" → "vertical"
        "horizontal" / "h" → "horizontal"
        "both" / "all" → "both"
        False / None / "none" → None
        """
        if value is False or value is None:
            return None
        if value is True:
            return "vertical"
        if isinstance(value, str):
            v = value.lower().strip()
            if v in ("vertical", "v", "y"):
                return "vertical"
            if v in ("horizontal", "h", "x"):
                return "horizontal"
            if v in ("both", "all", "xy", "yx"):
                return "both"
            if v in ("none", "false", "off"):
                return None
        return "vertical"  # 兜底

    # ============================================================
    # UI 结构
    # ============================================================
    def _setup_ui(self):
        self.setObjectName("heroTextarea")

        # --- 根布局 ---
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        # --- outside-top label ---
        self._outside_label = QLabel(self._label_text)
        self._outside_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._outside_label.setContentsMargins(0, 0, 0, 0)
        self._outside_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._outside_label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._outside_label, 0, Qt.AlignmentFlag.AlignLeft)

        # --- outside-left 行 ---
        self._outside_left_row = QWidget()
        _row = QHBoxLayout(self._outside_left_row)
        _row.setContentsMargins(0, 0, 0, 0)
        _row.setSpacing(8)

        self._outside_left_label = QLabel(self._label_text)
        self._outside_left_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._outside_left_label.setContentsMargins(0, 0, 0, 0)
        self._outside_left_label.setTextFormat(Qt.TextFormat.RichText)
        # outside-left 时，label 与 textarea 顶部对齐（多行场景）
        _row.addWidget(self._outside_left_label, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # --- inputWrapper ---
        self._wrapper = _InputWrapper()
        self._wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        wrap_layout = QHBoxLayout(self._wrapper)
        wrap_layout.setContentsMargins(12, 8, 12, 8)
        wrap_layout.setSpacing(8)

        # innerWrapper
        self._inner = QWidget()
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

        # 浮动 label —— parent 是 self（Input 根），手动定位
        self._inside_label = QLabel(self._label_text, self)
        self._inside_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._inside_label.setContentsMargins(0, 0, 0, 0)
        self._inside_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._inside_label.raise_()

        # 真正的多行输入控件
        self.text_edit = _TextEdit()
        self.text_edit.setPlaceholderText(self._placeholder)
        if self._is_readonly:
            self.text_edit.setReadOnly(True)
        self._inner_layout.addWidget(self.text_edit)

        wrap_layout.addWidget(self._inner, 1)

        # ============================================================
        # 占位 spacer：给绝对定位的 center_right / bottom_right 槽
        # 让出右侧空间，避免文字 wrap 时撞到按钮
        # 宽度由 _apply_styles → _refresh_abs_spacer_width() 动态计算
        # ============================================================
        self._abs_spacer = QWidget()
        self._abs_spacer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._abs_spacer.setFixedWidth(0)  # 默认 0，无内容时不占位
        wrap_layout.addWidget(self._abs_spacer, 0)

        # ============================================================
        # 三个位置槽（完全替换旧的 start/end/end_right 设计）
        # ============================================================
        # top_right_slot：wrapper 右上角（layout 内 AlignTop）
        # 典型用途：清除/关闭按钮、字数计数器、字符数徽章
        self._top_right_slot = QWidget()
        self._top_right_slot_layout = QHBoxLayout(self._top_right_slot)
        self._top_right_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._top_right_slot_layout.setSpacing(4)
        self._top_right_slot.hide()
        wrap_layout.addWidget(self._top_right_slot, 0, Qt.AlignmentFlag.AlignTop)

        # clear 按钮：始终在 top_right_slot **之后**（外侧），便于和 top_right_content 共存
        self._clear_btn = _ClearButton()
        self._clear_btn.hide()
        wrap_layout.addWidget(self._clear_btn, 0, Qt.AlignmentFlag.AlignTop)

        # ============================================================
        # 以下两个槽用绝对定位（parent = _wrapper），resizeEvent 实时重算位置
        # 这样可以真正贴"右下角"和"垂直居中"，不受 wrapper 内部 layout 影响
        # ============================================================
        # center_right：wrapper 垂直居中（随 wrapper 高度变化实时居中）
        self._center_right_holder = QWidget(self._wrapper)
        _crl = QHBoxLayout(self._center_right_holder)
        _crl.setContentsMargins(0, 0, 0, 0)
        _crl.setSpacing(0)
        self._center_right_slot_layout = _crl
        self._center_right_holder.hide()
        self._center_right_holder.raise_()

        # bottom_right：wrapper 右下角（类似 Tailwind 的 absolute right-X bottom-X）
        self._bottom_right_holder = QWidget(self._wrapper)
        _brl = QHBoxLayout(self._bottom_right_holder)
        _brl.setContentsMargins(0, 0, 0, 0)
        _brl.setSpacing(0)
        self._bottom_right_slot_layout = _brl
        self._bottom_right_holder.hide()
        self._bottom_right_holder.raise_()

        # ============================================================
        # Resize Grip：右下角小手柄（绝对定位 wrapper 的 child）
        # 默认显示，resizable=False 时隐藏
        # ============================================================
        self._resize_grip = _ResizeGrip(
            mode=self._resize_mode or "vertical",
            parent=self._wrapper,
        )
        self._resize_grip.drag_delta.connect(self._on_grip_drag)
        if self._resize_mode is None:
            self._resize_grip.hide()
        else:
            self._resize_grip.show()
            self._resize_grip.raise_()

        # 监听 wrapper resize，用于重新定位 center/bottom holder + grip
        self._wrapper.installEventFilter(self)

        _row.addWidget(self._wrapper, 1)
        self._root.addWidget(self._outside_left_row)

        # --- helper ---
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

        # label 颜色（动画插值起止）
        self._label_color_resting = QColor("#a1a1aa")
        self._label_color_floated = QColor("#71717a")

        self._relayout_for_label_placement()

    # ============================================================
    # 事件绑定
    # ============================================================
    def _bind_events(self):
        self.text_edit.textChanged.connect(self._on_text_changed)
        self._clear_btn.clicked.connect(self._on_clear_clicked)

        # 焦点事件
        self.text_edit.installEventFilter(self)
        # hover 事件
        self._wrapper.installEventFilter(self)
        self._wrapper.setMouseTracking(True)

        # 点击 wrapper 区域聚焦到 text_edit
        self._wrapper.mousePressEvent = self._on_wrapper_clicked

        # inside label 点击聚焦
        self._inside_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.text_edit:
            if event.type() == QEvent.Type.FocusIn:
                self._is_focused = True
                self._update_label_animation()
                self._apply_styles()
                self.focus_in.emit()
            elif event.type() == QEvent.Type.FocusOut:
                self._is_focused = False
                self._update_label_animation()
                self._apply_styles()
                self.focus_out.emit()
        elif obj is self._wrapper:
            if event.type() == QEvent.Type.Enter:
                self._is_hover = True
                self._apply_styles()
            elif event.type() == QEvent.Type.Leave:
                self._is_hover = False
                self._apply_styles()
            elif event.type() == QEvent.Type.Resize:
                # wrapper 尺寸变化 → 重摆 center_right / bottom_right 绝对定位槽
                self._reposition_absolute_holders()
        elif obj is self._inside_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.text_edit.setFocus()
                return True
        return super().eventFilter(obj, event)

    def _on_wrapper_clicked(self, event):
        self.text_edit.setFocus()

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        self._update_filled_state()
        self._update_label_animation()
        self._update_textarea_height()
        self.text_changed.emit(text)

    def _on_clear_clicked(self):
        self.text_edit.clear()
        self.text_edit.setFocus()
        self.cleared.emit()

    # ============================================================
    # 状态计算
    # ============================================================
    def _qcolor(self, s) -> QColor:
        if isinstance(s, QColor):
            return QColor(s)
        if s is None or s == "" or s == "transparent":
            return QColor(0, 0, 0, 0)
        s = s.strip()
        if s.startswith("rgba"):
            inner = s[s.index("(") + 1 : s.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            r = int(float(parts[0])); g = int(float(parts[1])); b = int(float(parts[2]))
            a = int(float(parts[3]) * 255) if len(parts) == 4 else 255
            return QColor(r, g, b, a)
        c = QColor(s)
        return c if c.isValid() else QColor(0, 0, 0, 0)

    def _has_label(self) -> bool:
        return bool(self._label_text)

    def _has_value(self) -> bool:
        return bool(self.text_edit.toPlainText())

    def _filled_within(self) -> bool:
        """Textarea 的特殊语义：label 始终保持浮起状态

        不同于 Input（单行）——单行没值时 label 停在中线装作 placeholder 比较合理；
        多行场景下输入区本身就有一大片空白，让 label 停在文本第一行中间装 placeholder
        视觉很奇怪（下面一大片空没东西）。所以：**Textarea 的 label 始终浮起**，
        等价于"永远当作有 placeholder"——保留聚焦/值/placeholder/start_content 的信号
        不影响外部逻辑，但浮起条件直接置 True。
        """
        return True

    def _update_filled_state(self):
        if self._is_clearable and not self._is_disabled and not self._is_readonly:
            self._clear_btn.set_visible(self._has_value())
        else:
            self._clear_btn.set_visible(False, animate=False)

    def _update_label_animation(self, animate: bool = True):
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
        return self.text_edit.toPlainText()

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)

    def clear(self):
        self.text_edit.clear()

    def set_value(self, value: str):
        self.text_edit.setPlainText(value)

    def set_placeholder(self, placeholder: str):
        self._placeholder = placeholder
        self.text_edit.setPlaceholderText(placeholder)
        self._update_label_animation()

    def set_label(self, label: str):
        self._label_text = label
        self._apply_styles()
        self._update_label_animation()

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        if variant == "underlined":
            variant = "flat"
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

    def set_min_rows(self, rows: int):
        self._min_rows = max(1, int(rows))
        if self._max_rows < self._min_rows:
            self._max_rows = self._min_rows
        self._update_textarea_height()

    def set_max_rows(self, rows: int):
        self._max_rows = max(self._min_rows, int(rows))
        self._update_textarea_height()

    def set_disable_autosize(self, disabled: bool):
        self._disable_autosize = disabled
        self._update_textarea_height()

    def set_resizable(self, value):
        """开关/切换手动 grip 拖动

        Args:
            value: True/False/"vertical"/"horizontal"/"both"
                   - True 等同 "vertical"
                   - False 隐藏 grip 并清除 manual_height（恢复 auto-resize）
        """
        new_mode = self._normalize_resize(value)
        self._resize_mode = new_mode
        if new_mode is None:
            self._resize_grip.hide()
            self._manual_height = None
            self._update_textarea_height()
        else:
            self._resize_grip.set_mode(new_mode)
            self._resize_grip.show()
            self._reposition_absolute_holders()

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
        self.text_edit.setReadOnly(readonly)
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

    def set_top_right_content(self, content, on_click=None):
        """设置 wrapper 右上角内容（layout 内 AlignTop）

        典型用途: 字数徽章、字符计数器、关闭按钮。
        与内置的 clear 按钮共存——clear 在 top_right_content 的外侧（更靠右）。
        """
        self._top_right_content = content
        if on_click is not None:
            self._on_top_right_click = on_click
        self._apply_styles()

    def set_center_right_content(self, content, on_click=None):
        """设置 wrapper 垂直居中（右侧）内容（绝对定位，随 wrapper 高度实时居中）

        典型用途: 始终垂直居中的发送按钮、确认按钮。
        """
        self._center_right_content = content
        if on_click is not None:
            self._on_center_right_click = on_click
        self._apply_styles()

    def set_bottom_right_content(self, content, on_click=None):
        """设置 wrapper 右下角内容（绝对定位，类似 Tailwind absolute right-X bottom-X）

        典型用途: 多行 Chat 风格的发送按钮、提交按钮。
        距右/底偏移由 `bottom_right_offset=(right_px, bottom_px)` 控制（默认 (8, 8)）。
        """
        self._bottom_right_content = content
        if on_click is not None:
            self._on_bottom_right_click = on_click
        self._apply_styles()

    def set_on_top_right_content_click(self, callback):
        self._on_top_right_click = callback
        self._apply_styles()

    def set_on_center_right_content_click(self, callback):
        self._on_center_right_click = callback
        self._apply_styles()

    def set_on_bottom_right_content_click(self, callback):
        self._on_bottom_right_click = callback
        self._apply_styles()

    def set_bottom_right_offset(self, right_px: int, bottom_px: int):
        self._bottom_right_offset = (int(right_px), int(bottom_px))
        self._reposition_absolute_holders()

    def set_center_right_offset(self, right_px: int):
        self._center_right_offset = int(right_px)
        self._reposition_absolute_holders()
