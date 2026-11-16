"""Button 组件尺寸配置。"""

# Button 支持的变体（HeroUI v2 Button 无 shadow，改用 ghost）
VALID_BUTTON_VARIANTS = ("solid", "bordered", "flat", "light", "faded", "ghost")

BUTTON_SIZES = {
    "sm": {
        "padding_y": 6,
        "padding_x": 12,
        "font_size": "13px",
        "font_weight": "500",
        "default_radius": "sm",
        "height": "18px",
        "min_width": 64,  # 官方 min-w-16：含左右留白与边框的总宽（border-box）
    },
    "md": {
        "padding_y": 10,
        "padding_x": 16,
        "font_size": "16px",
        "font_weight": "500",
        "default_radius": "md",
        "height": "26px",
        "min_width": 80,  # 官方 min-w-20
    },
    "lg": {
        "padding_y": 14,
        "padding_x": 24,  # 官方 px-6
        "font_size": "19px",
        "font_weight": "600",
        "default_radius": "lg",
        "height": "33px",
        "min_width": 96,  # 官方 min-w-24
    },
}

# 兼容长名称
BUTTON_SIZES["small"] = BUTTON_SIZES["sm"]
BUTTON_SIZES["medium"] = BUTTON_SIZES["md"]
BUTTON_SIZES["large"] = BUTTON_SIZES["lg"]

__all__ = ["BUTTON_SIZES"]
