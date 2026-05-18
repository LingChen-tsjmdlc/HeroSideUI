"""CircularProgress — 环形进度指示器。

显示 0-100% 的环形进度。`is_indeterminate=True` 时整圈以 30% 长度的弧
持续旋转，作为加载指示。
"""

import math
from typing import Optional

from PySide6.QtCore import (
    Property,
    QByteArray,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import SpinAnimation, StripeFlowAnimation
from ...core import ThemeProvider
from ...themes import CIRCULAR_PROGRESS_SIZES, FONT_FAMILY, HEROUI_COLORS


def _indicator_hex(name: str) -> str:
    """对应 HeroUI 的 `bg-{color}` (primary-500 / default-400)。"""
    if name == "default":
        return HEROUI_COLORS["default"][400]
    return HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])[500]


# ============================================================
# CircularProgress
# ============================================================
class CircularProgress(QWidget):
    """HeroUI 风格的圆形进度条

    结构: SVG ring (track + indicator arc) + 中心 value + 下方 label。

    参数同 Progress，除了没有 radius/is_striped。
    is_indeterminate=True 时，整圈以 30% 长度的弧持续旋转。
    """

    def __init__(
        self,
        value: float = 0.0,
        min_value: float = 0.0,
        max_value: float = 100.0,
        label: str = "",
        show_value_label: bool = False,
        value_label_formatter=None,
        color: str = "primary",
        size: str = "md",
        stroke_width: Optional[float] = None,
        is_indeterminate: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._min = min_value
        self._max = max_value
        # 初始化时夹紧到 [min, max]，与 set_value / set_range 行为一致
        self._value = max(self._min, min(self._max, value))
        self._label_text = label
        self._show_value = show_value_label
        self._formatter = value_label_formatter
        self._color = color
        self._size = size
        self._stroke_override = stroke_width
        self._is_indeterminate = is_indeterminate
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_cp_theme(theme)

        # 确定态动画：从当前 ratio → 目标 ratio
        # 先按 value 计算出初始 ratio，避免 label 初次渲染显示 0%
        self._anim_ratio = self._progress_ratio() if not is_indeterminate else 0.0
        self._ratio_anim = QPropertyAnimation(self, b"anim_ratio")
        self._ratio_anim.setDuration(500)
        self._ratio_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        self._apply_styles()
        self._refresh_text_labels()

        # indeterminate 旋转（复用 SpinAnimation；owner 设为 _svg 以便其 update 触发重绘）
        self._spin = SpinAnimation(owner=self._svg, duration=900)

        if is_indeterminate:
            self._spin.start()

        if is_disabled:
            self._apply_disabled_effect(True)

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ----- Qt properties -----
    def _get_ratio(self) -> float:
        return self._anim_ratio

    def _set_ratio(self, v: float):
        self._anim_ratio = v
        self._svg.update()
        # 同步 value label
        if self._show_value and not self._is_indeterminate:
            self._value_label.setText(self._format_value_from_ratio(v))

    anim_ratio = Property(float, _get_ratio, _set_ratio)

    # ----- UI 组装 -----
    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG（自绘）+ 内部居中 value label
        self._svg = _CircularSvg(owner=self)

        # value label 放在 SVG 上方（作为子控件，绝对居中）
        self._value_label = QLabel(self._svg)
        self._value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._svg, 0, Qt.AlignmentFlag.AlignHCenter)

        # label 在下方
        self._label = QLabel("")
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)

    def _apply_styles(self):
        cfg = CIRCULAR_PROGRESS_SIZES.get(self._size, CIRCULAR_PROGRESS_SIZES["md"])
        text_color = self._text_color()

        d = int(cfg["diameter"])
        self._svg.setFixedSize(d, d)
        self._value_label.setGeometry(0, 0, d, d)
        self._value_label.setStyleSheet(
            f"QLabel {{ color: {text_color}; font-family: {FONT_FAMILY}; "
            f"font-size: {cfg['value_font_size']}px; background: transparent; }}"
        )
        self._label.setStyleSheet(
            f"QLabel {{ color: {text_color}; font-family: {FONT_FAMILY}; "
            f"font-size: {cfg['label_font_size']}px; }}"
        )
        self._svg.update()

    def _refresh_text_labels(self):
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

        if self._show_value and not self._is_indeterminate:
            self._value_label.setText(self._format_value_from_ratio(self._anim_ratio))
            self._value_label.show()
        else:
            self._value_label.setText("")
            self._value_label.hide()

    def _format_value_from_ratio(self, ratio: float) -> str:
        if self._formatter is not None:
            v = self._min + ratio * (self._max - self._min)
            return str(self._formatter(v, self._min, self._max))
        return f"{int(round(ratio * 100))}%"

    # ----- 色彩 / 尺寸 -----
    def _progress_ratio(self) -> float:
        if self._max <= self._min:
            return 0.0
        return max(0.0, min(1.0, (self._value - self._min) / (self._max - self._min)))

    def _indicator_color(self) -> QColor:
        return QColor(_indicator_hex(self._color))

    def _track_color(self) -> QColor:
        is_dark = self._theme == "dark"
        base = HEROUI_COLORS["default"][600 if is_dark else 300]
        c = QColor(base)
        c.setAlphaF(0.5)
        return c

    def _text_color(self) -> str:
        return "#ecedee" if self._theme == "dark" else "#18181b"

    def _stroke_width(self) -> float:
        cfg = CIRCULAR_PROGRESS_SIZES.get(self._size, CIRCULAR_PROGRESS_SIZES["md"])
        if self._stroke_override is not None:
            return float(self._stroke_override)
        return float(cfg["stroke_width"])

    # ----- 禁用 -----
    def _apply_disabled_effect(self, disabled: bool):
        if disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setGraphicsEffect(None)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # ----- 公共 API -----
    def value(self) -> float:
        return self._value

    def set_value(self, v: float):
        self._value = max(self._min, min(self._max, v))
        self._refresh_text_labels()
        if self._is_indeterminate:
            return
        self._ratio_anim.stop()
        target = self._progress_ratio()
        if self._disable_animation:
            self._anim_ratio = target
            self._svg.update()
            return
        self._ratio_anim.setStartValue(self._anim_ratio)
        self._ratio_anim.setEndValue(target)
        self._ratio_anim.start()

    def set_range(self, min_value: float, max_value: float):
        self._min = min_value
        self._max = max_value
        self._value = max(self._min, min(self._max, self._value))
        self._anim_ratio = self._progress_ratio()
        self._refresh_text_labels()
        self._svg.update()

    def set_color(self, color: str):
        self._color = color
        self._svg.update()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_cp_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_cp_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_indeterminate(self, indet: bool):
        self._is_indeterminate = indet
        if indet:
            self._spin.start()
        else:
            self._spin.stop()
        self._refresh_text_labels()
        self._svg.update()

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._apply_disabled_effect(disabled)

    def set_label(self, label: str):
        self._label_text = label
        self._refresh_text_labels()

    def set_show_value_label(self, show: bool):
        self._show_value = show
        self._refresh_text_labels()


