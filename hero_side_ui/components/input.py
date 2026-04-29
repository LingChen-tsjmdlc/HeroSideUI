"""
HeroSideUI Input Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/input.ts

结构:
    Input (QWidget 容器)
        └── mainWrapper (V)
              ├── outside label (仅 outside / outside-top 模式)
              ├── inputWrapper (QFrame, 绘制背景/边框/圆角，内部 H 布局)
              │     ├── start_content (可选)
              │     ├── innerWrapper (V)
              │     │     ├── inside/outside-left label (浮动 / 静态)
              │     │     └── _LineEdit
              │     ├── end_content (可选)
              │     ├── clear_button (可选)
              │     └── underline_bar (仅 underlined 变体，覆盖在底部中心)
              └── helper (description 或 error，occupy fixed slot)

特性对齐 HeroUI:
    - 4 variants: flat / faded / bordered / underlined
    - 6 colors: default / primary / secondary / success / warning / danger
    - 3 sizes: sm / md / lg
    - 5 radius: none / sm / md / lg / full
    - 4 label placements: inside (默认) / outside / outside-left / outside-top
    - 状态: disabled / invalid / required / readonly / clearable
    - 动画: label 浮动 (200ms, ease-out) + underlined 下划线展开 + clear 按钮淡入缩放
    - 主题: light / dark
"""

from PySide6.QtWidgets import (
    QWidget,
    QLineEdit,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QPropertyAnimation,
    QEasingCurve,
    QSize,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, INPUT_SIZES
from ..utils import hex_to_rgba, load_svg_icon
from ..animation import LabelFloatAnimation, UnderlineBar


# ============================================================
# 内部控件：无边框/无焦点框的 QLineEdit
# ============================================================
class _LineEdit(QLineEdit):
    """继承 QLineEdit，禁用默认边框/焦点框以融入 inputWrapper 背景

    保留原生 API：textChanged / editingFinished / setText / text / setEchoMode 等。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrame(False)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


# ============================================================
# 清除按钮：带 opacity 淡入 + scale 效果
# ============================================================
class _ClearButton(QPushButton):
    """Clear 按钮。点击清空文本，跟随 filled 状态淡入/淡出"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0; }"
        )
        # 透明度效果：0=隐藏，0.7=正常，1.0=hover
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._visible = False

    def set_visible(self, visible: bool, animate: bool = True):
        """显示/隐藏（带淡入淡出）"""
        if visible == self._visible:
            return
        self._visible = visible
        target = 0.7 if visible else 0.0
        if animate:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(target)
            self._opacity_anim.start()
        else:
            self._opacity_effect.setOpacity(target)

        # 禁用时不响应点击
        self.setEnabled(visible)

    def enterEvent(self, event):
        if self._visible:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(1.0)
            self._opacity_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._visible:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(0.7)
            self._opacity_anim.start()
        super().leaveEvent(event)


