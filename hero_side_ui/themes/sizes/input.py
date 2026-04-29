"""Input 组件尺寸配置。

对齐 HeroUI v2 的 Input 规范：
  - 默认 outside label 时高度: sm=32 / md=40 / lg=48
  - inside label 时高度会变高: sm=48 / md=56 / lg=64
  - faded / bordered 的 border-width = 2px (border-medium)
  - underlined 的 border-bottom-width = 2px
  - clear button 从 scale 0.9 opacity 0 → scale 1.0 opacity 0.7 (HeroUI peer-data-[filled=true])
"""

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

__all__ = ["INPUT_SIZES"]
