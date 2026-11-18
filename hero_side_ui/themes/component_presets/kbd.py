"""KBD 尺寸表：每档 size 自带 radius 表（高度受限，全局 RADIUS 会被钳制重合）。"""

# 默认 (md) 像素规格 —— 兼容旧引用
KBD_SIZES = {
    "padding_x": 6,  # px-1.5 = 6px
    "padding_y": 2,  # py-0.5 = 2px
    "spacing": 2,  # space-x-0.5 = 2px (key 之间)
    "font_size": 13,  # sm 档字号
    "icon_size": 14,  # icon 渲染尺寸 (与字号同档)
    "min_height": 24,  # 视觉锚点（避免内容过少时高度塌陷）
}

# 三档 size 表 —— 内嵌独立 radius 像素表
# full 不入表，运行时由 _radius_px() 取 min_height // 2
KBD_SIZE_TABLE = {
    "sm": {
        "padding_x": 5,
        "padding_y": 0,
        "spacing": 2,
        "font_size": 13,
        "icon_size": 12,
        "min_height": 20,
        # h=20, half=10 → lg=7 与 full=10 相差 3px
        "radius": {"none": 0, "sm": 2, "md": 4, "lg": 7},
    },
    "md": {
        **KBD_SIZES,
        # h=24, half=12 → lg=9 与 full=12 相差 3px
        "radius": {"none": 0, "sm": 3, "md": 6, "lg": 9},
    },
    "lg": {
        "padding_x": 8,
        "padding_y": 4,
        "spacing": 3,
        "font_size": 16,
        "icon_size": 16,
        "min_height": 32,
        # h=32, half=16 → lg=12 与 full=16 相差 4px
        "radius": {"none": 0, "sm": 4, "md": 8, "lg": 12},
    },
}

VALID_KBD_SIZES = tuple(KBD_SIZE_TABLE.keys())

# 合法 radius —— 从 sm 档的 radius keys 取齐 + 'full'
# （三档 radius 表的 keys 必须一致）
VALID_KBD_RADII = (*tuple(KBD_SIZE_TABLE["sm"]["radius"].keys()), "full")

__all__ = [
    "KBD_SIZES",
    "KBD_SIZE_TABLE",
    "VALID_KBD_RADII",
    "VALID_KBD_SIZES",
]
