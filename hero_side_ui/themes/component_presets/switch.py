"""Switch (Toggle) 组件尺寸配置。

对齐 HeroUI v2 Switch 规范 (tailwind class → px):
    sm: wrapper w-10 h-6  = 40×24, thumb w-4 = 16, pressed w-5  = 20, ms-4 = 16
    md: wrapper w-12 h-7  = 48×28, thumb w-5 = 20, pressed w-6  = 24, ms-5 = 20  (默认)
    lg: wrapper w-14 h-8  = 56×32, thumb w-6 = 24, pressed w-7  = 28, ms-6 = 24

其他约定:
    wrapper 内 padding px-1 = 4px (左右 4px)；wrapper 圆角为胶囊 (height/2)
    startContent 左边距 start-1.5 = 6px，endContent 右边距 end-1.5 = 6px
    label gap (ms-2) = 8px
    thumb icon 字号：sm=12, md=14, lg=16 （与 startContent/endContent 同级）

source:
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/toggle.ts
"""

SWITCH_SIZES = {
    "sm": {
        "wrapper_w": 40,
        "wrapper_h": 24,
        "thumb": 16,            # 未按压 thumb 直径
        "thumb_pressed": 20,    # 按压时 thumb 的宽度 (高度不变 → 变椭圆)
        "pad": 4,               # wrapper 内左右 padding (px-1)
        "selected_shift": 16,   # 选中时 thumb 左边距 (相对 wrapper 内 pad 起点) -- ms-4
        "pressed_shift": 12,    # 按压且选中时 thumb 左边距 -- ml-3
        "content_pad": 6,       # startContent/endContent 距左/右边距 (start/end-1.5)
        "label_font_size": 13,  # text-small
        "icon_font_size": 12,   # text-tiny
        "label_gap": 8,         # label 与 wrapper 的间距 (ms-2)
    },
    "md": {
        "wrapper_w": 48,
        "wrapper_h": 28,
        "thumb": 20,
        "thumb_pressed": 24,
        "pad": 4,
        "selected_shift": 20,   # ms-5
        "pressed_shift": 16,    # ml-4
        "content_pad": 6,
        "label_font_size": 14,
        "icon_font_size": 14,
        "label_gap": 8,
    },
    "lg": {
        "wrapper_w": 56,
        "wrapper_h": 32,
        "thumb": 24,
        "thumb_pressed": 28,
        "pad": 4,
        "selected_shift": 24,   # ms-6
        "pressed_shift": 20,    # ml-5
        "content_pad": 6,
        "label_font_size": 16,
        "icon_font_size": 16,
        "label_gap": 8,
    },
}

# 别名，便于使用 small/medium/large
SWITCH_SIZES["small"] = SWITCH_SIZES["sm"]
SWITCH_SIZES["medium"] = SWITCH_SIZES["md"]
SWITCH_SIZES["large"] = SWITCH_SIZES["lg"]

__all__ = ["SWITCH_SIZES"]
