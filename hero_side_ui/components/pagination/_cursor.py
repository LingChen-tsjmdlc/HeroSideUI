"""分页器滑动光标 (_CursorWidget)。

绝对定位浮层(zIndex 在 items 之上)。功能:
  - 跟随 active item 几何 (translateX 等价于 setGeometry)
  - 切换时 scale 1.0 → 1.1 → 1.0 弹簧动效 (HeroUI 招牌)
  - 自绘 active 页码数字 + 主色填充
  - 切换页时新旧数字方向化交叉滚动 (页码增大向上,减小向下)
  - 鼠标穿透,首次出现淡入
"""

from typing import Optional

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from ...core.text_style import make_text_qfont

from ._palette import resolve_cursor_fill, resolve_cursor_text


class _CursorWidget(QWidget):
    """active 页面的高亮光标(浮于 items 之上)。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 视觉状态
        self._color = "primary"
        self._theme = "light"
        self._variant = "flat"
        self._radius_px = 8
        # 当前帧 scale (1.0 ~ 1.1)
        self._scale = 1.0
        # 内部 opacity 字段;真正淡入由父组件外加 QGraphicsOpacityEffect 负责
        self._opacity = 1.0
        # item 实际尺寸 (paint 基准, widget geometry 比这个大,留 pad 给 scale 扩张)
        self._item_w = 0
        self._item_h = 0
        # 双文字: progress 1.0 → 完全显示新文字;0.0 → 完全显示旧文字
        self._page_text = ""
        self._old_page_text = ""
        self._text_progress = 1.0
        self._font_size = 13
        # 文字交叉淡入动画 runner
        self._text_anim: Optional[QVariantAnimation] = None
        # 文字切换偏移幅度 (px)
        self._text_swap_offset = 4.0
        # 当前文字滚动方向:"up" 旧字向上滚出/新字从下方滚入(页码增大);
        # "down" 旧字向下滚出/新字从上方滚入(页码减小)
        self._text_direction = "up"

    # ============================================================
    # 配置 / 状态
    # ============================================================

    def configure(
        self,
        *,
        variant: Optional[str] = None,
        color: Optional[str] = None,
        theme: Optional[str] = None,
        radius_px: Optional[int] = None,
        font_size: Optional[int] = None,
    ):
        if variant is not None:
            self._variant = variant
        if color is not None:
            self._color = color
        if theme is not None:
            self._theme = theme
        if radius_px is not None:
            self._radius_px = int(radius_px)
        if font_size is not None:
            self._font_size = int(font_size)
        self.update()

    def set_item_size(self, w: int, h: int):
        self._item_w = int(w)
        self._item_h = int(h)
        self.update()

    def set_page_text(self, text: str):
        # 直接硬切 (无动画路径用)
        self._page_text = str(text)
        self._old_page_text = ""
        self._text_progress = 1.0
        self._stop_text_anim()
        self.update()

    def has_page_text(self) -> bool:
        """是否已设置过页码文本 (空字符串视为未设置)。"""
        return bool(self._page_text)

    def start_text_swap(
        self,
        new_text: str,
        *,
        duration_ms: int = 300,
        direction: str = "up",
    ):
        """启动新旧文字方向化交叉滚动动画 (与 cursor 滑动同步调用)。

        direction:
            "up"   - 页码增大方向,旧字向上滚出 + 新字从下方滚入
            "down" - 页码减小方向,旧字向下滚出 + 新字从上方滚入
        """
        new_text = str(new_text)
        # 文字未变 / 之前没有有效文字 → 不需要动画
        if new_text == self._page_text:
            return
        if not self._page_text:
            self._page_text = new_text
            self._text_progress = 1.0
            self.update()
            return
        self._stop_text_anim()
        self._old_page_text = self._page_text
        self._page_text = new_text
        self._text_direction = direction if direction in ("up", "down") else "up"
        self._text_progress = 0.0
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(max(1, int(duration_ms)))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _step(v):
            try:
                self._text_progress = float(v)
                self.update()
            except RuntimeError:
                pass

        def _done():
            self._text_progress = 1.0
            self._old_page_text = ""
            self._text_anim = None
            self.update()

        anim.valueChanged.connect(_step)
        anim.finished.connect(_done)
        self._text_anim = anim
        anim.start()

    def _stop_text_anim(self):
        if self._text_anim is not None:
            try:
                self._text_anim.stop()
            except RuntimeError:
                pass
            self._text_anim = None

    def set_scale(self, scale: float):
        self._scale = float(scale)
        self.update()

    def set_opacity(self, opacity: float):
        self._opacity = max(0.0, min(1.0, float(opacity)))
        self.update()

    # ============================================================
    # 绘制
    # ============================================================

    def paintEvent(self, ev):
        if self.width() <= 0 or self.height() <= 0:
            return
        if self._opacity <= 0.0:
            return
        if self._item_w <= 0 or self._item_h <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setOpacity(self._opacity)

        # 居中放置 item 矩形,按 _scale 围绕中心扩张
        rect = self._item_rect_scaled()

        # 主体填充
        fill = resolve_cursor_fill(self._color, self._theme)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius_px, self._radius_px)
        p.fillPath(path, fill)

        # active 页码: 双文字交叉淡入 (新文字从下方上移到位,旧文字向上淡出)
        if self._page_text or self._old_page_text:
            self._paint_swap_text(p, rect)

        p.end()

    def _paint_swap_text(self, p: QPainter, rect: QRectF):
        """绘制交叉淡入的新旧文字。"""
        text_color = resolve_cursor_text(self._color, self._theme)
        font = make_text_qfont(size=self._font_size, weight="medium")
        p.setFont(font)

        progress = max(0.0, min(1.0, self._text_progress))
        offset = self._text_swap_offset
        # "up" 滚动方向 sign = -1: 旧字 0→-offset, 新字 +offset→0
        # "down" 滚动方向 sign = +1: 旧字 0→+offset, 新字 -offset→0
        sign = -1.0 if self._text_direction == "up" else 1.0

        # 旧文字: 沿 sign 方向滚出
        if self._old_page_text and progress < 1.0:
            old_alpha = 1.0 - progress
            old_dy = sign * offset * progress
            old_color = QColor(text_color)
            old_color.setAlphaF(text_color.alphaF() * old_alpha)
            p.setPen(old_color)
            old_rect = QRectF(rect)
            old_rect.translate(0, old_dy)
            p.drawText(old_rect, Qt.AlignmentFlag.AlignCenter, self._old_page_text)

        # 新文字: 从 sign 反方向滚入
        if self._page_text:
            new_alpha = progress if self._old_page_text else 1.0
            new_dy = -sign * offset * (1.0 - progress) if self._old_page_text else 0.0
            new_color = QColor(text_color)
            new_color.setAlphaF(text_color.alphaF() * new_alpha)
            p.setPen(new_color)
            new_rect = QRectF(rect)
            new_rect.translate(0, new_dy)
            p.drawText(new_rect, Qt.AlignmentFlag.AlignCenter, self._page_text)

    def _item_rect_scaled(self) -> QRectF:
        """以 widget 中心为锚点,按 _scale 扩张 item 矩形。"""
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        sw = self._item_w * self._scale
        sh = self._item_h * self._scale
        return QRectF(cx - sw / 2.0, cy - sh / 2.0, sw, sh)


__all__ = ["_CursorWidget"]
