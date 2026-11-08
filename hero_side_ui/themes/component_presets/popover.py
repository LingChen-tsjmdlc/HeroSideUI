"""POPOVER_SHADOWS：四档多层叠加阴影（layers/blur/offset_y/alpha），与 Card 不共用。"""

POPOVER_SHADOWS = {
    "none": {"layers": 0, "blur": 0, "offset_y": 0, "alpha": 0},
    "sm": {"layers": 2, "blur": 4, "offset_y": 1, "alpha": 8},
    "md": {"layers": 3, "blur": 6, "offset_y": 1, "alpha": 12},
    "lg": {"layers": 4, "blur": 16, "offset_y": 4, "alpha": 18},
}

__all__ = ["POPOVER_SHADOWS"]
