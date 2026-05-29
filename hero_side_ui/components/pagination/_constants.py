"""Pagination 组件常量与枚举。"""

from enum import Enum

from ...themes import HEROUI_COLORS, RADIUS

# variant: 与 HeroUI v2 pagination.ts 对齐
VALID_VARIANTS = ("flat", "bordered", "light", "faded")

# color: HeroUI 全语义色（不含 neutral，参考 colors.py 注释）
VALID_COLORS = tuple(k for k in HEROUI_COLORS.keys() if k != "neutral")

VALID_SIZES = ("sm", "md", "lg")

# radius: 与 HeroUI 一致, full 不在 RADIUS 表内（动态算高度的一半）
VALID_RADII = tuple(k for k in RADIUS.keys() if k in ("none", "sm", "md", "lg")) + (
    "full",
)

VALID_THEMES = ("light", "dark")


class PaginationItemType(Enum):
    """对齐 HeroUI v2 use-pagination-base.ts 的 PaginationItemType。"""

    PAGE = "page"
    DOTS = "dots"
    PREV = "prev"
    NEXT = "next"


__all__ = [
    "VALID_VARIANTS",
    "VALID_COLORS",
    "VALID_SIZES",
    "VALID_RADII",
    "VALID_THEMES",
    "PaginationItemType",
]
