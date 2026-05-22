"""Tooltip 私有常量。

为什么独立：tooltip.py 已超 800 行红线，顺势把零散的 ARROW_SIZE / VALID_PLACEMENTS 集中到这里；
        _position.py 也需要 ARROW_SIZE，避免循环 import 与重复定义。
"""

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
