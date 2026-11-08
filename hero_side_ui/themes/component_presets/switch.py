"""Switch 尺寸：wrapper 40×24/48×28/56×32，thumb 16/20/24，内容内边距与 label gap。"""

SWITCH_SIZES = {
    "sm": {
        "wrapper_w": 40,
        "wrapper_h": 24,
        "thumb": 16,  # 未按压 thumb 直径
        "thumb_pressed": 20,  # 按压时 thumb 的宽度 (高度不变 → 变椭圆)
        "pad": 4,  # wrapper 内左右 padding (px-1)
        "selected_shift": 16,  # 选中时 thumb 左边距 (相对 wrapper 内 pad 起点) -- ms-4
        "pressed_shift": 12,  # 按压且选中时 thumb 左边距 -- ml-3
        "content_pad": 6,  # startContent/endContent 距左/右边距 (start/end-1.5)
        "label_font_size": 13,  # text-small
        "icon_font_size": 12,  # text-tiny
        "label_gap": 8,  # label 与 wrapper 的间距 (ms-2)
    },
    "md": {
        "wrapper_w": 48,
        "wrapper_h": 28,
        "thumb": 20,
        "thumb_pressed": 24,
        "pad": 4,
        "selected_shift": 20,  # ms-5
        "pressed_shift": 16,  # ml-4
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
        "selected_shift": 24,  # ms-6
        "pressed_shift": 20,  # ml-5
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
