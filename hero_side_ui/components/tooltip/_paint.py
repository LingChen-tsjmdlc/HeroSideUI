"""Tooltip 绘制 / 颜色 / 圆角 mixin。

为什么独立：tooltip.py 太大，把"颜色解析 + 圆角解析 + paintEvent + 箭头绘制"
这些纯渲染逻辑（不涉及事件/动画/状态机）剥出来。

宿主类需要提供以下属性/方法（已在 Tooltip 上）：
    self._color, self._theme, self._radius, self._shadow, self._show_arrow,
    self._actual_placement, self._scale_proxy, self._frame_margins(),
    self.width(), self.height(), self.rect()
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPainterPath

from ...themes import HEROUI_COLORS, POPOVER_SHADOWS
from ._constants import ARROW_SIZE, ARROW_INSET

__all__ = ["_TooltipPaintMixin"]


class _TooltipPaintMixin:
    """Tooltip 颜色 / 圆角 / 绘制相关 mixin。"""

    # ---- 颜色 ----
    def _bg_color(self) -> QColor:
        is_dark = self._theme == "dark"  # type: ignore[attr-defined]
        if self._color == "default":  # type: ignore[attr-defined]
            return QColor("#ffffff" if not is_dark else "#27272a")
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])  # type: ignore[attr-defined]
        return QColor(c[500])

    def _text_color(self) -> QColor:
        is_dark = self._theme == "dark"  # type: ignore[attr-defined]
        if self._color == "default":  # type: ignore[attr-defined]
            return QColor("#11181c" if not is_dark else "#ecedee")
        if self._color == "warning":  # type: ignore[attr-defined]
            return QColor("#000000")
        return QColor("#ffffff")

    # ---- 圆角 ----
    def _resolve_radius(self) -> float:
        if self._radius == "none":  # type: ignore[attr-defined]
            return 0.0
        if self._radius == "full":  # type: ignore[attr-defined]
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 8))  # type: ignore[attr-defined]

    def _content_rect_size(self) -> QSize:
        m = self._frame_margins()  # type: ignore[attr-defined]
        return QSize(
            max(0, self.width() - m[0] - m[2]),  # type: ignore[attr-defined]
            max(0, self.height() - m[1] - m[3]),  # type: ignore[attr-defined]
        )

    # ---- paintEvent ----
    def paintEvent(self, event):
        painter = QPainter(self)  # type: ignore[arg-type]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 动画期间：只画缩放后的 pixmap
        if self._scale_proxy.is_active():  # type: ignore[attr-defined]
            w, h = self.width(), self.height()  # type: ignore[attr-defined]
            m = self._frame_margins()  # type: ignore[attr-defined]
            place = self._actual_placement  # type: ignore[attr-defined]
            content_rect = QRectF(m[0], m[1], w - m[0] - m[2], h - m[1] - m[3])
            if place.startswith("top"):
                cx, cy = content_rect.center().x(), content_rect.bottom()
            elif place.startswith("bottom"):
                cx, cy = content_rect.center().x(), content_rect.top()
            elif place.startswith("left"):
                cx, cy = content_rect.right(), content_rect.center().y()
            elif place.startswith("right"):
                cx, cy = content_rect.left(), content_rect.center().y()
            else:
                cx, cy = content_rect.center().x(), content_rect.center().y()
            self._scale_proxy.draw(painter, self.rect(), anchor=(cx, cy))  # type: ignore[attr-defined]
            return

        m = self._frame_margins()  # type: ignore[attr-defined]
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["sm"])  # type: ignore[attr-defined]
        bg = self._bg_color()
        radius = self._resolve_radius()

        content_rect = QRectF(
            m[0], m[1], self.width() - m[0] - m[2], self.height() - m[1] - m[3]  # type: ignore[attr-defined]
        )

        # 阴影
        if cfg["layers"] > 0:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(cfg["layers"]):
                t = (i + 1) / cfg["layers"]
                grow = cfg["blur"] * (1 - t) + 1
                off = cfg["offset_y"] * (1 - t)
                rect = content_rect.adjusted(-grow, -grow + off, grow, grow + off)
                alpha = int(cfg["alpha"] * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(rect, radius, radius)
            painter.restore()

        # 主体
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)

        # 箭头
        if self._show_arrow:  # type: ignore[attr-defined]
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        """绘制箭头。

        - top/bottom 系列：底/顶边上；start→靠左，end→靠右，无后缀→居中
        - left/right 系列：右/左边上；start→靠上，end→靠下，无后缀→居中
        """
        place = self._actual_placement  # type: ignore[attr-defined]
        a = ARROW_SIZE
        path = QPainterPath()
        inset = ARROW_INSET
        edge_offset = 10

        if place.startswith("top"):
            base_y = content_rect.bottom() - inset
            tip_y = content_rect.bottom() + a
            cx = (
                content_rect.left() + edge_offset
                if "start" in place
                else (
                    content_rect.right() - edge_offset
                    if "end" in place
                    else content_rect.center().x()
                )
            )
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("bottom"):
            base_y = content_rect.top() + inset
            tip_y = content_rect.top() - a
            cx = (
                content_rect.left() + edge_offset
                if "start" in place
                else (
                    content_rect.right() - edge_offset
                    if "end" in place
                    else content_rect.center().x()
                )
            )
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("left"):
            base_x = content_rect.right() - inset
            tip_x = content_rect.right() + a
            cy = (
                content_rect.top() + edge_offset
                if "start" in place
                else (
                    content_rect.bottom() - edge_offset
                    if "end" in place
                    else content_rect.center().y()
                )
            )
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        elif place.startswith("right"):
            base_x = content_rect.left() + inset
            tip_x = content_rect.left() - a
            cy = (
                content_rect.top() + edge_offset
                if "start" in place
                else (
                    content_rect.bottom() - edge_offset
                    if "end" in place
                    else content_rect.center().y()
                )
            )
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        else:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawPath(path)
