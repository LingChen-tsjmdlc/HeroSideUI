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


# ============================================================
# Input 尺寸
# ============================================================
# 对齐 HeroUI v2 的 Input 规范：
#   - 默认 outside label 时高度: sm=32 / md=40 / lg=48
#   - inside label 时高度会变高: sm=48 / md=56 / lg=64
#   - faded / bordered 的 border-width = 2px (border-medium)
#   - underlined 的 border-bottom-width = 2px
#   - clear button 从 scale 0.9 opacity 0 → scale 1.0 opacity 0.7 (HeroUI peer-data-[filled=true])
INPUT_SIZES = {
    "sm": {
        # 外观
        "height": 32,
        "inside_height": 48,               # inside label 模式下的高度
        "padding_x": 8,
        "padding_y": 4,
        "inside_padding_y": 6,
        "gap": 8,                          # start_icon / input / end_icon 之间的间距
        # 字号（单位 px，对齐 HeroUI 的 text-tiny/small/medium）
        "label_font_size": 12,             # resting label font
        "label_float_font_size": 10,       # floated label font (≈ scale 85%)
        "input_font_size": 13,
        "outside_label_font_size": 12,
        "helper_font_size": 11,
        # 其它
        "default_radius": "sm",
        "clear_icon_size": 16,
        "start_icon_size": 16,
        "end_icon_size": 16,
        "border_width": 2,
        # inside label 浮起时相对 wrapper 内部的偏移 & 输入文字的预留空间
        # label_float_x/y 是相对 wrapper 内 padding 起点的偏移（正常落在 wrapper 内部左上）
        "label_float_x": 0,                # 贴 wrapper 左 padding 对齐 line_edit 左
        "label_float_y": 5,                # 距 wrapper 顶 5px（留呼吸空间，不要顶死）
        "inside_input_top_space": 14,      # inside 模式下输入文字上方预留高度（容纳浮起 label）
        "min_width": 240,                  # 组件整体最小宽度
    },
    "md": {
        "height": 40,
        "inside_height": 56,
        "padding_x": 12,
        "padding_y": 6,
        "inside_padding_y": 8,
        "gap": 8,
        "label_font_size": 13,
        "label_float_font_size": 11,
        "input_font_size": 14,
        "outside_label_font_size": 13,
        "helper_font_size": 12,
        "default_radius": "md",
        "clear_icon_size": 18,
        "start_icon_size": 18,
        "end_icon_size": 18,
        "border_width": 2,
        "label_float_x": 0,
        "label_float_y": 6,
        "inside_input_top_space": 16,
        "min_width": 260,
    },
    "lg": {
        "height": 48,
        "inside_height": 64,
        "padding_x": 14,
        "padding_y": 8,
        "inside_padding_y": 10,
        "gap": 10,
        "label_font_size": 15,
        "label_float_font_size": 13,
        "input_font_size": 16,
        "outside_label_font_size": 14,
        "helper_font_size": 13,
        "default_radius": "lg",
        "clear_icon_size": 20,
        "start_icon_size": 20,
        "end_icon_size": 20,
        "border_width": 2,
        "label_float_x": 0,
        "label_float_y": 7,
        "inside_input_top_space": 18,
        "min_width": 300,
    },
}

INPUT_SIZES["small"] = INPUT_SIZES["sm"]
INPUT_SIZES["medium"] = INPUT_SIZES["md"]
INPUT_SIZES["large"] = INPUT_SIZES["lg"]


# ============================================================
# Divider 尺寸
# ============================================================
# 对齐 HeroUI v2: h-divider = 1px, w-divider = 1px
DIVIDER_SIZES = {
    "horizontal": {
        "thickness": 1,   # 分割线高度 (px)
    },
    "vertical": {
        "thickness": 1,   # 分割线宽度 (px)
    },
}


# ============================================================
# Card 尺寸
# ============================================================
# 对齐 HeroUI v2 的 Card 规范:
#   - header/body/footer 的 padding 均为 p-3 (12px) —— 写死在组件里，不再暴露 size prop
#   - shadow: none/sm/md/lg
#   - radius: none/sm/md/lg (默认 lg)

# Card 阴影配置: 对齐 HeroUI shadow-small / shadow-medium / shadow-large
CARD_SHADOWS = {
    "none": {"offset_y": 0, "blur": 0, "spread": 0, "opacity": 0.0},
    "sm": {"offset_y": 1, "blur": 8, "spread": 0, "opacity": 0.06},
    "md": {"offset_y": 4, "blur": 14, "spread": 0, "opacity": 0.08},
    "lg": {"offset_y": 8, "blur": 30, "spread": 0, "opacity": 0.12},
}
