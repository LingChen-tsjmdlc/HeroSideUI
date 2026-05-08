"""
HeroSideUI Progress Components
基于 HeroUI v2 设计风格

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/progress.ts

Progress (线性进度条):
    结构:
        ┌──────────────┬────────┐   ← label / value 同一行（labelWrapper）
        │  Loading...  │  60%   │
        ├──────────────┴────────┤
        │ ████████░░░░░░░░░░░░░ │   ← track (背景) + indicator (前景)
        └────────────────────────┘
    变体: color × size × radius × is_striped × is_indeterminate × is_disabled × theme

CircularProgress (圆形进度条):
    结构: SVG 环形 arc (track + indicator)，中心 value 文字，下方 label。
    变体: color × size × is_indeterminate × is_disabled × theme
"""

import math

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    QRectF,
    QPointF,
    QSize,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QPainterPath,
    QTransform,
)
from typing import Optional

from ..themes import (
    HEROUI_COLORS, RADIUS, FONT_FAMILY,
    PROGRESS_SIZES, CIRCULAR_PROGRESS_SIZES,
)
from ..utils import hex_to_rgba
from ..animation import (
    IndeterminateBarAnimation, SpinAnimation, StripeFlowAnimation,
)


# ============================================================
# 颜色工具
# ============================================================
def _color_of(name: str, shade: int = 500) -> QColor:
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[shade])


def _indicator_hex(name: str) -> str:
    """对应 HeroUI 的 `bg-{color}` (primary-500 / default-400)"""
    if name == "default":
        return HEROUI_COLORS["default"][400]
    return HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])[500]


# ============================================================
# 线性 track 自绘
# ============================================================
class _LinearTrack(QWidget):
    """自绘 track + indicator（含斜纹 / 不确定态动画）"""

    def __init__(self, owner: "Progress", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._owner = owner
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # indeterminate 滑块动画（复用 IndeterminateBarAnimation）
        self._indet_loop = IndeterminateBarAnimation(
            owner=self, duration=1500, bar_ratio=0.4,
        )

        # 确定态：progress_px 动画（跟随 owner 宽度 * ratio）
        self._anim_ratio = 0.0
        self._ratio_anim = QPropertyAnimation(self, b"anim_ratio")
        self._ratio_anim.setDuration(500)
        self._ratio_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # striped 条带流动（复用 StripeFlowAnimation）
        self._stripe_flow = StripeFlowAnimation(
            owner=self, period=32.0, duration=1000,
        )

    # ----- Qt Properties -----
    def _get_ratio(self) -> float:
        return self._anim_ratio

    def _set_ratio(self, v: float):
        self._anim_ratio = v
        self.update()

    anim_ratio = Property(float, _get_ratio, _set_ratio)

    # ----- 动画控制 -----
    def start_indeterminate(self):
        self._indet_loop.start()
        self.update()

    def stop_indeterminate(self):
        self._indet_loop.stop()

    def start_stripe_flow(self):
        self._stripe_flow.start()

    def stop_stripe_flow(self):
        self._stripe_flow.stop()

    def animate_to(self, ratio: float, disable_animation: bool = False):
        self._ratio_anim.stop()
        if disable_animation:
            self._anim_ratio = ratio
            self.update()
            return
        self._ratio_anim.setStartValue(self._anim_ratio)
        self._ratio_anim.setEndValue(ratio)
        self._ratio_anim.start()

    # ----- 尺寸 -----
    def sizeHint(self):
        return QSize(200, self._owner._track_height())

    def minimumSizeHint(self):
        return QSize(40, self._owner._track_height())

    # ----- 绘制 -----
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        owner = self._owner
        radius = owner._resolve_radius(h)
        track_color = owner._track_color()
        indicator_color = owner._indicator_color()

        # 1) track 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        # 2) indicator
        if owner._is_indeterminate:
            bar_ratio = self._indet_loop.bar_ratio()
            bar_w = w * bar_ratio
            x = self._indet_loop.position * w
            rect = QRectF(x, 0, bar_w, h)
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
            painter.save()
            painter.setClipPath(clip)
            self._fill_indicator(painter, rect, indicator_color, radius)
            painter.restore()
        else:
            ratio = max(0.0, min(1.0, self._anim_ratio))
            if ratio <= 0.0:
                return
            bar_w = max(1.0, w * ratio)
            rect = QRectF(0, 0, bar_w, h)
            self._fill_indicator(painter, rect, indicator_color, radius)

    def _fill_indicator(
        self,
        painter: QPainter,
        rect: QRectF,
        color: QColor,
        radius: float,
    ):
        """画实心或带斜纹的 indicator。"""
        # 底色
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, radius, radius)

        if self._owner._is_striped:
            # 叠加 45° 白色半透明斜纹 + 流动
            stripe = 16  # 条带宽度
            period = self._stripe_flow.period()
            stripe_color = QColor(255, 255, 255, 48)
            # clip 到 indicator 区域
            clip_path = QPainterPath()
            clip_path.addRoundedRect(rect, radius, radius)
            painter.setClipPath(clip_path)
            painter.setBrush(stripe_color)

            h = rect.height()
            y_top = rect.top()
            y_bot = rect.bottom()
            # 流动: offset_value % period
            offset = self._stripe_flow.offset_value() % period
            # 起始 x 向左延伸至少 (h + period)，保证右端填满，左端不会露白
            x = rect.left() - h - period + offset
            while x < rect.right() + stripe + period:
                path = QPainterPath()
                path.moveTo(x, y_bot)
                path.lineTo(x + stripe, y_bot)
                path.lineTo(x + stripe + h, y_top)
                path.lineTo(x + h, y_top)
                path.closeSubpath()
                painter.fillPath(path, stripe_color)
                x += period

        painter.restore()


