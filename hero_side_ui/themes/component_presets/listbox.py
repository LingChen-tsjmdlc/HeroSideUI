"""Listbox 组件主题预设 (LISTBOX_SIZES)。

对齐 HeroUI v2 menu.ts（listbox 复用 menu 样式）:
  - listbox(base): p-1, gap-1
  - listbox(list): gap-0.5
  - listboxItem(base): px-2 py-1.5, rounded-small, gap-2
  - listboxItem(title): text-small (HeroUI 14px)
  - listboxItem(description): text-tiny (12px)
  - listboxItem(selectedIcon): w-3 h-3 (12px)
  - showDivider: 底部 1px 分隔，距离 -bottom-1 (4px) → 我们用 mb=6 + 底部 1px 线

数值定义（单位 px）：
  list_padding         listbox 容器 padding
  list_gap             item 之间的垂直间距 (gap-0.5 = 2px)
  group_gap            外层 base gap-1 = 4px (section 之间)
  item_padding_x       item 水平 padding (px-2 = 8)
  item_padding_y       item 垂直 padding (py-1.5 = 6)
  item_gap             title <-> description / icon 间距
  item_radius          item 自身圆角 (rounded-small = 4)
  title_font_size      标题字号
  desc_font_size       description 字号
  shortcut_font_size   shortcut 标记字号
  selected_icon_size   选中图标尺寸
  divider_height       showDivider 时分隔线高度
  divider_margin_bot   showDivider 时 item 与分隔线之间的额外间距
  empty_height         emptyContent 高度 (h-10 = 40)
"""

LISTBOX_SIZES = {
    "sm": {
        "list_padding": 4,
        "list_gap": 2,
        "group_gap": 4,
        "item_padding_x": 8,
        "item_padding_y": 4,
        "item_gap": 6,
        "item_radius": 6,
        "title_font_size": 12,
        "desc_font_size": 11,
        "shortcut_font_size": 10,
        "selected_icon_size": 11,
        "divider_height": 1,
        "divider_margin_bot": 6,
        "empty_height": 36,
    },
    "md": {
        "list_padding": 4,
        "list_gap": 2,
        "group_gap": 4,
        "item_padding_x": 8,
        "item_padding_y": 6,
        "item_gap": 8,
        "item_radius": 8,
        "title_font_size": 14,
        "desc_font_size": 12,
        "shortcut_font_size": 11,
        "selected_icon_size": 12,
        "divider_height": 1,
        "divider_margin_bot": 6,
        "empty_height": 40,
    },
    "lg": {
        "list_padding": 4,
        "list_gap": 2,
        "group_gap": 4,
        "item_padding_x": 10,
        "item_padding_y": 8,
        "item_gap": 10,
        "item_radius": 10,
        "title_font_size": 15,
        "desc_font_size": 13,
        "shortcut_font_size": 12,
        "selected_icon_size": 14,
        "divider_height": 1,
        "divider_margin_bot": 8,
        "empty_height": 44,
    },
}

LISTBOX_SIZES["small"] = LISTBOX_SIZES["sm"]
LISTBOX_SIZES["medium"] = LISTBOX_SIZES["md"]
LISTBOX_SIZES["large"] = LISTBOX_SIZES["lg"]

__all__ = ["LISTBOX_SIZES"]
