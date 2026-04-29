"""
HeroSideUI Card Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/card.ts
文档参考: https://v2.heroui.com/docs/components/card

结构:
    Card (QWidget, paintEvent 自绘外层阴影)
        └── _content (QWidget, objectName="heroCard", QSS 背景 + 圆角 + 边框)
                ├── CardHeader (标题插槽)
                ├── CardBody   (内容插槽)
                ├── CardFooter (底部插槽)
                └── RippleOverlay (水波纹层)

    早期实现用 QGraphicsDropShadowEffect 给 Card 本体挂阴影，但这会把
    整个子树离屏渲染为位图，和子控件（Button 的 PressScaleEffect 等）
    自带的 QGraphicsEffect 冲突，导致子控件整个消失。
    现在改为 paintEvent 多层 QPainter 自绘阴影，内层 _content 承载
    QSS 背景和全部装配内容，彻底避免嵌套 GraphicsEffect 问题。

    hover 300ms 过渡通过 QPropertyAnimation 驱动一个 float progress，
    在回调里插值计算 QColor 并刷新内层 _content 的 QSS。
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    QRectF,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY
from ..themes.sizes import CARD_SHADOWS
from ..utils import hex_to_rgba
from ..animation import RippleOverlay, PressScaleEffect

# Card 的固定结构参数（对齐 HeroUI，不再暴露 size prop）
# padding 统一 12，字号由用户自己在子控件上设置（header 用 h3，body 用正文）
_CARD_PADDING = 12


class CardHeader(QWidget):
    """Card 标题插槽"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroCardHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_padding(self, p: int):
        self._layout.setContentsMargins(p, p, p, p)


class CardBody(QWidget):
    """Card 内容插槽"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroCardBody")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_padding(self, p: int):
        self._layout.setContentsMargins(p, p, p, p)


class CardFooter(QWidget):
    """Card 底部插槽"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroCardFooter")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._is_blurred = False

    def set_padding(self, p: int):
        self._layout.setContentsMargins(p, p, p, p)

    def set_blurred(self, b: bool):
        self._is_blurred = b


