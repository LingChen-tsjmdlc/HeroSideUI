"""Tooltip 绘制 mixin：颜色/圆角解析 + paintEvent + 箭头（纯渲染无状态机）。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from ...core.shadow_paint import layers_for, paint_inset, paint_shadow
from ...themes import HEROUI_COLORS
from ...themes.theme_values import get_color_foreground, get_foreground, get_popup_background
from ._constants import ARROW_INSET, ARROW_SIZE

__all__ = ["_TooltipPaintMixin"]


class _TooltipPaintMixin:
    """Tooltip 颜色 / 圆角 / 绘制相关 mixin。"""

    # ---- 颜色 ----
    def _bg_color(self) -> QColor:
        """返回当前主题与配色下的背景色。"""
        if self._color == "default":  # type: ignore[attr-defined]
            return QColor(get_popup_background(self._theme))  # type: ignore[attr-defined]
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])  # type: ignore[attr-defined]
        return QColor(c[500])

    def _text_color(self) -> QColor:
        """返回当前主题与配色下的文字色。"""
        if self._color == "default":  # type: ignore[attr-defined]
            return QColor(get_foreground(self._theme))  # type: ignore[attr-defined]
        return QColor(get_color_foreground(self._color, self._theme))  # type: ignore[attr-defined]

    # ---- 圆角 ----
    def _resolve_radius(self) -> float:
        """解析当前圆角档位对应的像素半径。"""
        if self._radius == "none":  # type: ignore[attr-defined]
            return 0.0
        if self._radius == "full":  # type: ignore[attr-defined]
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 8))  # type: ignore[attr-defined]

    def _content_rect_size(self) -> QSize:
        """返回扣除外框留白后的内容区尺寸。"""
        m = self._frame_margins()  # type: ignore[attr-defined]
        return QSize(
            max(0, self.width() - m[0] - m[2]),  # type: ignore[attr-defined]
            max(0, self.height() - m[1] - m[3]),  # type: ignore[attr-defined]
        )

    # ---- paintEvent ----
    def paintEvent(self, event):
        """绘制阴影、主体与箭头；缩放动画期间改画代理快照。"""
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
        layers = layers_for(self._shadow, self._theme)  # type: ignore[attr-defined]
        bg = self._bg_color()
        radius = self._resolve_radius()

        content_rect = QRectF(
            m[0],
            m[1],
            self.width() - m[0] - m[2],
            self.height() - m[1] - m[3],  # type: ignore[attr-defined]
        )

        # 阴影：公共阴影（多层预合成 + 九宫格缓存）
        paint_shadow(painter, content_rect, radius, layers)

        # 主体 + 暗色内描边
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)
        paint_inset(painter, content_rect, radius, layers)

        # 箭头
        if self._show_arrow:  # type: ignore[attr-defined]
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        """绘制箭头：start/end/无后缀分别对应靠左/靠右/居中（或上/下）。"""
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
