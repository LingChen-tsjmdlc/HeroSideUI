"""Dropdown 视觉同步 mixin：主题重刷、菜单宽高刷新与 per-item 配色。"""

from ..._shared.overlays.bounds import space_above, space_below
from ...core import ThemeProvider
from ...themes import DROPDOWN_SIZES


class _DropdownStylingMixin:
    """Dropdown 视觉同步 mixin（主题 / 菜单几何 / 单项配色）。"""

    # ============================================================
    # 主题
    # ============================================================
    def _resolve_theme(self, mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；auto 取全局主题，其余回退 light。
        """
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            固定主题（_theme_mode != auto）时直接返回；
            广播后重刷 per-item 颜色覆盖。
        """
        if self._theme_mode != "auto":
            return
        self._theme = theme
        self._apply_item_color_overrides()

    # ============================================================
    # 菜单几何
    # ============================================================
    def _size_cfg(self) -> dict:
        """取当前尺寸档位配置。

        Returns:
            DROPDOWN_SIZES 中的配置字典；非法档位回退 md。
        """
        return DROPDOWN_SIZES.get(self._size, DROPDOWN_SIZES["md"])

    def _popover_radius(self) -> str:
        """浮层圆角档位。

        Returns:
            full 在浮层上退化为 lg（菜单项仍可以是 full）。
        """
        return "lg" if self._radius == "full" else self._radius

    def _menu_min_width(self) -> int:
        """菜单最小宽度。

        Returns:
            用户显式指定优先，否则取 size token 的 menu_min_width。
        """
        if self._min_width is not None:
            return int(self._min_width)
        return int(self._size_cfg()["menu_min_width"])

    def _menu_max_height(self) -> int | None:
        """菜单最大高度。

        Returns:
            用户显式指定（下限 1）才限制；None 表示完全由内容撑开。
        """
        if self._max_height is not None:
            return max(1, int(self._max_height))
        return None

    def _room_for_menu(self) -> int | None:
        """按弹出方向取窗口内可用高度；左右弹出时不限。

        Note:
            优先指定方向：该侧够放最小菜单（80px）就按该侧算；
            不够时 Popover 会翻到另一侧，这时按上下较大的一侧算。
        """
        place = self._placement  # Dropdown 自己持有设定方向，不去读 Popover 的私有属性
        try:
            margins = self._popover.frame_margins()
            below = int(space_below(self._trigger, margins) - 6)
            above = int(space_above(self._trigger, margins) - 6)
        except RuntimeError:
            return None
        if place.startswith("bottom"):
            return below if below >= 80 else max(below, above)
        if place.startswith("top"):
            return above if above >= 80 else max(below, above)
        return None

    def _menu_height_cap(self, prefer_below: bool) -> int:
        """菜单高度上限。

        Args:
            prefer_below: True 时按窗口内可用高度截断并留 80px 下限。

        Returns:
            0 表示不限制（完全贴内容）；否则为所有上限中的最小值。
        """
        caps = []
        user_cap = self._menu_max_height()
        if user_cap is not None:
            caps.append(user_cap)
        room = self._room_for_menu() if prefer_below else None
        if room is not None:
            caps.append(max(80, room))
        return max(1, min(caps)) if caps else 0

    @staticmethod
    def _layout_content_height(layout) -> int:
        """累加 layout 里可见子项的 sizeHint。

        Args:
            layout: 目标 QLayout。

        Returns:
            可见子项高度之和 + 间距 + 上下 margin；隐藏项与 stretch 不计。
        """
        gap = max(0, layout.spacing())
        m = layout.contentsMargins()
        kids = [layout.itemAt(i).widget() for i in range(layout.count())]
        kids = [w for w in kids if w is not None and not w.isHidden()]
        h = sum(w.sizeHint().height() for w in kids)
        h += max(0, len(kids) - 1) * gap
        return int(h + m.top() + m.bottom())

    def _visible_menu_height(self) -> int:
        """按可见子项累算菜单真实高度。

        Returns:
            菜单内容高度（至少 1px）；异常时回退 listbox.sizeHint().height()。

        Note:
            不读 minimumSizeHint——首展前后会变。
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
        """计算菜单目标高度。

        Args:
            prefer_below: 是否优先向下展开（决定高度上限）。

        Returns:
            min(内容高度, 上限)；上限为 0 时直接返回内容高度。
        """
        cap = self._menu_height_cap(prefer_below)
        content = self._visible_menu_height()
        return max(1, min(content, cap) if cap > 0 else content)

    def _refresh_menu_height(self, prefer_below: bool = False) -> None:
        """刷新菜单滚动区高度并按需重定位 popover。

        Args:
            prefer_below: True 时按优先向下展开计算上限。

        Note:
            min == max 必须同时夹住：ScrollShadow 的 sizeHint 是 Qt 缓存值
            （QScrollArea 只在 setWidget 时刷新），不夹住就会被撑高、
            底部多出一截空白。
        """
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
        """把 item 自带的 color 重新下发。

        Note:
            listbox 统一下发样式后会把单项色覆盖掉，故主题切换 / 装配后
            需按 _item_colors 重新 apply_style 一遍。
        """
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
