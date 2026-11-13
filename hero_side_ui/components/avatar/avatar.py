"""Avatar 头像：自绘背景+圆角图像+描边环；fallback 三级兜底（图→首字母→人像）。
图像复用 ImageLoader，完成 fade-in。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ..._shared.images import ImageLoader, ImageSrc
from ...animation import stop_tween, tween_property
from ...core import ThemeProvider
from ...themes import (
    AVATAR_RING_OFFSET,
    AVATAR_RING_WIDTH,
    AVATAR_SIZES,
    RADIUS,
    VALID_AVATAR_SIZES,
)
from ...utils import load_svg_icon
from ..text import Text
from ._styling import build_avatar_styles


def safe_initials(name: str) -> str:
    """从姓名生成首字母缩写。

    Args:
        name: 完整姓名字符串。

    Returns:
        取首末单词首字符（大写）至多两个；无空格取首字符；空输入返回空串。
    """
    if not name:
        return ""
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


class _IconCanvas(QLabel):
    """默认人像图标画布（空 QLabel 当画布，setPixmap 着色跟主题）。

    非文字用途 QLabel（承载 icon pixmap），不走 Text 组件。
    """

    def __init__(self, parent: QWidget | None = None):
        """初始化透明无鼠标事件的图标画布。

        Args:
            parent: Qt 父对象。

        Note:
            WA_TransparentForMouseEvents 让点击穿透到宿主 Avatar，
            不影响其 pressable 交互。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_name = "heroui--avatar-person"
        self._px = 24
        self._color = "#ffffff"

    def apply(self, icon_name: str, px: int, color: str):
        """应用图标名、尺寸与颜色并重渲染。

        Args:
            icon_name: SVG 图标名。
            px: 渲染尺寸，单位像素。
            color: 十六进制颜色，随主题前景色。
        """
        self._icon_name = icon_name
        self._px = px
        self._color = color
        self.setPixmap(load_svg_icon(icon_name, size=px, color=color))