# ============================================================
# Progress - 线性
# ============================================================
class Progress(QWidget):
    """HeroUI 风格的线性进度条

    参数:
        value: 当前进度值（default 0，范围 [min_value, max_value]）
        min_value / max_value: 进度值范围（默认 0 / 100）
        label: 左上角文字（可空）
        show_value_label: 是否在右上角显示百分比（默认 False）
        value_label_formatter: 自定义显示，如 lambda v,minv,maxv: f"{v}/{maxv}"
        color: default / primary / secondary / success / warning / danger
        size: sm / md / lg
        radius: none / sm / md / lg / full（默认 full）
        is_striped: 斜纹填充
        is_indeterminate: 未定态滚动
        is_disabled: 禁用（半透明 + 禁止交互）
        disable_animation: 关闭 500ms 过渡
        theme: light / dark

    公共 API:
        set_value / value / set_range / set_color / set_size / set_radius
        set_is_striped / set_is_indeterminate / set_is_disabled / set_theme
        set_label / set_show_value_label
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
        radius: str = "full",
        is_striped: bool = False,
        is_indeterminate: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "light",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._value = value
        self._min = min_value
        self._max = max_value
        self._label_text = label
        self._show_value = show_value_label
        self._formatter = value_label_formatter
        self._color = color
        self._size = size
        self._radius = radius
        self._is_striped = is_striped
        self._is_indeterminate = is_indeterminate
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme = theme

        self._setup_ui()
        self._apply_styles()
        self._refresh_text_labels()

        # 启动动画/刷新 indicator
        if is_indeterminate:
            self._track.start_indeterminate()
        else:
            self._track.animate_to(self._progress_ratio(),
                                   disable_animation=True)

        if is_striped and not disable_animation:
            self._track.start_stripe_flow()

        if is_disabled:
            self._apply_disabled_effect(True)

    # ------------------------------------------------------------
    # UI 组装
    # ------------------------------------------------------------
    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        # label row
        self._label_row = QHBoxLayout()
        self._label_row.setContentsMargins(0, 0, 0, 0)
        self._label_row.setSpacing(8)
        self._label = QLabel("")
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label = QLabel("")
        self._value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._label_row.addWidget(self._label, 0, Qt.AlignmentFlag.AlignLeft)
        self._label_row.addStretch()
        self._label_row.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignRight)
        self._label_row_widget = QWidget()
        self._label_row_widget.setLayout(self._label_row)
        self._layout.addWidget(self._label_row_widget)

        # track
        self._track = _LinearTrack(owner=self)
        self._layout.addWidget(self._track)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _apply_styles(self):
        cfg = PROGRESS_SIZES.get(self._size, PROGRESS_SIZES["md"])
        text_color = self._text_color()

        self._label.setStyleSheet(
            f"QLabel {{ color: {text_color}; font-family: {FONT_FAMILY}; "
            f"font-size: {cfg['label_font_size']}px; }}"
        )
        self._value_label.setStyleSheet(
            f"QLabel {{ color: {text_color}; font-family: {FONT_FAMILY}; "
            f"font-size: {cfg['value_font_size']}px; }}"
        )
        # 让 track 重新跑 sizeHint
        self._track.updateGeometry()
        self._track.setFixedHeight(self._track_height())
        self._track.update()

    def _refresh_text_labels(self):
        # label
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

        # value
        if self._show_value and not self._is_indeterminate:
            self._value_label.setText(self._format_value())
            self._value_label.show()
        else:
            self._value_label.setText("")
            self._value_label.hide()

        # 如果 label 和 value 都没有，隐藏整个 row
        self._label_row_widget.setVisible(
            bool(self._label_text) or (self._show_value and not self._is_indeterminate)
        )

    def _format_value(self) -> str:
        if self._formatter is not None:
            return str(self._formatter(self._value, self._min, self._max))
        pct = int(round(self._progress_ratio() * 100))
        return f"{pct}%"

    # ------------------------------------------------------------
    # 颜色 / 尺寸 / 进度计算（供 _LinearTrack 读）
    # ------------------------------------------------------------
    def _progress_ratio(self) -> float:
        if self._max <= self._min:
            return 0.0
        return max(0.0, min(1.0, (self._value - self._min) / (self._max - self._min)))

    def _track_height(self) -> int:
        cfg = PROGRESS_SIZES.get(self._size, PROGRESS_SIZES["md"])
        return int(cfg["track_height"])

    def _track_color(self) -> QColor:
        # HeroUI: bg-default-300/50  (light) / bg-default-600/50 (dark 近似)
        is_dark = self._theme == "dark"
        base = HEROUI_COLORS["default"][600 if is_dark else 300]
        c = QColor(base)
        c.setAlphaF(0.5)
        return c

    def _indicator_color(self) -> QColor:
        return QColor(_indicator_hex(self._color))

    def _text_color(self) -> str:
        return "#ecedee" if self._theme == "dark" else "#18181b"

    def _resolve_radius(self, track_h: int) -> float:
        # Progress 只支持 none / sm / full
        if self._radius == "none":
            return 0.0
        if self._radius == "sm":
            return 4.0
        # full 或未知值：胶囊
        return track_h / 2.0

    # ------------------------------------------------------------
    # 禁用效果
    # ------------------------------------------------------------
    def _apply_disabled_effect(self, disabled: bool):
        if disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setGraphicsEffect(None)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------
    def value(self) -> float:
        return self._value

    def set_value(self, v: float):
        self._value = max(self._min, min(self._max, v))
        self._refresh_text_labels()
        if not self._is_indeterminate:
            self._track.animate_to(self._progress_ratio(),
                                   disable_animation=self._disable_animation)

    def set_range(self, min_value: float, max_value: float):
        self._min = min_value
        self._max = max_value
        self._value = max(self._min, min(self._max, self._value))
        self._refresh_text_labels()
        if not self._is_indeterminate:
            self._track.animate_to(self._progress_ratio(), disable_animation=True)

    def set_color(self, color: str):
        self._color = color
        self._track.update()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: str):
        self._radius = radius
        self._track.update()

    def set_theme(self, theme: str):
        self._theme = theme
        self._apply_styles()

    def set_is_striped(self, striped: bool):
        self._is_striped = striped
        if striped and not self._disable_animation:
            self._track.start_stripe_flow()
        else:
            self._track.stop_stripe_flow()
        self._track.update()

    def set_is_indeterminate(self, indet: bool):
        self._is_indeterminate = indet
        if indet:
            self._track.start_indeterminate()
        else:
            self._track.stop_indeterminate()
            self._track.animate_to(self._progress_ratio(),
                                   disable_animation=self._disable_animation)
        self._refresh_text_labels()

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._apply_disabled_effect(disabled)

    def set_label(self, label: str):
        self._label_text = label
        self._refresh_text_labels()

    def set_show_value_label(self, show: bool):
        self._show_value = show
        self._refresh_text_labels()


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
        theme: str = "light",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._value = value
        self._min = min_value
        self._max = max_value
        self._label_text = label
        self._show_value = show_value_label
        self._formatter = value_label_formatter
        self._color = color
        self._size = size
        self._stroke_override = stroke_width
        self._is_indeterminate = is_indeterminate
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme = theme

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
        self._theme = theme
        self._apply_styles()

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


# ============================================================
# 便捷别名：Spinner
# ============================================================
class Spinner(CircularProgress):
    """CircularProgress 的 loading 别名。

    默认 `is_indeterminate=True`，无需传参即可作为加载转圈使用::

        from hero_side_ui import Spinner
        spinner = Spinner()                        # primary / md
        spinner2 = Spinner(color="secondary", size="lg")
        spinner3 = Spinner(label="Loading...")     # 带下方文字
    """

    def __init__(
        self,
        color: str = "primary",
        size: str = "md",
        label: str = "",
        stroke_width: Optional[float] = None,
        theme: str = "light",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            is_indeterminate=True,
            color=color,
            size=size,
            label=label,
            stroke_width=stroke_width,
            theme=theme,
            parent=parent,
        )

