"""HeroSideUI Avatar — HeroUI v2 Avatar 组件 PySide6 复刻。

样式来源:  https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/avatar.ts
组件来源:  https://github.com/heroui-inc/heroui/tree/main/packages/components/avatar

结构:
    Avatar (QWidget)
    ├── paintEvent 自绘：solid 背景 + 圆角 clip 的图像 + isBordered 描边环
    └── _fallback (Text 首字母 / _IconCanvas 默认人像 / 自定义 QWidget)，
        仅在无图 / 图未加载 / showFallback 时叠在上层显示

图像加载复用 ImageLoader（本地/URL/QPixmap 统一），加载完成 fade-in。
name 存在时 fallback 显示首字母（safe_initials），否则显示默认人像 SVG。
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ...core import ThemeProvider
from ...themes import (
    AVATAR_RING_OFFSET,
    AVATAR_RING_WIDTH,
    AVATAR_SIZES,
    RADIUS,
    VALID_AVATAR_SIZES,
)
from ...utils import load_svg_icon
from ..image._loader import ImageLoader, ImageSrc
from ..text import Text
from ._styling import build_avatar_styles


def safe_initials(name: str) -> str:
    """从姓名生成首字母缩写（对齐 HeroUI safeInitials）。

    取首个单词与末个单词的首字符，最多两个字母，转大写。
    单词切分不出时（如中文无空格）返回首字符。
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

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_name = "heroui--avatar-person"
        self._px = 24
        self._color = "#ffffff"

    def apply(self, icon_name: str, px: int, color: str):
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
        name: Optional[str] = None,
        icon: Optional[str] = None,
        fallback: Optional[QWidget] = None,
        color: str = "default",
        radius: str = "full",
        size: str = "md",
        is_bordered: bool = False,
        is_disabled: bool = False,
        show_fallback: bool = False,
        disable_animation: bool = False,
        is_pressable: bool = False,
        on_click: Optional[Callable[[], None]] = None,
        on_hover: Optional[Callable[[bool], None]] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
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
        self._theme = (
            ThemeProvider.instance().current_theme if theme == "auto" else theme
        )

        # 图像状态
        self._status = "pending"  # pending / loading / loaded / failed
        self._pixmap: Optional[QPixmap] = None
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
        self._name_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        # 默认人像图标画布
        self._icon_canvas = _IconCanvas(self)

        # fade-in 动画（图像 opacity 0→1，对齐 transition-opacity 500ms）
        self._fade_anim = QPropertyAnimation(self, b"imgOpacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

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
        if self._radius == "full":
            return side / 2.0
        token_px = int(RADIUS.get(self._radius, RADIUS["md"]).rstrip("px"))
        return float(min(token_px, side // 2))

    # ============================================================
    # 加载
    # ============================================================
    def _kick_load(self):
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
        self._status = "loaded"
        self._pixmap = pm
        self._refresh_overlay()
        self._fade_in()
        self.loaded.emit()

    def _on_failed(self):
        self._status = "failed"
        self._pixmap = None
        self._refresh_overlay()
        self.failed.emit()
        self.update()

    def _fade_in(self):
        if self._disable_animation:
            self._img_opacity = 1.0
            self.update()
            return
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    # ============================================================
    # fallback 显隐
    # ============================================================
    def _has_image(self) -> bool:
        return self._status == "loaded" and self._pixmap is not None

    def _should_show_fallback(self) -> bool:
        """对齐 HeroUI：无 src、或（有 src 但未加载成功且 showFallback）时显示兜底。"""
        if not self._src:
            return True
        if not self._has_image():
            return self._show_fallback
        return False

    def _refresh_overlay(self):
        """根据当前状态决定 fallback 各层显隐。"""
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
        """object-fit: cover 绘制图像。"""
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
        if not self._is_disabled:
            self.hovered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 离开时若还处于按下态，视为取消按压
        self._is_pressed = False
        if not self._is_disabled:
            self.unhovered.emit()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
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
        return self._img_opacity

    def _set_img_op(self, v: float):
        self._img_opacity = v
        self.update()

    imgOpacity = Property(float, _get_img_op, _set_img_op)

    # ============================================================
    # 公共 setter / 访问器
    # ============================================================
    def set_src(self, src: ImageSrc):
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

    def set_name(self, name: Optional[str]):
        self._name = name
        self._refresh_overlay()

    def set_icon(self, icon: str):
        self._icon = icon
        self._apply_styles()

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_radius(self, radius: str):
        self._radius = radius
        self.update()

    def set_size(self, size: str):
        if size not in VALID_AVATAR_SIZES:
            return
        self._size = size
        self._apply_styles()

    def set_bordered(self, bordered: bool):
        self._is_bordered = bordered
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._apply_styles()

    def set_show_fallback(self, show: bool):
        self._show_fallback = show
        self._refresh_overlay()

    def set_pressable(self, pressable: bool):
        self._is_pressable = pressable
        self._apply_styles()

    def status(self) -> str:
        return self._status

    def pixmap(self) -> Optional[QPixmap]:
        return self._pixmap

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
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
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._name_label.set_theme(theme)
        self._apply_styles()


__all__ = ["Avatar", "safe_initials"]
