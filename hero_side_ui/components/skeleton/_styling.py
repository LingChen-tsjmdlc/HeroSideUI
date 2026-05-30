"""Skeleton 样式 token — 严格对齐 HeroUI skeleton.ts。

HeroUI 官方实现:
- bg-content3(亮) / bg-content2(暗)
- shimmer: before:bg-gradient-to-r from-transparent via-content4 to-transparent
- 暗色: dark:before:via-default-700/10
- 动画: translateX(-100%) → translateX(200%), 2s ease infinite
- top border: before:border-content4/30

关键: 官方只有 3 个渐变色标 (transparent → via → transparent)，
via 色就是唯一的高光，不需要 peak/edge 分层。
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS


def build_skeleton_styles(theme: str) -> dict:
    """返回 Skeleton 各层颜色 token。

    shimmer_via 是条带唯一的中间色 (RGBA 元组)，
    对应官方的 from-transparent via-X to-transparent。
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
