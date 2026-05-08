"""Popover 组件主题预设。

POPOVER_SHADOWS 定义 Popover 的 4 档阴影预设 (none/sm/md/lg)，对齐 HeroUI v2
的 shadow-small / shadow-medium / shadow-large 语义。注意：Popover 的阴影通过
QGraphicsDropShadowEffect 多层叠加实现（layers 字段表示叠加层数），和 Card 的
CSS box-shadow 规格不同，所以两者不共用同一组数据。

字段说明:
    layers   - 叠加的投影层数（0 表示不画阴影）
    blur     - 模糊半径 (px)
    offset_y - 垂直偏移 (px)
    alpha    - 每层阴影的 alpha 值 (0~255)
"""

POPOVER_SHADOWS = {
    "none": {"layers": 0, "blur": 0, "offset_y": 0, "alpha": 0},
    "sm": {"layers": 2, "blur": 4, "offset_y": 1, "alpha": 8},
    "md": {"layers": 3, "blur": 6, "offset_y": 1, "alpha": 12},
    "lg": {"layers": 3, "blur": 8, "offset_y": 2, "alpha": 14},
}

__all__ = ["POPOVER_SHADOWS"]
