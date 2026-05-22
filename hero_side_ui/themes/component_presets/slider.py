"""Slider 组件尺寸配置。

对齐 HeroUI v2 Slider 规范 (tailwind class → px):
    sm:  thumb 20×20 (w-5 h-5) | inner-dot 16×16 (after:w-4 h-4) | track h-1=4 | text-small=13
    md:  thumb 24×24 (w-6 h-6) | inner-dot 20×20 (after:w-5 h-5) | track h-3=12 | text-small=13   ← 默认
    lg:  thumb 28×28 (w-7 h-7) | inner-dot 20×20 (after:w-5 h-5) | track h-7=28 | text-medium=15

约定：
    - thumb 是外圈/光晕（color 注入），inner-dot (after) 是中心白点（bg-background）
    - track 圆角 rounded-full；filler 颜色 = color；底色 = default-300/50
    - hasMarks 时 base 多 mb-5；mark 文本 lg 时 mt-2，否则 mt-1
    - thumb 拖拽时 inner-dot 缩放 scale-80 (除非 disableThumbScale=True)
    - showOutline=True 时 thumb 多一圈 ring-2 (background)
    - 垂直方向 (isVertical) 与水平方向交换 w/h，本 preset 仅给出标量数值，
      朝向相关 layout 在组件内部翻转

source:
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/slider.ts
"""

SLIDER_SIZES = {
    "sm": {
        "thumb": 20,  # w-5 h-5
        "inner_dot": 16,  # after:w-4 h-4
        "track_thickness": 4,  # h-1 (水平) / w-1 (垂直)
        "label_font_size": 13,  # text-small
        "value_font_size": 13,
        "mark_font_size": 12,
        "mark_offset": 4,  # mt-1 默认
    },
    "md": {
        "thumb": 24,  # w-6 h-6
        "inner_dot": 20,  # after:w-5 h-5
        "track_thickness": 12,  # h-3 / w-3
        "label_font_size": 13,
        "value_font_size": 13,
        "mark_font_size": 13,
        "mark_offset": 4,
    },
    "lg": {
        "thumb": 28,  # w-7 h-7
        "inner_dot": 20,  # after:w-5 h-5
        "track_thickness": 28,  # h-7 / w-7
        "label_font_size": 15,
        "value_font_size": 15,
        "mark_font_size": 14,
        "mark_offset": 8,  # mt-2
    },
}

# 别名：small/medium/large
SLIDER_SIZES["small"] = SLIDER_SIZES["sm"]
SLIDER_SIZES["medium"] = SLIDER_SIZES["md"]
SLIDER_SIZES["large"] = SLIDER_SIZES["lg"]

__all__ = ["SLIDER_SIZES"]
