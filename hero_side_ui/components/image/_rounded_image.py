"""HeroSideUI Image — 圆角图像层。

QLabel 子类，承担：
- 圆角 clip 自绘（QSS border-radius 不真实裁剪）
- object-fit 五种语义
- isZoomed scale 与 fade-in 两个 Qt Property（动画驱动）
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from ._styling import resolve_radius_px


class _RoundedImage(QLabel):
    """圆角图像层，hover 缩放 + fade-in 通过 Qt Property 驱动。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        # QLabel 默认会画 palette 背景把下层 _blurred 整片挡住
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._pixmap: Optional[QPixmap] = None
        self._radius: str = "lg"
        self._object_fit: str = "cover"
        self._zoom: float = 1.0
        self._opacity: float = 0.0  # data-loaded 后 0→1

    # ============== Qt Properties (供动画驱动) ==============
    def _get_zoom(self) -> float:
        return self._zoom

    def _set_zoom(self, v: float):
        self._zoom = v
        self.update()

    zoomFactor = Property(float, _get_zoom, _set_zoom)

    def _get_op(self) -> float:
        return self._opacity

    def _set_op(self, v: float):
        self._opacity = v
        self.update()

    fadeOpacity = Property(float, _get_op, _set_op)

    # ============================================================
    def set_source_pixmap(self, pm: Optional[QPixmap]):
        self._pixmap = pm
        self.update()

    def set_radius(self, r: str):
        self._radius = r
        self.update()

    def set_object_fit(self, fit: str):
        self._object_fit = fit
        self.update()

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(max(0.0, min(1.0, self._opacity)))

        w, h = self.width(), self.height()
        r_px = resolve_radius_px(self._radius, w, h)

        # 圆角裁剪
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), r_px, r_px)
        painter.setClipPath(path)

        # 按 object-fit 计算目标区域，再叠加 zoom 缩放
        pm = self._pixmap
        scaled_w = int(w * self._zoom)
        scaled_h = int(h * self._zoom)
        target = self._fit_size(pm.size(), QSize(scaled_w, scaled_h), self._object_fit)
        offset_x = (w - target.width()) // 2
        offset_y = (h - target.height()) // 2
        painter.drawPixmap(offset_x, offset_y, target.width(), target.height(), pm)
        painter.end()

    @staticmethod
    def _fit_size(src: QSize, dst: QSize, fit: str) -> QSize:
        """按 CSS object-fit 语义计算目标绘制尺寸。"""
        if src.width() == 0 or src.height() == 0:
            return dst
        sx = dst.width() / src.width()
        sy = dst.height() / src.height()
        if fit == "fill":
            return dst
        if fit == "none":
            return src
        if fit == "contain":
            s = min(sx, sy)
            return QSize(int(src.width() * s), int(src.height() * s))
        if fit == "scale-down":
            # 取 none 与 contain 中较小者
            s = min(sx, sy, 1.0)
            return QSize(int(src.width() * s), int(src.height() * s))
        # 默认 cover：按长边比例放大铺满
        s = max(sx, sy)
        return QSize(int(src.width() * s), int(src.height() * s))


__all__ = ["_RoundedImage"]
