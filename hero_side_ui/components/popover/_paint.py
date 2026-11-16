"""Popover paintEvent mixin：颜色/圆角解析 + 阴影主体箭头自绘。"""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from ...themes import HEROUI_COLORS
from ...core.shadow_paint import layers_for, paint_inset, paint_shadow
from ...themes.theme_values import get_color_foreground, get_foreground, get_popup_background
from ._constants import ARROW_INSET, ARROW_SIZE


class _PopoverPaintMixin:
    """Popover paint / 颜色 / 圆角 mixin。"""

    # ============================================================
    # 颜色
    # ============================================================
    def _bg_color(self) -> QColor:
        """解析当前 popover 底色。

        Returns:
            QColor: default 取 popup_background；其余取调色板 500 色。
        """
        if self._color == "default":
            return QColor(get_popup_background(self._theme))
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        return QColor(c[500])

    def current_bg_color(self) -> QColor:
        """返回当前实际底色，供子组件 duck-typing 融合使用（与 Card 同语义）。"""
        return self._bg_color()

    def current_corner_radius(self) -> float:
        """返回当前实际圆角半径 px，供 ScrollShadow 等子组件裁剪渐变用。"""
        return float(self._resolve_radius())

    def _text_color(self) -> QColor:
        """解析内容文字色（供裸 QLabel 反色使用）。

        Returns:
            QColor: 默认色取 foreground；其余取该语义色的实色字色。
        """
        if self._color == "default":
            return QColor(get_foreground(self._theme))
        return QColor(get_color_foreground(self._color, self._theme))

    # ============================================================
    # 圆角
    # ============================================================
    def _resolve_radius(self) -> float:
        """解析圆角半径像素值。

        Returns:
            float: none=0；full=内容半高；sm/md/lg 取固定映射（4/8/14）。
        """
        if self._radius == "none":
            return 0.0
        if self._radius == "full":
            # 半高
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 14))

    def _content_rect_size(self) -> QSize:
        """计算内容矩形尺寸（扣掉 frame margin 后的实际绘制区域）。

        Returns:
            QSize: 内容区宽高。
        """
        m = self._frame_margins()
        return QSize(max(0, self.width() - m[0] - m[2]), max(0, self.height() - m[1] - m[3]))

    # ============================================================
    # 绘制：阴影 + 圆角主体 + 箭头
    # ============================================================
    def paintEvent(self, event):
        """自绘阴影、圆角主体背景与箭头。

        Args:
            event: Qt 绘制事件。

        Note:
            缩放动画期间（_scale_proxy 活跃）只绘制缩放后的 pixmap，
            跳过常规绘制；否则按 effective_frame_margins 绘制多层阴影 +
            圆角主体 + 可选箭头。
        """
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
        layers = layers_for(self._shadow, self._theme)
        bg = self._bg_color()
        radius = self._resolve_radius()

        # 内容矩形（即 frame 内层）
        content_rect = QRectF(m[0], m[1], self.width() - m[0] - m[2], self.height() - m[1] - m[3])

        # ---- 1) 阴影：公共阴影（多层预合成 + 九宫格缓存）----
        paint_shadow(painter, content_rect, radius, layers)

        # ---- 2) 主体背景 + 暗色内描边 ----
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)
        paint_inset(painter, content_rect, radius, layers)

        # ---- 3) arrow（仅当 arrow=True）----
        if self._arrow:
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        """根据当前 placement 自绘指向 trigger 的三角形箭头。

        Args:
            painter: 当前 QPainter。
            content_rect: 内容矩形（箭头基底贴近其边缘）。
            bg: 箭头填充色，通常与主体背景一致。
        """
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
