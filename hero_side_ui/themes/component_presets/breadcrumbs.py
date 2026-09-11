"""Breadcrumbs 组件尺寸配置。

对照 HeroUI breadcrumbs.ts：
- item 字号：sm text-tiny(12) / md text-small(14) / lg text-medium(16)
- solid/bordered 列表内边距：sm px-2 py-1 / md px-2.5 py-1.5 / lg px-3 py-2
- separator：px-1(4)
"""

BREADCRUMBS_SIZES = {
    "sm": {"font": 12, "padding_x": 8, "padding_y": 4},
    "md": {"font": 14, "padding_x": 10, "padding_y": 6},
    "lg": {"font": 16, "padding_x": 12, "padding_y": 8},
}

# 官方折叠默认值
BREADCRUMBS_MAX_ITEMS = 8
BREADCRUMBS_ITEMS_BEFORE_COLLAPSE = 1
BREADCRUMBS_ITEMS_AFTER_COLLAPSE = 2

# 非 current 项透明度（官方 hover:opacity-hover / active:opacity-disabled）
BREADCRUMBS_HOVER_OPACITY = 0.8
BREADCRUMBS_ACTIVE_OPACITY = 0.5

VALID_BREADCRUMBS_SIZES = ("sm", "md", "lg")
VALID_BREADCRUMBS_VARIANTS = ("solid", "bordered", "light")
VALID_BREADCRUMBS_RADII = ("none", "sm", "md", "lg", "full")
VALID_BREADCRUMBS_COLORS = ("foreground", "primary", "secondary", "success", "warning", "danger")
VALID_BREADCRUMBS_UNDERLINES = ("none", "active", "hover", "focus", "always")

__all__ = [
    "BREADCRUMBS_SIZES",
    "BREADCRUMBS_MAX_ITEMS",
    "BREADCRUMBS_ITEMS_BEFORE_COLLAPSE",
    "BREADCRUMBS_ITEMS_AFTER_COLLAPSE",
    "BREADCRUMBS_HOVER_OPACITY",
    "BREADCRUMBS_ACTIVE_OPACITY",
    "VALID_BREADCRUMBS_SIZES",
    "VALID_BREADCRUMBS_VARIANTS",
    "VALID_BREADCRUMBS_RADII",
    "VALID_BREADCRUMBS_COLORS",
    "VALID_BREADCRUMBS_UNDERLINES",
]
