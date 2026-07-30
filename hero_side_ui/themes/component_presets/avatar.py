"""Avatar 组件尺寸配置。

对照 HeroUI avatar.ts 的 size variant：
- sm: w-8 h-8(32) text-tiny(12)
- md: w-10 h-10(40) text-tiny(12)
- lg: w-14 h-14(56) text-small(14)
isBordered: ring-2 ring-offset-2 → 边框 2px + 与背景间隔 2px。
icon 占盒子 80%（对照 AvatarIcon 的 width/height 80%）。
AvatarGroup 堆叠重叠量 -ms-2 ≈ 8px，hover 时后一个位移 12px（-translate-x-3）。
"""

# text_size 用项目 Text 的 token（xs/sm/md），不是 px
AVATAR_SIZES = {
    "sm": {
        "box": 32,
        "text_size": "xs",   # 12px ≈ text-tiny
        "icon_ratio": 0.8,
    },
    "md": {
        "box": 40,
        "text_size": "xs",   # 12px ≈ text-tiny
        "icon_ratio": 0.8,
    },
    "lg": {
        "box": 56,
        "text_size": "sm",   # 14px ≈ text-small
        "icon_ratio": 0.8,
    },
}

# isBordered: ring 宽度 + 与背景的偏移间隔（ring-2 ring-offset-2）
AVATAR_RING_WIDTH = 2
AVATAR_RING_OFFSET = 2

# AvatarGroup 堆叠：相邻头像重叠量（-ms-2 = 0.5rem）
AVATAR_GROUP_OVERLAP = 8
# hover 时后续头像让位位移（data-[hover]:-translate-x-3 = 0.75rem）
AVATAR_GROUP_HOVER_SHIFT = 12
# grid 模式格子间距（gap-3 = 0.75rem）
AVATAR_GROUP_GRID_GAP = 12
# grid 模式默认列数（grid-cols-4）
AVATAR_GROUP_GRID_COLS = 4

# 兼容长名称
AVATAR_SIZES["small"] = AVATAR_SIZES["sm"]
AVATAR_SIZES["medium"] = AVATAR_SIZES["md"]
AVATAR_SIZES["large"] = AVATAR_SIZES["lg"]

VALID_AVATAR_SIZES = ("sm", "md", "lg")
VALID_AVATAR_COLORS = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
VALID_AVATAR_RADII = ("none", "sm", "md", "lg", "full")

__all__ = [
    "AVATAR_SIZES",
    "AVATAR_RING_WIDTH",
    "AVATAR_RING_OFFSET",
    "AVATAR_GROUP_OVERLAP",
    "AVATAR_GROUP_HOVER_SHIFT",
    "AVATAR_GROUP_GRID_GAP",
    "AVATAR_GROUP_GRID_COLS",
    "VALID_AVATAR_SIZES",
    "VALID_AVATAR_COLORS",
    "VALID_AVATAR_RADII",
]
