"""Calendar 日期格：QAbstractButton 自绘，只读注入 CellState 渲染。
hover 背景 150ms 补间，对齐 calendar.ts。
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from ...animation import tween_value
from ...core import make_text_qfont
from ...utils import aligned_color_pair
from . import _palette as pal
from ._grid import CellState

_HOVER_ANIM_MS = 150


class _CalendarCell(QAbstractButton):
    def __init__(self, size: int, parent=None) -> None:
        """创建固定尺寸的日期格按钮。

        Args:
            size: 格子边长（像素）。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._cs: CellState | None = None
        self._color = "primary"
        self._theme = "light"
        self._font_size = 14
        self._hovered = False

        # hover 背景补间：0=无底，1=完全 hover 底
        self._hover_t = 0.0
        self._hover_anim = None

    # ---- 父注入 -------------------------------------------------------

    def apply_state(self, cs: CellState, *, color: str, theme: str, font_size: int) -> None:
        """注入渲染状态并按可交互性更新启用态与光标。

        Args:
            cs: 父层算好的 CellState（只读注入，本类不自持业务状态）。
            color: 语义色名。
            theme: 主题名。
            font_size: 日期数字字号。
        """
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
        """当前状态是否允许 hover 效果。

        Returns:
            非空格、非禁用、非不可用、非只读时为 True。
        """
        cs = self._cs
        return bool(
            cs
            and not cs.is_empty
            and not cs.is_disabled
            and not cs.is_unavailable
            and not cs.is_readonly
        )

    def enterEvent(self, ev) -> None:
        """鼠标进入：可 hover 时启动淡入补间。

        Args:
            ev: Qt 进入事件。
        """
        if self._can_hover():
            self._hovered = True
            self._start_hover_anim(1.0)
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        """鼠标离开：回落补间到无底态。

        Args:
            ev: Qt 离开事件。
        """
        self._hovered = False
        self._start_hover_anim(0.0)
        super().leaveEvent(ev)

    def _start_hover_anim(self, target: float) -> None:
        """启动 hover 背景透明度补间。

        Args:
            target: 目标值，进入为 1.0、离开为 0.0。
        """
        tween_value(
            self,
            "_hover_anim",
            self._hover_t,
            target,
            self._on_hover_tick,
            duration=_HOVER_ANIM_MS,
            easing=QEasingCurve.Type.Linear,
        )

    def _on_hover_tick(self, v) -> None:
        """补间回调：写入进度并重绘。

        Args:
            v: 当前插值（0.0 ~ 1.0）。
        """
        self._hover_t = float(v)
        self.update()

    # ---- 绘制 ---------------------------------------------------------

    def paintEvent(self, ev) -> None:
        """自绘日期格：连接背景 → 圆形底 → 数字 → 删除线 → today 圆点。

        Args:
            ev: Qt 绘制事件。

        Note:
            空格（is_empty）直接返回不绘制。
        """
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
            p.drawLine(int(crect.left() + 8), int(mid_y), int(crect.right() - 8), int(mid_y))

        # today 圆点（未选中时，底部小圆点）
        if cs.is_today and not cs.is_selected:
            dot_r = 1.5
            dcx = crect.center().x()
            dcy = crect.bottom() - 3
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(pal.today_ring(self._color, self._theme))
            p.drawEllipse(QRectF(dcx - dot_r, dcy - dot_r, dot_r * 2, dot_r * 2))

        p.end()

    def _paint_range_bg(
        self, p: QPainter, w: float, h: float, crect: QRectF, radius: float
    ) -> None:
        """绘制范围连接背景。

        Args:
            p: 当前 QPainter。
            w: 整格宽度（连接背景铺满整格以衔接相邻格）。
            h: 整格高度。
            crect: 圆形日期区几何。
            radius: 圆半径。

        Note:
            行首 / 行尾端收成半圆；单端（起点 / 终点）只画对应半边，
            另半边留给端点的实底圆。
        """
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

    def _resolve_bg(self) -> QColor | None:
        """解析圆形底色。

        Returns:
            选中 / range 端点为语义色实底；range 中间格无实底；
            hover 期间返回按进度插值的透明 → hover 色过渡。
        """
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
        """解析数字文字色。

        Returns:
            禁用 / 不可用 → disabled 色；选中与端点 → 选中前景色；
            range 中间 → 连接前景色；hover 过半 → hover 色；其余常态色。
        """
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
    """线性插值两个 QColor（含 alpha）。

    Args:
        a: 起始色。
        b: 目标色。
        t: 插值系数 0.0 ~ 1.0。

    Returns:
        插值后的新 QColor。
    """
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )
