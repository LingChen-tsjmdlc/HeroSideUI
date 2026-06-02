"""Kbd 组件主题预设。

对齐 HeroUI v2 kbd.ts:
  base: px-1.5 py-0.5 + space-x-0.5 + font-normal + text-small + shadow-small + rounded-small

HeroUI 原版无 size / radius variant；本组件按项目惯例扩展三档 size。
radius 像素值不走全局 RADIUS token —— Kbd 高度受限（18~28px），
全局值（如 lg=14）会被 Qt 钳制到短边一半导致与 full 视觉重合。
故每档 size 自带一张 radius 表，且保证 lg 严格小于 full（差 2px）。
"""

# 默认 (md) 像素规格 —— 兼容旧引用
KBD_SIZES = {
    "padding_x": 6,  # px-1.5 = 6px
    "padding_y": 2,  # py-0.5 = 2px
    "spacing": 2,  # space-x-0.5 = 2px (key 之间)
    "font_size": 14,  # text-small (Tailwind text-sm 约 14px)
    "icon_size": 14,  # icon 渲染尺寸 (与字号同档)
    "min_height": 22,  # 视觉锚点（避免内容过少时高度塌陷）
}

# 三档 size 表 —— 内嵌独立 radius 像素表
# full 不入表，运行时由 _radius_px() 取 min_height // 2
KBD_SIZE_TABLE = {
    "sm": {
        "padding_x": 5,
        "padding_y": 1,
        "spacing": 2,
        "font_size": 12,
        "icon_size": 12,
        "min_height": 18,
        # h=18, half=9 → lg=7 与 full=9 相差 2px
        "radius": {"none": 0, "sm": 2, "md": 4, "lg": 7},
    },
    "md": {
        **KBD_SIZES,
        # h=22, half=11 → lg=9 与 full=11 相差 2px
        "radius": {"none": 0, "sm": 3, "md": 6, "lg": 9},
    },
    "lg": {
        "padding_x": 8,
        "padding_y": 4,
        "spacing": 3,
        "font_size": 16,
        "icon_size": 16,
        "min_height": 28,
        # h=28, half=14 → lg=12 与 full=14 相差 2px
        "radius": {"none": 0, "sm": 4, "md": 8, "lg": 12},
    },
}

VALID_KBD_SIZES = tuple(KBD_SIZE_TABLE.keys())

# 合法 radius —— 从 sm 档的 radius keys 取齐 + 'full'
# （三档 radius 表的 keys 必须一致）
VALID_KBD_RADII = tuple(KBD_SIZE_TABLE["sm"]["radius"].keys()) + ("full",)

# shadow-small 阴影预设（与 Card sm 同源，对齐 HeroUI shadow-small）
KBD_SHADOW = {
    "offset_y": 1,
    "blur": 8,
    "opacity": 0.06,
}

__all__ = [
    "KBD_SIZES",
    "KBD_SIZE_TABLE",
    "VALID_KBD_SIZES",
    "VALID_KBD_RADII",
    "KBD_SHADOW",
]
