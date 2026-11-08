"""Skeleton 样式 token：三色标渐变（transparent→via→transparent），对齐 skeleton.ts。"""

from __future__ import annotations

from ...themes import HEROUI_COLORS


def build_skeleton_styles(theme: str) -> dict:
    """按主题返回骨架屏各层颜色 token。

    Args:
        theme: 主题名，dark 时改用极淡的白色高光。

    Returns:
        含 base_bg、shimmer_via、top_border 的字典；shimmer_via 为唯一高光中间色。
    """
    d = HEROUI_COLORS["default"]
    is_dark = theme == "dark"

    # skeleton.ts: bg-content3 light / bg-content2 dark
    base_bg = d[100] if not is_dark else d[800]

    if is_dark:
        # 暗底: via-default-700/10 — 极其微妙的高光
        shimmer_via = (255, 255, 255, 0.08)
        top_border = (255, 255, 255, 0.06)
    else:
        # 亮底: via-content4 — content4 ≈ zinc-300/#d4d4d8
        shimmer_via = (0, 0, 0, 0.06)
        top_border = (0, 0, 0, 0.06)

    return {
        "base_bg": base_bg,
        "shimmer_via": shimmer_via,
        "top_border": top_border,
    }
