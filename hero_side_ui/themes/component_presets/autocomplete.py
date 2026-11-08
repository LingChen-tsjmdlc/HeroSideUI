"""AUTOCOMPLETE_SIZES：selector/clear 图标尺寸、按钮命中区、popover 高度上限。"""

AUTOCOMPLETE_SIZES = {
    "sm": {
        "selector_icon_size": 14,
        "clear_icon_size": 12,
        "end_btn_size": 18,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 220,
    },
    "md": {
        "selector_icon_size": 16,
        "clear_icon_size": 14,
        "end_btn_size": 20,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 260,
    },
    "lg": {
        "selector_icon_size": 18,
        "clear_icon_size": 16,
        "end_btn_size": 22,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 300,
    },
}

AUTOCOMPLETE_SIZES["small"] = AUTOCOMPLETE_SIZES["sm"]
AUTOCOMPLETE_SIZES["medium"] = AUTOCOMPLETE_SIZES["md"]
AUTOCOMPLETE_SIZES["large"] = AUTOCOMPLETE_SIZES["lg"]

__all__ = ["AUTOCOMPLETE_SIZES"]
