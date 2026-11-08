"""Card 组件：外壳自绘多层阴影 + 内层 QSS 背景的双层结构。

不用 QGraphicsDropShadowEffect，避免与子控件自带 GraphicsEffect 嵌套冲突
导致子控件消失；hover 由属性动画插值刷新 QSS。
"""

from PySide6.QtCore import (
    Property,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import PressScaleEffect, RippleOverlay, tween_property
from ...core import ThemeProvider
from ...themes import CARD_SHADOWS, HEROUI_COLORS, RADIUS
from ...utils import hex_to_rgba

# Card 的固定结构参数（对齐 HeroUI，不再暴露 size prop）
# padding 统一 12，字号由用户自己在子控件上设置（header 用 h3，body 用正文）
_CARD_PADDING = 12


def _sync_word_wrap_label_height(label: QLabel) -> None:
    """同步 wordWrap QLabel 的最小高度。

    Args:
        label: 开启自动换行的 QLabel。

    Note:
        Qt 布局常给 wrapped label 只分配 unconstrained sizeHint 高度，
        Card 窄宽度换行后内容被裁；按 heightForWidth 补最小高度防裁剪。
    """
    if not label.wordWrap() or label.width() <= 0:
        return
    h = label.heightForWidth(label.width())
    if h > 0:
        label.setMinimumHeight(h)


class CardHeader(QWidget):
    """Card 标题插槽"""

    def __init__(self, parent: QWidget | None = None):
        """创建横向标题插槽容器。

        Args:
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("heroCardHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_padding(self, p: int):
        """设置四向内边距。

        Args:
            p: 内边距，单位像素。
        """
        self._layout.setContentsMargins(p, p, p, p)


class CardBody(QWidget):
    """Card 内容插槽"""

    def __init__(self, parent: QWidget | None = None):
        """创建纵向内容插槽容器。

        Args:
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("heroCardBody")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_padding(self, p: int):
        """设置四向内边距。

        Args:
            p: 内边距，单位像素。
        """
        self._layout.setContentsMargins(p, p, p, p)

    def resizeEvent(self, event):
        """尺寸变化后同步内部换行 label 的最小高度。

        Args:
            event: Qt 尺寸变化事件。
        """
        super().resizeEvent(event)
        # QLabel(wordWrap=True) 在 Qt 布局里经常只拿到 unconstrained sizeHint
        # 的高度；Card 窄宽度换行后就会被裁掉。CardBody 作为插槽容器，负责
        # 根据当前实际宽度把 wrapped label 的最小高度同步到 heightForWidth。
        for label in self.findChildren(QLabel):
            _sync_word_wrap_label_height(label)
        self._layout.invalidate()


class CardFooter(QWidget):
    """Card 底部插槽"""

    def __init__(self, parent: QWidget | None = None):
        """创建横向底部插槽容器。

        Args:
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("heroCardFooter")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._is_blurred = False

    def set_padding(self, p: int):
        """设置四向内边距。

        Args:
            p: 内边距，单位像素。
        """
        self._layout.setContentsMargins(p, p, p, p)

    def set_blurred(self, b: bool):
        """记录磨砂态标记（样式由 Card 统一下发）。

        Args:
            b: True 表示该 footer 走半透明磨砂样式。
        """
        self._is_blurred = b


class Card(QWidget):
    """HeroUI 风格卡片容器：Header/Body/Footer 插槽 + hover 过渡。"""

    pressed = Signal()

    def __init__(
        self,
        shadow: str = "sm",
        radius: str = "lg",
        is_hoverable: bool = False,
        is_pressable: bool = False,
        is_disabled: bool = False,
        is_blurred: bool = False,
        is_footer_blurred: bool = False,
        full_width: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建卡片容器：外壳自绘阴影 + 内层 QSS 背景的双层结构。

        Args:
            shadow: 阴影级别。
            radius: 圆角档位。
            is_hoverable: 是否启用 hover 背景过渡。
            is_pressable: 是否启用按压交互（缩放 + 水波纹 + pressed 信号）。
            is_disabled: 是否禁用。
            is_blurred: 内容区是否半透明磨砂。
            is_footer_blurred: footer 是否半透明磨砂。
            full_width: 是否横向撑满。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。

        Note:
            不用 QGraphicsDropShadowEffect——会与子控件自带 GraphicsEffect
            嵌套冲突导致子控件消失，改为外壳 paintEvent 多层自绘阴影。
        """
        super().__init__(parent)
        self._shadow = shadow
        self._radius = radius
        self._is_hoverable = is_hoverable
        self._is_pressable = is_pressable
        self._is_disabled = is_disabled
        self._is_blurred = is_blurred
        self._is_footer_blurred = is_footer_blurred
        self._full_width = full_width
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._is_hovered = False
        self._is_pressed_state = False

        self._header: CardHeader | None = None
        self._body: CardBody | None = None
        self._footer: CardFooter | None = None
        self._content: QWidget | None = None  # 在 _setup_ui 中创建

        # hover 过渡: 0.0=normal, 1.0=hovered
        self._hover_progress = 0.0
        self._hover_anim = None

        self._setup_ui()
        self._apply_styles()

        # 按压动画（挂在内层 _content 上，避免影响外壳 paintEvent 阴影）
        self._press_scale: PressScaleEffect | None = None
        self._ripple_overlay: RippleOverlay | None = None
        if self._is_pressable:
            self._press_scale = PressScaleEffect(target=self._content)
            self._ripple_overlay = RippleOverlay(
                parent=self._content,
                color=self._get_ripple_color(),
                ripple_enabled=True,
            )

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ---- hover_progress property (动画驱动) ----
    def _get_hp(self) -> float:
        """Property getter：返回 hover 过渡进度。

        Returns:
            0.0 为常态，1.0 为完全 hover 态。
        """
        return self._hover_progress

    def _set_hp(self, v: float):
        """Property setter：写入进度并逐帧刷新 QSS。

        Args:
            v: 新进度值，由 tween 动画每帧调用。
        """
        self._hover_progress = v
        self._refresh_qss()  # 每帧更新 QSS

    hover_progress = Property(float, _get_hp, _set_hp)

    # ============================================================
    def _setup_ui(self):
        """搭建外壳 + 内层 _content 的双层结构。

        Note:
            外壳不挂 QSS 背景也不用 WA_TranslucentBackground（会影响子树
            渲染），只负责 paintEvent 画阴影；QSS 背景挂在内层 _content。
        """
        # 外壳: 不挂 QSS 背景、也不使用 WA_TranslucentBackground（会影响子树渲染）
        # 只负责 paintEvent 画阴影 + 用外 margin 给阴影留空间
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        # 外层 layout: 只留阴影 margin，把 _content 放进去
        self._outer_layout = QVBoxLayout(self)
        m = self._shadow_margin()
        self._outer_layout.setContentsMargins(m, m, m, m)
        self._outer_layout.setSpacing(0)

        # 内层 _content: 承载 QSS 背景 + 所有装配内容
        self._content = QWidget(self)
        self._content.setObjectName("heroCard")
        self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._outer_layout.addWidget(self._content)

        # 内容装配 layout 落在 _content 上
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.setMouseTracking(True)

    def _shadow_margin(self) -> int:
        """根据阴影级别计算外壳四周预留的绘制空间。

        Returns:
            blur 一半 + |offset_y| + 2 的富余；disabled 或无阴影时为 0。
        """
        if self._is_disabled:
            return 0
        scfg = CARD_SHADOWS.get(self._shadow, CARD_SHADOWS["md"])
        if scfg["opacity"] <= 0:
            return 0
        # margin = blur 半径 + offset 的绝对值，再加一点富余
        return int(scfg["blur"]) // 2 + abs(int(scfg["offset_y"])) + 2

    # ============================================================
    # 外壳 paintEvent: 多层半透明圆角矩形模拟阴影（替代 QGraphicsDropShadowEffect）
    # 好处: 不会对整个子树做离屏渲染，子控件自带的 QGraphicsEffect（如 Button 的
    #       PressScaleEffect）可以正常工作。
    # ============================================================
    def paintEvent(self, event):
        """外壳自绘多层半透明圆角矩形模拟阴影。

        Args:
            event: Qt 绘制事件。

        Note:
            不对整个子树做离屏渲染，子控件自带的 QGraphicsEffect
            （如 Button 的 PressScaleEffect）可正常工作。
        """
        if self._is_disabled:
            return
        scfg = CARD_SHADOWS.get(self._shadow, CARD_SHADOWS["md"])
        if scfg["opacity"] <= 0:
            return

        m = self._shadow_margin()
        if m <= 0:
            return

        # _content 在外壳中的实际 rect（考虑外 margin）
        inner = self._content.geometry()
        r = self._resolve_radius()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # 多层叠加模拟 blur: 从外到内扩散，alpha 从低到高
        layers = max(4, int(scfg["blur"]) // 2)
        max_alpha = scfg["opacity"] * 255
        offset_y = int(scfg["offset_y"])

        for i in range(layers, 0, -1):
            # 第 i 层从 inner 向外扩 (i * m / layers) 像素
            expand = int(i * m / layers)
            rect = QRectF(
                inner.x() - expand,
                inner.y() - expand + offset_y,
                inner.width() + 2 * expand,
                inner.height() + 2 * expand,
            )
            # 外层 alpha 低，内层 alpha 高（形成扩散感）
            # 用 (layers - i + 1) / layers^2 这种递减权重
            alpha = max_alpha * (layers - i + 1) / (layers * layers)
            painter.setBrush(QColor(0, 0, 0, int(alpha)))
            painter.drawRoundedRect(rect, r + expand, r + expand)

        painter.end()

    # ============================================================
    # QSS 背景（挂在内层 _content 上，不会被任何离屏渲染遮挡子控件）
    # ============================================================

    def _get_normal_bg(self) -> QColor:
        """正常态背景色。

        Returns:
            磨砂态返回半透明底；普通态亮色纯白、暗色 default-900。
        """
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        if self._is_blurred:
            return (
                self._parse_color(hex_to_rgba("#18181b", 0.20))
                if is_dark
                else self._parse_color(hex_to_rgba("#ffffff", 0.45))
            )
        return QColor(dc[900]) if is_dark else QColor("#ffffff")

    def _get_hover_bg(self) -> QColor:
        """hover 态背景色。

        Returns:
            磨砂态提高透明度的底色；普通态亮色 default-100、暗色 default-800。
        """
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        if self._is_blurred:
            return (
                self._parse_color(hex_to_rgba("#18181b", 0.30))
                if is_dark
                else self._parse_color(hex_to_rgba("#ffffff", 0.55))
            )
        return QColor(dc[800]) if is_dark else QColor(dc[100])

    @staticmethod
    def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
        """线性插值两个 QColor（含 alpha）。

        Args:
            c1: 起始色。
            c2: 目标色。
            t: 插值系数 0.0 ~ 1.0。

        Returns:
            插值后的新 QColor。
        """
        return QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
            int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )

    def _current_bg(self) -> QColor:
        """按 hover 进度插值后的当前背景色。

        Returns:
            非 hoverable 直接返回常态色；否则在两态间插值。
        """
        if not self._is_hoverable:
            return self._get_normal_bg()
        return self._lerp_color(self._get_normal_bg(), self._get_hover_bg(), self._hover_progress)

    def current_bg_color(self) -> QColor:
        """返回当前实际底色（主题 / hover 解析后）。

        Returns:
            供 ScrollShadow 等子组件读取的 QColor 副本。
        """
        return QColor(self._current_bg())

    def _refresh_qss(self):
        """刷新内层 _content 的 QSS 背景色（hover 动画每帧回调）。

        Note:
            构造早期 _content 可能还没创建，先守卫；
            同步 palette.Window 让子孙 widget 能读到 Card 实际底色——
            仅改 Window，严禁动 Base/Text（Input 挖空坑）。
        """
        # 初次构造阶段 _content 可能还没创建
        if not hasattr(self, "_content") or self._content is None:
            return
        bg = self._current_bg()
        r = self._resolve_radius()
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]

        border = ""
        if is_dark and not self._is_blurred:
            border = f"border: 1px solid {dc[800]};"
        else:
            border = "border: none;"

        self._content.setStyleSheet(f"""
            #heroCard {{
                background-color: rgba({bg.red()}, {bg.green()}, {bg.blue()}, {bg.alpha()});
                border-radius: {r}px;
                {border}
            }}
        """)

        # 同步 _content 的 palette.Window = QSS 实际画的底色。
        # QSS 自身不触达 palette,但子孙 widget 通过 Qt palette propagation
        # 会继承到这里,从而可以通过 self.palette().color(Window) 读到 Card 的
        # 实际底色(如 ScrollShadow 的 _fade_color 用来与背景融合)。
        # 仅改 Window——严禁动 Base/Text(MEMORY 22/23 Input 挖空坑)。
        pal = self._content.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        self._content.setPalette(pal)

    # ============================================================
    # 三层装配
    # ============================================================

    def add_header(self, header: CardHeader):
        """追加 header 插槽。

        Args:
            header: 标题插槽实例。

        Note:
            所有 add_* 按调用顺序追加到末尾，因此
            `add_header → add_divider → add_body → add_divider → add_footer`
            的视觉结果就是这个顺序，divider 不会被后插入的 body 挤走。
        """
        self._header = header
        self._layout.addWidget(header)
        self._raise_ripple()
        self._apply_section_styles()

    def add_body(self, body: CardBody):
        """追加 body 插槽并应用分区样式。

        Args:
            body: 内容插槽实例。
        """
        self._body = body
        self._layout.addWidget(body)
        self._raise_ripple()
        self._apply_section_styles()

    def add_footer(self, footer: CardFooter):
        """追加 footer 插槽，按配置下发磨砂态。

        Args:
            footer: 底部插槽实例。
        """
        self._footer = footer
        self._layout.addWidget(footer)
        if self._is_footer_blurred:
            footer.set_blurred(True)
        self._raise_ripple()
        self._apply_section_styles()

    def add_divider(self):
        """在末尾追加水平分割线。

        Returns:
            新创建的 Divider 实例。
        """
        from ..divider import Divider

        d = Divider(orientation="horizontal", theme=self._theme)
        self._layout.addWidget(d)
        self._raise_ripple()
        return d

    def insert_divider(self, index: int):
        """在指定位置插入水平分割线。

        Args:
            index: 插入的布局位置。

        Returns:
            新创建的 Divider 实例。
        """
        from ..divider import Divider

        d = Divider(orientation="horizontal", theme=self._theme)
        self._layout.insertWidget(index, d)
        self._raise_ripple()
        return d

    def _raise_ripple(self):
        """把水波纹覆盖层置顶，避免被新插入的插槽盖住。"""
        if self._ripple_overlay:
            self._ripple_overlay.raise_()

    # ============================================================
    # 样式
    # ============================================================

    def _apply_styles(self):
        """整体样式刷新：阴影 margin、QSS、效果、尺寸策略与光标。

        Note:
            disabled 半透明挂 _content（不影响外壳阴影绘制）；
            pressable 时 _content 上已有 PressScaleEffect，不得覆盖。
        """
        # 更新外层阴影 margin（shadow 级别变了会需要重算）
        if hasattr(self, "_outer_layout"):
            m = self._shadow_margin()
            self._outer_layout.setContentsMargins(m, m, m, m)

        self._refresh_qss()

        # disabled: 整体半透明（挂在 _content 上，不影响外壳阴影绘制）
        if hasattr(self, "_content") and self._content is not None:
            if self._is_disabled:
                eff = QGraphicsOpacityEffect(self._content)
                eff.setOpacity(0.5)
                self._content.setGraphicsEffect(eff)
            elif self._is_pressable:
                # pressable 模式: _content 上已挂 PressScaleEffect，不要覆盖
                pass
            else:
                # 非 pressable 且非 disabled: 清理 _content 上任何残留 effect
                if not self._is_pressable:
                    self._content.setGraphicsEffect(None)

        # 外壳触发重绘（阴影）
        self.update()

        # sizePolicy: 默认水平 Preferred + 垂直 Fixed —— 避免父 layout (如 QHBoxLayout)
        # 把所有 Card 等高拉伸，导致 _content 被外 margin 挤压变小。
        # 视觉上每张 Card 的高度由各自内容 sizeHint 决定，shadow 变大时
        # 外壳跟着长高（多出的是阴影空间），_content 内容区始终稳定。
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        if self._is_pressable and not self._is_disabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._is_disabled:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.unsetCursor()

        self._apply_section_styles()

    def _apply_section_styles(self):
        """给 header / body / footer 下发内边距与分区 QSS。"""
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        p, r = _CARD_PADDING, self._resolve_radius()
        tc = dc[100] if is_dark else dc[900]
        stc = dc[400] if is_dark else dc[500]

        if self._header:
            self._header.set_padding(p)
            self._header.setStyleSheet(f"""
                #heroCardHeader {{
                    background: transparent; border: none;
                    border-top-left-radius: {r}px; border-top-right-radius: {r}px;
                    color: {tc};
                }}""")

        if self._body:
            self._body.set_padding(p)
            self._body.setStyleSheet(f"""
                #heroCardBody {{
                    background: transparent; border: none;
                    color: {tc};
                }}""")

        if self._footer:
            self._footer.set_padding(p)
            fbg, fex = "transparent", ""
            if self._is_footer_blurred:
                fbg = hex_to_rgba("#18181b", 0.7) if is_dark else hex_to_rgba("#ffffff", 0.7)
                fex = "border-top: 1px solid rgba(255, 255, 255, 0.1);"
            self._footer.setStyleSheet(f"""
                #heroCardFooter {{
                    background-color: {fbg}; border: none;
                    border-bottom-left-radius: {r}px; border-bottom-right-radius: {r}px;
                    color: {stc}; {fex}
                }}""")

    def _resolve_radius(self) -> int:
        """解析圆角像素值。

        Returns:
            radius 档位对应 token 的 int 值；解析失败回退 14。
        """
        rk = self._radius or "lg"
        rs = RADIUS.get(rk, RADIUS["lg"])
        try:
            return int(rs.replace("px", ""))
        except Exception:
            return 14

    @staticmethod
    def _parse_color(s: str) -> QColor:
        """把 rgba() 函数式或 HEX 字符串转成 QColor。

        Args:
            s: rgba(r,g,b,a) 或 #RRGGBB 形式的颜色字符串。

        Returns:
            对应的 QColor。
        """
        if s.startswith("rgba("):
            parts = s.replace("rgba(", "").replace(")", "").split(",")
            return QColor(
                int(parts[0]),
                int(parts[1]),
                int(parts[2]),
                int(float(parts[3].strip()) * 255),
            )
        return QColor(s)

    def _get_ripple_color(self) -> QColor:
        """按主题取水波纹颜色。

        Returns:
            暗色白波纹、亮色黑波纹。
        """
        return QColor(255, 255, 255) if self._theme == "dark" else QColor(0, 0, 0)

    # ============================================================
    # 交互
    # ============================================================

    def enterEvent(self, event):
        """鼠标进入：hoverable 时播 hover 过渡动画。

        Args:
            event: Qt 进入事件。
        """
        if self._is_hoverable and not self._is_disabled:
            self._is_hovered = True
            tween_property(self, "_hover_anim", b"hover_progress", 1.0, duration=300)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：hoverable 时回落到常态。

        Args:
            event: Qt 离开事件。
        """
        if self._is_hoverable:
            self._is_hovered = False
            tween_property(self, "_hover_anim", b"hover_progress", 0.0, duration=300)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下：pressable 时触发水波纹与按压缩放。

        Args:
            event: Qt 鼠标按下事件。

        Note:
            水波纹坐标需从外壳映射到内层 _content。
        """
        if (
            self._is_pressable
            and not self._is_disabled
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._is_pressed_state = True
            if self._ripple_overlay:
                # 坐标从外壳转到内层 _content
                pos_in_content = self._content.mapFrom(self, event.position().toPoint())
                self._ripple_overlay.add_ripple(pos_in_content)
            if self._press_scale:
                self._press_scale.press()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：恢复缩放，仍在卡内才发 pressed 信号。

        Args:
            event: Qt 鼠标释放事件。
        """
        if (
            self._is_pressable
            and not self._is_disabled
            and event.button() == Qt.MouseButton.LeftButton
        ):
            if self._press_scale:
                self._press_scale.release()
            if self._is_pressed_state:
                self._is_pressed_state = False
                if self.rect().contains(event.position().toPoint()):
                    self.pressed.emit()
        super().mouseReleaseEvent(event)

    # ============================================================
    # 公共 API
    # ============================================================

    def set_shadow(self, s: str):
        """切换阴影级别并重算外壳 margin。

        Args:
            s: 阴影级别名。
        """
        self._shadow = s
        self._apply_styles()

    def set_radius(self, r: str):
        """切换圆角档位并刷新 QSS。

        Args:
            r: 圆角档位名。
        """
        self._radius = r
        self._apply_styles()

    def set_theme(self, t: str):
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            t: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
        if t == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = t
            self._theme = t
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_hoverable(self, v: bool):
        """切换 hover 过渡开关。

        Args:
            v: True 时 hover 背景过渡生效。
        """
        self._is_hoverable = v
        self._apply_styles()

    def set_is_pressable(self, v: bool):
        """切换按压交互开关，按需补建缩放与水波纹效果。

        Args:
            v: True 启用按压缩放 + 水波纹。

        Note:
            关闭时不销毁 overlay，只 set_enabled(False)，
            再次开启可复用同一实例。
        """
        self._is_pressable = v
        if v and not self._press_scale:
            self._press_scale = PressScaleEffect(target=self._content)
        if v and not self._ripple_overlay:
            self._ripple_overlay = RippleOverlay(
                parent=self._content,
                color=self._get_ripple_color(),
                ripple_enabled=True,
            )
            self._raise_ripple()
        elif not v and self._ripple_overlay:
            self._ripple_overlay.set_enabled(False)
        self._apply_styles()

    def set_is_disabled(self, v: bool):
        """切换禁用态。

        Args:
            v: True 时半透明并禁用交互。
        """
        self._is_disabled = v
        self._apply_styles()

    def set_is_blurred(self, v: bool):
        """切换内容区磨砂态。

        Args:
            v: True 时背景走半透明。
        """
        self._is_blurred = v
        self._apply_styles()

    def set_is_footer_blurred(self, v: bool):
        """切换 footer 磨砂态并联动已有 footer。

        Args:
            v: True 时 footer 走半透明磨砂样式。
        """
        self._is_footer_blurred = v
        if self._footer:
            self._footer.set_blurred(v)
        self._apply_styles()

    def set_full_width(self, v: bool):
        """切换横向撑满。

        Args:
            v: True 时水平 sizePolicy 为 Expanding。
        """
        self._full_width = v
        self._apply_styles()

    # ============================================================
    # 尺寸代理: 把外部传入的固定/最小/最大尺寸作用到内层 _content
    # 这样 "setFixedWidth(350)" 的 350 是可视 Card 宽度，
    # 而 Card 外壳会自动扩展到 350 + 2 * shadow_margin 以容纳阴影。
    # ============================================================

    def setFixedSize(self, *args):  # type: ignore[override]
        if self._content is not None:
            self._content.setFixedSize(*args)
        else:
            super().setFixedSize(*args)

    def setFixedWidth(self, w: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setFixedWidth(w)
        else:
            super().setFixedWidth(w)

    def setFixedHeight(self, h: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setFixedHeight(h)
        else:
            super().setFixedHeight(h)

    def setMinimumWidth(self, w: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setMinimumWidth(w)
        else:
            super().setMinimumWidth(w)

    def setMinimumHeight(self, h: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setMinimumHeight(h)
        else:
            super().setMinimumHeight(h)

    def setMinimumSize(self, *args):  # type: ignore[override]
        if self._content is not None:
            self._content.setMinimumSize(*args)
        else:
            super().setMinimumSize(*args)

    def setMaximumWidth(self, w: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setMaximumWidth(w)
        else:
            super().setMaximumWidth(w)

    def setMaximumHeight(self, h: int):  # type: ignore[override]
        if self._content is not None:
            self._content.setMaximumHeight(h)
        else:
            super().setMaximumHeight(h)

    def setMaximumSize(self, *args):  # type: ignore[override]
        if self._content is not None:
            self._content.setMaximumSize(*args)
        else:
            super().setMaximumSize(*args)

    def header(self) -> CardHeader | None:
        """返回 header 插槽。

        Returns:
            当前 header；未添加时为 None。
        """
        return self._header

    def body(self) -> CardBody | None:
        """返回 body 插槽。

        Returns:
            当前 body；未添加时为 None。
        """
        return self._body

    def footer(self) -> CardFooter | None:
        """返回 footer 插槽。

        Returns:
            当前 footer；未添加时为 None。
        """
        return self._footer