# ============================================================
# inputWrapper：带背景/边框/圆角的画布
# ============================================================
class _InputWrapper(QFrame):
    """输入框背景容器 — 用 QPainter 手绘背景 + 边框 + 圆角

    维护 bg_color / border_color / bottom_line_color 三个 Qt Property，
    通过 QPropertyAnimation 插值实现 150ms 颜色过渡（对齐 HeroUI 的
    `transition-background !duration-150` 与 `transition-colors`）。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroInputWrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        # 自绘，不需要 Qt 默认背景
        self.setAutoFillBackground(False)

        self._bg_color = QColor(0, 0, 0, 0)
        self._border_color = QColor(0, 0, 0, 0)
        self._bottom_line_color = QColor(0, 0, 0, 0)  # underlined 变体底部静态线
        self._border_width = 0  # 0 = 不画边框
        self._radius_px = 8
        self._show_bottom_line = False  # underlined 模式下为 True

        # 动画
        self._bg_anim = QPropertyAnimation(self, b"bg_color")
        self._bg_anim.setDuration(150)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._border_anim = QPropertyAnimation(self, b"border_color")
        self._border_anim.setDuration(150)
        self._border_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._bottom_anim = QPropertyAnimation(self, b"bottom_line_color")
        self._bottom_anim.setDuration(150)
        self._bottom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- Qt Properties (动画插值目标) ----
    from PySide6.QtCore import Property as _QtProperty  # 避免和 typing Property 冲突

    def _get_bg(self) -> QColor:
        return self._bg_color

    def _set_bg(self, c: QColor):
        self._bg_color = c
        self.update()

    bg_color = _QtProperty(QColor, _get_bg, _set_bg)

    def _get_border(self) -> QColor:
        return self._border_color

    def _set_border(self, c: QColor):
        self._border_color = c
        self.update()

    border_color = _QtProperty(QColor, _get_border, _set_border)

    def _get_bottom(self) -> QColor:
        return self._bottom_line_color

    def _set_bottom(self, c: QColor):
        self._bottom_line_color = c
        self.update()

    bottom_line_color = _QtProperty(QColor, _get_bottom, _set_bottom)

    # ---- 配置接口 ----
    def set_static(self, *, border_width: int, radius_px: int, show_bottom_line: bool):
        """设置非动画属性"""
        self._border_width = border_width
        self._radius_px = radius_px
        self._show_bottom_line = show_bottom_line
        self.update()

    def set_bg_color(self, c: QColor, animate: bool = True):
        if animate:
            self._bg_anim.stop()
            self._bg_anim.setStartValue(QColor(self._bg_color))
            self._bg_anim.setEndValue(QColor(c))
            self._bg_anim.start()
        else:
            self._bg_color = QColor(c)
            self.update()

    def set_border_color(self, c: QColor, animate: bool = True):
        if animate:
            self._border_anim.stop()
            self._border_anim.setStartValue(QColor(self._border_color))
            self._border_anim.setEndValue(QColor(c))
            self._border_anim.start()
        else:
            self._border_color = QColor(c)
            self.update()

    def set_bottom_line_color(self, c: QColor, animate: bool = True):
        if animate:
            self._bottom_anim.stop()
            self._bottom_anim.setStartValue(QColor(self._bottom_line_color))
            self._bottom_anim.setEndValue(QColor(c))
            self._bottom_anim.start()
        else:
            self._bottom_line_color = QColor(c)
            self.update()

    # ---- 手绘背景 + 边框 ----
    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        bw = self._border_width
        r = self._radius_px

        if self._show_bottom_line:
            # underlined 变体：只画底部 2px 静态线（聚焦时的彩色展开线由 UnderlineBar 覆盖）
            if self._bottom_line_color.alpha() > 0:
                painter.fillRect(0, h - 2, w, 2, self._bottom_line_color)
            painter.end()
            return

        # 圆角矩形背景
        if bw > 0:
            # 有边框：先画边框底，再画内部背景
            inner_offset = bw / 2.0
            # 画边框（stroke）
            if self._border_color.alpha() > 0:
                painter.setPen(QPen(self._border_color, bw))
                painter.setBrush(self._bg_color if self._bg_color.alpha() > 0 else Qt.BrushStyle.NoBrush)
                rect = QRectF(inner_offset, inner_offset, w - bw, h - bw)
                painter.drawRoundedRect(rect, max(0, r - inner_offset), max(0, r - inner_offset))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self._bg_color)
                painter.drawRoundedRect(0, 0, w, h, r, r)
        else:
            # 无边框：只画背景
            painter.setPen(Qt.PenStyle.NoPen)
            if self._bg_color.alpha() > 0:
                painter.setBrush(self._bg_color)
                painter.drawRoundedRect(0, 0, w, h, r, r)
        painter.end()


# ============================================================
# Input 主体
# ============================================================
class Input(QWidget):
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
        theme: str = "light",
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
        self._theme = theme

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
    # 样式应用
    # ============================================================
    def _apply_styles(self):
        """计算并应用全部样式"""
        is_dark = self._theme == "dark"
        size_config = INPUT_SIZES.get(self._size, INPUT_SIZES["md"])
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 根控件 ----
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 禁用整体半透明
        if self._is_disabled:
            self.setGraphicsEffect(None)  # 清除
            self.setStyleSheet("QWidget#heroInput { color: palette(disabled); }")
        else:
            self.setStyleSheet("")

        # ---- inputWrapper 高度 ----
        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()
        height = size_config["inside_height"] if is_inside else size_config["height"]
        self._wrapper.setFixedHeight(height)

        # ---- 最小宽度 ----
        min_w = size_config.get("min_width", 260)
        self.setMinimumWidth(min_w)
        self._wrapper.setMinimumWidth(min_w)

        # ---- Input 根容器: outside 模式下给顶部预留空间作为浮出 label 的落脚处 ----
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
        # underlined 特殊 padding
        if self._variant == "underlined":
            self._wrapper.layout().setContentsMargins(4, 0, 4, 0)
        else:
            self._wrapper.layout().setContentsMargins(pad_x, pad_y, pad_x, pad_y)

        # ---- innerWrapper: inside 模式下给输入文字上方留出浮起 label 的空间 ----
        # 这样输入的文字会被挤到下半部分，与浮起的 label 有视觉呼吸感
        # outside 模式下 label 浮到 wrapper 外部，不占 wrapper 内部空间，无需预留
        if is_inside:
            top_space = size_config["inside_input_top_space"]
            self._inner_layout.setContentsMargins(0, top_space, 0, 0)
            # ★ start/end content 图标与 clear button 也一起下移，与输入文字水平对齐
            # 否则它们会居中于整个高高度 wrapper，相对输入文字显得偏上
            self._start_slot_layout.setContentsMargins(0, top_space, 0, 0)
            self._end_slot_layout.setContentsMargins(0, top_space, 0, 0)
            # clear 按钮没有自己的 layout，用 contentsMargins 直接设
            self._clear_btn.setContentsMargins(0, top_space, 0, 0)
        else:
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._start_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._end_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._clear_btn.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper 背景/边框/圆角 (手绘 + 150ms 过渡) ----
        bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color = \
            self._resolve_wrapper_colors(is_dark, colors, dc)

        # 根据当前 hover/focus 状态选色
        if self._is_focused:
            cur_bg = bg_focus
            cur_border = border_focus
        elif self._is_hover:
            cur_bg = bg_hover
            cur_border = border_hover
        else:
            cur_bg = bg
            cur_border = border_color

        # 圆角解析
        radius_px_str = self._resolve_radius(size_config)
        # 从字符串 "8px" 解析成 int
        try:
            radius_px = int(radius_px_str.replace("px", ""))
        except Exception:
            radius_px = 8

        bw = size_config["border_width"]

        # 首次应用（构造期）不要用动画，避免从全透明淡入
        animate = getattr(self, "_styles_applied_once", False)

        if self._variant == "underlined":
            # underlined: 透明背景 + 底部 2px 分割线
            base_line_color = dc[700] if is_dark else dc[200]
            hover_line_color = dc[600] if is_dark else dc[300]
            cur_bottom = hover_line_color if self._is_hover else base_line_color

            self._wrapper.set_static(border_width=0, radius_px=0, show_bottom_line=True)
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(self._qcolor(cur_bottom), animate=animate)

            # 聚焦色的下划线由 UnderlineBar 覆盖绘制
            self._underline.set_color(QColor(main_color))
            self._underline.show()

        elif self._variant == "flat":
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        elif self._variant == "faded":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        elif self._variant == "bordered":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            # bordered 背景透明
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        else:
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        # 标记首次应用已完成，后续切换都走动画
        self._styles_applied_once = True

        # ---- line_edit 样式 ----
        fg_color, placeholder_color = self._resolve_input_text_color(is_dark, colors, dc)
        self.line_edit.setStyleSheet(
            f"""
            QLineEdit {{
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
        # 占位符颜色
        pal = self.line_edit.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_color))
        self.line_edit.setPalette(pal)

        # ---- 禁用态 ----
        if self._is_disabled:
            self.line_edit.setEnabled(False)
            self._wrapper.setEnabled(False)
            op = QGraphicsOpacityEffect(self)
            op.setOpacity(0.5)
            self.setGraphicsEffect(op)
        else:
            self.line_edit.setEnabled(True)
            self._wrapper.setEnabled(True)
            self.setGraphicsEffect(None)

        # ---- Label 配色 ----
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

        # ---- 内部 label 字号 ----
        self._inside_label.setStyleSheet(
            f"QLabel {{ background: transparent; font-family: {FONT_FAMILY}; }}"
        )

        # ---- start/end icon ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- clear button icon ----
        if self._is_clearable:
            ic_size = size_config["clear_icon_size"]
            ic_color = QColor(dc[400] if is_dark else dc[500])
            pix = load_svg_icon(
                "heroicons--x-circle-solid", size=ic_size, color=ic_color
            )
            self._clear_btn.setIcon(pix)
            self._clear_btn.setIconSize(QSize(ic_size, ic_size))
            self._clear_btn.setFixedSize(ic_size + 4, ic_size + 4)
            self._clear_btn.setVisible(True)  # 仅控制 opacity，不 hide widget
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

        # ---- 重新摆放 label 位置 ----
        self._relayout_for_label_placement()
        self._reposition_inside_label()
        self._reposition_underline()

    # ------------------------------------------------------------
    # 颜色决策
    # ------------------------------------------------------------
    def _flat_bg_colors(self, is_dark: bool, colors: dict, dc: dict):
        """抽离 flat 变体的三态底色，供 faded(底色) / bordered(默认边框) 复用。

        ★ HeroSideUI 规则：
        - 亮色主题 hover/focus: 朝"压暗"方向走（色阶数字变大，颜色变深）
          resting {color}-100 → hover {color}-200 → focus {color}-200
          default: resting default-100 → hover default-200 → focus default-200
        - 暗色主题 hover/focus: 朝"提亮"方向走（透明度增加，看起来更亮）
          resting rgba({color}, 0.15) → hover rgba({color}, 0.25) → focus rgba({color}, 0.25)
          default: resting default-800 → hover default-700 → focus default-700

        返回 (bg, bg_hover, bg_focus)。
        """
        is_default = self._color == "default"
        if is_default:
            if is_dark:
                # 暗色 default: 提亮（800 → 700）
                bg = dc[800]
                bg_hover = dc[700]
                bg_focus = dc[700]
            else:
                # 亮色 default: 压暗（100 → 200）
                bg = dc[100]
                bg_hover = dc[200]
                bg_focus = dc[200]
        else:
            if is_dark:
                # 暗色有色: 提亮（透明度增加）
                bg = hex_to_rgba(colors[500], 0.15)
                bg_hover = hex_to_rgba(colors[500], 0.25)
                bg_focus = hex_to_rgba(colors[500], 0.25)
            else:
                # 亮色有色: 压暗（100 → 200）
                bg = colors[100]
                bg_hover = colors[200]
                bg_focus = colors[200]
        return bg, bg_hover, bg_focus

    def _resolve_wrapper_colors(self, is_dark: bool, colors: dict, dc: dict):
        """返回 (bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color)

        HeroSideUI 自定义规则（对 HeroUI 的偏离）:
        - flat: 同 HeroUI —— 浅彩/浅灰底，hover/focus 略变化。无边框。
        - faded: **底色使用 flat 的底色**（不再是固定灰 default-100）；
                 边框行为保留 —— 默认灰，hover/focus 变主色（default 时变 default-400）
        - bordered: **默认边框 = flat 的底色**（浅彩或浅灰），透明背景；
                    hover 边框变 {color}-400（暗色 -600），
                    focus 边框变 {color}-500（暗色保持 -500）。default 时 hover→500 focus→900/50。
        - underlined: 透明底 + 底部 2px 线（hover 变浅灰），focus 时底部 after 彩条展开。
        """
        is_default = self._color == "default"
        # 主色: 用于 focus 边框 / underlined after / label
        main_color = colors[500] if not is_default else (dc[50] if is_dark else dc[900])

        if self._variant == "flat":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        elif self._variant == "faded":
            # ★ 偏离 HeroUI: 底色使用 flat 的底色（而不是固定灰 default-100）
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            # ★ 默认边框: 比底色"深一档"，仍在同色色板范围内，使边框能隐约看出
            #   亮色: 底 {color}-100 → 边 {color}-200 (或 default-200)
            #   暗色: 底是半透明主色 → 边用色板里更可见的一档 ({color}-700 / default-700)
            if is_default:
                default_border = dc[700] if is_dark else dc[200]
            else:
                # 有色情况：取同色系比底色深一档
                default_border = colors[700] if is_dark else colors[200]
            # hover / focus 过渡
            default_border_hover = dc[500] if is_dark else dc[400]
            border = default_border
            border_color = default_border
            if is_default:
                border_hover = default_border_hover
                border_focus = default_border_hover
            else:
                border_hover = colors[500]
                border_focus = colors[500]

        elif self._variant == "bordered":
            # ★ 偏离 HeroUI: 默认边框 = flat 的底色；
            #   边框的归宿就是 500 主色，hover/focus 都会变主色
            #   亮色: hover {color}-400 (比 500 亮一档) → focus {color}-500
            #   暗色: hover {color}-600 (比 500 深一档) → focus {color}-500
            flat_bg, _, _ = self._flat_bg_colors(is_dark, colors, dc)
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = flat_bg           # 默认: flat 底色
            border_color = flat_bg
            if is_default:
                # default 色: hover default-400, focus default-500
                border_hover = dc[400]
                border_focus = dc[500]
            else:
                if is_dark:
                    border_hover = colors[600]
                    border_focus = colors[500]
                else:
                    border_hover = colors[400]
                    border_focus = colors[500]

        else:  # underlined
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        # isInvalid 覆盖
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            main_color = d[500]
            if self._variant == "flat":
                bg = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
                bg_hover = hex_to_rgba(d[500], 0.25) if is_dark else d[100]
                bg_focus = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
            elif self._variant == "bordered":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]
            elif self._variant == "faded":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]

        return bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color

    def _resolve_input_text_color(self, is_dark: bool, colors: dict, dc: dict):
        """返回 (fg_color, placeholder_color)"""
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return (
                d[400] if is_dark else d[500],
                d[400] if is_dark else d[500],
            )

        # flat 有色变体：文字跟随主色（HeroUI: text-{color}-600 / dark:text-{color}）
        if self._variant == "flat" and self._color != "default":
            if self._color in ("success", "warning"):
                fg = colors[500] if is_dark else colors[600]
                ph = colors[500] if is_dark else colors[600]
            elif self._color == "danger":
                fg = colors[500] if is_dark else colors[500]
                ph = colors[500] if is_dark else colors[500]
            else:  # primary / secondary
                fg = colors[400] if is_dark else colors[500]
                ph = colors[400] if is_dark else colors[500]
            return fg, ph

        # 默认
        fg = dc[100] if is_dark else dc[900]
        ph = dc[400] if is_dark else dc[500]
        return fg, ph

    def _resolve_label_resting_color(self, is_dark: bool, colors: dict, dc: dict) -> str:
        """未浮动时 label 颜色 — HeroUI 默认 text-foreground-500"""
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        return dc[400] if is_dark else dc[500]

    def _resolve_label_floated_color(self, is_dark: bool, colors: dict, dc: dict) -> str:
        """浮动后（聚焦/有值）label 颜色"""
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        # 有色变体: label 跟主色
        if self._color != "default":
            if self._variant == "flat" and self._color in ("success", "warning"):
                return colors[500] if is_dark else colors[600]
            return colors[500] if not is_dark else colors[400]
        # default: 聚焦时变深
        return dc[100] if is_dark else dc[900]

    # ------------------------------------------------------------
    # 圆角
    # ------------------------------------------------------------
    def _resolve_radius(self, size_config: dict) -> str:
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            h = size_config["height"]
            return f"{h // 2}px"
        return RADIUS.get(radius_key, RADIUS["md"])

    # ------------------------------------------------------------
    # start / end content (图标 or 自定义 widget)
    # ------------------------------------------------------------
    def _render_adornment_icons(self, is_dark, colors, dc, size_config):
        """渲染 start_content / end_content 到对应槽位。

        content 规则：
            - None：隐藏槽位
            - str：当作图标名/SVG 路径，渲染为图标。如果同时有 on_*_click，则包成可点击按钮
            - QWidget：直接放入槽位（当作用户自定义组件，比如 Button）
        """
        self._fill_slot(
            slot=self._start_slot,
            slot_layout=self._start_slot_layout,
            content=self._start_content,
            on_click=self._on_start_click,
            icon_size=size_config["start_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )
        self._fill_slot(
            slot=self._end_slot,
            slot_layout=self._end_slot_layout,
            content=self._end_content,
            on_click=self._on_end_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )

    def _fill_slot(self, slot, slot_layout, content, on_click, icon_size, is_dark, dc):
        """把 content 填充到 slot 容器中。"""
        # 先清空槽位里"我们自己创建的"widget（不删除用户外部 widget，只 takeAt）
        while slot_layout.count():
            item = slot_layout.takeAt(0)
            w = item.widget()
            if w is None:
                continue
            # 如果是我们内部创建的图标 label / 按钮，安全删除
            if w.property("_hs_internal") is True:
                w.deleteLater()
            else:
                # 用户 widget，只从布局里移除，reparent 到 None
                w.setParent(None)

        if content is None:
            slot.hide()
            return

        # content 是 QWidget（用户塞进来的自定义组件）
        if isinstance(content, QWidget):
            slot_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignVCenter)
            slot.show()
            return

        # content 是字符串：图标名 / SVG 路径
        icon_color = QColor(dc[400] if is_dark else dc[500])
        pix = load_svg_icon(str(content), size=icon_size, color=icon_color)

        if on_click is not None:
            # 包成可点击按钮
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
            # 静态图标
            lbl = QLabel()
            lbl.setProperty("_hs_internal", True)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl.setFixedSize(icon_size, icon_size)
            lbl.setPixmap(pix)
            slot_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        slot.show()

    # ------------------------------------------------------------
    # label 位置切换
    # ------------------------------------------------------------
    def _relayout_for_label_placement(self):
        """根据 label_placement 切换 inside / outside / outside-top / outside-left 的 label 显隐

        - inside: 浮动 label（_inside_label），浮起终点在 inputWrapper 内顶部
        - outside: 浮动 label（_inside_label），浮起终点在 inputWrapper 上方外部（飞出 wrapper）
        - outside-top: 静态 label（_outside_label），始终固定在 inputWrapper 上方
        - outside-left: 静态 label（_outside_left_label），固定在 inputWrapper 左侧
        """
        has_label = self._has_label()

        # 默认全部隐藏
        self._outside_label.setVisible(False)
        self._outside_left_label.setVisible(False)
        self._inside_label.setVisible(False)

        # outside-left 使用横向行布局，其他使用竖向
        self._outside_left_row.setContentsMargins(0, 0, 0, 0)

        if self._label_placement == "outside-top" and has_label:
            # 静态 label 在上方
            self._outside_label.setVisible(True)
        elif self._label_placement == "outside-left" and has_label:
            self._outside_left_label.setVisible(True)
        elif self._label_placement in ("inside", "outside") and has_label:
            # inside 与 outside 都用浮动 label 动画，差别只在浮起终点
            self._inside_label.setVisible(True)

    def _reposition_inside_label(self):
        """手动摆放浮动 label 的位置（根据当前动画 progress）

        用于 inside 和 outside 两种 placement。
        """
        if not self._has_label() or self._label_placement not in ("inside", "outside"):
            return

        progress = self._label_anim._progress
        self._apply_label_progress(progress)

    def _apply_label_progress(self, progress: float):
        """根据 progress 插值 label 的 geometry / fontSize / color

        label 的 parent 是 Input 根控件，坐标需基于 Input 根容器。
        resting: label 位于 inputWrapper 垂直中心（模拟 placeholder 位置）
        floated:
            - inside:  label 飞到 inputWrapper 内部左上角
            - outside: label 飞出 inputWrapper 到达 Input 根顶部（在 wrapper 上方外部）
        """
        size_config = INPUT_SIZES.get(self._size, INPUT_SIZES["md"])

        f_rest = size_config["label_font_size"]
        f_float = size_config["label_float_font_size"]
        font_size = f_rest + (f_float - f_rest) * progress

        # 字体应用
        font = QFont(FONT_FAMILY.split(",")[0].strip().strip("'\""))
        font.setPixelSize(int(round(font_size)))
        font.setWeight(QFont.Weight.Medium if progress > 0.5 else QFont.Weight.Normal)
        self._inside_label.setFont(font)
        self._inside_label.adjustSize()

        # ---- 定位 ----
        # wrapper 在 Input 根坐标系中的位置
        # （wrapper 的 parent 可能是 outside_left_row，不一定是 self，所以需要 mapTo）
        from PySide6.QtCore import QPoint
        wrapper_pos_in_self = self._wrapper.mapTo(self, QPoint(0, 0))
        wrapper_x = wrapper_pos_in_self.x()
        wrapper_y = wrapper_pos_in_self.y()
        wrapper_w = self._wrapper.width()
        wrapper_h = self._wrapper.height()

        # wrapper 内部 padding（用于决定 label 在 wrapper 内部的对齐基点）
        pad_x = size_config["padding_x"]
        if self._variant == "underlined":
            pad_x = 4

        label_h = self._inside_label.height()

        # resting: label 在 wrapper 垂直中心、水平贴 wrapper 左 padding（像 placeholder 位置）
        x_rest = wrapper_x + pad_x
        y_rest = wrapper_y + (wrapper_h - label_h) // 2

        # floated 终点
        if self._label_placement == "outside":
            # outside: label 飞出 wrapper 到上方外部（Input 根坐标系下 y < wrapper_y）
            # 终点 y = 0（Input 根顶部），x = 0（贴左）
            x_float = 0
            # 让 label 底端稍微贴近 wrapper 顶（留 2px 间隙）
            y_float = max(0, wrapper_y - label_h - 2)
        else:
            # inside: label 浮到 wrapper 内部左上角（跟 line_edit 左对齐，距 wrapper 顶有呼吸间隙）
            # label_float_x/y 是相对 wrapper 内部 padding 起点的偏移
            x_float = wrapper_x + pad_x + size_config.get("label_float_x", 0)
            y_float = wrapper_y + size_config.get("label_float_y", 6)

        x = int(x_rest + (x_float - x_rest) * progress)
        y = int(y_rest + (y_float - y_rest) * progress)

        self._inside_label.move(x, y)
        self._inside_label.raise_()

        # 颜色插值
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
        """LabelFloatAnimation 的回调"""
        self._apply_label_progress(progress)

    # ------------------------------------------------------------
    # underline 摆放
    # ------------------------------------------------------------
    def _reposition_underline(self):
        if self._variant != "underlined":
            return
        w = self._wrapper.width()
        h = self._wrapper.height()
        self._underline.setGeometry(0, h - 2, w, 2)
        self._underline.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_underline()
        self._reposition_inside_label()

    def showEvent(self, event):
        super().showEvent(event)
        # 首次显示后再摆放一次，因为构造期 geometry 尚未生效
        self._reposition_inside_label()
        self._reposition_underline()

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
        self._theme = theme
        self._apply_styles()

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
