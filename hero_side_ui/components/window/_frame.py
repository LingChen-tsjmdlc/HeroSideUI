"""窗口外框：覆盖层负责擦出圆角并描边；非原生平台另有 8 个缩放热区。"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ...themes import WINDOW_SPEC


def _corner_params(radius: float, smoothing: float, budget: float) -> tuple:
    """超椭圆一个角的几何参数（Figma 的 corner smoothing 算法，与苹果连续圆角同类）。

    Args:
        radius: 圆角半径。
        smoothing: 平滑度 0~1。
        budget: 一条边上留给一个角的最大长度，通常是短边的一半。

    Returns:
        (a, b, c, d, p, 圆弧弦长, 圆弧夹角度数, 实际半径)。p 是角在边上占用的长度。
    """
    radius = min(radius, budget)
    smoothing = max(0.0, min(smoothing, budget / radius - 1)) if radius > 0 else 0.0
    p = min((1 + smoothing) * radius, budget)
    arc_deg = 90 * (1 - smoothing)
    arc_len = math.sin(math.radians(arc_deg / 2)) * radius * math.sqrt(2)
    alpha = (90 - arc_deg) / 2
    p3p4 = radius * math.tan(math.radians(alpha / 2))
    beta = 45 * smoothing
    c = p3p4 * math.cos(math.radians(beta))
    d = c * math.tan(math.radians(beta))
    b = (p - arc_len - c - d) / 3
    a = 2 * b
    return a, b, c, d, p, arc_len, arc_deg, radius, beta


def rounded_path(rect: QRectF, radius: float, smoothing: float | None = None) -> QPainterPath:
    """超椭圆圆角矩形路径（smoothing 为 0 时就是普通圆角矩形）。

    Args:
        rect: 矩形。
        radius: 圆角半径。
        smoothing: 平滑度 0~1；None 取 WINDOW_SPEC["corner_smoothing"]。
    """
    if smoothing is None:
        smoothing = WINDOW_SPEC["corner_smoothing"]
    path = QPainterPath()
    w, h = rect.width(), rect.height()
    if radius <= 0 or w <= 0 or h <= 0:
        path.addRect(rect)
        return path
    a, b, c, d, p, arc_len, arc_deg, r, beta = _corner_params(radius, smoothing, min(w, h) / 2)
    k = 4 / 3 * math.tan(math.radians(arc_deg / 4))  # 圆弧的三次贝塞尔近似系数
    cb, sb = math.cos(math.radians(beta)), math.sin(math.radians(beta))
    cb2, sb2 = sb, cb  # 圆弧终点切线方向 (90°-beta)

    # 以"右上角在原点、x 向左为负、y 向下为正"的局部坐标写一个角，再旋转到四个角
    seg = [
        ((-p + a, 0), (-p + a + b, 0), (-p + a + b + c, d)),
        (
            (-p + a + b + c + k * r * cb, d + k * r * sb),
            (-p + a + b + c + arc_len - k * r * cb2, d + arc_len - k * r * sb2),
            (-p + a + b + c + arc_len, d + arc_len),
        ),
        (
            (-p + a + b + c + arc_len + d, d + arc_len + c),
            (-p + a + b + c + arc_len + d, d + arc_len + b + c),
            (0, p),
        ),
    ]
    x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
    maps = [  # 依次：右上、右下、左下、左上
        lambda x, y: QPointF(x1 + x, y0 + y),
        lambda x, y: QPointF(x1 - y, y1 + x),
        lambda x, y: QPointF(x0 - x, y1 - y),
        lambda x, y: QPointF(x0 + y, y0 - x),
    ]
    path.moveTo(QPointF(x0 + p, y0))  # 从顶边上左上角的终点出发，顺时针走一圈
    for m in maps:
        path.lineTo(m(-p, 0))
        for c1, c2, e in seg:
            path.cubicTo(m(*c1), m(*c2), m(*e))
    path.closeSubpath()
    return path


class _FrameOverlay(QWidget):
    """盖在窗口最上层的透明覆盖层，鼠标事件全部穿透。

    Note:
        子控件会盖住窗口四角，所以不能只靠窗口自己画圆角：这里用 Clear 合成模式把
        圆角外的像素擦成透明，再沿弧线描 1px 边。实验里子控件重绘、窗口缩放、
        1.0 / 1.5 / 2.0 缩放下四角都没有残留方角。
    """

    def __init__(self, parent: QWidget):
        """创建覆盖层。

        Args:
            parent: 窗口。
        """
        super().__init__(parent)
        self._radius = 0
        self._border = QColor("#e4e4e7")
        self._draw_border = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def apply(self, radius: int, border: QColor, draw_border: bool):
        """更新圆角、描边色与是否描边。

        Args:
            radius: 圆角像素；0 表示直角。
            border: 描边颜色。
            draw_border: 是否画描边（最大化 / 全屏时不画）。
        """
        self._radius = radius
        self._border = QColor(border)
        self._draw_border = draw_border
        self.update()

    def paintEvent(self, _event):
        """擦掉圆角外区域，再描边。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        if self._radius > 0:
            # 擦除区域比圆角向内多收 0.75px：抗锯齿的边界像素会被整格擦净，不会漏出子控件
            # 方角上的浅色（否则圆角外有一圈半透明毛边）；弧线本身由下面的描边补回。
            outside = QPainterPath()
            outside.addRect(rect)
            outside = outside.subtracted(
                rounded_path(rect.adjusted(0.75, 0.75, -0.75, -0.75), max(0.0, self._radius - 0.75))
            )
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillPath(outside, Qt.GlobalColor.black)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if not self._draw_border:
            return
        p.setPen(QPen(self._border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        inner = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        if self._radius > 0:
            p.drawPath(rounded_path(inner, max(0.0, self._radius - 0.5)))
        else:
            p.drawRect(inner)


# 热区名 → (光标, 对应边)
_GRIP_DEFS = {
    "left": (Qt.CursorShape.SizeHorCursor, Qt.Edge.LeftEdge),
    "right": (Qt.CursorShape.SizeHorCursor, Qt.Edge.RightEdge),
    "top": (Qt.CursorShape.SizeVerCursor, Qt.Edge.TopEdge),
    "bottom": (Qt.CursorShape.SizeVerCursor, Qt.Edge.BottomEdge),
    "top_left": (Qt.CursorShape.SizeFDiagCursor, Qt.Edge.TopEdge | Qt.Edge.LeftEdge),
    "bottom_right": (Qt.CursorShape.SizeFDiagCursor, Qt.Edge.BottomEdge | Qt.Edge.RightEdge),
    "top_right": (Qt.CursorShape.SizeBDiagCursor, Qt.Edge.TopEdge | Qt.Edge.RightEdge),
    "bottom_left": (Qt.CursorShape.SizeBDiagCursor, Qt.Edge.BottomEdge | Qt.Edge.LeftEdge),
}


class _Grip(QWidget):
    """单个缩放热区：悬停换光标，按下请求系统缩放。"""

    def __init__(self, name: str, parent: QWidget):
        """创建热区。

        Args:
            name: 热区名，见 _GRIP_DEFS。
            parent: 窗口。
        """
        super().__init__(parent)
        cursor, edges = _GRIP_DEFS[name]
        self._edges = edges
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def mousePressEvent(self, event):
        """左键按下：交给系统开始缩放。"""
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemResize(self._edges)
            event.accept()
            return
        super().mousePressEvent(event)


class _GripSet:
    """8 个缩放热区的集合，只在非原生平台使用（Windows 走原生命中测试）。"""

    def __init__(self, window: QWidget):
        """创建 8 个热区，初始隐藏。

        Args:
            window: 宿主窗口。
        """
        self._grips = {name: _Grip(name, window) for name in _GRIP_DEFS}
        self.set_active(False)

    def set_active(self, active: bool):
        """整体启用 / 停用。

        Args:
            active: False 时全部隐藏，不再拦截鼠标。
        """
        for g in self._grips.values():
            g.setVisible(active)

    def relayout(self, width: int, height: int, edge: int):
        """按窗口尺寸摆放热区并置顶。

        Args:
            width: 窗口宽。
            height: 窗口高。
            edge: 热区厚度。
        """
        g = self._grips
        e = edge
        g["left"].setGeometry(0, e, e, max(0, height - 2 * e))
        g["right"].setGeometry(width - e, e, e, max(0, height - 2 * e))
        g["top"].setGeometry(e, 0, max(0, width - 2 * e), e)
        g["bottom"].setGeometry(e, height - e, max(0, width - 2 * e), e)
        g["top_left"].setGeometry(0, 0, e, e)
        g["top_right"].setGeometry(width - e, 0, e, e)
        g["bottom_left"].setGeometry(0, height - e, e, e)
        g["bottom_right"].setGeometry(width - e, height - e, e, e)
        for w in g.values():
            w.raise_()


__all__ = ["_FrameOverlay", "_GripSet", "rounded_path"]
