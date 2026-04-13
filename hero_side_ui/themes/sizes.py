"""
HeroUI v2 组件尺寸系统 (Component Sizes)

各组件的尺寸配置。以后新增组件在这里加对应的 XXX_SIZES 即可。
"""

BUTTON_SIZES = {
    "sm": {
        "padding_y": 6,
        "padding_x": 12,
        "font_size": "13px",
        "font_weight": "500",
        "default_radius": "sm",
        "height": "18px",
        "min_width": "36px",
    },
    "md": {
        "padding_y": 10,
        "padding_x": 16,
        "font_size": "16px",
        "font_weight": "500",
        "default_radius": "md",
        "height": "26px",
        "min_width": "52px",
    },
    "lg": {
        "padding_y": 14,
        "padding_x": 20,
        "font_size": "19px",
        "font_weight": "600",
        "default_radius": "lg",
        "height": "33px",
        "min_width": "66px",
    },
}

# 兼容长名称
BUTTON_SIZES["small"] = BUTTON_SIZES["sm"]
BUTTON_SIZES["medium"] = BUTTON_SIZES["md"]
BUTTON_SIZES["large"] = BUTTON_SIZES["lg"]


# ============================================================
# Accordion 尺寸
# ============================================================
ACCORDION_SIZES = {
    "sm": {
        "trigger_padding_y": 6,
        "content_padding_y": 0,
        "title_font_size": "14px",
        "subtitle_font_size": "12px",
        "content_font_size": "13px",
        "indicator_size": 16,
    },
    "md": {
        "trigger_padding_y": 8,
        "content_padding_y": 2,
        "title_font_size": "16px",
        "subtitle_font_size": "13px",
        "content_font_size": "14px",
        "indicator_size": 18,
    },
    "lg": {
        "trigger_padding_y": 12,
        "content_padding_y": 4,
        "title_font_size": "18px",
        "subtitle_font_size": "14px",
        "content_font_size": "16px",
        "indicator_size": 20,
    },
}
