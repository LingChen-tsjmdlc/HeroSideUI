"""Progress 线性进度条：labelWrapper + track/indicator；striped/indeterminate 变体。"""

from PySide6.QtCore import (
    Property,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import (
    IndeterminateBarAnimation,
    StripeFlowAnimation,
    tween_property,
)
from ...core import ThemeProvider
from ...themes import (
    HEROUI_COLORS,
    PROGRESS_SIZES,
)
from ..text import Text


# ============================================================
# 颜色工具
# ============================================================
def _color_of(name: str, shade: int = 500) -> QColor:
    """把语义色名与阶调解析为 QColor。

    Args:
        name: 语义色名；未知色名回退到 primary。
        shade: 调色板阶调。

    Returns:
        QColor: 对应的颜色对象。
    """
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[shade])


def _indicator_hex(name: str) -> str:
    """把语义色名映射为 HeroUI 的 `bg-{color}` 色值。

    Args:
        name: 语义色名；default 取 400 阶，其余取 500 阶。

    Returns:
        str: 十六进制色值。
    """
    if name == "default":
        return HEROUI_COLORS["default"][400]
    return HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])[500]


# ============================================================
# 线性 track 自绘
# ============================================================
class _LinearTrack(QWidget):
    """线性进度条自绘层：track 与 indicator 的绘制及动画驱动。

    Note:
        颜色、圆角、进度比与变体状态均从宿主 Progress 读取。
    """

    def __init__(self, owner: "Progress", parent: QWidget | None = None):
        """构造自绘层并准备三条动画通道。

        Args:
            owner: 所属的 Progress，供绘制时读取配置与状态。
            parent: 父控件。

        Note:
            未定态滑块与斜纹流动各有独立动画实例；确定态过渡走
            anim_ratio Qt 属性的 tween 通道。
        """
        super().__init__(parent)
        self._owner = owner
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # indeterminate 滑块动画（复用 IndeterminateBarAnimation）
        self._indet_loop = IndeterminateBarAnimation(
            owner=self,
            duration=1500,
            bar_ratio=0.4,
        )

        # 确定态：progress_px 动画（跟随 owner 宽度 * ratio）
        self._anim_ratio = 0.0
        self._ratio_anim = None

        # striped 条带流动（复用 StripeFlowAnimation）
        self._stripe_flow = StripeFlowAnimation(
            owner=self,
            period=32.0,
            duration=1000,
        )

    # ----- Qt Properties -----
    def _get_ratio(self) -> float:
        """读取当前绘制用的进度比。

        Returns:
            float: 0..1 的进度比。
        """
        return self._anim_ratio

    def _set_ratio(self, v: float):
        """更新绘制用的进度比并触发重绘。

        Args:
            v: 新的进度比（0..1）。
        """
        self._anim_ratio = v
        self.update()

    anim_ratio = Property(float, _get_ratio, _set_ratio)

    # ----- 动画控制 -----
    def start_indeterminate(self):
        """启动未定态滑块循环并立即重绘。"""
        self._indet_loop.start()
        self.update()

    def stop_indeterminate(self):
        """停止未定态滑块循环。"""
        self._indet_loop.stop()

    def start_stripe_flow(self):
        """启动斜纹流动循环。"""
        self._stripe_flow.start()

    def stop_stripe_flow(self):
        """停止斜纹流动循环。"""
        self._stripe_flow.stop()

    def animate_to(self, ratio: float, disable_animation: bool = False):
        """把绘制进度过渡到目标比例。

        Args:
            ratio: 目标进度比（0..1）。
            disable_animation: True 时立即应用目标值，不播放 500ms 过渡。

        Note:
            经 tween_property 写入 anim_ratio；同通道的旧过渡会被抢占。
        """
        tween_property(
            self, "_ratio_anim", b"anim_ratio", ratio, duration=500, animated=not disable_animation
        )

    # ----- 尺寸 -----
    def sizeHint(self):
        """返回建议尺寸。

        Returns:
            QSize: 宽 200、高为宿主轨道高度的尺寸。
        """
        return QSize(200, self._owner._track_height())

    def minimumSizeHint(self):
        """返回最小建议尺寸。

        Returns:
            QSize: 宽 40、高为宿主轨道高度的尺寸。
        """
        return QSize(40, self._owner._track_height())

    # ----- 绘制 -----
    def paintEvent(self, event):
        """自绘 track 圆角底与 indicator（含斜纹与未定态滑块）。

        Args:
            event: Qt 绘制事件。

        Note:
            颜色、圆角与变体状态全部经 owner 解析；未定态滑块与斜纹
            各自裁剪到圆角轮廓内。
        """
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
        """绘制 indicator 底色，斜纹态叠加 45° 半透明流动条带。

        Args:
            painter: 调用方的画笔。
            rect: indicator 区域。
            color: indicator 底色。
            radius: 轨道圆角半径。

        Note:
            条带起点向左外扩 h + period，保证流动时两端不露白；偏移量
            由 StripeFlowAnimation 提供。
        """
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
    """HeroUI 风格线性进度条：label 行 + 自绘 track/indicator。

    Note:
        支持 striped 与 indeterminate 变体；构造参数见 __init__。
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
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构造线性进度条。

        Args:
            value: 初始进度值（会被夹紧到 [min, max]）。
            min_value: 范围下界。
            max_value: 范围上界。
            label: 左上说明文字。
            show_value_label: 是否在右上显示百分比。
            value_label_formatter: 自定义值格式化回调 (value, min, max)。
            color: 语义色名。
            size: sm/md/lg 尺寸档位。
            radius: 圆角 token；仅 none/sm 有独立取值，其余按胶囊处理。
            is_striped: 是否叠加斜纹填充。
            is_indeterminate: 是否显示未定态滚动滑块。
            is_disabled: 禁用（半透明 + 禁用手势）。
            disable_animation: 关闭 500ms 进度过渡与斜纹流动。
            theme: light/dark/auto。
            parent: 父控件。

        Note:
            构造末尾按初始变体启动对应动画循环；auto 模式注册到
            ThemeProvider，由广播回调刷新配色。
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
        self._radius = radius
        self._is_striped = is_striped
        self._is_indeterminate = is_indeterminate
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._setup_ui()
        self._apply_styles()
        self._refresh_text_labels()

        # 启动动画/刷新 indicator
        if is_indeterminate:
            self._track.start_indeterminate()
        else:
            self._track.animate_to(self._progress_ratio(), disable_animation=True)

        if is_striped and not disable_animation:
            self._track.start_stripe_flow()

        if is_disabled:
            self._apply_disabled_effect(True)

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ------------------------------------------------------------
    # UI 组装
    # ------------------------------------------------------------
    def _setup_ui(self):
        """组装 label 行与自绘 track 的纵向布局。

        Note:
            两个 Text 均设为鼠标事件透明；无文字且无值标签时整行由
            _refresh_text_labels 隐藏。
        """
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        # label row
        self._label_row = QHBoxLayout()
        self._label_row.setContentsMargins(0, 0, 0, 0)
        self._label_row.setSpacing(8)
        self._label = Text("", selectable=False)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label = Text("", selectable=False)
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
        """按 size 档位刷新文字字号、颜色与 track 高度。

        Note:
            updateGeometry 让 _LinearTrack 的 sizeHint 重新生效，故须在
            设置固定高度之前调用。
        """
        cfg = PROGRESS_SIZES.get(self._size, PROGRESS_SIZES["md"])
        text_color = self._text_color()

        self._label.set_size(cfg["label_font_size"])
        self._label.set_color(text_color)
        self._value_label.set_size(cfg["value_font_size"])
        self._value_label.set_color(text_color)
        # 让 track 重新跑 sizeHint
        self._track.updateGeometry()
        self._track.setFixedHeight(self._track_height())
        self._track.update()

    def _refresh_text_labels(self):
        """刷新两个标签的文本、可见性及 label 行的整体显隐。"""
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
        """把当前进度值格式化为右上显示文本。

        Returns:
            str: 百分比文本，或自定义 formatter 的返回值。
        """
        if self._formatter is not None:
            return str(self._formatter(self._value, self._min, self._max))
        pct = round(self._progress_ratio() * 100)
        return f"{pct}%"

    # ------------------------------------------------------------
    # 颜色 / 尺寸 / 进度计算（供 _LinearTrack 读）
    # ------------------------------------------------------------
    def _progress_ratio(self) -> float:
        """把当前 value 换算为 0..1 进度比。

        Returns:
            float: 范围非法或越界时返回夹紧后的比例。
        """
        if self._max <= self._min:
            return 0.0
        return max(0.0, min(1.0, (self._value - self._min) / (self._max - self._min)))

    def _track_height(self) -> int:
        """返回当前 size 档位对应的轨道高度。

        Returns:
            int: 轨道高度（px）；未知档位回退到 md。
        """
        cfg = PROGRESS_SIZES.get(self._size, PROGRESS_SIZES["md"])
        return int(cfg["track_height"])

    def _track_color(self) -> QColor:
        """返回轨道底色。

        Returns:
            QColor: 半透明灰色，亮色取 default-300、暗色取 default-600。

        Note:
            对应 HeroUI 的 bg-default-300/50，暗色为近似值。
        """
        # HeroUI: bg-default-300/50  (light) / bg-default-600/50 (dark 近似)
        is_dark = self._theme == "dark"
        base = HEROUI_COLORS["default"][600 if is_dark else 300]
        c = QColor(base)
        c.setAlphaF(0.5)
        return c

    def _indicator_color(self) -> QColor:
        """返回 indicator 颜色。

        Returns:
            QColor: 由 _indicator_hex 解析出的语义色。
        """
        return QColor(_indicator_hex(self._color))

    def _text_color(self) -> str:
        """返回标签文字色。

        Returns:
            str: 十六进制色值，暗色浅字、亮色深字。
        """
        return "#ecedee" if self._theme == "dark" else "#18181b"

    def _resolve_radius(self, track_h: int) -> float:
        """把 radius token 解析为绘制用的圆角半径。

        Args:
            track_h: 当前轨道高度（px）。

        Returns:
            float: none 返回 0、sm 返回 4，其余按胶囊取 track_h / 2。
        """
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
        """应用或移除禁用态的半透明与光标反馈。

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

    # ------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------
    def value(self) -> float:
        """返回当前进度值。

        Returns:
            float: 已夹紧到 [min, max] 的 value。
        """
        return self._value

    def set_value(self, v: float):
        """设置进度值并播放过渡。

        Args:
            v: 目标进度值，会被夹紧到当前范围。

        Note:
            未定态下只刷新标签，不改动滑块动画。
        """
        self._value = max(self._min, min(self._max, v))
        self._refresh_text_labels()
        if not self._is_indeterminate:
            self._track.animate_to(
                self._progress_ratio(), disable_animation=self._disable_animation
            )

    def set_range(self, min_value: float, max_value: float):
        """设置进度范围并重新夹紧当前值。

        Args:
            min_value: 新的下界。
            max_value: 新的上界。

        Note:
            范围变更后立即同步 indicator，不播放过渡动画。
        """
        self._min = min_value
        self._max = max_value
        self._value = max(self._min, min(self._max, self._value))
        self._refresh_text_labels()
        if not self._is_indeterminate:
            self._track.animate_to(self._progress_ratio(), disable_animation=True)

    def set_color(self, color: str):
        """设置 indicator 语义色并立即重绘。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._track.update()

    def set_size(self, size: str):
        """设置尺寸档位并刷新样式。

        Args:
            size: sm/md/lg。
        """
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: str):
        """设置轨道圆角档位并立即重绘。

        Args:
            radius: 圆角 token；仅 none/sm 有独立取值，其余按胶囊处理。
        """
        self._radius = radius
        self._track.update()

    def set_theme(self, theme: str):
        """设置主题模式并刷新样式。

        Args:
            theme: auto 订阅 ThemeProvider 广播；light/dark 固定。

        Note:
            从 auto 切到固定主题时会注销注册，避免继续接收广播。
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
        """应用 ThemeProvider 广播的主题。

        Args:
            theme: 广播的目标主题（light/dark）。

        Note:
            由 Provider 回调触发，不走 set_theme 以免重复注册。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析为实际主题。

        Args:
            mode: auto/light/dark。

        Returns:
            str: light 或 dark；auto 取 Provider 当前值。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_striped(self, striped: bool):
        """开启或关闭斜纹填充。

        Args:
            striped: True 显示斜纹。

        Note:
            disable_animation 为真时不启动条带流动，只保留静态斜纹。
        """
        self._is_striped = striped
        if striped and not self._disable_animation:
            self._track.start_stripe_flow()
        else:
            self._track.stop_stripe_flow()
        self._track.update()

    def set_is_indeterminate(self, indet: bool):
        """切换未定态滚动滑块。

        Args:
            indet: True 进入未定态。

        Note:
            退出未定态时按当前 ratio 过渡回确定态，并刷新值标签。
        """
        self._is_indeterminate = indet
        if indet:
            self._track.start_indeterminate()
        else:
            self._track.stop_indeterminate()
            self._track.animate_to(
                self._progress_ratio(), disable_animation=self._disable_animation
            )
        self._refresh_text_labels()

    def set_is_disabled(self, disabled: bool):
        """设置禁用状态。

        Args:
            disabled: True 进入禁用态。
        """
        self._is_disabled = disabled
        self._apply_disabled_effect(disabled)

    def set_label(self, label: str):
        """设置左上说明文字。

        Args:
            label: 文字内容；空串隐藏该标签。
        """
        self._label_text = label
        self._refresh_text_labels()

    def set_show_value_label(self, show: bool):
        """设置右上是否显示进度值。

        Args:
            show: True 显示百分比或自定义文本。
        """
        self._show_value = show
        self._refresh_text_labels()
