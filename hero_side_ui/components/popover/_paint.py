"""Popover paintEvent 与颜色/圆角解析 mixin（私有）。

负责：
- _bg_color / current_bg_color / _text_color：颜色解析
- _resolve_radius / _content_rect_size：圆角与内容区尺寸
- paintEvent: 阴影 + 圆角主体 + 箭头自绘
"""

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ...themes import HEROUI_COLORS, POPOVER_SHADOWS

from ._constants import ARROW_INSET, ARROW_SIZE


class _PopoverPaintMixin:
    """Popover paint / 颜色 / 圆角 mixin。"""

    # ============================================================
    # 颜色
    # ============================================================
    def _bg_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#ffffff" if not is_dark else "#27272a")
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        return QColor(c[500])

    def current_bg_color(self) -> QColor:
        """公共 getter：返回 popover 当前实际底色 (含 color/theme 解析)。

        供子组件（如 ScrollShadow / Autocomplete 列表容器）需要"与 popover 底色严丝
        合缝融合" 时使用——遍历 parent 链 duck-typing 查找 ``current_bg_color`` 同名
        方法即可。

        与 Card 的 :meth:`current_bg_color` 同语义、同签名。
        """
        return self._bg_color()

    def current_corner_radius(self) -> float:
        """公共 getter：返回 popover 当前实际圆角半径 (px)。

        供 ScrollShadow 这类需要"把渐变阴影裁剪到圆角矩形内"的子组件使用：
        阴影 overlay 是矩形 widget，paintEvent 里画的是矩形渐变；当滚到中间时
        顶/底两条阴影都显示，会把 popover 圆角内的 4 个角染色（看起来像直角）。
        通过 duck-typing 沿父链找到这个 API → overlay 用 QPainterPath 裁剪到
        圆角矩形 → 阴影自然跟随圆角内收。

        约定与 ``current_bg_color`` 一致：duck-typing 范式（MEMORY 第 32 条）。
        """
        return float(self._resolve_radius())

    def _text_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#11181c" if not is_dark else "#ecedee")
        if self._color == "warning":
            return QColor("#000000")
        return QColor("#ffffff")

    # ============================================================
    # 圆角
    # ============================================================
    def _resolve_radius(self) -> float:
        if self._radius == "none":
            return 0.0
        if self._radius == "full":
            # 半高
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 14))

    def _content_rect_size(self) -> QSize:
        m = self._frame_margins()
        return QSize(
            max(0, self.width() - m[0] - m[2]), max(0, self.height() - m[1] - m[3])
        )

    # ============================================================
    # 绘制：阴影 + 圆角主体 + 箭头
    # ============================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # ---- 动画期间：只画缩放后的 pixmap，跳过常规绘制 ----
        if self._scale_proxy.is_active():
            w, h = self.width(), self.height()
            # 缩放锚点：靠近 trigger 的那一侧（arrow 所在边的中点）
            # 这样 scale 动画的视觉是"从 trigger 方向展开/收回"，更贴合 HeroUI
            m = self._frame_margins()
            place = self._actual_placement
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
            self._scale_proxy.draw(painter, self.rect(), anchor=(cx, cy))
            return

        m = self._effective_frame_margins()
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["md"])
        bg = self._bg_color()
        radius = self._resolve_radius()

        # 内容矩形（即 frame 内层）
        content_rect = QRectF(
            m[0], m[1], self.width() - m[0] - m[2], self.height() - m[1] - m[3]
        )

        # ---- 1) 阴影：多层半透明，越往外越透明 ----
        if cfg["layers"] > 0:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            # 从外到内画 layers 层，外层扩散大但透明度低
            for i in range(cfg["layers"]):
                t = (i + 1) / cfg["layers"]  # 0..1，内→外
                grow = cfg["blur"] * (1 - t) + 1
                off = cfg["offset_y"] * (1 - t)
                rect = content_rect.adjusted(-grow, -grow + off, grow, grow + off)
                # alpha 渐进：外层最淡（t 小），内层最浓（t→1）
                alpha = int(cfg["alpha"] * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(rect, radius, radius)
            painter.restore()

        # ---- 2) 主体背景 ----
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)

        # ---- 3) arrow（仅当 arrow=True）----
        if self._arrow:
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        place = self._actual_placement
        a = ARROW_SIZE
        path = QPainterPath()

        # arrow 基底向 content_rect **内部** 偏移 ARROW_INSET，
        # 让三角形底边被 content 盖住一小段，避免圆角在 start/end 时露缝隙。
        inset = ARROW_INSET

        if place.startswith("top"):
            # arrow 在底部（指向 trigger 方向 = 下）
            base_y = content_rect.bottom() - inset
            tip_y = content_rect.bottom() + a
            if "start" in place:
                cx = content_rect.left() + 14 + a
            elif "end" in place:
                cx = content_rect.right() - 14 - a
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("bottom"):
            base_y = content_rect.top() + inset
            tip_y = content_rect.top() - a
            if "start" in place:
                cx = content_rect.left() + 14 + a
            elif "end" in place:
                cx = content_rect.right() - 14 - a
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("left"):
            base_x = content_rect.right() - inset
            tip_x = content_rect.right() + a
            if "start" in place:
                # start 顶对齐 → 箭头在顶部 25%
                cy = content_rect.top() + max(14 + a, content_rect.height() * 0.25)
            elif "end" in place:
                # end 底对齐 → 箭头在底部 25%
                cy = content_rect.bottom() - max(14 + a, content_rect.height() * 0.25)
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        elif place.startswith("right"):
            base_x = content_rect.left() + inset
            tip_x = content_rect.left() - a
            if "start" in place:
                cy = content_rect.top() + max(14 + a, content_rect.height() * 0.25)
            elif "end" in place:
                cy = content_rect.bottom() - max(14 + a, content_rect.height() * 0.25)
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        else:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawPath(path)

