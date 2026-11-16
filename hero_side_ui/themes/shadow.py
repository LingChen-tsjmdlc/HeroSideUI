"""阴影层数据与官方 HeroUI 默认值（亮暗各 sm/md/lg 三档，每档多层）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    """单层阴影。

    Args:
        y: 向下偏移（px）。
        blur: CSS 模糊半径（px）。
        color: 十六进制颜色。
        opacity: 不透明度 0~1。
        inset: True 表示画在边框内侧的 1px 描边。
    """

    y: float
    blur: float
    color: str
    opacity: float
    inset: bool = False


SHADOW_COLOR = "#020304"  # 外阴影/遮罩色：近黑，须比暗色窗口底更暗
INSET_COLOR = "#FEFEFF"  # 暗色内描边色：近白

DEFAULT_SHADOW: dict = {
    "light": {
        "sm": (
            Layer(0, 5, SHADOW_COLOR, 0.02),
            Layer(2, 10, SHADOW_COLOR, 0.06),
            Layer(0, 1, SHADOW_COLOR, 0.30),
        ),
        "md": (
            Layer(0, 15, SHADOW_COLOR, 0.03),
            Layer(2, 30, SHADOW_COLOR, 0.08),
            Layer(0, 1, SHADOW_COLOR, 0.30),
        ),
        "lg": (
            Layer(0, 30, SHADOW_COLOR, 0.04),
            Layer(30, 60, SHADOW_COLOR, 0.12),
            Layer(0, 1, SHADOW_COLOR, 0.30),
        ),
    },
    "dark": {
        "sm": (
            Layer(0, 5, SHADOW_COLOR, 0.05),
            Layer(2, 10, SHADOW_COLOR, 0.20),
            Layer(0, 1, INSET_COLOR, 0.15, True),
        ),
        "md": (
            Layer(0, 15, SHADOW_COLOR, 0.06),
            Layer(2, 30, SHADOW_COLOR, 0.22),
            Layer(0, 1, INSET_COLOR, 0.15, True),
        ),
        "lg": (
            Layer(0, 30, SHADOW_COLOR, 0.07),
            Layer(30, 60, SHADOW_COLOR, 0.26),
            Layer(0, 1, INSET_COLOR, 0.15, True),
        ),
    },
}

SHADOW_TIERS = ("sm", "md", "lg")

__all__ = ["DEFAULT_SHADOW", "SHADOW_COLOR", "SHADOW_TIERS", "Layer"]
