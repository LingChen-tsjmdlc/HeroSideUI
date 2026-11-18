"""Button 组件尺寸配置。"""

# Button 支持的变体（HeroUI v2 Button 无 shadow，改用 ghost）
VALID_BUTTON_VARIANTS = ("solid", "bordered", "flat", "light", "faded", "ghost")

# 桌面端四档（官方 HeroUI 只有 sm / md / lg 三档，这里是有意偏离）。
# 文字按钮总高 = 内容高 height + 2 * padding_y：24 / 32 / 40 / 48（bordered / ghost / faded 再加边框 2px）；
# 图标按钮边长 = 同一个值。字号绑定全局字号档位 10 / 13 / 16 / 19。
BUTTON_SIZES = {
    "sm": {
        "padding_y": 4,
        "padding_x": 8,
        "font_size": "10px",
        "font_weight": "500",
        "default_radius": 4,  # 默认圆角像素（不传 radius 时用）；也可以传档位名
        "height": "16px",
        "min_width": 48,  # 含左右留白与边框的总宽（border-box）
    },
    "md": {
        "padding_y": 6,
        "padding_x": 12,
        "font_size": "13px",
        "font_weight": "500",
        "default_radius": 8,
        "height": "20px",
        "min_width": 64,
    },
    "lg": {
        "padding_y": 8,
        "padding_x": 16,
        "font_size": "16px",
        "font_weight": "500",
        "default_radius": 12,
        "height": "24px",
        "min_width": 80,
    },
    "xl": {
        "padding_y": 10,
        "padding_x": 24,
        "font_size": "19px",
        "font_weight": "600",
        "default_radius": 16,
        "height": "28px",
        "min_width": 96,
    },
}

# 兼容长名称（官方三档名）
BUTTON_SIZES["small"] = BUTTON_SIZES["sm"]
BUTTON_SIZES["medium"] = BUTTON_SIZES["md"]
BUTTON_SIZES["large"] = BUTTON_SIZES["lg"]

__all__ = ["BUTTON_SIZES"]
