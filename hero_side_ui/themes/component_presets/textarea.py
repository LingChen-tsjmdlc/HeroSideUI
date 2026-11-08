"""Textarea 尺寸：继承 INPUT_SIZES，补 row_height/文本 padding/inside 顶部预留；无 underlined。"""

TEXTAREA_SIZES = {
    "sm": {
        # 行高（根据 input_font_size * 1.55 取整估算，实际由 fontMetrics 校准）
        "row_height": 20,
        # 内边距（用于 wrapper layout 边距）
        "padding_x": 10,
        "padding_y": 8,
        "inside_padding_y": 8,
        "gap": 8,
        # 字号
        "label_font_size": 12,
        "label_float_font_size": 10,
        "input_font_size": 13,
        "outside_label_font_size": 12,
        "helper_font_size": 11,
        # 其它
        "default_radius": "sm",
        "clear_icon_size": 16,
        "start_icon_size": 16,
        "end_icon_size": 16,
        "border_width": 2,
        # inside label 浮起偏移 & 文本顶部预留
        "label_float_x": 0,
        "label_float_y": 5,
        "inside_input_top_space": 18,  # textarea 比 input 多一点，让浮起 label 与第一行文字有呼吸
        "min_width": 240,
    },
    "md": {
        "row_height": 22,
        "padding_x": 12,
        "padding_y": 10,
        "inside_padding_y": 10,
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
        "inside_input_top_space": 20,
        "min_width": 260,
    },
    "lg": {
        "row_height": 26,
        "padding_x": 14,
        "padding_y": 12,
        "inside_padding_y": 12,
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
        "inside_input_top_space": 22,
        "min_width": 300,
    },
}

TEXTAREA_SIZES["small"] = TEXTAREA_SIZES["sm"]
TEXTAREA_SIZES["medium"] = TEXTAREA_SIZES["md"]
TEXTAREA_SIZES["large"] = TEXTAREA_SIZES["lg"]

__all__ = ["TEXTAREA_SIZES"]
