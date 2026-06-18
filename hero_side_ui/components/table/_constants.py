"""Table 组件常量与枚举。对齐 HeroUI v2 table.ts variants。"""

from ...themes import HEROUI_COLORS, RADIUS

# color: HeroUI 全语义色（不含 neutral）。对应 table.ts color variants 的 6 档。
VALID_COLORS = tuple(k for k in HEROUI_COLORS.keys() if k != "neutral")

VALID_SIZES = ("sm", "md", "lg")

# radius: 影响表头 / 选中·hover 行条的圆角。full 时行条/表头变全圆（药丸），
# 但 wrapper Card 不跟随 full（见 table.py，full → Card 用 lg）。
VALID_RADII = tuple(k for k in RADIUS.keys() if k in ("none", "sm", "md", "lg")) + (
    "full",
)

# shadow: 对齐 table.ts shadow variant
VALID_SHADOWS = ("none", "sm", "md", "lg")

# layout: table-auto / table-fixed
VALID_LAYOUTS = ("auto", "fixed")

# selectionMode: none / single / multiple
VALID_SELECTION_MODES = ("none", "single", "multiple")

# 单元格内容水平对齐
VALID_ALIGNS = ("start", "center", "end")

VALID_THEMES = ("light", "dark")

__all__ = [
    "VALID_COLORS",
    "VALID_SIZES",
    "VALID_RADII",
    "VALID_SHADOWS",
    "VALID_LAYOUTS",
    "VALID_SELECTION_MODES",
    "VALID_ALIGNS",
    "VALID_THEMES",
]
