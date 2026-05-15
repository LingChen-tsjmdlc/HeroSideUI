"""Popover 包内的共享常量（私有）。"""

ARROW_SIZE = 5
"""箭头一半边长（视觉像 5~6px 的小箭头）。"""

ARROW_INSET = 2
"""箭头底边相对 content_rect 向内偏移，避免圆角缝隙。"""

DEFAULT_PADDING = 10
"""popover 内部内容的默认 padding。"""

VALID_PLACEMENTS = {
    "top",
    "top-start",
    "top-end",
    "bottom",
    "bottom-start",
    "bottom-end",
    "left",
    "left-start",
    "left-end",
    "right",
    "right-start",
    "right-end",
}
"""合法的 placement 值（12 种 corner/center 组合）。"""
