"""SLIDER_SIZES：thumb 20/24/28、track 4/12/28、inner-dot 等；朝向翻转在组件内做。"""

SLIDER_SIZES = {
    "sm": {
        "thumb": 20,  # w-5 h-5
        "inner_dot": 16,  # after:w-4 h-4
        "track_thickness": 4,  # h-1 (水平) / w-1 (垂直)
        "label_font_size": 13,  # text-small
        "value_font_size": 13,
        "mark_font_size": 12,
        "mark_offset": 4,  # mt-1 默认
    },
    "md": {
        "thumb": 24,  # w-6 h-6
        "inner_dot": 20,  # after:w-5 h-5
        "track_thickness": 12,  # h-3 / w-3
        "label_font_size": 13,
        "value_font_size": 13,
        "mark_font_size": 13,
        "mark_offset": 4,
    },
    "lg": {
        "thumb": 28,  # w-7 h-7
        "inner_dot": 20,  # after:w-5 h-5
        "track_thickness": 28,  # h-7 / w-7
        "label_font_size": 15,
        "value_font_size": 15,
        "mark_font_size": 14,
        "mark_offset": 8,  # mt-2
    },
}

# 别名：small/medium/large
SLIDER_SIZES["small"] = SLIDER_SIZES["sm"]
SLIDER_SIZES["medium"] = SLIDER_SIZES["md"]
SLIDER_SIZES["large"] = SLIDER_SIZES["lg"]

__all__ = ["SLIDER_SIZES"]
