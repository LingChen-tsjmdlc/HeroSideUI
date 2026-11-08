"""Chip 尺寸：高 24/28/32，单字锁方 20/24/28，dot 8px。"""

# text_size 用项目 Text 的 token（xs/sm/md），不是 px
CHIP_SIZES = {
    "sm": {
        "height": 24,
        "padding_x": 8,
        "text_size": "xs",
        "avatar_size": 16,
        "close_icon_size": 16,
        "one_char_size": 20,
        "gap": 4,
        "default_radius": "full",
    },
    "md": {
        "height": 28,
        "padding_x": 10,
        "text_size": "sm",
        "avatar_size": 20,
        "close_icon_size": 18,
        "one_char_size": 24,
        "gap": 4,
        "default_radius": "full",
    },
    "lg": {
        "height": 32,
        "padding_x": 12,
        "text_size": "md",
        "avatar_size": 24,
        "close_icon_size": 20,
        "one_char_size": 28,
        "gap": 6,
        "default_radius": "full",
    },
}

# 统一小圆点直径（HeroUI dot: w-2 h-2）
CHIP_DOT_SIZE = 8

# 兼容长名称
CHIP_SIZES["small"] = CHIP_SIZES["sm"]
CHIP_SIZES["medium"] = CHIP_SIZES["md"]
CHIP_SIZES["large"] = CHIP_SIZES["lg"]

VALID_CHIP_SIZES = ("sm", "md", "lg")
VALID_CHIP_VARIANTS = ("solid", "bordered", "light", "flat", "faded", "shadow", "dot")
VALID_CHIP_RADII = ("none", "sm", "md", "lg", "full")

__all__ = [
    "CHIP_DOT_SIZE",
    "CHIP_SIZES",
    "VALID_CHIP_RADII",
    "VALID_CHIP_SIZES",
    "VALID_CHIP_VARIANTS",
]
