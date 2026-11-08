"""Avatar 尺寸：sm 32/md 40/lg 56；bordered ring 2+2；组重叠 8px hover 让位 12px。"""

# text_size 用项目 Text 的 token（xs/sm/md），不是 px
AVATAR_SIZES = {
    "sm": {
        "box": 32,
        "text_size": "xs",  # 12px ≈ text-tiny
        "icon_ratio": 0.8,
    },
    "md": {
        "box": 40,
        "text_size": "xs",  # 12px ≈ text-tiny
        "icon_ratio": 0.8,
    },
    "lg": {
        "box": 56,
        "text_size": "sm",  # 14px ≈ text-small
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
    "AVATAR_GROUP_GRID_COLS",
    "AVATAR_GROUP_GRID_GAP",
    "AVATAR_GROUP_HOVER_SHIFT",
    "AVATAR_GROUP_OVERLAP",
    "AVATAR_RING_OFFSET",
    "AVATAR_RING_WIDTH",
    "AVATAR_SIZES",
    "VALID_AVATAR_COLORS",
    "VALID_AVATAR_RADII",
    "VALID_AVATAR_SIZES",
]
