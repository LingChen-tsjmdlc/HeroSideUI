"""Slider 自绘画布：_SliderCanvas 类，负责 track + filler + step + mark + thumb 全部绘制。

设计：
    - canvas 是 Slider 的子 widget，独立持有 paintEvent；
      鼠标事件转发回 owner（Slider）的 _canvas_mouse_xxx 方法，由 owner 处理拖拽/命中。
    - 所有颜色查询走 _palette，所有几何走 _geometry —— 避免 owner.<私有方法> 紧耦合。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...core import make_text_qfont
from . import _palette as palette
from ._geometry import (
    RING_GAP,
    RING_WIDTH,
    ratio_of,
    resolve_thumb_radius,
    thumb_centers,
    track_geom,
    track_visual_geom,
)


class _SliderCanvas(QWidget):
    """slider 的纯绘图区 + 鼠标事件转发到 owner。

    单独抽出来是因为父级 Slider 的 layout 还要承载 label_row_widget 等子 widget，
    而 canvas 区域只关心 track 几何 —— 父子分工更清晰且方便定位事件坐标。
    """

    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ============================================================
    # 鼠标事件转发
    # ============================================================
    def mousePressEvent(self, event):
        self._owner._canvas_mouse_press(event)
        if not event.isAccepted():
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._owner._canvas_mouse_move(event)
        if not event.isAccepted():
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._owner._canvas_mouse_release(event)
        if not event.isAccepted():
            super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        # 鼠标离开 canvas → 通知 owner 清 _hovered_idx，避免 hover 状态滞留
        self._owner._canvas_leave()
        super().leaveEvent(event)

    # ============================================================
    # 绘制
    # ============================================================
    def paintEvent(self, event):
        owner = self._owner
        cfg = owner._cfg()
        is_v = owner._orientation == "vertical"
        theme = owner._theme

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        track = track_geom(
            cfg, owner._orientation, self.width(), self.height(), bool(owner._marks)
        )
        track_vis = track_visual_geom(
            cfg, owner._orientation, self.width(), self.height(), bool(owner._marks)
        )
        # track 默认胶囊（rounded-full）：圆角 = 厚度/2
        thickness = cfg["track_thickness"]
        track_radius = thickness / 2.0

        # ---- 1) track 背景（用 track_vis：两端延伸到 thumb 外缘，避免与圆形 thumb 产生尖缝隙）----
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.track_bg_color(theme))
        painter.drawRoundedRect(track_vis, track_radius, track_radius)

        # ---- 2) filler ----
        if owner._is_range:
            lo, hi = owner._value
            filler_lo, filler_hi = lo, hi
        else:
            offset = (
                owner._fill_offset if owner._fill_offset is not None else owner._min
            )
            cur = owner._value
            filler_lo = min(offset, cur)
            filler_hi = max(offset, cur)

        r_lo = ratio_of(filler_lo, owner._min, owner._max)
        r_hi = ratio_of(filler_hi, owner._min, owner._max)

        if r_hi > r_lo:
            # 端点圆角策略——按“是否 thumb 端”判定，与几何贴边无关：
            #   - thumb 端：永远直角，且永远止于 thumb 圆心 (track 而非 track_vis)。
            #     thumb 是圆形且其外缘已经突出在 track 之外，
            #     filler 的 thumb 端被 thumb 完整盖住——
            #     若让它圆角并外延到 track_vis 边，反而会被 thumb 圆切出反弧凹陷。
            #   - 自由端（无 thumb 占住的那侧）：圆角，止于 track_vis 边
            #     以便和 track 背景共享胶囊外形（普通 slider origin 端常见）。
            # 普通 slider 只有 1 个 thumb，在 value 处；range slider 两端都是 thumb。
            if owner._hide_thumb:
                # hide_thumb：根本没有 thumb 物体，filler 两端都视作自由端
                # → 完整胶囊，与 track 背景外形一致
                lo_is_thumb = False
                hi_is_thumb = False
            elif owner._is_range:
                # 两端都是 thumb 端 → 都直角，都止于 thumb 圆心
                lo_is_thumb = True
                hi_is_thumb = True
            else:
                # 普通模式：value 那一侧才是 thumb 端
                # filler_lo = min(offset, value), filler_hi = max(offset, value)
                lo_is_thumb = owner._value <= offset
                hi_is_thumb = not lo_is_thumb
            # 起端 (lo) / 终端 (hi) 是否需要圆角 = 是否自由端
            round_start = not lo_is_thumb
            round_end = not hi_is_thumb
            # 自由端"外延到 track_vis 边"只在该端已贴近轨道极值时生效，
            # 否则会把按比例计算的 lo/hi 直接拉到 0%/100%，导致 filler 全填。
            # 例：hide_thumb + value=58，两端都是自由端，但 hi=58% 不应被拉到 100%。
            extend_lo = round_start and r_lo <= 1e-6
            extend_hi = round_end and r_hi >= 1.0 - 1e-6
            if is_v:
                # 垂直：start = 下端 (bottom)，end = 上端 (top)
                y_top = track.bottom() - r_hi * track.height()
                y_bot = track.bottom() - r_lo * track.height()
                # 仅当贴极值时才外延到 track_vis 边（与背景齐平）；
                # thumb 端绝不外延，止于 thumb 圆心
                if extend_hi:
                    y_top = track_vis.top()
                if extend_lo:
                    y_bot = track_vis.bottom()
                filler_rect = QRectF(
                    track_vis.left(), y_top, track_vis.width(), y_bot - y_top
                )
            else:
                # 水平：start = 左端，end = 右端
                x_left = track.left() + r_lo * track.width()
                x_right = track.left() + r_hi * track.width()
                if extend_lo:
                    x_left = track_vis.left()
                if extend_hi:
                    x_right = track_vis.right()
                filler_rect = QRectF(
                    x_left, track_vis.top(), x_right - x_left, track_vis.height()
                )
            painter.setBrush(palette.filler_color(owner._color, theme))
            path = self._make_track_path(
                filler_rect, track_radius, round_start, round_end, is_v
            )
            painter.drawPath(path)

        # ---- 3) step 标记 (showSteps) ----
        if owner._show_steps and owner._step > 0:
            self._paint_step_dots(painter, owner, track, is_v, filler_lo, filler_hi)

        # ---- 4) marks 文字 ----
        if owner._marks:
            self._paint_marks(painter, owner, track, is_v, filler_lo, filler_hi, cfg)

        # ---- 5) thumbs ----
        if not owner._hide_thumb:
            centers = thumb_centers(
                track,
                owner._orientation,
                owner._min,
                owner._max,
                owner._value,
                owner._is_range,
            )
            for i, c in enumerate(centers):
                self._paint_thumb(
                    painter,
                    owner,
                    c,
                    owner._drag_press_t[i],
                    focused=(owner._is_range and owner._focused_idx == i),
                )

        painter.end()

    # ============================================================
    # 子绘制
    # ============================================================
    @staticmethod
    def _paint_step_dots(painter, owner, track, is_v, filler_lo, filler_hi):
        # 沿 track 等距画小点 (HeroUI: w-1.5 h-1.5；lg 用 w-2 h-2)
        dot_r = 3.0 if owner._size != "lg" else 4.0
        n = int(round((owner._max - owner._min) / owner._step))
        theme = owner._theme
        size = owner._size
        in_color = palette.step_dot_in_range(theme)
        out_color = palette.step_dot_out_of_range(size)
        for i in range(n + 1):
            v = owner._min + i * owner._step
            r = ratio_of(v, owner._min, owner._max)
            if is_v:
                cx = track.center().x()
                cy = track.bottom() - r * track.height()
            else:
                cx = track.left() + r * track.width()
                cy = track.center().y()
            in_range = (filler_lo - 1e-9) <= v <= (filler_hi + 1e-9)
            painter.setBrush(in_color if in_range else out_color)
            painter.drawEllipse(QPointF(cx, cy), dot_r, dot_r)

    def _paint_marks(self, painter, owner, track, is_v, filler_lo, filler_hi, cfg):
        painter.save()
        painter.setFont(make_text_qfont(cfg["mark_font_size"], "normal"))
        fm = QFontMetrics(painter.font())
        text_color = QColor("#ecedee" if owner._theme == "dark" else "#11181c")
        for v, lbl in owner._marks:
            r = ratio_of(v, owner._min, owner._max)
            in_range = (filler_lo - 1e-9) <= v <= (filler_hi + 1e-9)
            color = QColor(text_color)
            color.setAlphaF(1.0 if in_range else 0.5)
            painter.setPen(color)
            if is_v:
                cy = track.bottom() - r * track.height()
                text_x = track.right() + cfg["mark_offset"] + 2
                text_w = self.width() - text_x
                painter.drawText(
                    QRectF(text_x, cy - fm.height() / 2, text_w, fm.height()),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    lbl,
                )
            else:
                cx = track.left() + r * track.width()
                text_y = track.bottom() + cfg["mark_offset"]
                text_w = fm.horizontalAdvance(lbl) + 8
                painter.drawText(
                    QRectF(cx - text_w / 2, text_y, text_w, fm.height()),
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                    lbl,
                )
        painter.restore()

    @staticmethod
    def _paint_thumb(
        painter,
        owner,
        center: QPointF,
        press_t: float,
        focused: bool,
    ):
        cfg = owner._cfg()
        thumb_size = cfg["thumb"]
        inner_dot = cfg["inner_dot"]
        # 拖拽时 inner_dot scale-80
        if not owner._disable_thumb_scale:
            inner_size = inner_dot * (1.0 - 0.2 * press_t)
        else:
            inner_size = inner_dot

        radius = resolve_thumb_radius(owner._radius, thumb_size)
        inner_radius = radius * (inner_size / thumb_size) if thumb_size > 0 else 0

        # ring (showOutline 或 range 模式下被键盘聚焦的 thumb)
        if owner._show_outline or focused:
            ring_size = thumb_size + (RING_WIDTH + RING_GAP) * 2
            ring_rect = QRectF(
                center.x() - ring_size / 2,
                center.y() - ring_size / 2,
                ring_size,
                ring_size,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            ring_c = palette.ring_color(owner._theme)
            ring_c.setAlphaF(1.0 if owner._show_outline else 0.6)
            painter.setBrush(ring_c)
            painter.drawRoundedRect(
                ring_rect,
                radius + RING_WIDTH + RING_GAP,
                radius + RING_WIDTH + RING_GAP,
            )
        # 阴影 (轻微, 模拟 shadow-small): 向下偏移 1px
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRectF(
                center.x() - thumb_size / 2,
                center.y() - thumb_size / 2 + 1,
                thumb_size,
                thumb_size,
            ),
            radius,
            radius,
        )

        # 外圈 thumb (color)
        painter.setBrush(palette.thumb_color(owner._color, owner._theme))
        painter.drawRoundedRect(
            QRectF(
                center.x() - thumb_size / 2,
                center.y() - thumb_size / 2,
                thumb_size,
                thumb_size,
            ),
            radius,
            radius,
        )

        # inner dot (bg-background)
        painter.setBrush(palette.inner_dot_color(owner._theme))
        painter.drawRoundedRect(
            QRectF(
                center.x() - inner_size / 2,
                center.y() - inner_size / 2,
                inner_size,
                inner_size,
            ),
            inner_radius,
            inner_radius,
        )

    # ============================================================
    # 工具：filler 路径构造（两端独立控制圆角/直角）
    # ============================================================
    @staticmethod
    def _make_track_path(
        rect: QRectF,
        radius: float,
        round_start: bool,
        round_end: bool,
        is_v: bool,
    ) -> QPainterPath:
        """构造一段 track 路径：只在指定端圆角，另一端直角。

        为什么需要：thumb 是圆形，若 filler 那端也圆角则两个圆相切会
        产生反弧凹陷；所以 filler 的 thumb 端必须是直角（被 thumb 圆盖住）。

        坐标系统统一：“start 端”=水平 left / 垂直 bottom；“end 端”=水平 right / 垂直 top。
        这跟 filler 的 r_lo / r_hi 语义对齐。
        """
        # radius 防过冲：不能超过“厚度/2”也不能超过“长度/2”
        thickness = rect.height() if not is_v else rect.width()
        length = rect.width() if not is_v else rect.height()
        r = max(0.0, min(radius, thickness / 2.0, length / 2.0))

        path = QPainterPath()
        if r <= 0.0:
            path.addRect(rect)
            return path

        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if not is_v:
            # 水平：start=左端，end=右端。从左上角起，顺时针。
            # 起点：左上角（取决于 round_start）
            path.moveTo(x + (r if round_start else 0.0), y)
            # 顶边 → 右上角
            path.lineTo(x + w - (r if round_end else 0.0), y)
            if round_end:
                path.arcTo(x + w - 2 * r, y, 2 * r, 2 * r, 90, -90)
            # 右边 → 右下角
            path.lineTo(x + w, y + h - (r if round_end else 0.0))
            if round_end:
                path.arcTo(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, 0, -90)
            # 底边 → 左下角
            path.lineTo(x + (r if round_start else 0.0), y + h)
            if round_start:
                path.arcTo(x, y + h - 2 * r, 2 * r, 2 * r, -90, -90)
            # 左边 → 左上角
            path.lineTo(x, y + (r if round_start else 0.0))
            if round_start:
                path.arcTo(x, y, 2 * r, 2 * r, 180, -90)
        else:
            # 垂直：start=下端（bottom），end=上端（top）。
            # 从左上角（end 端的一侧）起，顺时针。
            path.moveTo(x + (r if round_end else 0.0), y)
            path.lineTo(x + w - (r if round_end else 0.0), y)
            if round_end:
                path.arcTo(x + w - 2 * r, y, 2 * r, 2 * r, 90, -90)
            path.lineTo(x + w, y + h - (r if round_start else 0.0))
            if round_start:
                path.arcTo(x + w - 2 * r, y + h - 2 * r, 2 * r, 2 * r, 0, -90)
            path.lineTo(x + (r if round_start else 0.0), y + h)
            if round_start:
                path.arcTo(x, y + h - 2 * r, 2 * r, 2 * r, -90, -90)
            path.lineTo(x, y + (r if round_end else 0.0))
            if round_end:
                path.arcTo(x, y, 2 * r, 2 * r, 180, -90)
        path.closeSubpath()
        return path
