"""Dropdown 组件主题预设 (DROPDOWN_SIZES)。

Dropdown 是"触发器 + 浮层菜单"的组合体，尺寸大头都在子组件里
（菜单项交给 Listbox、浮层外观交给 Popover），这里只补 Dropdown 自身特有的：

  - popover_max_height   菜单最大可视高度 (px)，超出后内部滚动
  - menu_min_width       菜单最小宽度 (px)，对齐 HeroUI 的 min-w-[200px]
"""

DROPDOWN_SIZES = {
    "sm": {
        "popover_max_height": 220,
        "menu_min_width": 180,
    },
    "md": {
        "popover_max_height": 260,
        "menu_min_width": 200,
    },
    "lg": {
        "popover_max_height": 300,
        "menu_min_width": 220,
    },
}

DROPDOWN_SIZES["small"] = DROPDOWN_SIZES["sm"]
DROPDOWN_SIZES["medium"] = DROPDOWN_SIZES["md"]
DROPDOWN_SIZES["large"] = DROPDOWN_SIZES["lg"]

__all__ = ["DROPDOWN_SIZES"]
