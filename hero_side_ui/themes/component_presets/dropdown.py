"""DROPDOWN_SIZES：popover_max_height 与 menu_min_width（对齐 min-w-[200px]）。"""

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
