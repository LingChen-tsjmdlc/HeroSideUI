"""Pagination 单个 item (_PaginationItem)。

QAbstractButton 子类,负责自绘 + press scale 动画。
四种类型: PAGE / PREV / NEXT / DOTS,父组件按 type 注入文本/图标。
"""

from typing import Optional

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QWidget

from ...animation import PressScaleEffect
from ...core.text_style import make_text_qfont
from ...themes import PAGINATION_SIZES
from ...utils import load_svg_icon

from ._constants import PaginationItemType
from ._ellipsis_icon import _DotsIcon
from ._palette import (
    resolve_compact_corners,
    resolve_item_bg,
    resolve_item_border,
    resolve_item_disabled_text,
    resolve_item_text,
    resolve_cursor_text,
)


class _PaginationItem(QAbstractButton):
    """Pagination 单个按钮(页码/方向键/省略号)。"""

    # 在父组件激活时由 active_changed 通知
    activated = Signal()

    def __init__(
        self,
        item_type: PaginationItemType,
        *,
        page: Optional[int] = None,
        is_before: bool = False,  # 仅 DOTS 用: True=左侧省略号
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._type = item_type
        self._page = page  # PAGE: 页码; PREV/NEXT: None; DOTS: None
        self._is_before = bool(is_before)

        # 视觉状态(由父组件 apply_state 注入)
        self._variant = "flat"
        self._color = "primary"
        self._size = "md"
        self._theme = "light"
        self._radius = "md"
        self._is_compact = False
        self._is_first = False
        self._is_last = False
        self._is_active = False  # 当前选中页面
        self._show_active_fill = False  # disable_cursor_animation 时由父注入
        self._size_cfg = PAGINATION_SIZES["md"]

        # 鼠标交互
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # ClickFocus: 只接受鼠标点击聚焦,不参与 Tab 导航 (避免被隔壁组件 reparent 时焦点漂移过来)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 禁用 native focus rect (Fusion style 默认会画虚线焦点框)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        # focus-visible 语义: 仅键盘 Tab 聚焦才显 ring (鼠标点击不显)
        self._focus_visible = False

        # 子部件: PREV/NEXT 装 chevron icon, DOTS 装 _DotsIcon
        self._icon_label: Optional[QWidget] = None
        if self._type in (PaginationItemType.PREV, PaginationItemType.NEXT):
            self._setup_chevron()
        elif self._type == PaginationItemType.DOTS:
            self._setup_dots()

        # press scale 0.97 动画
        self._press_scaler: Optional[PressScaleEffect] = None
        # 延迟创建 (disable_animation=True 时不创建)

        self._apply_size()

    # ============================================================
    # 子部件初始化
    # ============================================================

    def _setup_chevron(self):
        """PREV/NEXT 按钮的 chevron 图标。"""
        from PySide6.QtWidgets import QLabel

        lbl = QLabel(self)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label = lbl
        # 居中布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)

    def _setup_dots(self):
        """DOTS 按钮的省略号/双 chevron 切换图标。"""
        icon = _DotsIcon(
            is_before=self._is_before, size=self._size_cfg["icon_size"], parent=self
        )
        self._icon_label = icon
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)

    # ============================================================
    # 公共属性
    # ============================================================

    def item_type(self) -> PaginationItemType:
        return self._type

    def page(self) -> Optional[int]:
        return self._page

    def is_before(self) -> bool:
        return self._is_before

    def set_position_flags(self, *, is_first: bool, is_last: bool):
        """isCompact 时根据位置决定圆角剪裁。"""
        self._is_first = bool(is_first)
        self._is_last = bool(is_last)
        self.update()

    def set_active(self, active: bool):
        """是否为当前选中页(供 disable_cursor_animation 时自填充)。"""
        a = bool(active)
        if a == self._is_active:
            return
        self._is_active = a
        self._refresh_icon_color()
        self.update()

    def set_show_active_fill(self, show: bool):
        """disable_cursor_animation 模式下,active item 自己填充 cursor 色。"""
        s = bool(show)
        if s == self._show_active_fill:
            return
        self._show_active_fill = s
        self.update()

    # ============================================================
    # 样式注入
    # ============================================================

    def apply_state(
        self,
        *,
        variant: str,
        color: str,
        size: str,
        theme: str,
        radius: str,
        is_compact: bool,
        disable_animation: bool,
    ):
        self._variant = variant
        self._color = color
        self._size = size
        self._theme = theme
        self._radius = radius
        self._is_compact = bool(is_compact)
        self._size_cfg = PAGINATION_SIZES[size]
        self._apply_size()
        # press scale: 仅当未禁用动画时启用
        self._update_press_scaler(disable_animation)
        self._refresh_icon_color()
        self.update()

    def _apply_size(self):
        cfg = self._size_cfg
        h = cfg["item_height"]
        min_w = cfg["item_min_width"]
        self.setFixedHeight(h)
        self.setMinimumWidth(min_w)
        # 内边距: 数字两侧 padding_x
        # PAGE 类型用宽度 = max(min_w, font_metrics + 2*padding_x)
        if self._icon_label is not None:
            # icon 图标尺寸跟随 size
            icon_size = cfg["icon_size"]
            if isinstance(self._icon_label, _DotsIcon):
                self._icon_label.set_icon_size(icon_size)
            else:
                self._icon_label.setFixedSize(icon_size, icon_size)

    def _update_press_scaler(self, disable_animation: bool):
        if disable_animation:
            if self._press_scaler is not None:
                self.setGraphicsEffect(None)
                self._press_scaler = None
            return
        if self._press_scaler is None:
            self._press_scaler = PressScaleEffect(self)

    # ============================================================
    # icon 着色
    # ============================================================

    def _resolve_icon_color(self) -> QColor:
        """图标色 = 当前应该显示的文字色。"""
        if not self.isEnabled():
            return resolve_item_disabled_text(self._theme)
        if self._is_active and self._show_active_fill:
            return resolve_cursor_text(self._color, self._theme)
        return resolve_item_text(self._theme)

    def _refresh_icon_color(self):
        """PREV/NEXT/DOTS 图标随状态/主题刷新颜色。"""
        if self._icon_label is None:
            return
        color = self._resolve_icon_color()
        cfg = self._size_cfg
        size = cfg["icon_size"]
        if isinstance(self._icon_label, _DotsIcon):
            self._icon_label.set_icon_color(color)
            return
        # PREV/NEXT
        if self._type == PaginationItemType.PREV:
            name = "heroicons--chevron-left"
        else:
            name = "heroicons--chevron-right"
        from PySide6.QtWidgets import QLabel

        if isinstance(self._icon_label, QLabel):
            pm = load_svg_icon(name, size=size, color=color)
            self._icon_label.setPixmap(pm)
            self._icon_label.setFixedSize(size, size)

    # ============================================================
    # 鼠标事件 (driving press scale + DOTS hover icon swap)
    # ============================================================

    def enterEvent(self, ev):
        super().enterEvent(ev)
        if self._type == PaginationItemType.DOTS and isinstance(
            self._icon_label, _DotsIcon
        ):
            self._icon_label.set_hover(True)
        self.update()

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        if self._type == PaginationItemType.DOTS and isinstance(
            self._icon_label, _DotsIcon
        ):
            self._icon_label.set_hover(False)
        self.update()

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if self._press_scaler is not None and ev.button() == Qt.MouseButton.LeftButton:
            self._press_scaler.press()

    def mouseReleaseEvent(self, ev):
        if self._press_scaler is not None:
            self._press_scaler.release()
        super().mouseReleaseEvent(ev)

    def focusInEvent(self, ev):
        super().focusInEvent(ev)
        # focus-visible: 仅 Tab/Backtab 键盘聚焦才亮 ring
        reason = ev.reason()
        self._focus_visible = reason in (
            Qt.FocusReason.TabFocusReason,
            Qt.FocusReason.BacktabFocusReason,
        )
        if self._type == PaginationItemType.DOTS and isinstance(
            self._icon_label, _DotsIcon
        ):
            self._icon_label.set_hover(True)
        self.update()

    def focusOutEvent(self, ev):
        super().focusOutEvent(ev)
        self._focus_visible = False
        if self._type == PaginationItemType.DOTS and isinstance(
            self._icon_label, _DotsIcon
        ):
            self._icon_label.set_hover(False)
        self.update()

    # ============================================================
    # 自绘
    # ============================================================

    def paintEvent(self, ev):
        from ._palette import resolve_radius_px

        if self.width() <= 0 or self.height() <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        radius_px = resolve_radius_px(self._radius, self.height())
        # 紧凑模式: rect 占满 widget,中间 item 左右紧贴邻居形成连续胶囊
        # 非紧凑: 0.5px 内缩用于 1px 边框居中绘制
        if self._is_compact:
            rect = QRectF(0, 0, self.width(), self.height())
        else:
            rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        # compact 模式: 中间 item 不留圆角
        tl, tr, br, bl = resolve_compact_corners(
            self._is_compact, self._is_first, self._is_last, radius_px
        )
        path = self._build_corner_path(rect, tl, tr, br, bl)

        # 底色: active + show_active_fill 走 cursor 色,否则走 variant 状态色
        # 紧凑模式下禁用 hover/pressed 底色变化,所有 item 共享一致底色
        is_hover = (not self._is_compact) and self.underMouse() and self.isEnabled()
        is_pressed = (not self._is_compact) and self.isDown() and self.isEnabled()
        if self._is_active and self._show_active_fill:
            from ._palette import resolve_cursor_fill

            fill = resolve_cursor_fill(self._color, self._theme)
            p.fillPath(path, fill)
        else:
            bg = resolve_item_bg(
                self._variant,
                self._theme,
                hover=is_hover,
                pressed=is_pressed,
                active=self._is_active,
            )
            if bg is not None:
                p.fillPath(path, bg)

        # 边框 (bordered/faded)
        border = resolve_item_border(self._variant, self._theme)
        if border is not None:
            cfg = self._size_cfg
            border_w = cfg["border_width"]
            pen = QPen(border)
            pen.setWidthF(border_w)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if self._is_compact:
                # 紧凑模式: 仅画外侧边框,避免相邻 item 边框相撞产生双线
                self._paint_compact_border(p, rect, tl, tr, br, bl)
            else:
                p.drawPath(path)

        # 数字文字 (PAGE 类型)
        if self._type == PaginationItemType.PAGE and self._page is not None:
            self._paint_page_text(p)

        # focus ring (focus-visible 仅键盘聚焦时显示)
        if self._focus_visible and self.isEnabled():
            self._paint_focus_ring(p, rect, radius_px)

        p.end()

    def _build_corner_path(
        self, rect: QRectF, tl: int, tr: int, br: int, bl: int
    ) -> QPainterPath:
        """构造 4 角独立圆角的 path (compact 模式必需)。"""
        path = QPainterPath()
        if tl == tr == br == bl:
            path.addRoundedRect(rect, tl, tl)
            return path
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        path.moveTo(x + tl, y)
        path.lineTo(x + w - tr, y)
        if tr > 0:
            path.quadTo(x + w, y, x + w, y + tr)
        path.lineTo(x + w, y + h - br)
        if br > 0:
            path.quadTo(x + w, y + h, x + w - br, y + h)
        path.lineTo(x + bl, y + h)
        if bl > 0:
            path.quadTo(x, y + h, x, y + h - bl)
        path.lineTo(x, y + tl)
        if tl > 0:
            path.quadTo(x, y, x + tl, y)
        path.closeSubpath()
        return path

    def _paint_compact_border(
        self, p: QPainter, rect: QRectF, tl: int, tr: int, br: int, bl: int
    ):
        """紧凑模式: 仅画外侧边框,避免相邻 item 边框相撞。"""
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        # 单一 item: 画完整闭环
        if self._is_first and self._is_last:
            path = self._build_corner_path(rect, tl, tr, br, bl)
            p.drawPath(path)
            return
        path = QPainterPath()
        if self._is_first:
            # 首项: 上 + 左 + 下 (带左上/左下圆角)
            path.moveTo(x + w, y)
            path.lineTo(x + tl, y)
            if tl > 0:
                path.quadTo(x, y, x, y + tl)
            path.lineTo(x, y + h - bl)
            if bl > 0:
                path.quadTo(x, y + h, x + bl, y + h)
            path.lineTo(x + w, y + h)
        elif self._is_last:
            # 末项: 上 + 右 + 下 (带右上/右下圆角)
            path.moveTo(x, y)
            path.lineTo(x + w - tr, y)
            if tr > 0:
                path.quadTo(x + w, y, x + w, y + tr)
            path.lineTo(x + w, y + h - br)
            if br > 0:
                path.quadTo(x + w, y + h, x + w - br, y + h)
            path.lineTo(x, y + h)
        else:
            # 中间: 仅上下两条横线
            path.moveTo(x, y)
            path.lineTo(x + w, y)
            path.moveTo(x, y + h)
            path.lineTo(x + w, y + h)
        p.drawPath(path)

    def _paint_page_text(self, p: QPainter):
        """绘制页码数字。"""
        cfg = self._size_cfg
        if not self.isEnabled():
            color = resolve_item_disabled_text(self._theme)
        elif self._is_active and self._show_active_fill:
            color = resolve_cursor_text(self._color, self._theme)
        else:
            color = resolve_item_text(self._theme)
        font = make_text_qfont(size=cfg["font_size"], weight="medium")
        p.setFont(font)
        p.setPen(color)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self._page))

    def _paint_focus_ring(self, p: QPainter, rect: QRectF, radius_px: int):
        """HeroUI focus-visible: 2px ring + 2px offset。"""
        from ...themes import HEROUI_COLORS

        ring_color = QColor(
            HEROUI_COLORS[self._color][500]
            if self._color != "default"
            else HEROUI_COLORS["primary"][500]
        )
        ring_color.setAlpha(180)
        # 偏移 2px 在外画 ring
        offset = 2.0
        ring_rect = rect.adjusted(-offset, -offset, offset, offset)
        ring_path = QPainterPath()
        rr = radius_px + int(offset)
        ring_path.addRoundedRect(ring_rect, rr, rr)
        pen = QPen(ring_color)
        pen.setWidthF(2.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ring_path)

    # ============================================================
    # SizeHint
    # ============================================================

    def sizeHint(self) -> QSize:
        cfg = self._size_cfg
        return QSize(cfg["item_min_width"], cfg["item_height"])


__all__ = ["_PaginationItem"]
