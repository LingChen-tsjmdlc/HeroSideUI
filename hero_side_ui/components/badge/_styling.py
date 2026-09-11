"""Badge color tokens（4 variants × 6 colors × 2 themes）。

配色与 Chip 的 solid/flat/faded/shadow 完全同源（HeroUI colorVariants），
直接复用 chip._styling 的映射，避免两份映射漂移。
注意：Badge 的 faded 边框被官方 showOutline variant 恒覆盖
（showOutline=True → 2px 宿主背景描边；False → border-0），
因此本函数不产出 border，描边完全由 Badge 组件按 show_outline 决定。
"""

from __future__ import annotations

from ..chip._styling import build_chip_styles


def build_badge_styles(variant: str, color: str, theme: str) -> dict:
    """返回 Badge 角标配色 token。

    variant: solid/flat/faded/shadow；color: 6 语义色；theme: light/dark
    Keys: bg, fg, shadow_color, has_shadow
    """
    if variant not in ("solid", "flat", "faded", "shadow"):
        variant = "solid"
    tok = build_chip_styles(variant, color, theme)
    return {
        "bg": tok["bg"],
        "fg": tok["fg"],
        "shadow_color": tok["shadow_color"],
        "has_shadow": tok["has_shadow"],
    }