class _CircularSvg(QWidget):
    """圆形进度条的自绘核心（track + indicator arc）"""

    def __init__(self, owner: "CircularProgress", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return
        owner = self._owner

        stroke_w = owner._stroke_width()
        margin = stroke_w / 2.0 + 1.0
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        track_color = owner._track_color()
        indicator_color = owner._indicator_color()

        # ---- 1) track 圈 ----
        pen = QPen(track_color, stroke_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        # ---- 2) indicator arc ----
        pen2 = QPen(indicator_color, stroke_w)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Qt 的 drawArc 单位是 1/16 度，起点 3 点钟方向，逆时针正角
        # 我们希望从 12 点钟开始顺时针，所以起点角 = 90°，span 取负
        if owner._is_indeterminate:
            # 30% 弧在旋转（角度从 SpinAnimation 读取）
            start_deg = 90.0 - owner._spin.angle_value()
            span_deg = -0.3 * 360.0
            painter.drawArc(
                rect,
                int(start_deg * 16),
                int(span_deg * 16),
            )
        else:
            ratio = max(0.0, min(1.0, owner._anim_ratio))
            if ratio <= 0.0:
                return
            start_deg = 90.0
            span_deg = -ratio * 360.0
            painter.drawArc(
                rect,
                int(start_deg * 16),
                int(span_deg * 16),
            )

