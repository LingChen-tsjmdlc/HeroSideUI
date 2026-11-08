"""DATE_INPUT token：段 px-0.5 + 负 margin 收紧、border 2px；尺寸主体沿用 INPUT_SIZES。"""

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

DATE_INPUT_SIZES = {key: {**INPUT_SIZES[key], **_SEGMENT_TOKENS[key]} for key in ("sm", "md", "lg")}

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
