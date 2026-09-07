"""Dropdown 视觉同步 mixin（私有）。

负责：
- 主题解析与全局主题变更时的配色重刷
- 菜单宽度 / 高度刷新（宽度跟 trigger，高度默认贴内容，传 max_height 才固定）
- per-item 颜色覆盖（如"删除"项染 danger）
"""

from typing import Optional

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from ...core import ThemeProvider
from ...themes import DROPDOWN_SIZES


class _DropdownStylingMixin:
    """Dropdown 视觉同步 mixin（主题 / 菜单几何 / 单项配色）。"""

    # ============================================================
    # 主题
    # ============================================================
    def _resolve_theme(self, mode: str) -> str:
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        if self._theme_mode != "auto":
            return
        self._theme = theme
        self._apply_item_color_overrides()

    # ============================================================
    # 菜单几何
    # ============================================================
    def _size_cfg(self) -> dict:
        return DROPDOWN_SIZES.get(self._size, DROPDOWN_SIZES["md"])

    def _popover_radius(self) -> str:
        """浮层圆角；full 在浮层上退化为 lg（菜单项仍可以是 full）。"""
        return "lg" if self._radius == "full" else self._radius

    def _menu_min_width(self) -> int:
        """用户显式指定优先，否则走 size token。"""
        if self._min_width is not None:
            return int(self._min_width)
        return int(self._size_cfg()["menu_min_width"])

    def _menu_max_height(self) -> Optional[int]:
        """用户显式指定才限制；None = 完全由内容撑开。"""
        if self._max_height is not None:
            return max(1, int(self._max_height))
        return None

    def _screen_rect(self):
        screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _available_height_below(self) -> int:
        """trigger 下方到屏幕底还剩多少可用高度。"""
        rect = self._screen_rect()
        if rect is None:
            return int(self._size_cfg()["popover_max_height"])
        pos = self._trigger.mapToGlobal(QPoint(0, 0))
        _, _, _, bottom_margin = self._popover._frame_margins()
        return int(
            rect.bottom() - (pos.y() + self._trigger.height()) - 6 - bottom_margin
        )

    def _available_height_above(self) -> int:
        """trigger 上方到屏幕顶还剩多少可用高度。"""
        rect = self._screen_rect()
        if rect is None:
            return int(self._size_cfg()["popover_max_height"])
        pos = self._trigger.mapToGlobal(QPoint(0, 0))
        _, top_margin, _, _ = self._popover._frame_margins()
        return int(pos.y() - rect.top() - 6 - top_margin)

    def _menu_height_cap(self, prefer_below: bool) -> int:
        """高度上限；0 表示不限制（完全贴内容）。"""
        caps = []
        user_cap = self._menu_max_height()
        if user_cap is not None:
            caps.append(user_cap)
        if prefer_below:
            # 下方放不下会翻到上方，所以按两侧较大的一侧截断；
            # 再留个下限，别把菜单压成一条缝
            room = max(self._available_height_below(), self._available_height_above())
            caps.append(max(80, room))
        return max(1, min(caps)) if caps else 0

    @staticmethod
    def _layout_content_height(layout) -> int:
        """累加 layout 里可见子项的 sizeHint（隐藏项与 stretch 不计）。"""
        gap = max(0, layout.spacing())
        m = layout.contentsMargins()
        kids = [layout.itemAt(i).widget() for i in range(layout.count())]
        kids = [w for w in kids if w is not None and not w.isHidden()]
        h = sum(w.sizeHint().height() for w in kids)
        h += max(0, len(kids) - 1) * gap
        return int(h + m.top() + m.bottom())

    def _visible_menu_height(self) -> int:
        """菜单内容真实高度。

        按可见子项累算，不读 Qt 缓存的 minimumSizeHint —— 那个值在
        首次 show 前后会变（布局激活 + QScrollArea 拉伸），导致首开与
        后续打开高度不一致。
        """
        lb = self._listbox
        try:
            outer = lb._outer
            m = outer.contentsMargins()
            gap = max(0, outer.spacing())
            kids = [outer.itemAt(i).widget() for i in range(outer.count())]
            kids = [w for w in kids if w is not None and not w.isHidden()]
            list_h = self._layout_content_height(lb._list_v)
            h = sum(list_h if w is lb._list else w.sizeHint().height() for w in kids)
            h += max(0, len(kids) - 1) * gap
            return max(1, int(h + m.top() + m.bottom()))
        except Exception:
            return max(1, int(lb.sizeHint().height()))

    def _menu_target_height(self, prefer_below: bool) -> int:
        cap = self._menu_height_cap(prefer_below)
        content = self._visible_menu_height()
        return max(1, min(content, cap) if cap > 0 else content)

    def _refresh_menu_height(self, prefer_below: bool = False) -> None:
        target = self._menu_target_height(prefer_below)
        # min == max：ScrollShadow 的 sizeHint 是 Qt 缓存值（QScrollArea 只在
        # setWidget 时刷新），不把上下限夹住就会被它撑高、底部多出一截空白
        self._scroll.setMinimumHeight(target)
        self._scroll.setMaximumHeight(target)
        self._scroll.updateGeometry()
        if self._is_open:
            self._reposition_popover()

    def _refresh_menu_width(self) -> None:
        """菜单宽度至少等于 trigger，且不小于 size token 的最小宽度。"""
        w = max(self._trigger.width(), self._menu_min_width())
        self._scroll.setMinimumWidth(w)
        self._scroll.setMaximumWidth(w)

    # ============================================================
    # per-item 颜色覆盖
    # ============================================================
    def _apply_item_color_overrides(self) -> None:
        """把 item 自带的 color 重新下发（listbox 统一下发后会被覆盖）。"""
        if not self._item_colors:
            return
        lb = self._listbox
        for it in lb.items():
            color = self._item_colors.get(it.key())
            if not color:
                continue
            it.apply_style(
                variant=self._variant,
                color=color,
                size=self._size,
                radius=lb._radius,
                theme=self._theme,
                disable_animation=self._disable_animation,
                hide_selected_icon=self._hide_selected_icon,
                highlight_on_focus=lb._highlight_on_focus,
                selectable=lb._selection_mode != "none",
            )
