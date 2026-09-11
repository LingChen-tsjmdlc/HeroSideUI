"""Badge 组件尺寸配置。

对照 HeroUI badge.ts 的 size / compound variants：
- isDot 固定圆点：sm w-3(12) / md w-3.5(14) / lg w-4(16)
- isOneChar 正方形：sm w-4(16) / md w-5(20) / lg w-6(24)
- 多字符：px-1(4)，高 sm 16 / md 20 / lg 20（md/lg 官方同为 text-small）
- 角标锚点偏移（相对被包裹内容边缘，中心悬在边缘上）：
  rectangle 5% / circle 10%（placement × shape compound variants）
- 文字字号：sm 10 / md 14 / lg 16
"""

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
    "BADGE_SIZES",
    "BADGE_PLACEMENT_OFFSETS",
    "VALID_BADGE_SIZES",
    "VALID_BADGE_VARIANTS",
    "VALID_BADGE_SHAPES",
    "VALID_BADGE_PLACEMENTS",
]
