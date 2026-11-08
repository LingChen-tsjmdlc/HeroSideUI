"""Checkbox 尺寸：box 16/20/24，radius 按 RADIUS.md 比例 0.5/0.6/0.7 运行时算。"""

CHECKBOX_SIZES = {
    "sm": {
        "box": 16,  # wrapper 尺寸
        "icon_w": 12,  # check icon 宽
        "icon_h": 8,  # check icon 高
        "label_font_size": 13,  # text-small
        "gap": 8,  # wrapper 与 label 的间距 (me-2 = 8px)
        "border_width": 2,
        "box_radius_ratio": 0.5,  # box 圆角 = RADIUS.md * 0.5
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
