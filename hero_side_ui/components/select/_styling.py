"""Select 视觉同步 mixin（私有）。

负责：
- 末尾按钮（clear / arrow）尺寸根据 size 刷新
- 末尾按钮 icon 颜色根据 theme / color 刷新
- clear 按钮显隐根据 hover/value 状态计算
- enter/leave 维护 hover 标志
- input.line_edit 强制只读、点击切换 popover
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS, SELECT_SIZES
from ...utils import load_svg_icon


class _SelectStylingMixin:
    """Select 视觉同步 mixin。"""

    # ============================================================
    # 内部：图标 / 尺寸刷新
    # ============================================================
    def _refresh_end_btn_sizes(self):
        cfg = SELECT_SIZES.get(self._size, SELECT_SIZES["md"])
        size = cfg["end_btn_size"]
        self._end.clear_btn.set_icon_only_side(size)
        self._end.selector_btn.setFixedSize(size, size)
        self._end._h.setSpacing(cfg["end_gap"])

    def _refresh_end_icons(self):
        cfg = SELECT_SIZES.get(self._size, SELECT_SIZES["md"])

        # Clear 按钮：交给 Button 自管 icon 着色
        self._end.clear_btn.set_icon(self._clear_icon)
        self._end.clear_btn.set_icon_size(cfg["clear_icon_size"])

        # Selector chevron 颜色策略（对齐 HeroUI v2 select.ts:
        # color != default 时 selectorIcon 直接染主题色）
        if self._color != "default":
            sel_color = QColor(HEROUI_COLORS[self._color][500])
        else:
            sel_color = QColor(HEROUI_COLORS["default"][500])

        sel_pix = load_svg_icon(
            self._selector_icon,
            size=cfg["selector_icon_size"],
            color=sel_color,
            stroke_width=2.5,
        )
        self._end.selector_btn.set_pixmap(sel_pix)

    def _refresh_clear_visibility(self):
        has_value = bool(self._selected_keys)
        is_focused = self._input.line_edit.hasFocus() or self._is_open
        show = (
            self._is_clearable
            and has_value
            and not self._is_disabled
            and not self._user_is_readonly
            and not self._disallow_empty_selection
            and (self._is_hovered or is_focused)
        )
        self._end.clear_btn.setVisible(show)

    # ============================================================
    # Hover 跟踪
    # ============================================================
    def enterEvent(self, event):
        self._is_hovered = True
        self._refresh_clear_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._refresh_clear_visibility()
        super().leaveEvent(event)
