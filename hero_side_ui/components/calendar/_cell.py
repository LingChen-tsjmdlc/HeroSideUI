"""Calendar 单个日期格子（自绘按钮，零业务判断由 CellState 驱动）。

继承 QAbstractButton：自带 hover/press/clicked/focus。渲染只读注入的
CellState + color/theme，绘制圆形底 + 日期数字 + today 圆点 + unavailable 删除线。
hover 背景做 150ms 平滑补间（对齐 calendar.ts transition duration-150）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from ...core import make_text_qfont
from ...utils import aligned_color_pair
from ._grid import CellState
from . import _palette as pal

_HOVER_ANIM_MS = 150


class _CalendarCell(QAbstractButton):
    def __init__(self, size: int, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._cs: Optional[CellState] = None
        self._color = "primary"
        self._theme = "light"
        self._font_size = 14
        self._hovered = False

        # hover 背景补间：0=无底，1=完全 hover 底
        self._hover_t = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(_HOVER_ANIM_MS)
        self._hover_anim.valueChanged.connect(self._on_hover_tick)

    # ---- 父注入 -------------------------------------------------------

    def apply_state(self, cs: CellState, *, color: str, theme: str, font_size: int) -> None:
        self._cs = cs
        self._color = color
        self._theme = theme
        self._font_size = font_size
        interactive = not cs.is_empty and not cs.is_disabled and not cs.is_unavailable
        self.setEnabled(interactive)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if interactive else Qt.CursorShape.ArrowCursor
        )
        self.update()

    # ---- hover 动画 ---------------------------------------------------

    def _can_hover(self) -> bool:
        cs = self._cs
        return bool(cs and not cs.is_empty and not cs.is_disabled
                    and not cs.is_unavailable and not cs.is_readonly)

    def enterEvent(self, ev) -> None:
        if self._can_hover():
            self._hovered = True
            self._start_hover_anim(1.0)
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        self._hovered = False
        self._start_hover_anim(0.0)
        super().leaveEvent(ev)

    def _start_hover_anim(self, target: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_t)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _on_hover_tick(self, v) -> None:
        self._hover_t = float(v)
        self.update()

    # ---- 绘制 ---------------------------------------------------------

    def paintEvent(self, ev) -> None:
        cs = self._cs
        if cs is None or cs.is_empty:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cell = self._size
        # cell 圆形区域（居中，边长 = _size）
        cx = w / 2.0
        crect = QRectF(cx - cell / 2 + 0.5, 0.5, cell - 1, cell - 1)
        radius = cell / 2.0

        # 范围连接背景（画在整个 cell 宽度，端点处收成半圆）
        if cs.is_range_selection:
            self._paint_range_bg(p, w, h, crect, radius)

        # 圆形底（单选高亮 / range 端点实底 / hover）
        bg = self._resolve_bg()
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawEllipse(crect)

        # 文字
        p.setPen(QPen(self._resolve_text_color()))
        weight = "medium" if cs.is_selected else "normal"
        p.setFont(make_text_qfont(self._font_size, weight))
        p.drawText(crect, Qt.AlignmentFlag.AlignCenter, cs.label)

        # unavailable 删除线
        if cs.is_unavailable:
            mid_y = crect.center().y()
            p.setPen(QPen(self._resolve_text_color(), 1))
            p.drawLine(int(crect.left() + 8), int(mid_y),
                       int(crect.right() - 8), int(mid_y))

        # today 圆点（未选中时，底部小圆点）
        if cs.is_today and not cs.is_selected:
            dot_r = 1.5
            dcx = crect.center().x()
            dcy = crect.bottom() - 3
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(pal.today_ring(self._color, self._theme))
            p.drawEllipse(QRectF(dcx - dot_r, dcy - dot_r, dot_r * 2, dot_r * 2))

        p.end()

    def _paint_range_bg(self, p: QPainter, w: float, h: float,
                        crect: QRectF, radius: float) -> None:
        """范围连接背景：整格宽的浅底矩形，行首/行尾端收成半圆。"""
        cs = self._cs
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.range_middle_bg(self._color, self._theme))
        top = crect.top()
        bh = crect.height()
        # 默认铺满整个 cell 宽度（衔接相邻格）；行首/行尾/单端收圆角
        left = 0.0
        right = w
        left_round = cs.is_range_start or cs.is_selection_start
        right_round = cs.is_range_end or cs.is_selection_end
        # 端点：连接背景只画半边（起点画右半、终点画左半），另半边留给实底圆
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        r = radius
        rect = QRectF(left, top, right - left, bh)
        if left_round and right_round:
            path.addRoundedRect(rect, r, r)
        elif left_round:
            path.moveTo(rect.right(), rect.top())
            path.lineTo(rect.left() + r, rect.top())
            path.arcTo(rect.left(), rect.top(), 2 * r, 2 * r, 90, 180)
            path.lineTo(rect.right(), rect.bottom())
            path.closeSubpath()
        elif right_round:
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right() - r, rect.top())
            path.arcTo(rect.right() - 2 * r, rect.top(), 2 * r, 2 * r, 90, -180)
            path.lineTo(rect.left(), rect.bottom())
            path.closeSubpath()
        else:
            path.addRect(rect)
        p.drawPath(path)
        p.restore()

    def _resolve_bg(self) -> Optional[QColor]:
        cs = self._cs
        # range 端点：语义色实底圆
        if cs.is_range_selection:
            if cs.is_selection_start or cs.is_selection_end:
                return pal.selected_bg(self._color, self._theme)
            return None  # 中间格只有连接背景，无实底圆
        if cs.is_selected:
            return pal.selected_bg(self._color, self._theme)
        if self._hover_t <= 0:
            return None
        target = pal.hover_bg(self._color, self._theme)
        start, end = aligned_color_pair(QColor(0, 0, 0, 0), target)
        return _lerp_color(start, end, self._hover_t)

    def _resolve_text_color(self) -> QColor:
        cs = self._cs
        if cs.is_disabled or cs.is_unavailable:
            return pal.disabled_text(self._theme)
        if cs.is_range_selection:
            if cs.is_selection_start or cs.is_selection_end:
                return pal.selected_text(self._color, self._theme)
            return pal.range_middle_text(self._color, self._theme)
        if cs.is_selected:
            return pal.selected_text(self._color, self._theme)
        if self._hover_t > 0.5:
            return pal.hover_text(self._color, self._theme)
        return pal.normal_text(self._theme)


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )
