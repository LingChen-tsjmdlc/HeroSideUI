"""Progress / CircularProgress 组件尺寸配置。

对齐 HeroUI v2 的规范:
  Linear Progress:
    sm: track h-1 (≈ 4px)  + text-small (13px)
    md: track h-3 (≈ 12px) + text-medium (14px)   ← 默认
    lg: track h-5 (≈ 20px) + text-large (16px)

  Circular Progress (直径 / 环粗细随 size 同步变化):
    sm: 32×32  + stroke 3.5
    md: 44×44  + stroke 5.0                    ← 默认
    lg: 56×56  + stroke 7.0
"""

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

__all__ = ["PROGRESS_SIZES", "CIRCULAR_PROGRESS_SIZES"]
