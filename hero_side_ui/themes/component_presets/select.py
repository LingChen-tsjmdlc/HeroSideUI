"""SELECT_SIZES：图标/按钮尺寸、rotate 时长、popover 高度与 chip_max 折叠数。"""

SELECT_SIZES = {
    "sm": {
        "selector_icon_size": 14,
        "clear_icon_size": 12,
        "end_btn_size": 18,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 220,
        "chip_max": 2,
    },
    "md": {
        "selector_icon_size": 16,
        "clear_icon_size": 14,
        "end_btn_size": 20,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 260,
        "chip_max": 3,
    },
    "lg": {
        "selector_icon_size": 18,
        "clear_icon_size": 16,
        "end_btn_size": 22,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 300,
        "chip_max": 3,
    },
}

SELECT_SIZES["small"] = SELECT_SIZES["sm"]
SELECT_SIZES["medium"] = SELECT_SIZES["md"]
SELECT_SIZES["large"] = SELECT_SIZES["lg"]

__all__ = ["SELECT_SIZES"]
