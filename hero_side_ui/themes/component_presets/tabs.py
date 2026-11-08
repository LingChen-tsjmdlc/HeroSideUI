"""Tabs 尺寸预设 TABS_SIZES：sm/md/lg 的 tab 高度、字号与 padding token。

对齐 HeroUI tabs.ts；underlined cursor 2px 高 80% 宽，bordered 边框 2px。
"""

TABS_SIZES = {
    "sm": {
        "tab_height": 28,
        "tab_font_size": 12,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 36,
    },
    "md": {
        "tab_height": 32,
        "tab_font_size": 13,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 44,
    },
    "lg": {
        "tab_height": 36,
        "tab_font_size": 15,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 52,
    },
}

# 兼容长名称
TABS_SIZES["small"] = TABS_SIZES["sm"]
TABS_SIZES["medium"] = TABS_SIZES["md"]
TABS_SIZES["large"] = TABS_SIZES["lg"]

__all__ = ["TABS_SIZES"]
