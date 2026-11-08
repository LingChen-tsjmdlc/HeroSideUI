"""Tooltip 私有常量（ARROW_SIZE 等）；独立成文件避免循环 import。"""

from __future__ import annotations

ARROW_SIZE = 5  # 箭头一半边长
ARROW_INSET = 2  # 箭头底边相对 content_rect 向内偏移

# 合法 placement
VALID_PLACEMENTS = frozenset(
    {
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
)
