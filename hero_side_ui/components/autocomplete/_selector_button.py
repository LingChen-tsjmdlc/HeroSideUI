"""_SelectorButton — Autocomplete 右侧的下拉箭头按钮（私有）。

点击时切换 popover 开/关。
"""

from PySide6.QtGui import QPixmap
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import QPushButton

from ...animation import stop_tween, tween_value
from ...core import ThemeProvider
from ...utils import load_svg_icon




# ============================================================
# Selector 按钮：能 tween 旋转
# ============================================================
class _SelectorButton(QPushButton):
    """selectorButton：底层 svg 图标 + 通过 QTransform 旋转动画。

    由于 QIcon 已经 rasterize，QSS `transform: rotate()` 在 PySide 无效；
    我们自己 paint 时把 pixmap 用 QTransform 旋转 ``self._angle`` 角度。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFlat(True)
        self.setStyleSheet("border: 0; background: transparent; padding: 0;")
        self._pixmap: Optional[QPixmap] = None
        self._angle: float = 0.0  # 0=指向下；180=指向上
        self._angle_anim_runner = None  # tween runner

    def set_pixmap(self, pix: QPixmap):
        self._pixmap = pix
        self.update()

    def angle(self) -> float:
        return self._angle

    def set_angle(self, deg: float, *, animated: bool, duration: int = 150):
        if animated and self._angle != deg:
            tween_value(
                self,
                "_angle_anim_runner",
                float(self._angle),
                float(deg),
                self._on_angle_step,
                duration=duration,
            )
        else:
            self._angle = deg
            self.update()

    def _on_angle_step(self, v):
        self._angle = float(v)
        self.update()

    def paintEvent(self, e):
        if self._pixmap is None or self._pixmap.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        # 在 button 中心绘制旋转后的 pixmap
        cx = self.width() / 2
        cy = self.height() / 2
        p.translate(cx, cy)
        p.rotate(self._angle)
        w = self._pixmap.width()
        h = self._pixmap.height()
        # 高 DPI 时 pixmap 实际像素是 deviceWidth/PixelRatio
        dpr = self._pixmap.devicePixelRatio() or 1.0
        dw = w / dpr
        dh = h / dpr
        p.drawPixmap(int(-dw / 2), int(-dh / 2), self._pixmap)
        p.end()
