"""Table 列头单元格（自绘）。

对齐 HeroUI v2 table.ts 的 ``th`` slot：
  - bg-default-100，首列左圆角、尾列右圆角（rounded-s-lg / rounded-e-lg）
  - text-tiny font-semibold text-foreground-500，hover 时 foreground-400
  - data-[sortable=true] 可排序：hover 显示排序箭头；激活列箭头常显，
    descending 旋转 180°（chevron-down 默认指向 ascending? HeroUI: 默认 down，
    ascending 时 rotate-180 → 朝上）

排序箭头用 chevron-down SVG 渲染到一个包内私有 QLabel（铁律 9 例外：纯图形）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QTransform
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from ...utils.icon_utils import load_svg_icon
from ..text import Text
from . import _palette as pal
from ._cell import _ALIGN_FLAGS
from ._constants import VALID_ALIGNS


class _SortIcon(QLabel):
    """排序箭头（纯图形 QLabel，铁律 9 例外）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._size = 14
        self._color = QColor("#888888")
        self._descending = True
        self._visible_icon = False

    def configure(self, *, size: int, color: QColor, descending: bool, visible: bool):
        self._size = size
        self._color = color
        self._descending = descending
        self._visible_icon = visible
        self._render()

    def _render(self):
        if not self._visible_icon:
            self.clear()
            self.setFixedSize(self._size, self._size)
            return
        pm = load_svg_icon(
            "heroicons--chevron-down", size=self._size, color=self._color, stroke_width=3
        )
        # ascending 时朝上（旋转 180）
        if not self._descending:
            pm = pm.transformed(QTransform().rotate(180), Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(pm)
        self.setFixedSize(self._size, self._size)


class _TableColumnHeader(QWidget):
    """列头单元格。自绘 default-100 底色 + 圆角拼接，承载标题 + 排序箭头。"""

    sort_clicked = Signal(str)  # 发出列 key

    def __init__(self, key: str, label: str = "", *, align: str = "start",
                 allows_sorting: bool = False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._key = key
        if align not in VALID_ALIGNS:
            align = "start"
        self._align = align
        self._allows_sorting = allows_sorting

        # 样式状态
        self._color = "default"
        self._size = "md"
        self._theme = "light"
        self._radius = "lg"
        self._is_first_col = False
        self._is_last_col = False
        self._hide_header = False
        self._header_gap = 0  # 底部预留间距，仅占位不绘制背景

        # 排序状态
        self._is_sort_active = False
        self._sort_descending = True

        self._hover = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setAlignment(_ALIGN_FLAGS[self._align])

        self._label = Text(label, weight="bold", theme="auto")
        self._layout.addWidget(self._label)

        self._sort_icon = _SortIcon(self)
        self._layout.addWidget(self._sort_icon)
        self._sort_icon.setVisible(allows_sorting)

        if allows_sorting:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def key(self) -> str:
        return self._key

    def allows_sorting(self) -> bool:
        return self._allows_sorting

    # ------------------------------------------------------------
    def apply_style(
        self, *, color: str, size: str, theme: str, radius: str,
        is_first_col: bool, is_last_col: bool, hide_header: bool,
    ):
        self._color = color
        self._size = size
        self._theme = theme
        self._radius = radius
        self._is_first_col = is_first_col
        self._is_last_col = is_last_col
        self._hide_header = hide_header

        from ...themes import TABLE_SIZES

        cfg = TABLE_SIZES.get(size, TABLE_SIZES["md"])
        px = cfg["cell_padding_x"]
        self._header_gap = cfg.get("header_gap", 0)
        # 顶部内容区 + 底部预留间距：layout 上边距 0，下边距 = header_gap，
        # 让文字/箭头落在背景块内，背景块只画顶部 header_height 那段。
        self._layout.setContentsMargins(px, 0, px, self._header_gap)
        if hide_header:
            self.setFixedHeight(0)
            self.setVisible(False)
        else:
            self.setVisible(True)
            total_h = cfg["header_height"] + self._header_gap
            self.setMinimumHeight(total_h)
            self.setMaximumHeight(total_h)

        self._label.set_size(cfg["header_font_size"])
        self._refresh_label_color()
        self._refresh_sort_icon()
        self.update()

    def set_sort_state(self, *, active: bool, descending: bool):
        self._is_sort_active = active
        self._sort_descending = descending
        self._refresh_sort_icon()
        self._refresh_label_color()

    # ------------------------------------------------------------
    def _refresh_label_color(self):
        if self._hover and self._allows_sorting:
            c = pal.header_text_hover(self._theme)
        else:
            c = pal.header_text(self._theme)
        self._label.set_color(c.name())

    def _refresh_sort_icon(self):
        if not self._allows_sorting:
            self._sort_icon.setVisible(False)
            return
        self._sort_icon.setVisible(True)
        from ...themes import TABLE_SIZES

        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        # 激活列常显；否则仅 hover 时显示中性下箭头作为可排序提示
        visible = self._is_sort_active or self._hover
        color = pal.header_text_hover(self._theme) if self._hover else pal.header_text(self._theme)
        # 非激活态显示中性下箭头；激活态按 asc(朝上)/desc(朝下)
        descending = self._sort_descending if self._is_sort_active else True
        self._sort_icon.configure(
            size=cfg["sort_icon_size"],
            color=color,
            descending=descending,
            visible=visible,
        )

    # ------------------------------------------------------------
    def enterEvent(self, e):
        self._hover = True
        self._refresh_label_color()
        self._refresh_sort_icon()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._refresh_label_color()
        self._refresh_sort_icon()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._allows_sorting and e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.pos()):
            self.sort_clicked.emit(self._key)
        super().mouseReleaseEvent(e)

    # ------------------------------------------------------------
    def paintEvent(self, e):
        if self._hide_header:
            return
        # 背景块只画顶部 (height - header_gap)，底部 header_gap 留白做表头与内容的间距
        bg_h = max(0, self.height() - self._header_gap)
        r = pal.resolve_radius_px(self._radius, bg_h)
        tl = bl = r if self._is_first_col else 0
        tr = br = r if self._is_last_col else 0

        from ._cell import _rounded_path

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), bg_h)
        path = _rounded_path(rect, tl, tr, br, bl)
        p.fillPath(path, pal.header_bg(self._theme))


__all__ = ["_TableColumnHeader"]
