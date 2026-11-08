"""PAGINATION_SIZES：item 32/36/40、字号、gap 4、cursor 弹簧 1.1/300ms 等字段。"""

PAGINATION_SIZES = {
    "sm": {
        "item_height": 32,
        "item_min_width": 32,
        "font_size": 12,
        "padding_x": 4,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 14,
    },
    "md": {
        "item_height": 36,
        "item_min_width": 36,
        "font_size": 13,
        "padding_x": 8,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 16,
    },
    "lg": {
        "item_height": 40,
        "item_min_width": 40,
        "font_size": 15,
        "padding_x": 8,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 18,
    },
}

# 兼容长名称
PAGINATION_SIZES["small"] = PAGINATION_SIZES["sm"]
PAGINATION_SIZES["medium"] = PAGINATION_SIZES["md"]
PAGINATION_SIZES["large"] = PAGINATION_SIZES["lg"]

__all__ = ["PAGINATION_SIZES"]
