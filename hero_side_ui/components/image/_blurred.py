"""Image isBlurred 副本图层：saturated pixmap + 模糊，默认 10px 可倍率调。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsBlurEffect, QLabel, QWidget

# 处理前先缩放到的最大边长。模糊副本会被 blur 抹掉细节，
# 缩到 200px 既能让逐像素 saturate 飞快，又不影响视觉。
_MAX_PROCESS_SIZE = 200

# 默认模糊半径（px）——比 HeroUI 原生 16px 温和一档
_DEFAULT_BLUR_RADIUS = 10.0


def _saturate(image: QImage, factor: float = 1.5) -> QImage:
    """模拟 CSS saturate(150%)：基于 HSV-S 通道缩放每个像素。

    Args:
        image: 源 QImage。
        factor: 饱和度倍率，默认 1.5。

    Returns:
        转为 ARGB32 并逐像素调整饱和度后的新 QImage；空图原样返回。
    """
    if image.isNull():
        return image
    img = image.convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    for y in range(h):
        for x in range(w):
            c = img.pixelColor(x, y)
            hue, sat, val, alpha = c.getHsv()
            sat = max(0, min(255, int(sat * factor)))
            c.setHsv(hue, sat, val, alpha)
            img.setPixelColor(x, y, c)
    return img


def _apply_alpha(pixmap: QPixmap, alpha: float) -> QPixmap:
    """整图 alpha 预乘。

    Args:
        pixmap: 源 QPixmap。
        alpha: 目标不透明度 0.0 ~ 1.0。

    Returns:
        用 DestinationIn 涂半透明遮罩后的新 QPixmap；空图原样返回。
    """
    if pixmap.isNull():
        return pixmap
    out = QPixmap(pixmap.size())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.fillRect(out.rect(), QColor(0, 0, 0, int(alpha * 255)))
    painter.end()
    return out


def _shrink_for_processing(pm: QPixmap) -> QPixmap:
    """把图缩到 _MAX_PROCESS_SIZE 内，便于像素级 saturate。

    Args:
        pm: 源 QPixmap。

    Returns:
        保持宽高比缩到 200px 内的 QPixmap；原本就不超长的原样返回。
    """
    if pm.isNull():
        return pm
    if max(pm.width(), pm.height()) <= _MAX_PROCESS_SIZE:
        return pm
    return pm.scaled(
        _MAX_PROCESS_SIZE,
        _MAX_PROCESS_SIZE,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class BlurredImage(QLabel):
    """wrapper 底层（z=0）的模糊副本图层。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        blur_amount: float = 1.0,
    ):
        """创建模糊副本图层。

        Args:
            parent: Qt 父对象。
            blur_amount: 模糊强度倍率；默认 1.0 对应 10px 半径。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setScaledContents(True)

        # 默认 10px，blur_amount 为倍率调节
        self._blur = QGraphicsBlurEffect(self)
        self._blur.setBlurRadius(_DEFAULT_BLUR_RADIUS * max(0.0, blur_amount))
        self._blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        self.setGraphicsEffect(self._blur)

        self._processed: QPixmap | None = None

    def set_blur_amount(self, amount: float):
        """运行期调整模糊强度倍率。

        Args:
            amount: 新倍率；负值按 0 处理。
        """
        self._blur.setBlurRadius(_DEFAULT_BLUR_RADIUS * max(0.0, float(amount)))

    def set_source(self, pixmap: QPixmap):
        """设置图源并做 shrink → saturate(1.5) → alpha=0.3 预处理。

        Args:
            pixmap: 源 QPixmap；None 或空图时清空图层。
        """
        if pixmap is None or pixmap.isNull():
            self._processed = None
            self.clear()
            return
        small = _shrink_for_processing(pixmap)
        sat_image = _saturate(small.toImage(), 1.5)
        sat_pixmap = QPixmap.fromImage(sat_image)
        self._processed = _apply_alpha(sat_pixmap, 0.30)
        self.setPixmap(self._processed)


__all__ = ["BlurredImage"]
