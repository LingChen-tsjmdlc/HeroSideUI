"""_CursorWidget — Tabs 的"光标"，跟随选中项滑动的高亮背景（私有）。

走 paintEvent 自绘 + tween_geometry 驱动位移；圆角根据 variant 自适应。
"""

from PySide6.QtCore import QRectF

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget
from ._helpers import _resolve_cursor_fill




# ============================================================
# CursorWidget: 选中指示器（矩形填充 / 下划线）
# ============================================================


class _CursorWidget(QWidget):
    """绝对定位的指示器层。父是 TabList。

    根据 variant 绘制不同形态:
      - solid/bordered/light: 整块圆角矩形 + (color=default 时画 shadow-small)
      - underlined: 底部 2px 80% 宽度的水平线（垂直方向布局时改为右/左侧 2px 线）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._variant = "solid"
        self._color = "default"
        self._theme = "light"
        self._radius_px = 8
        self._placement = "top"
        self._underline_h = 2
        self._underline_ratio = 0.8

    def configure(self, *, variant=None, color=None, theme=None,
                  radius_px=None, placement=None,
                  underline_h=None, underline_ratio=None):
        if variant is not None: self._variant = variant
        if color is not None: self._color = color
        if theme is not None: self._theme = theme
        if radius_px is not None: self._radius_px = radius_px
        if placement is not None: self._placement = placement
        if underline_h is not None: self._underline_h = underline_h
        if underline_ratio is not None: self._underline_ratio = underline_ratio
        self.update()

    def paintEvent(self, ev):
        if self.width() <= 0 or self.height() <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self._variant == "underlined":
            self._paint_underline(p)
        else:
            self._paint_filled(p)
        p.end()

    def _paint_filled(self, p: QPainter):
        rect = QRectF(0, 0, self.width(), self.height())
        fill = _resolve_cursor_fill(self._variant, self._color, self._theme)
        if fill is None:
            return

        # default 色（亮色 = 白）画一个 shadow-small：底部一层柔和阴影
        if self._color == "default":
            shadow = QColor(0, 0, 0, 26 if self._theme == "light" else 0)
            if shadow.alpha() > 0:
                # 简化版 shadow-small: 向下 2px、blur 3px 的轻阴影
                for i in range(3):
                    a = int(shadow.alpha() * (1 - i / 3))
                    if a <= 0:
                        continue
                    sc = QColor(shadow.red(), shadow.green(), shadow.blue(), a)
                    sr = rect.adjusted(-i, -i + 1, i, i + 1)
                    path = QPainterPath()
                    path.addRoundedRect(sr, self._radius_px, self._radius_px)
                    p.fillPath(path, sc)

        path = QPainterPath()
        path.addRoundedRect(rect, self._radius_px, self._radius_px)
        p.fillPath(path, fill)

    def _paint_underline(self, p: QPainter):
        line_color = _resolve_cursor_fill(self._variant, self._color, self._theme)
        if line_color is None:
            return
        h = self._underline_h
        ratio = self._underline_ratio
        if self._placement in ("start", "end"):
            # 垂直方向：在 tab 的右边或左边画一条竖线
            line_w = h
            line_h = self.height() * ratio
            x = (self.width() - line_w) / 2 if self._placement == "top" else 0
            if self._placement == "start":
                # 列表在左，文本在右；下划线画在右边缘
                x = self.width() - line_w
            else:  # end
                x = 0
            y = (self.height() - line_h) / 2
            p.fillRect(QRectF(x, y, line_w, line_h), line_color)
        else:
            # 水平方向：底部
            line_w = self.width() * ratio
            x = (self.width() - line_w) / 2
            if self._placement == "bottom":
                # bottom 布局下 tabList 在 panel 下方，cursor 仍画在 tab 底部
                y = self.height() - h
            else:
                y = self.height() - h
            p.fillRect(QRectF(x, y, line_w, h), line_color)