class Avatar(QWidget):
    """HeroUI v2 风格 Avatar 头像。"""

    # 图片加载
    loaded = Signal()
    failed = Signal()
    # 交互事件（自定义点击 / hover）
    clicked = Signal()
    pressed = Signal()
    released = Signal()
    hovered = Signal()  # 鼠标进入
    unhovered = Signal()  # 鼠标离开

    def __init__(
        self,
        src: ImageSrc = None,
        name: str | None = None,
        icon: str | None = None,
        fallback: QWidget | None = None,
        color: str = "default",
        radius: str = "full",
        size: str = "md",
        is_bordered: bool = False,
        is_disabled: bool = False,
        show_fallback: bool = False,
        disable_animation: bool = False,
        is_pressable: bool = False,
        on_click: Callable[[], None] | None = None,
        on_hover: Callable[[bool], None] | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建头像并装配首字母 / 图标 / 图像三级渲染。

        Args:
            src: 图像来源（路径 / URL / QPixmap），None 走 fallback。
            name: 姓名字符串，用于生成首字母兜底。
            icon: 自定义 fallback 图标名。
            fallback: 完全自定义的兜底 widget，优先级最高。
            color: 语义色，决定底色与 ring。
            radius: 圆角档位；full 为圆形。
            size: 尺寸档位，非法值回退 md。
            is_bordered: 是否画描边环。
            is_disabled: 是否禁用。
            show_fallback: 有 src 但加载失败时是否显示兜底。
            disable_animation: 关闭图像 fade-in。
            is_pressable: 是否启用点击交互。
            on_click: 点击回调，等价 connect(clicked)。
            on_hover: hover 回调 fn(entered: bool)。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。

        Note:
            fallback 三级优先级：自定义 widget > name 首字母 > 人像图标。
        """
        super().__init__(parent)
        self.setObjectName("HeroAvatar")

        self._src = src
        self._name = name
        self._icon = icon or "heroui--avatar-person"
        self._fallback_widget = fallback
        self._color = color
        self._radius = radius
        self._size = size if size in VALID_AVATAR_SIZES else "md"
        self._is_bordered = is_bordered
        self._is_disabled = is_disabled
        self._show_fallback = show_fallback
        self._disable_animation = disable_animation
        self._is_pressable = is_pressable
        self._is_pressed = False
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme

        # 图像状态
        self._status = "pending"  # pending / loading / loaded / failed
        self._pixmap: QPixmap | None = None
        self._img_opacity = 0.0

        self._build_ui()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._apply_styles()
        self._kick_load()

        # 便捷回调：等价于外部 connect
        if on_click is not None:
            self.clicked.connect(on_click)
        if on_hover is not None:
            self.hovered.connect(lambda cb=on_hover: cb(True))
            self.unhovered.connect(lambda cb=on_hover: cb(False))

    # ============================================================
    # 构建
    # ============================================================
    def _build_ui(self):
        """构建首字母 label、图标画布与 fade 动画槽位。

        Note:
            首字母承载用户可读文案走 Text 组件；图标画布是纯 pixmap
            载体用 QLabel。两者都透明化鼠标事件。
        """
        # 首字母文字（承载用户可读文案 → 走 Text 组件）
        self._name_label = Text(
            "",
            size=AVATAR_SIZES[self._size]["text_size"],
            weight="normal",
            selectable=False,
            theme=self._theme,
            parent=self,
        )
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # 默认人像图标画布
        self._icon_canvas = _IconCanvas(self)

        # fade-in 动画（图像 opacity 0→1，对齐 transition-opacity 500ms）
        self._fade_anim = None

    # ============================================================
    # 尺寸 / 布局
    # ============================================================
    def _outer_margin(self) -> int:
        """描边环占用的外圈厚度（ring + offset），非 bordered 时为 0。"""
        if not self._is_bordered:
            return 0
        return AVATAR_RING_WIDTH + AVATAR_RING_OFFSET

    def _box_side(self) -> int:
        """头像内容盒子边长（不含描边环）。"""
        return AVATAR_SIZES[self._size]["box"]

    def _content_rect(self) -> QRectF:
        """内容盒子（图像 / 背景）几何，扣掉描边外圈。"""
        m = self._outer_margin()
        return QRectF(m, m, self._box_side(), self._box_side())

    def _radius_px(self, side: int) -> float:
        """按档位计算内容盒圆角像素值。

        Args:
            side: 内容盒边长。

        Returns:
            full 时为边长一半；其余取 token 并按短边一半截断。
        """
        if self._radius == "full":
            return side / 2.0
        token_px = int(RADIUS.get(self._radius, RADIUS["md"]).rstrip("px"))
        return float(min(token_px, side // 2))

    # ============================================================
    # 加载
    # ============================================================
    def _kick_load(self):
        """创建 ImageLoader 并按 src 状态启动或待命。

        Note:
            src 为 None 时停在 pending 态只刷新 overlay；
            有 src 才标记 loading 并发起加载。
        """
        self._loader = ImageLoader(self)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_failed)
        if self._src is None:
            self._status = "pending"
            self._refresh_overlay()
            return
        self._status = "loading"
        self._refresh_overlay()
        self._loader.load(self._src)

    def _on_loaded(self, pm: QPixmap):
        """图像加载成功：存 pixmap、刷新层级并 fade-in。

        Args:
            pm: 加载完成的 QPixmap。
        """
        self._status = "loaded"
        self._pixmap = pm
        self._refresh_overlay()
        self._fade_in()
        self.loaded.emit()

    def _on_failed(self):
        """图像加载失败：清 pixmap、转 failed 态并刷新。"""
        self._status = "failed"
        self._pixmap = None
        self._refresh_overlay()
        self.failed.emit()
        self.update()

    def _fade_in(self):
        """播放或直达图像淡入。

        Note:
            disable_animation 时 tween 以 animated=False 直达终态 1.0；
            否则从 0.0 过渡，时长 500ms 对齐 CSS transition-opacity。
        """
        stop_tween(self, "_fade_anim")
        if not self._disable_animation:
            self.imgOpacity = 0.0
        tween_property(
            self,
            "_fade_anim",
            b"imgOpacity",
            1.0,
            duration=500,
            animated=not self._disable_animation,
        )

    # ============================================================
    # fallback 显隐
    # ============================================================
    def _has_image(self) -> bool:
        """是否已有可绘制的已加载图像。

        Returns:
            status 为 loaded 且 pixmap 非 None 时为 True。
        """
        return self._status == "loaded" and self._pixmap is not None

    def _should_show_fallback(self) -> bool:
        """对齐 HeroUI：无 src、或（有 src 但未加载成功且 showFallback）时显示兜底。"""
        if not self._src:
            return True
        if not self._has_image():
            return self._show_fallback
        return False

    def _refresh_overlay(self):
        """按当前状态决定 fallback 三层的显隐与排布。

        优先级：自定义 fallback widget > name 首字母 > 人像图标；
        决策依据 _should_show_fallback，最后统一走 _layout_overlay。
        """
        show_fb = self._should_show_fallback()

        # 自定义 fallback 优先
        if self._fallback_widget is not None:
            self._fallback_widget.setParent(self)
            self._fallback_widget.setVisible(show_fb)
            self._name_label.setVisible(False)
            self._icon_canvas.setVisible(False)
        elif self._name:
            self._name_label.setText(safe_initials(self._name))
            self._name_label.setVisible(show_fb)
            self._icon_canvas.setVisible(False)
        else:
            self._name_label.setVisible(False)
            self._icon_canvas.setVisible(show_fb)

        self._layout_overlay()
        self.update()

    def _layout_overlay(self):
        """兜底层铺满内容盒子并居中。"""
        rect = self._content_rect().toRect()
        self._name_label.setGeometry(rect)
        self._icon_canvas.setGeometry(rect)
        if self._fallback_widget is not None:
            self._fallback_widget.setGeometry(rect)

    # ============================================================
    # 样式
    # ============================================================
    def _apply_styles(self):
        """按尺寸、配色与状态刷新几何、颜色、效果与光标。

        固定尺寸 = box 边长 + 两侧描边外圈；禁用态挂 50% 半透明效果；
        光标规则：禁用为禁止符、pressable 为手型、其余还原默认。
        """
        side = self._box_side()
        m = self._outer_margin()
        total = side + 2 * m
        self.setFixedSize(total, total)

        s = build_avatar_styles(self._color, self._theme)
        self._style = s

        # 首字母文字色 + 尺寸
        self._name_label.set_size(AVATAR_SIZES[self._size]["text_size"])
        self._name_label.set_color(s["fg"])

        # 默认图标：80% 盒子，跟前景色
        icon_px = int(side * AVATAR_SIZES[self._size]["icon_ratio"])
        self._icon_canvas.apply(self._icon, icon_px, s["fg"])

        self.setEnabled(not self._is_disabled)
        # 禁用态：整控件半透明（图标/文字/自绘环一起变淡）
        if self._is_disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
        else:
            self.setGraphicsEffect(None)

        # 光标：可点击且未禁用 → 手型；禁用 → 禁止
        if self._is_disabled:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        elif self._is_pressable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

        self._refresh_overlay()
        self.update()

    # ============================================================
    # 绘制
    # ============================================================
    def paintEvent(self, event):
        """自绘头像：描边环 → solid 底 → cover 图像。

        Args:
            event: Qt 绘制事件。

        Note:
            图像按 _img_opacity 混合绘制实现 fade-in；全部内容裁剪在
            圆角路径内。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self._content_rect()
        side = self._box_side()
        r_px = self._radius_px(side)

        # 1) 描边环（ring + offset）：先画 ring 色圆角矩形，再挖出 offset 缝隙
        if self._is_bordered:
            self._paint_ring(painter, rect, r_px)

        # 2) 内容裁剪路径
        path = QPainterPath()
        path.addRoundedRect(rect, r_px, r_px)

        # 3) solid 背景（fallback 时可见；有图时被图覆盖）
        painter.save()
        painter.setClipPath(path)
        painter.fillRect(rect, QColor(self._style["bg"]))

        # 4) 图像（cover 铺满 + fade-in opacity）
        if self._has_image():
            painter.setOpacity(max(0.0, min(1.0, self._img_opacity)))
            self._draw_cover(painter, rect)
        painter.restore()
        painter.end()

    def _paint_ring(self, painter: QPainter, content: QRectF, content_r: float):
        """绘制描边环：ring 色整圈 + offset 色缝隙。

        Args:
            painter: 当前 QPainter。
            content: 内容盒几何。
            content_r: 内容盒圆角。

        Note:
            先画 ring 色大圆角矩形，再用 offset 色挖出缝隙，
            视觉上形成 ring 与头像之间的分离带。
        """
        m = self._outer_margin()
        full = QRectF(0, 0, self.width(), self.height())
        ring_r = content_r + m
        # ring 色整圈
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._style["ring_color"]))
        painter.drawRoundedRect(full, ring_r, ring_r)
        # 挖出 offset 缝隙（用背景色）
        gap = QRectF(
            AVATAR_RING_WIDTH,
            AVATAR_RING_WIDTH,
            full.width() - 2 * AVATAR_RING_WIDTH,
            full.height() - 2 * AVATAR_RING_WIDTH,
        )
        gap_r = content_r + AVATAR_RING_OFFSET
        painter.setBrush(QColor(self._style["offset_color"]))
        painter.drawRoundedRect(gap, gap_r, gap_r)
        painter.restore()

    def _draw_cover(self, painter: QPainter, rect: QRectF):
        """object-fit: cover 绘制图像。

        Args:
            painter: 当前 QPainter。
            rect: 目标绘制区域。

        Note:
            取 max 缩放比保证铺满，多余部分裁剪在圆角路径外。
        """
        pm = self._pixmap
        if pm is None or pm.isNull():
            return
        pw, ph = pm.width(), pm.height()
        if pw <= 0 or ph <= 0:
            return
        w, h = rect.width(), rect.height()
        scale = max(w / pw, h / ph)
        tw, th = pw * scale, ph * scale
        ox = rect.x() + (w - tw) / 2
        oy = rect.y() + (h - th) / 2
        painter.drawPixmap(QRectF(ox, oy, tw, th), pm, QRectF(0, 0, pw, ph))

    # ============================================================
    # 交互事件（自定义点击 / hover）
    # ============================================================
    def enterEvent(self, event):
        """鼠标进入：非禁用时发 hovered 信号。

        Args:
            event: Qt 进入事件。
        """
        if not self._is_disabled:
            self.hovered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：复位按压态并（非禁用时）发 unhovered。

        Args:
            event: Qt 离开事件。
        """
        # 离开时若还处于按下态，视为取消按压
        self._is_pressed = False
        if not self._is_disabled:
            self.unhovered.emit()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下：pressable 且左键时记按压态并发 pressed。

        Args:
            event: Qt 鼠标按下事件。
        """
        if (
            self._is_pressable
            and not self._is_disabled
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._is_pressed = True
            self.pressed.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放：发出 released，释放点仍在头像内才算 clicked。

        Args:
            event: Qt 鼠标释放事件。
        """
        if (
            self._is_pressable
            and not self._is_disabled
            and event.button() == Qt.MouseButton.LeftButton
        ):
            was_pressed = self._is_pressed
            self._is_pressed = False
            self.released.emit()
            # 仅当释放点仍在头像范围内才算一次有效点击
            if was_pressed and self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ============================================================
    # Qt Property（fade 动画驱动）
    # ============================================================
    def _get_img_op(self) -> float:
        """Property getter：返回当前图像透明度。

        Returns:
            0.0 ~ 1.0 的透明度值。
        """
        return self._img_opacity

    def _set_img_op(self, v: float):
        """Property setter：写入透明度并触发重绘。

        Args:
            v: 新透明度，由 fade 动画每帧调用。
        """
        self._img_opacity = v
        self.update()

    imgOpacity = Property(float, _get_img_op, _set_img_op)

    # ============================================================
    # 公共 setter / 访问器
    # ============================================================
    def set_src(self, src: ImageSrc):
        """替换图像来源并重新加载。

        Args:
            src: 新图像来源；None 时回到 pending 态走 fallback。

        Note:
            置空 pixmap 与透明度，避免旧图在新加载期间闪现。
        """
        self._src = src
        self._pixmap = None
        self._img_opacity = 0.0
        if src is not None:
            self._status = "loading"
            self._refresh_overlay()
            self._loader.load(src)
        else:
            self._status = "pending"
            self._refresh_overlay()

    def set_name(self, name: str | None):
        """更新姓名并刷新首字母兜底层。

        Args:
            name: 新姓名；None 清空首字母显示。
        """
        self._name = name
        self._refresh_overlay()

    def set_icon(self, icon: str):
        """更新 fallback 图标名并重渲染。

        Args:
            icon: 新图标名。
        """
        self._icon = icon
        self._apply_styles()

    def set_color(self, color: str):
        """切换语义色并重算配色。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._apply_styles()

    def set_radius(self, radius: str):
        """切换圆角档位并重绘。

        Args:
            radius: 圆角档位名。
        """
        self._radius = radius
        self.update()

    def set_size(self, size: str):
        """切换尺寸档位并重算几何。

        Args:
            size: 尺寸档位名；非法值忽略。
        """
        if size not in VALID_AVATAR_SIZES:
            return
        self._size = size
        self._apply_styles()

    def set_bordered(self, bordered: bool):
        """切换描边环并重算尺寸（环占外圈）。

        Args:
            bordered: True 画 ring + offset。
        """
        self._is_bordered = bordered
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        """切换禁用态（半透明 + 禁止光标 + 拦截交互）。

        Args:
            disabled: True 表示禁用。
        """
        self._is_disabled = disabled
        self._apply_styles()

    def set_show_fallback(self, show: bool):
        """切换加载失败时是否显示兜底。

        Args:
            show: True 时失败态也显示首字母 / 图标。
        """
        self._show_fallback = show
        self._refresh_overlay()

    def set_pressable(self, pressable: bool):
        """切换可点击交互（手型光标 + 按压信号）。

        Args:
            pressable: True 启用点击交互。
        """
        self._is_pressable = pressable
        self._apply_styles()

    def status(self) -> str:
        """返回图像加载状态。

        Returns:
            pending / loading / loaded / failed。
        """
        return self._status

    def pixmap(self) -> QPixmap | None:
        """返回已加载的图像。

        Returns:
            当前 QPixmap；未加载成功时为 None。
        """
        return self._pixmap

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 的注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._name_label.set_theme(self._theme)
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._name_label.set_theme(theme)
        self._apply_styles()


__all__ = ["Avatar", "safe_initials"]
