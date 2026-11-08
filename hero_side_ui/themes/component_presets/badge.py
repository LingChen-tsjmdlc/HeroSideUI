"""Badge 尺寸：圆点 12/14/16、单字 16/20/24、多字符高 16/20/20；锚点偏移 5%/10%。"""

BADGE_SIZES = {
    "sm": {
        "dot": 12,
        "one_char": 16,
        "multi_height": 16,
        "padding_x": 4,
        "text_size": 10,
    },
    "md": {
        "dot": 14,
        "one_char": 20,
        "multi_height": 20,
        "padding_x": 4,
        "text_size": 14,
    },
    "lg": {
        "dot": 16,
        "one_char": 24,
        "multi_height": 20,
        "padding_x": 4,
        "text_size": 16,
    },
}

# shape 只影响锚点偏移比例（官方两种 shape 均为 rounded-full）
BADGE_PLACEMENT_OFFSETS = {"rectangle": 0.05, "circle": 0.10}

# 兼容长名称
BADGE_SIZES["small"] = BADGE_SIZES["sm"]
BADGE_SIZES["medium"] = BADGE_SIZES["md"]
BADGE_SIZES["large"] = BADGE_SIZES["lg"]

VALID_BADGE_SIZES = ("sm", "md", "lg")
VALID_BADGE_VARIANTS = ("solid", "flat", "faded", "shadow")
VALID_BADGE_SHAPES = ("circle", "rectangle")
VALID_BADGE_PLACEMENTS = ("top-right", "top-left", "bottom-right", "bottom-left")

__all__ = [
    "BADGE_PLACEMENT_OFFSETS",
    "BADGE_SIZES",
    "VALID_BADGE_PLACEMENTS",
    "VALID_BADGE_SHAPES",
    "VALID_BADGE_SIZES",
    "VALID_BADGE_VARIANTS",
]
