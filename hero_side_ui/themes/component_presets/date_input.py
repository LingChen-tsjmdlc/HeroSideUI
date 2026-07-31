"""DateInput 组件尺寸配置。

对齐 HeroUI v2 的 date-input.ts：
  - 高度 sm=32 / md=40 / lg=48；inside label 时 sm=48 / md=56 / lg=64
  - 段自身 px-0.5 + rounded-md，段间靠负 margin 收紧（-ml-1）
  - faded / bordered 的 border-width = 2px (border-medium)

尺寸主体沿用 INPUT_SIZES（DateInput 与 Input 共享外框视觉），此处只
补出段特有的 token，避免两处各写一份高度/字号导致视觉漂移。
"""

from .input import INPUT_SIZES

# 段特有 token
#   segment_padding_x  段内左右内边距（对应 HeroUI px-0.5）
#   segment_radius     段焦点底色的圆角（HeroUI rounded-md）
#
# HeroUI 用 `-ml-1` 负 margin 抵消段自身 px-0.5 来收紧段间距。Qt 里两条路都不通：
# QBoxLayout 的负 spacing 不让 widget 重叠，QSS 负 margin 又会污染 sizeHint。
# 因此直接把 padding 取到"视觉等效"的小值，让每个 widget 都保持自然宽度。
_SEGMENT_TOKENS = {
    "sm": {"segment_padding_x": 1, "segment_radius": 4},
    "md": {"segment_padding_x": 1, "segment_radius": 6},
    "lg": {"segment_padding_x": 2, "segment_radius": 8},
}

DATE_INPUT_SIZES = {
    key: {**INPUT_SIZES[key], **_SEGMENT_TOKENS[key]} for key in ("sm", "md", "lg")
}

DATE_INPUT_SIZES["small"] = DATE_INPUT_SIZES["sm"]
DATE_INPUT_SIZES["medium"] = DATE_INPUT_SIZES["md"]
DATE_INPUT_SIZES["large"] = DATE_INPUT_SIZES["lg"]

VALID_DATE_INPUT_SIZES = ("sm", "md", "lg")
VALID_DATE_INPUT_VARIANTS = ("flat", "faded", "bordered", "underlined")
VALID_DATE_INPUT_LABEL_PLACEMENTS = (
    "inside",
    "outside",
    "outside-left",
    "outside-top",
)

__all__ = [
    "DATE_INPUT_SIZES",
    "VALID_DATE_INPUT_LABEL_PLACEMENTS",
    "VALID_DATE_INPUT_SIZES",
    "VALID_DATE_INPUT_VARIANTS",
]
