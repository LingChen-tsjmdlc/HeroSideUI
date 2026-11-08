"""Spinner 尺寸：直径/border/dot/bar 各档；lg 笔触自绘修正加粗一档。"""

SPINNER_SIZES = {
    "sm": {
        "diameter": 20,
        "diameter_wave_dots": 20,
        "border_width": 2,
        "dot_size": 4,
        "label_font_size": 12,
        "bar_length": 5,
        "bar_width": 1.5,
    },
    "md": {
        "diameter": 32,
        "diameter_wave_dots": 32,
        "border_width": 3,
        "dot_size": 6,
        "label_font_size": 14,
        "bar_length": 8,
        "bar_width": 2.5,
    },
    "lg": {
        "diameter": 40,
        "diameter_wave_dots": 48,
        "border_width": 4,
        "dot_size": 10,
        "label_font_size": 16,
        "bar_length": 12,
        "bar_width": 3.5,
    },
}

# 别名
SPINNER_SIZES["small"] = SPINNER_SIZES["sm"]
SPINNER_SIZES["medium"] = SPINNER_SIZES["md"]
SPINNER_SIZES["large"] = SPINNER_SIZES["lg"]

__all__ = ["SPINNER_SIZES"]