class Card(QWidget):
    """HeroUI 风格卡片容器

    背景通过 QSS 设置（不用 paintEvent 自绘，因为 QGraphicsDropShadowEffect
    的离屏渲染会导致 paintEvent 背景遮挡子控件）。

    hover 过渡通过 QPropertyAnimation 驱动 _hover_progress (0→1)，
    每帧回调里线性插值两个 QColor 然后刷新 QSS。
    """

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
        theme: str = "light",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._shadow = shadow
        self._radius = radius
        self._is_hoverable = is_hoverable
        self._is_pressable = is_pressable
        self._is_disabled = is_disabled
        self._is_blurred = is_blurred
        self._is_footer_blurred = is_footer_blurred
        self._full_width = full_width
        self._theme = theme

        self._is_hovered = False
        self._is_pressed_state = False

        self._header: Optional[CardHeader] = None
        self._body: Optional[CardBody] = None
        self._footer: Optional[CardFooter] = None
        self._content: Optional[QWidget] = None  # 在 _setup_ui 中创建

        # hover 过渡: 0.0=normal, 1.0=hovered
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hover_progress")
        self._hover_anim.setDuration(300)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        self._apply_styles()

        # 按压动画（挂在内层 _content 上，避免影响外壳 paintEvent 阴影）
        self._press_scale: Optional[PressScaleEffect] = None
        self._ripple_overlay: Optional[RippleOverlay] = None
        if self._is_pressable:
            self._press_scale = PressScaleEffect(target=self._content)
            self._ripple_overlay = RippleOverlay(
                parent=self._content,
                color=self._get_ripple_color(),
                ripple_enabled=True,
            )

    # ---- hover_progress property (动画驱动) ----
    def _get_hp(self) -> float:
        return self._hover_progress

    def _set_hp(self, v: float):
        self._hover_progress = v
        self._refresh_qss()  # 每帧更新 QSS

    hover_progress = Property(float, _get_hp, _set_hp)

    # ============================================================
    def _setup_ui(self):
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
        """根据 shadow 级别计算外层 margin（为 paintEvent 阴影留出绘制空间）"""
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
        """正常态背景色"""
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
        """hover 态背景色"""
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
        """线性插值两个 QColor"""
        return QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
            int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )

    def _current_bg(self) -> QColor:
        """当前插值后的背景色"""
        if not self._is_hoverable:
            return self._get_normal_bg()
        return self._lerp_color(
            self._get_normal_bg(), self._get_hover_bg(), self._hover_progress
        )

    def _refresh_qss(self):
        """刷新内层 _content 的 QSS 背景色（每帧回调）"""
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

    # ============================================================
    # 三层装配
    # ============================================================

    def add_header(self, header: CardHeader):
        """追加 header 插槽。所有 add_* 都是按调用顺序追加到末尾，
        因此 `add_header → add_divider → add_body → add_divider → add_footer`
        的视觉结果就是这个顺序，不会出现 divider 被后插入的 body 挤走的情况。
        """
        self._header = header
        self._layout.addWidget(header)
        self._raise_ripple()
        self._apply_section_styles()

    def add_body(self, body: CardBody):
        self._body = body
        self._layout.addWidget(body)
        self._raise_ripple()
        self._apply_section_styles()

    def add_footer(self, footer: CardFooter):
        self._footer = footer
        self._layout.addWidget(footer)
        if self._is_footer_blurred:
            footer.set_blurred(True)
        self._raise_ripple()
        self._apply_section_styles()

    def add_divider(self):
        from .divider import Divider

        d = Divider(orientation="horizontal", theme=self._theme)
        self._layout.addWidget(d)
        self._raise_ripple()
        return d

    def insert_divider(self, index: int):
        from .divider import Divider

        d = Divider(orientation="horizontal", theme=self._theme)
        self._layout.insertWidget(index, d)
        self._raise_ripple()
        return d

    def _raise_ripple(self):
        if self._ripple_overlay:
            self._ripple_overlay.raise_()

    # ============================================================
    # 样式
    # ============================================================

    def _apply_styles(self):
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
                    color: {tc}; font-family: {FONT_FAMILY};
                }}""")

        if self._body:
            self._body.set_padding(p)
            self._body.setStyleSheet(f"""
                #heroCardBody {{
                    background: transparent; border: none;
                    color: {tc}; font-family: {FONT_FAMILY};
                }}""")

        if self._footer:
            self._footer.set_padding(p)
            fbg, fex = "transparent", ""
            if self._is_footer_blurred:
                fbg = (
                    hex_to_rgba("#18181b", 0.7)
                    if is_dark
                    else hex_to_rgba("#ffffff", 0.7)
                )
                fex = "border-top: 1px solid rgba(255, 255, 255, 0.1);"
            self._footer.setStyleSheet(f"""
                #heroCardFooter {{
                    background-color: {fbg}; border: none;
                    border-bottom-left-radius: {r}px; border-bottom-right-radius: {r}px;
                    color: {stc}; font-family: {FONT_FAMILY}; {fex}
                }}""")

    def _resolve_radius(self) -> int:
        rk = self._radius or "lg"
        rs = RADIUS.get(rk, RADIUS["lg"])
        try:
            return int(rs.replace("px", ""))
        except:
            return 14

    @staticmethod
    def _parse_color(s: str) -> QColor:
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
        return QColor(255, 255, 255) if self._theme == "dark" else QColor(0, 0, 0)

    # ============================================================
    # 交互
    # ============================================================

    def enterEvent(self, event):
        if self._is_hoverable and not self._is_disabled:
            self._is_hovered = True
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_progress)
            self._hover_anim.setEndValue(1.0)
            self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._is_hoverable:
            self._is_hovered = False
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._hover_progress)
            self._hover_anim.setEndValue(0.0)
            self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
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
        self._shadow = s
        self._apply_styles()

    def set_radius(self, r: str):
        self._radius = r
        self._apply_styles()

    def set_theme(self, t: str):
        self._theme = t
        self._apply_styles()

    def set_is_hoverable(self, v: bool):
        self._is_hoverable = v
        self._apply_styles()

    def set_is_pressable(self, v: bool):
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
        self._is_disabled = v
        self._apply_styles()

    def set_is_blurred(self, v: bool):
        self._is_blurred = v
        self._apply_styles()

    def set_is_footer_blurred(self, v: bool):
        self._is_footer_blurred = v
        if self._footer:
            self._footer.set_blurred(v)
        self._apply_styles()

    def set_full_width(self, v: bool):
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

    def header(self) -> Optional[CardHeader]:
        return self._header

    def body(self) -> Optional[CardBody]:
        return self._body

    def footer(self) -> Optional[CardFooter]:
        return self._footer
