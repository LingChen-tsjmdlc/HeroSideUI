"""Spinner 组件尺寸配置。

对齐 HeroUI v2 整体尺寸；笔触粗细在 HeroUI 原版 sm=2/md=3/lg=3，但 Qt
自绘下视觉感更弱（CSS border 与 QPen 渲染厚度不同），所以 lg 提到 4px
让 size 变大时线条同步变粗。

整体直径:
  default/simple/gradient/spinner: sm=20 / md=32 / lg=40
  wave/dots:                       sm=20 / md=32 / lg=48

字体:        sm=12 / md=14 / lg=16
Border:      sm=2  / md=3  / lg=4   ← 自绘修正过
Dot 直径:    sm=4  / md=6  / lg=10  ← lg 也调粗一档
Bar 尺寸:    sm 5×1.5 / md 8×2.5 / lg 12×3.5
"""

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
