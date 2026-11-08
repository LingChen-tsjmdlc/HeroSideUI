"""Link 预设：字号 14/16/18，block hover 色块 /20，opacity 值来源 default-layout.ts。"""

# 字号 (px) —— 与 SIZE_MAP 对齐
LINK_SIZES = {
    "sm": {
        "font_size": 14,  # text-small
        "icon_size": 14,
        "block_pad_x": 8,  # px-2
        "block_pad_y": 4,  # py-1
    },
    "md": {
        "font_size": 16,  # text-medium
        "icon_size": 16,
        "block_pad_x": 8,
        "block_pad_y": 4,
    },
    "lg": {
        "font_size": 18,  # text-large
        "icon_size": 18,
        "block_pad_x": 8,
        "block_pad_y": 4,
    },
}

VALID_LINK_SIZES = tuple(LINK_SIZES.keys())

# color 维度 —— foreground 走主题正文色, 其余走 HeroUI 语义色
VALID_LINK_COLORS = (
    "foreground",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)

# underline 维度
VALID_LINK_UNDERLINES = ("none", "hover", "always", "active", "focus")

# 透明度 token (default-layout.ts 同源)
LINK_OPACITY = {
    "hover_light": 0.8,  # opacity-hover light
    "hover_dark": 0.9,  # opacity-hover dark
    "disabled": 0.5,  # opacity-disabled (含 active)
}

# isBlock 模式参数
LINK_BLOCK = {
    "radius": 12,  # rounded-xl = 12px
    "bg_alpha_foreground": 0.10,  # foreground/10
    "bg_alpha_color": 0.20,  # color/20 (其余 5 色)
    "anim_duration": 200,  # transition-background ~200ms
}

# opacity 过渡时长 (transition-opacity ~150ms)
LINK_OPACITY_DURATION = 150

__all__ = [
    "LINK_BLOCK",
    "LINK_OPACITY",
    "LINK_OPACITY_DURATION",
    "LINK_SIZES",
    "VALID_LINK_COLORS",
    "VALID_LINK_SIZES",
    "VALID_LINK_UNDERLINES",
]
