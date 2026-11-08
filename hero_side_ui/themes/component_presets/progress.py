"""Progress 尺寸：线性 track 4/12/20；环形 32/44/56 + stroke 3.5/5/7。"""

PROGRESS_SIZES = {
    "sm": {
        "track_height": 4,
        "label_font_size": 13,
        "value_font_size": 13,
    },
    "md": {
        "track_height": 12,
        "label_font_size": 14,
        "value_font_size": 14,
    },
    "lg": {
        "track_height": 20,
        "label_font_size": 16,
        "value_font_size": 16,
    },
}

CIRCULAR_PROGRESS_SIZES = {
    "sm": {
        "diameter": 32,
        "stroke_width": 3.5,
        "label_font_size": 13,
        "value_font_size": 10,
    },
    "md": {
        "diameter": 44,
        "stroke_width": 5.0,
        "label_font_size": 14,
        "value_font_size": 11,
    },
    "lg": {
        "diameter": 56,
        "stroke_width": 7.0,
        "label_font_size": 15,
        "value_font_size": 13,
    },
}

for d in (PROGRESS_SIZES, CIRCULAR_PROGRESS_SIZES):
    d["small"] = d["sm"]
    d["medium"] = d["md"]
    d["large"] = d["lg"]

__all__ = ["CIRCULAR_PROGRESS_SIZES", "PROGRESS_SIZES"]
