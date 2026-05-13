"""
HeroSideUI Textarea Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://v2.heroui.com/docs/components/textarea
样式逻辑: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/input.ts

结构:
    Textarea (QWidget 容器)
        └── mainWrapper (V)
              ├── outside label (仅 outside-top 模式)
              ├── inputWrapper (QFrame, 绘制背景/边框/圆角)
              │     ├── [layout] innerWrapper (V)
              │     │             ├── inside/outside label (浮动)
              │     │             └── _TextEdit (多行)
              │     ├── [layout] top_right_slot (右上角，AlignTop)
              │     ├── [layout] clear_btn (右上角，AlignTop，外侧)
              │     ├── [absolute] center_right_holder (垂直居中，绝对定位)
              │     └── [absolute] bottom_right_holder (右下角，绝对定位)
              └── helper (description 或 error)

与 Input 的核心差异：
    - 内部控件: QTextEdit 取代 QLineEdit
    - 高度: 由 min_rows / max_rows + fontMetrics.lineSpacing() 动态计算，不再固定
    - auto-resize: 内容增减自动调整高度，超过 max_rows 出现垂直滚动条
    - disable_autosize: 关闭后高度固定在 min_rows
    - 不支持 underlined 变体（HeroUI Textarea 没有这个变体）
    - 内容槽完全重设计：top_right / center_right / bottom_right 三槽
      (不再保留 Input 的 start_content/end_content)
    - inside/outside label 始终浮起（不像 Input 那样停中线装 placeholder）
    - 信号 height_changed: 内容驱动高度变化时发射 (height, row_height)
"""

from PySide6.QtWidgets import (
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QSize,
)
from PySide6.QtGui import QColor, QFont, QPalette, QFontMetrics
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, TEXTAREA_SIZES
from ..utils import hex_to_rgba, load_svg_icon
from ..animation import LabelFloatAnimation
from ..core import ThemeProvider

# 复用 Input 里已经写好的私有控件：背景 wrapper + 清除按钮
# 这两个类与单行/多行无关，纯视觉，不需要重写
from .input import _InputWrapper, _ClearButton


