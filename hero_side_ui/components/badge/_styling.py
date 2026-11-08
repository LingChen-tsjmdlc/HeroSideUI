"""Badge 配色 token：复用 Chip 同源映射；border 由 show_outline 决定不在此产出。"""

from __future__ import annotations

from ..chip._styling import build_chip_styles


def build_badge_styles(variant: str, color: str, theme: str) -> dict:
    """返回角标配色 token（复用 Chip 同源映射）。

    Args:
        variant: 变体名；非法值回退 solid。
        color: 语义色名，透传给 chip 的取色器。
        theme: 主题名，dark 走深色取值。

    Returns:
        含 bg / fg / shadow_color / has_shadow 的 dict；
        border 不在此产出，由 Badge 按 show_outline 决定。
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
