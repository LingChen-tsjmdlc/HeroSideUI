"""CircularProgress 环形进度：SVG ring + 中心 value + 下方 label。
indeterminate 时 30% 弧持续旋转。
"""

from PySide6.QtCore import (
    Property,
    QRectF,
    Qt,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import SpinAnimation, tween_property
from ...core import ThemeProvider
from ...themes import CIRCULAR_PROGRESS_SIZES, HEROUI_COLORS
from ..text import Text


def _indicator_hex(name: str) -> str:
    """把进度条颜色名映射为 HeroUI 的 `bg-{color}` 色值（primary-500 / default-400）。

    Args:
        name: 语义色名（default/primary/...）。

    Returns:
        str: 对应调色板的十六进制色值。
    """
    if name == "default":
        return HEROUI_COLORS["default"][400]
    return HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])[500]


# ============================================================
# CircularProgress
# ============================================================
class CircularProgress(QWidget):
    """HeroUI 风格圆形进度条；参数同 Progress（无 radius/is_striped）。"""

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
        stroke_width: float | None = None,
        is_indeterminate: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构造环形进度条。

        Args:
            value: 初始进度值（会被夹紧到 [min, max]）。
            min_value: 范围下界。
            max_value: 范围上界。
            label: 下方说明文字。
            show_value_label: 是否在环心显示百分比。
            value_label_formatter: 自定义值格式化回调 (value, min, max)。
            color: 语义色名。
            size: sm/md/lg 尺寸档位。
            stroke_width: 环线宽（px），None 取尺寸默认。
            is_indeterminate: 未定态（旋转弧）。
            is_disabled: 禁用（半透明 + 禁用手势）。
            disable_animation: 关闭过渡动画。
            theme: light/dark/auto。
            parent: 父控件。

        Note:
            无 radius/is_striped（与线性 Progress 不同）；indeterminate 下
            用 SpinAnimation 驱动 30% 弧持续旋转。
        """
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
        self._ratio_anim = None

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
        """返回当前动画进度比（供 anim_ratio Qt 属性读取）。

        Returns:
            float: 0..1 的进度比。
        """
        return self._anim_ratio

    def _set_ratio(self, v: float):
        """设置动画进度比并触发重绘与 value label 同步。

        Args:
            v: 新的进度比（0..1）。
        """
        self._anim_ratio = v
        self._svg.update()
        # 同步 value label
        if self._show_value and not self._is_indeterminate:
            self._value_label.setText(self._format_value_from_ratio(v))

    anim_ratio = Property(float, _get_ratio, _set_ratio)

    # ----- UI 组装 -----
    def _setup_ui(self):
        """组装 SVG 自绘层 + 中心 value label + 下方 label 的布局。"""
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG（自绘）+ 内部居中 value label
        self._svg = _CircularSvg(owner=self)

        # value label 放在 SVG 上方（作为子控件，绝对居中）
        self._value_label = Text("", parent=self._svg, selectable=False)
        self._value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._svg, 0, Qt.AlignmentFlag.AlignHCenter)

        # label 在下方
        self._label = Text("", selectable=False)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)

    def _apply_styles(self):
        """根据 size/color/theme 应用 SVG 尺寸、value/label 字号与颜色。"""
        cfg = CIRCULAR_PROGRESS_SIZES.get(self._size, CIRCULAR_PROGRESS_SIZES["md"])
        text_color = self._text_color()

        d = int(cfg["diameter"])
        self._svg.setFixedSize(d, d)
        self._value_label.setGeometry(0, 0, d, d)
        self._value_label.set_size(cfg["value_font_size"])
        self._value_label.set_color(text_color)
        self._label.set_size(cfg["label_font_size"])
        self._label.set_color(text_color)
        self._svg.update()

    def _refresh_text_labels(self):
        """刷新下方 label 与中心 value label 的文本与可见性。"""
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

        if self._show_value and not self._is_indeterminate:
            self._value_label.setText(self._format_value_from_ratio(self._anim_ratio))
            self._value_label.show()
        else:
            self._value_label.setText("")
            self._value_label.hide()

    def _format_value_from_ratio(self, ratio: float) -> str:
        """把进度比格式化为显示文本（百分比或自定义 formatter）。

        Args:
            ratio: 进度比（0..1）。

        Returns:
            str: 格式化后的文本（默认百分比，自定义 formatter 走回调）。
        """
        if self._formatter is not None:
            v = self._min + ratio * (self._max - self._min)
            return str(self._formatter(v, self._min, self._max))
        return f"{round(ratio * 100)}%"

    # ----- 色彩 / 尺寸 -----
    def _progress_ratio(self) -> float:
        """把当前 value 换算为 0..1 进度比。

        Returns:
            float: 进度比（范围外被夹紧到 0/1）。
        """
        if self._max <= self._min:
            return 0.0
        return max(0.0, min(1.0, (self._value - self._min) / (self._max - self._min)))

    def _indicator_color(self) -> QColor:
        """返回进度弧（indicator）颜色。

        Returns:
            QColor: 由 _indicator_hex 解析的色。
        """
        return QColor(_indicator_hex(self._color))

    def _track_color(self) -> QColor:
        """返回轨道（track）底色（亮/暗下 default 300/600 半透明）。

        Returns:
            QColor: 半透明灰。
        """
        is_dark = self._theme == "dark"
        base = HEROUI_COLORS["default"][600 if is_dark else 300]
        c = QColor(base)
        c.setAlphaF(0.5)
        return c

    def _text_color(self) -> str:
        """返回文字色（暗色浅、亮色深）。

        Returns:
            str: 十六进制色值。
        """
        return "#ecedee" if self._theme == "dark" else "#18181b"

    def _stroke_width(self) -> float:
        """返回环线宽度（px），优先用自定义覆盖值。

        Returns:
            float: 线宽。
        """
        cfg = CIRCULAR_PROGRESS_SIZES.get(self._size, CIRCULAR_PROGRESS_SIZES["md"])
        if self._stroke_override is not None:
            return float(self._stroke_override)
        return float(cfg["stroke_width"])

    # ----- 禁用 -----
    def _apply_disabled_effect(self, disabled: bool):
        """应用/移除禁用视觉效果（半透明 + 禁用手势）。

        Args:
            disabled: True 进入禁用态。
        """
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
        """返回当前进度值。

        Returns:
            float: 当前 value（已夹紧到 [min, max]）。
        """
        return self._value

    def set_value(self, v: float):
        """设置进度值（夹紧到范围）并播放过渡动画。

        Args:
            v: 目标进度值。
        """
        self._value = max(self._min, min(self._max, v))
        self._refresh_text_labels()
        if not self._is_indeterminate:
            tween_property(
                self,
                "_ratio_anim",
                b"anim_ratio",
                self._progress_ratio(),
                duration=500,
                animated=not self._disable_animation,
            )

    def set_range(self, min_value: float, max_value: float):
        """设置进度范围并重新夹紧当前值。

        Args:
            min_value: 新的下界。
            max_value: 新的上界。
        """
        self._min = min_value
        self._max = max_value
        self._value = max(self._min, min(self._max, self._value))
        tween_property(self, "_ratio_anim", b"anim_ratio", self._progress_ratio(), duration=0)
        self._refresh_text_labels()

    def set_color(self, color: str):
        """设置语义色并立即重绘。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._svg.update()

    def set_size(self, size: str):
        """设置尺寸档位并刷新样式。

        Args:
            size: sm/md/lg。
        """
        self._size = size
        self._apply_styles()

    def set_theme(self, theme: str):
        """设置主题模式（auto/light/dark）。

        Args:
            theme: auto 订阅 ThemeProvider 广播；light/dark 固定。

        Note:
            切换后刷新样式（SVG/文字色随主题变化）。
        """
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
        """ThemeProvider 广播回调，应用新主题。

        Args:
            theme: 由 ThemeProvider 广播的目标主题（light/dark）。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_cp_theme(mode: str) -> str:
        """解析主题模式为实际主题。

        Args:
            mode: auto/light/dark。

        Returns:
            str: light 或 dark。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_indeterminate(self, indet: bool):
        """切换未定态（旋转弧）。

        Args:
            indet: True 进入未定态，启动 SpinAnimation。
        """
        self._is_indeterminate = indet
        if indet:
            self._spin.start()
        else:
            self._spin.stop()
        self._refresh_text_labels()
        self._svg.update()

    def set_is_disabled(self, disabled: bool):
        """设置禁用状态。

        Args:
            disabled: True 进入禁用态。
        """
        self._is_disabled = disabled
        self._apply_disabled_effect(disabled)

    def set_label(self, label: str):
        """设置下方说明文字。

        Args:
            label: 文字内容。
        """
        self._label_text = label
        self._refresh_text_labels()

    def set_show_value_label(self, show: bool):
        """设置是否在环心显示进度值。

        Args:
            show: True 显示百分比/自定义文本。
        """
        self._show_value = show
        self._refresh_text_labels()


class _CircularSvg(QWidget):
    """圆形进度条的自绘核心（track + indicator arc）。"""

    def __init__(self, owner: "CircularProgress", parent: QWidget | None = None):
        """构造自绘 SVG 核心。

        Args:
            owner: 所属的 CircularProgress，用于读取颜色/进度/旋转角度。
            parent: 父控件。
        """
        super().__init__(parent)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        """自绘 track 圈与 indicator 弧（含未定态旋转）。

        Args:
            event: Qt 绘制事件。

        Note:
            indeterminate 下取 SpinAnimation 角度绘制 30% 弧；
            确定态按 anim_ratio 绘制对应比例弧，从 12 点钟顺时针。
        """
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