# ============================================================
# 内部控件：无边框 / 透明背景的 QTextEdit
# ============================================================
class _TextEdit(QTextEdit):
    """无边框透明背景的 QTextEdit，融入 _InputWrapper 底色。

    选用 QTextEdit 而不是 QPlainTextEdit 的核心原因：
        QPlainTextEdit 的 verticalScrollBar.value 单位 = 行号（block index），
        是整数，没有"半行"概念，所以拖动 scrollbar 永远跳行（Qt 框架级限制，
        无法通过 hooks 解决）。QTextEdit 的 scrollbar 是像素单位，拖动天然平滑。

    - setFrameStyle(NoFrame): 去掉默认 frame
    - palette.Base = transparent: 防止 Fusion 风格画白底
    - viewport setAutoFillBackground(False) + palette.Base 透明 同步
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from PySide6.QtWidgets import QFrame
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

        # 主体调色板
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.setPalette(pal)

        # viewport 也要透明，否则会画白底
        vp = self.viewport()
        vp.setAutoFillBackground(False)
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        vp.setPalette(vp_pal)

        # 滚动策略
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 自动换行（widget 宽度）
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # 关闭富文本接受（粘贴时纯文本）
        self.setAcceptRichText(False)

        # 去掉 QTextDocument 默认 4px 上下 margin，让文字第一行紧贴 viewport 顶
        # 这样 label 浮起位置、top_right 槽等才能和文字光学对齐
        self.document().setDocumentMargin(0)


# ============================================================
# Resize Grip：手动拖动改变 wrapper 高度的小手柄
# ============================================================
class _ResizeGrip(QWidget):
    """右下角小手柄，拖动改变 textarea 高度

    支持方向: vertical / horizontal / both，由 mode 决定 cursor 形状和拖动轴
    自绘两条斜线（HeroUI 风格薄灰线），不依赖外部图标
    """

    drag_started = Signal()
    drag_delta = Signal(int, int)   # (dx, dy)
    drag_ended = Signal()

    def __init__(self, mode: str = "vertical", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._mode = mode
        self._press_pos = None
        self.setFixedSize(14, 14)
        self.setCursor(self._cursor_for_mode())
        self.setMouseTracking(True)
        self._line_color = QColor("#a1a1aa")  # neutral-400 默认；外部可 set_line_color

    def _cursor_for_mode(self) -> Qt.CursorShape:
        if self._mode == "horizontal":
            return Qt.CursorShape.SizeHorCursor
        if self._mode == "both":
            return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.SizeVerCursor  # vertical 默认

    def set_mode(self, mode: str):
        self._mode = mode
        self.setCursor(self._cursor_for_mode())
        self.update()

    def set_line_color(self, color: QColor):
        self._line_color = QColor(color)
        self.update()

    # ---- 鼠标事件：分发 drag_started / drag_delta / drag_ended ----
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self.drag_started.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._press_pos is not None:
            cur = event.globalPosition().toPoint()
            dx = cur.x() - self._press_pos.x()
            dy = cur.y() - self._press_pos.y()
            # 锁轴
            if self._mode == "vertical":
                dx = 0
            elif self._mode == "horizontal":
                dy = 0
            self.drag_delta.emit(dx, dy)
            self._press_pos = cur
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            self._press_pos = None
            self.drag_ended.emit()
            event.accept()

    # ---- 自绘两条斜线 ----
    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._line_color)
        pen.setWidth(1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        w = self.width()
        h = self.height()
        # 两条 45° 斜线（HTML textarea 风格）：从右下角向左上扩散
        # 短线
        p.drawLine(w - 3, h - 8, w - 8, h - 3)
        # 长线
        p.drawLine(w - 3, h - 4, w - 4, h - 3)


# ============================================================
# Textarea 主体
# ============================================================
class Textarea(QWidget):
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
            from ..core import SmoothScroll
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
    # 高度计算（auto-resize 核心）
    # ============================================================
    def _calc_row_height(self) -> int:
        """根据当前字体度量计算一行的实际像素高度（包含 line spacing）"""
        font = self.text_edit.font()
        fm = QFontMetrics(font)
        # lineSpacing 比 height 多出 leading，更接近 textarea 实际行距
        return fm.lineSpacing()

    def _calc_content_rows(self) -> int:
        """估算当前内容占用的视觉行数（含 wrap）"""
        doc = self.text_edit.document()
        # 使其布局到当前 viewport 宽度下
        viewport_w = self.text_edit.viewport().width()
        if viewport_w > 0:
            doc.setTextWidth(viewport_w)

        # 用 documentLayout 报告的总块数 + 每块的 line count
        total_lines = 0
        block = doc.begin()
        while block.isValid():
            layout = block.layout()
            if layout is not None:
                total_lines += max(1, layout.lineCount())
            else:
                total_lines += 1
            block = block.next()
        return max(1, total_lines)

    def _update_textarea_height(self):
        """根据 minRows/maxRows/disable_autosize 计算并应用高度

        如果用户手动拖动过 grip（self._manual_height 不为 None），优先用该高度，
        绕过 auto-resize 逻辑。调 reset_manual_height() 可恢复 auto-resize。
        """
        row_h = self._calc_row_height()
        self._cached_row_height = row_h
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        is_inside = self._label_placement == "inside" and self._has_label()

        if self._manual_height is not None:
            # 手动模式：用户拖到的高度优先
            total_h = self._manual_height
        else:
            # auto-resize 模式：按 min/max_rows 算
            if self._disable_autosize:
                target_rows = self._min_rows
            else:
                content_rows = self._calc_content_rows()
                target_rows = max(self._min_rows, min(self._max_rows, content_rows))

            text_area_h = row_h * target_rows
            pad_top, pad_bottom = self._current_wrapper_paddings(size_config, is_inside)
            label_reserve = size_config["inside_input_top_space"] if is_inside else 0
            total_h = text_area_h + pad_top + pad_bottom + label_reserve

        # 应用到 wrapper
        if self._wrapper.height() != total_h:
            self._wrapper.setFixedHeight(total_h)

        # textarea 自身固定高度 = wrapper 高度 - padding - label_reserve（让滚动条只在 maxRows 满时出现）
        # 让 _TextEdit 自己占据 inner 给的剩余空间，不显式 setFixedHeight，
        # 这样它会自动跟随 inner 的 layout —— inner_layout 是 setContentsMargins 把
        # 顶部 label_reserve 让出来后的剩余空间。

        # 触发 height_changed（仅在变化时）
        if total_h != self._last_emitted_height:
            self._last_emitted_height = total_h
            self.height_changed.emit(total_h, row_h)

        # 重新摆 label 位置（高度变了）
        self._reposition_inside_label()

    def _current_wrapper_paddings(self, size_config, is_inside: bool):
        """返回当前 wrapper layout 的上下 padding"""
        pad_y = size_config["inside_padding_y"] if is_inside else size_config["padding_y"]
        return pad_y, pad_y

    # ============================================================
    # 样式应用
    # ============================================================
    def _apply_styles(self):
        is_dark = self._theme == "dark"
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 提前给 QTextEdit 直接 setFont，让 fontMetrics.lineSpacing()
        #      在 row_h 计算之前就拿到正确字号；后面 setStyleSheet 还会再设一次
        #      字号是同一个值，不会冲突。
        font_for_metrics = QFont(FONT_FAMILY.split(",")[0].strip().strip("'\""))
        font_for_metrics.setPixelSize(size_config["input_font_size"])
        self.text_edit.setFont(font_for_metrics)

        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        if self._is_disabled:
            self.setStyleSheet("QWidget#heroTextarea { color: palette(disabled); }")
        else:
            self.setStyleSheet("")

        # ---- 最小宽度 ----
        min_w = size_config.get("min_width", 260)
        self.setMinimumWidth(min_w)
        self._wrapper.setMinimumWidth(min_w)

        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()

        # ---- 根容器上边距 (outside 模式给浮起 label 留位置) ----
        if is_outside_float:
            top_reserve = size_config["label_float_font_size"] + 6
            self._root.setContentsMargins(0, top_reserve, 0, 0)
        else:
            self._root.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper padding ----
        pad_x = size_config["padding_x"]
        pad_y = size_config["padding_y"] if not is_inside else size_config["inside_padding_y"]
        if self._radius == "full":
            pad_x += 4
        self._wrapper.layout().setContentsMargins(pad_x, pad_y, pad_x, pad_y)

        # ---- innerWrapper / top_right_slot / clear_btn top margin ----
        # 三槽新设计：
        #   top_right_slot: 在 layout 内，AlignTop；inside 模式下要下推 inside_input_top_space
        #     以避开浮起的 label（否则 label 和 top_right_content 会重叠）
        #   center_right / bottom_right: 绝对定位，resizeEvent 里实时摆放，不受 layout 影响
        #   clear_btn: 行为同 top_right_slot
        if is_inside:
            top_space = size_config["inside_input_top_space"]
            self._inner_layout.setContentsMargins(0, top_space, 0, 0)
            self._top_right_slot_layout.setContentsMargins(0, top_space, 0, 0)
            self._clear_btn.setContentsMargins(0, top_space, 0, 0)
        else:
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._top_right_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._clear_btn.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper 颜色（复用 Input 的颜色决策逻辑）----
        bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color = \
            self._resolve_wrapper_colors(is_dark, colors, dc)

        if self._is_focused:
            cur_bg = bg_focus; cur_border = border_focus
        elif self._is_hover:
            cur_bg = bg_hover; cur_border = border_hover
        else:
            cur_bg = bg; cur_border = border_color

        radius_px_str = self._resolve_radius(size_config)
        try:
            radius_px = int(radius_px_str.replace("px", ""))
        except Exception:
            radius_px = 8

        bw = size_config["border_width"]
        animate = getattr(self, "_styles_applied_once", False)

        if self._variant == "flat":
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        elif self._variant == "faded":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        elif self._variant == "bordered":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        else:
            # fallback to flat
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)

        self._styles_applied_once = True

        # ---- text_edit 样式 ----
        fg_color, placeholder_color = self._resolve_input_text_color(is_dark, colors, dc)
        self.text_edit.setStyleSheet(
            f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {fg_color};
                font-family: {FONT_FAMILY};
                font-size: {size_config['input_font_size']}px;
                selection-background-color: {colors[200]};
                padding: 0;
            }}
            """
        )
        # 注：QScrollBar 样式由 ScrollStyle 单例统一管理（apply_global），
        # 这里不再写局部 QSS。如果需要某个 textarea 用不同色滚动条，
        # 可以自己 text_edit.setStyleSheet 追加 QScrollBar 段。
        pal = self.text_edit.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_color))
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.text_edit.setPalette(pal)
        # viewport 同步
        vp = self.text_edit.viewport()
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        vp.setPalette(vp_pal)

        # ---- 禁用态 ----
        if self._is_disabled:
            self.text_edit.setEnabled(False)
            self._wrapper.setEnabled(False)
            op = QGraphicsOpacityEffect(self)
            op.setOpacity(0.5)
            self.setGraphicsEffect(op)
        else:
            self.text_edit.setEnabled(True)
            self._wrapper.setEnabled(True)
            self.setGraphicsEffect(None)

        # ---- Label 颜色 ----
        self._label_color_resting = QColor(
            self._resolve_label_resting_color(is_dark, colors, dc)
        )
        self._label_color_floated = QColor(
            self._resolve_label_floated_color(is_dark, colors, dc)
        )

        # ---- outside label ----
        outside_label_font = size_config["outside_label_font_size"]
        outside_qss = (
            f"QLabel {{ color: {self._label_color_floated.name()}; "
            f"font-family: {FONT_FAMILY}; font-size: {outside_label_font}px; "
            f"font-weight: 500; }}"
        )
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        display_label = self._label_text + req_mark if self._label_text else ""
        self._outside_label.setText(display_label)
        self._outside_label.setStyleSheet(outside_qss)
        self._outside_left_label.setText(display_label)
        self._outside_left_label.setStyleSheet(outside_qss)

        # ---- 内部 label 样式 ----
        self._inside_label.setStyleSheet(
            f"QLabel {{ background: transparent; font-family: {FONT_FAMILY}; }}"
        )

        # ---- start/end icon ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- clear button icon ----
        if self._is_clearable:
            ic_size = size_config["clear_icon_size"]
            ic_color = QColor(dc[400] if is_dark else dc[500])
            pix = load_svg_icon("heroicons--x-circle-solid", size=ic_size, color=ic_color)
            self._clear_btn.setIcon(pix)
            self._clear_btn.setIconSize(QSize(ic_size, ic_size))
            self._clear_btn.setFixedSize(ic_size + 4, ic_size + 4)
            self._clear_btn.setVisible(True)
        else:
            self._clear_btn.hide()

        # ---- helper ----
        helper_font = size_config["helper_font_size"]
        if self._is_invalid and self._error_message:
            self._helper_label.setText(self._error_message)
            self._helper_label.setStyleSheet(
                f"QLabel {{ color: {HEROUI_COLORS['danger'][500]}; "
                f"font-family: {FONT_FAMILY}; font-size: {helper_font}px; }}"
            )
            self._helper_label.show()
        elif self._description:
            self._helper_label.setText(self._description)
            desc_color = dc[400] if is_dark else dc[500]
            self._helper_label.setStyleSheet(
                f"QLabel {{ color: {desc_color}; "
                f"font-family: {FONT_FAMILY}; font-size: {helper_font}px; }}"
            )
            self._helper_label.show()
        else:
            self._helper_label.hide()

        # ---- 重新摆 label/高度 ----
        self._relayout_for_label_placement()
        self._update_textarea_height()

        # ---- 把自己的滚动条颜色注册给 ScrollStyle，让 hover 动画也用这个色 ----
        # 仅当组件 color 不是 "default" 时才注册自定义色；否则让全局 ScrollStyle 默认色
        # （neutral —— 纯灰中性色）生效。这样 Textarea(color="primary") 滚动条用 primary，
        # Textarea(color="default") 滚动条用 neutral（更纯灰、更中性）。
        try:
            from ..core import ScrollStyle
            v_bar = self.text_edit.verticalScrollBar()
            h_bar = self.text_edit.horizontalScrollBar()
            override = self._color if self._color != "default" else None
            ScrollStyle.instance().set_bar_color(v_bar, override)
            ScrollStyle.instance().set_bar_color(h_bar, override)
        except Exception:
            pass  # 没装 ScrollStyle 也不影响 textarea 工作

        # ---- grip 颜色跟随主题（亮色 neutral-400，暗色 neutral-500）----
        if hasattr(self, "_resize_grip"):
            grip_color = HEROUI_COLORS["neutral"][500] if is_dark else HEROUI_COLORS["neutral"][400]
            self._resize_grip.set_line_color(QColor(grip_color))

    # ------------------------------------------------------------
    # 颜色决策（与 Input 完全对齐，复制实现）
    # ------------------------------------------------------------
    def _flat_bg_colors(self, is_dark: bool, colors: dict, dc: dict):
        is_default = self._color == "default"
        if is_default:
            if is_dark:
                bg = dc[800]; bg_hover = dc[700]; bg_focus = dc[700]
            else:
                bg = dc[100]; bg_hover = dc[200]; bg_focus = dc[200]
        else:
            if is_dark:
                bg = hex_to_rgba(colors[500], 0.15)
                bg_hover = hex_to_rgba(colors[500], 0.25)
                bg_focus = hex_to_rgba(colors[500], 0.25)
            else:
                bg = colors[100]; bg_hover = colors[200]; bg_focus = colors[200]
        return bg, bg_hover, bg_focus

    def _resolve_wrapper_colors(self, is_dark: bool, colors: dict, dc: dict):
        is_default = self._color == "default"
        main_color = colors[500] if not is_default else (dc[50] if is_dark else dc[900])

        if self._variant == "flat":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            border = "transparent"; border_color = "transparent"
            border_hover = "transparent"; border_focus = "transparent"

        elif self._variant == "faded":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            if is_default:
                default_border = dc[700] if is_dark else dc[200]
            else:
                default_border = colors[700] if is_dark else colors[200]
            default_border_hover = dc[500] if is_dark else dc[400]
            border = default_border; border_color = default_border
            if is_default:
                border_hover = default_border_hover
                border_focus = default_border_hover
            else:
                border_hover = colors[500]; border_focus = colors[500]

        elif self._variant == "bordered":
            flat_bg, _, _ = self._flat_bg_colors(is_dark, colors, dc)
            bg = "transparent"; bg_hover = "transparent"; bg_focus = "transparent"
            border = flat_bg; border_color = flat_bg
            if is_default:
                border_hover = dc[400]; border_focus = dc[500]
            else:
                if is_dark:
                    border_hover = colors[600]; border_focus = colors[500]
                else:
                    border_hover = colors[400]; border_focus = colors[500]
        else:
            bg = "transparent"; bg_hover = "transparent"; bg_focus = "transparent"
            border = "transparent"; border_color = "transparent"
            border_hover = "transparent"; border_focus = "transparent"

        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            main_color = d[500]
            if self._variant == "flat":
                bg = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
                bg_hover = hex_to_rgba(d[500], 0.25) if is_dark else d[100]
                bg_focus = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
            elif self._variant == "bordered":
                border = d[500]; border_color = d[500]
                border_hover = d[500]; border_focus = d[500]
            elif self._variant == "faded":
                border = d[500]; border_color = d[500]
                border_hover = d[500]; border_focus = d[500]

        return bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color

    def _resolve_input_text_color(self, is_dark: bool, colors: dict, dc: dict):
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return (
                d[400] if is_dark else d[500],
                d[400] if is_dark else d[500],
            )
        if self._variant == "flat" and self._color != "default":
            if self._color in ("success", "warning"):
                fg = colors[500] if is_dark else colors[600]
                ph = colors[500] if is_dark else colors[600]
            elif self._color == "danger":
                fg = colors[500] if is_dark else colors[500]
                ph = colors[500] if is_dark else colors[500]
            else:
                fg = colors[400] if is_dark else colors[500]
                ph = colors[400] if is_dark else colors[500]
            return fg, ph
        fg = dc[100] if is_dark else dc[900]
        ph = dc[400] if is_dark else dc[500]
        return fg, ph

    def _resolve_label_resting_color(self, is_dark, colors, dc) -> str:
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        return dc[400] if is_dark else dc[500]

    def _resolve_label_floated_color(self, is_dark, colors, dc) -> str:
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        if self._color != "default":
            if self._variant == "flat" and self._color in ("success", "warning"):
                return colors[500] if is_dark else colors[600]
            return colors[500] if not is_dark else colors[400]
        return dc[100] if is_dark else dc[900]

    def _resolve_radius(self, size_config: dict) -> str:
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            # textarea 高度可变，full 用一个稳定的大圆角而不是 height/2
            return "20px"
        return RADIUS.get(radius_key, RADIUS["md"])

    # ------------------------------------------------------------
    # start / end content
    # ------------------------------------------------------------
    def _render_adornment_icons(self, is_dark, colors, dc, size_config):
        # top_right_slot: 在 layout 内（layout 已管好位置）
        self._fill_slot(
            slot=self._top_right_slot,
            slot_layout=self._top_right_slot_layout,
            content=self._top_right_content,
            on_click=self._on_top_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark, dc=dc,
        )
        # center_right / bottom_right：绝对定位 holder
        self._fill_slot(
            slot=self._center_right_holder,
            slot_layout=self._center_right_slot_layout,
            content=self._center_right_content,
            on_click=self._on_center_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark, dc=dc,
        )
        self._fill_slot(
            slot=self._bottom_right_holder,
            slot_layout=self._bottom_right_slot_layout,
            content=self._bottom_right_content,
            on_click=self._on_bottom_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark, dc=dc,
        )
        # 绝对定位的 holder 渲染完后，sizeHint 可能变了，重摆位置
        self._reposition_absolute_holders()

    def _fill_slot(self, slot, slot_layout, content, on_click, icon_size, is_dark, dc):
        while slot_layout.count():
            item = slot_layout.takeAt(0)
            w = item.widget()
            if w is None:
                continue
            if w.property("_hs_internal") is True:
                w.deleteLater()
            else:
                w.setParent(None)

        if content is None:
            slot.hide()
            return

        if isinstance(content, QWidget):
            slot_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignVCenter)
            content.show()
            slot.show()
            return

        icon_color = QColor(dc[400] if is_dark else dc[500])
        pix = load_svg_icon(str(content), size=icon_size, color=icon_color)

        if on_click is not None:
            btn = QPushButton()
            btn.setProperty("_hs_internal", True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(pix)
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setFixedSize(icon_size + 4, icon_size + 4)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; padding: 0; }"
            )
            btn.clicked.connect(on_click)
            slot_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            lbl = QLabel()
            lbl.setProperty("_hs_internal", True)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl.setFixedSize(icon_size, icon_size)
            lbl.setPixmap(pix)
            slot_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        slot.show()

    # ------------------------------------------------------------
    # label 位置 & 浮动定位
    # ------------------------------------------------------------
    def _relayout_for_label_placement(self):
        has_label = self._has_label()
        self._outside_label.setVisible(False)
        self._outside_left_label.setVisible(False)
        self._inside_label.setVisible(False)
        self._outside_left_row.setContentsMargins(0, 0, 0, 0)

        if self._label_placement == "outside-top" and has_label:
            self._outside_label.setVisible(True)
        elif self._label_placement == "outside-left" and has_label:
            self._outside_left_label.setVisible(True)
        elif self._label_placement in ("inside", "outside") and has_label:
            self._inside_label.setVisible(True)

    def _reposition_inside_label(self):
        if not self._has_label() or self._label_placement not in ("inside", "outside"):
            return
        progress = self._label_anim._progress
        self._apply_label_progress(progress)

    def _apply_label_progress(self, progress: float):
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        f_rest = size_config["label_font_size"]
        f_float = size_config["label_float_font_size"]
        font_size = f_rest + (f_float - f_rest) * progress

        font = QFont(FONT_FAMILY.split(",")[0].strip().strip("'\""))
        font.setPixelSize(int(round(font_size)))
        font.setWeight(QFont.Weight.Medium if progress > 0.5 else QFont.Weight.Normal)
        self._inside_label.setFont(font)
        self._inside_label.adjustSize()

        from PySide6.QtCore import QPoint
        wrapper_pos_in_self = self._wrapper.mapTo(self, QPoint(0, 0))
        wrapper_x = wrapper_pos_in_self.x()
        wrapper_y = wrapper_pos_in_self.y()
        wrapper_h = self._wrapper.height()

        pad_x = size_config["padding_x"]
        label_h = self._inside_label.height()

        # resting 位置：textarea 多行场景下应该停在文本第一行附近，
        # 而不是 wrapper 垂直中心（否则 textarea 越高 label 越居中越奇怪）。
        # 第一行文字的近似 y = wrapper 顶 + 当前 wrapper padding_top
        is_inside = self._label_placement == "inside"
        cur_pad_y = (size_config["inside_padding_y"]
                     if is_inside and self._has_label()
                     else size_config["padding_y"])
        # 把 label 垂直居中在第一行高度内
        row_h = self._cached_row_height or self._calc_row_height()
        first_row_top = wrapper_y + cur_pad_y
        # 当 inside 模式下，文本本身被 inner_layout 推下 inside_input_top_space，
        # 所以 label resting 也应该跟着推下，否则和占位符不对齐
        if is_inside and self._has_label():
            first_row_top += size_config["inside_input_top_space"]
        y_rest = first_row_top + (row_h - label_h) // 2
        x_rest = wrapper_x + pad_x

        # floated 终点
        if self._label_placement == "outside":
            x_float = 0
            y_float = max(0, wrapper_y - label_h - 2)
        else:
            x_float = wrapper_x + pad_x + size_config.get("label_float_x", 0)
            y_float = wrapper_y + size_config.get("label_float_y", 6)

        x = int(x_rest + (x_float - x_rest) * progress)
        y = int(y_rest + (y_float - y_rest) * progress)
        self._inside_label.move(x, y)
        self._inside_label.raise_()

        c1 = self._label_color_resting
        c2 = self._label_color_floated
        r = int(c1.red() + (c2.red() - c1.red()) * progress)
        g = int(c1.green() + (c2.green() - c1.green()) * progress)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * progress)

        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        self._inside_label.setTextFormat(Qt.TextFormat.RichText)
        self._inside_label.setText(
            f"<span style='color:rgb({r},{g},{b});'>{self._label_text}</span>{req_mark}"
        )
        self._inside_label.adjustSize()

    def _on_label_progress(self, progress: float):
        self._apply_label_progress(progress)

    # ============================================================
    # 事件钩子
    # ============================================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 宽度变化会影响 wrap → 行数 → 高度
        self._update_textarea_height()
        self._reposition_inside_label()
        self._reposition_absolute_holders()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_textarea_height()
        self._reposition_inside_label()
        self._reposition_absolute_holders()

    # ============================================================
    # 绝对定位槽（center_right / bottom_right）的实时重摆
    # ============================================================
    def _refresh_abs_spacer_width(self):
        """计算 _abs_spacer 应占的宽度，让 inner 在 layout 里给绝对定位槽让出空间。

        center_right / bottom_right 是绝对定位 holder（不在 wrapper layout 里），
        layout 不知道它们存在，inner 会撑满到 wrapper 右内边距 → 文字 wrap 撞按钮。
        修复：spacer 在 layout 里"代替"它们占位。

        ⚠️ 减去已在 layout 里占位的部分：
          - top_right_slot 已经在 layout 里给 top_right_content 让位
          - clear_btn 已经在 layout 里给清除按钮让位
          - layout spacing (8px) 已经在 _inner 和 top_right_slot 之间留出空隙
          这些"已让位"的宽度落在 wrapper 右侧的同一 X 范围内，所以 spacer 只需要补
          "绝对定位 holder 总宽度 - 已让位部分"，否则会重复让位（双槽时尤其明显）。
        """
        gap = 3  # 文字与按钮之间的最小呼吸间距（不可调，跟 input 的 padding_x 配合）

        # 绝对定位 holder 需要的总让位宽度
        abs_need = 0
        if self._center_right_content is not None:
            self._center_right_holder.adjustSize()
            abs_need = max(abs_need, self._center_right_holder.width()
                           + int(self._center_right_offset))
        if self._bottom_right_content is not None:
            self._bottom_right_holder.adjustSize()
            right_off, _ = self._bottom_right_offset
            abs_need = max(abs_need, self._bottom_right_holder.width()
                           + int(right_off))

        # layout 里已经让出的右侧宽度（top_right_slot + clear_btn + 它们各自的 spacing）
        layout_already_reserved = 0
        wrap_layout = self._wrapper.layout()
        wrap_spacing = wrap_layout.spacing() if wrap_layout else 0
        if self._top_right_content is not None and self._top_right_slot.isVisible():
            self._top_right_slot.adjustSize()
            layout_already_reserved += self._top_right_slot.width() + wrap_spacing
        if self._is_clearable and not self._is_disabled and not self._is_readonly:
            # clear_btn 显隐由淡入淡出控制，但 widget 始终在 layout 里、占着 size
            cw = self._clear_btn.width() or self._clear_btn.sizeHint().width()
            if cw > 0:
                layout_already_reserved += cw + wrap_spacing

        # spacer 只需要补足"绝对定位需要 - layout 已让出"
        need = max(0, abs_need - layout_already_reserved)
        if need > 0:
            need += gap  # 仅当 spacer 真要占位时才加 gap

        if self._abs_spacer.width() != need:
            self._abs_spacer.setFixedWidth(need)

    def _reposition_absolute_holders(self):
        """根据 wrapper 当前几何，重摆 center_right_holder 和 bottom_right_holder。

        在 wrapper Resize / textarea 高度变化 / show / 内容变更后调用。
        位置规则:
          - center_right: 距 wrapper 右边 `center_right_offset`px，垂直居中
          - bottom_right: 距 wrapper 右/底 `bottom_right_offset` (right_px, bottom_px)
        """
        # 重新算 spacer 宽度（内容/sizeHint 可能已变）
        self._refresh_abs_spacer_width()

        ww = self._wrapper.width()
        wh = self._wrapper.height()

        # center_right
        if self._center_right_content is not None and self._center_right_holder.isVisible():
            self._center_right_holder.adjustSize()
            cw = self._center_right_holder.width()
            ch = self._center_right_holder.height()
            x = max(0, ww - cw - int(self._center_right_offset))
            y = max(0, (wh - ch) // 2)
            self._center_right_holder.move(x, y)
            self._center_right_holder.raise_()

        # bottom_right
        if self._bottom_right_content is not None and self._bottom_right_holder.isVisible():
            self._bottom_right_holder.adjustSize()
            bw = self._bottom_right_holder.width()
            bh = self._bottom_right_holder.height()
            right_off, bottom_off = self._bottom_right_offset
            x = max(0, ww - bw - int(right_off))
            y = max(0, wh - bh - int(bottom_off))
            self._bottom_right_holder.move(x, y)
            self._bottom_right_holder.raise_()

        # resize grip：贴 wrapper 右下角，距右/底 2px
        # 注意：bottom_right_content 存在时 grip 自动隐藏，避免和按钮重叠
        if (self._resize_mode is not None
                and self._bottom_right_content is None):
            self._resize_grip.show()
            gw = self._resize_grip.width()
            gh = self._resize_grip.height()
            self._resize_grip.move(max(0, ww - gw - 2), max(0, wh - gh - 2))
            self._resize_grip.raise_()
        else:
            self._resize_grip.hide()

    # ============================================================
    # 手动拖动 resize：grip drag_delta 信号回调
    # ============================================================
    def _on_grip_drag(self, dx: int, dy: int):
        """grip 拖动 → 调整 wrapper 高度/宽度

        进入 manual_height_mode（self._manual_height 不为 None），
        _update_textarea_height 会优先用此值，绕过 auto-resize。
        """
        if self._resize_mode is None:
            return

        # 取一个最小高度（min_rows 对应的高度）和软上限（屏幕可视范围内）
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        row_h = self._cached_row_height or self._calc_row_height()
        is_inside = self._label_placement == "inside" and self._has_label()
        pad_top, pad_bottom = self._current_wrapper_paddings(size_config, is_inside)
        label_reserve = size_config["inside_input_top_space"] if is_inside else 0
        min_h = row_h * self._min_rows + pad_top + pad_bottom + label_reserve

        # 当前实际高度作为基准；后续 dy 累加
        cur_h = self._manual_height if self._manual_height is not None else self._wrapper.height()

        if self._resize_mode in ("vertical", "both"):
            new_h = max(min_h, cur_h + dy)
            self._manual_height = new_h
            self._wrapper.setFixedHeight(new_h)
            # 通知绝对槽 + 高度信号
            self._reposition_absolute_holders()
            self.height_changed.emit(new_h, row_h)

        # horizontal/both 暂不实现宽度拖动（textarea 通常 full_width）

    def reset_manual_height(self):
        """清除手动拖动设置的高度，恢复 auto-resize 行为"""
        self._manual_height = None
        self._update_textarea_height()

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
