"""
TOOLTIP_SIZES 定义 Tooltip 的 3 档尺寸预设 (sm/md/lg)，对齐 HeroUI v2

每档包含:
  - font_size: 内容文字字号 (px)
  - padding: 内容区 padding (px)
"""

TOOLTIP_SIZES = {
    "sm": {"font_size": 12, "padding": 6},
    "md": {"font_size": 13, "padding": 8},
    "lg": {"font_size": 14, "padding": 10},
}

__all__ = ["TOOLTIP_SIZES"]
