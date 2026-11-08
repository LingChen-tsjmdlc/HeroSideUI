"""LISTBOX_SIZES：容器/item padding、字号、选中图标 12、分隔线与空态等字段。"""

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
