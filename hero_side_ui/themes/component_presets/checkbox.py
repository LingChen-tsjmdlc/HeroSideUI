"""Checkbox 组件尺寸配置。

对齐 HeroUI v2 的 checkbox 规范:
    sm: 16x16 box + text-small + icon 12x8 + me-2 + radius = RADIUS.md * 0.5
    md: 20x20 box + text-medium + icon 16x12 + me-2 + radius = RADIUS.md * 0.6  (默认)
    lg: 24x24 box + text-large + icon 20x16 + me-2 + radius = RADIUS.md * 0.7

box_radius_ratio 会在运行时 * RADIUS["md"] 计算像素值；显式传入 radius 时
(none/sm/md/lg/full)，则改用 RADIUS 常量或 full 特殊处理。
"""

CHECKBOX_SIZES = {
    "sm": {
        "box": 16,               # wrapper 尺寸
        "icon_w": 12,            # check icon 宽
        "icon_h": 8,             # check icon 高
        "label_font_size": 13,   # text-small
        "gap": 8,                # wrapper 与 label 的间距 (me-2 = 8px)
        "border_width": 2,
        "box_radius_ratio": 0.5, # box 圆角 = RADIUS.md * 0.5
    },
    "md": {
        "box": 20,
        "icon_w": 16,
        "icon_h": 12,
        "label_font_size": 14,
        "gap": 8,
        "border_width": 2,
        "box_radius_ratio": 0.6,
    },
    "lg": {
        "box": 24,
        "icon_w": 20,
        "icon_h": 16,
        "label_font_size": 16,
        "gap": 8,
        "border_width": 2,
        "box_radius_ratio": 0.7,
    },
}

CHECKBOX_SIZES["small"] = CHECKBOX_SIZES["sm"]
CHECKBOX_SIZES["medium"] = CHECKBOX_SIZES["md"]
CHECKBOX_SIZES["large"] = CHECKBOX_SIZES["lg"]

__all__ = ["CHECKBOX_SIZES"]
