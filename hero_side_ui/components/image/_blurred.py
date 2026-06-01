"""Image isBlurred 副本图层。

对应 HeroUI:
    blur-lg (≈ 16px) + scale-105 + saturate-150 + opacity-30 + translate-y-1

用一份 saturated 后的 QPixmap 配合 QGraphicsBlurEffect 实现。
默认 blur 半径调为 10px（比 HeroUI 原生更温和），
可通过 blur_amount 倍率调整。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QGraphicsBlurEffect, QLabel, QWidget

# 处理前先缩放到的最大边长。模糊副本会被 blur 抹掉细节，
# 缩到 200px 既能让逐像素 saturate 飞快，又不影响视觉。
_MAX_PROCESS_SIZE = 200

# 默认模糊半径（px）——比 HeroUI 原生 16px 温和一档
_DEFAULT_BLUR_RADIUS = 10.0


def _saturate(image: QImage, factor: float = 1.5) -> QImage:
    """模拟 CSS saturate(150%)：基于 HSV-S 通道缩放每个像素。"""
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
    """整图 alpha 预乘——用 DestinationIn 涂半透明遮罩。"""
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
    """把图缩到 _MAX_PROCESS_SIZE 内，便于像素级 saturate。"""
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
        parent: Optional[QWidget] = None,
        blur_amount: float = 1.0,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setScaledContents(True)

        # 默认 10px，blur_amount 为倍率调节
        self._blur = QGraphicsBlurEffect(self)
        self._blur.setBlurRadius(_DEFAULT_BLUR_RADIUS * max(0.0, blur_amount))
        self._blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        self.setGraphicsEffect(self._blur)

        self._processed: Optional[QPixmap] = None

    def set_blur_amount(self, amount: float):
        """运行期调整模糊强度倍率。"""
        self._blur.setBlurRadius(_DEFAULT_BLUR_RADIUS * max(0.0, float(amount)))

    def set_source(self, pixmap: QPixmap):
        """设置图源；内部做 shrink → saturate(1.5) → alpha=0.3 预处理。"""
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
