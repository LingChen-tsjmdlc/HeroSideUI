"""HeroSideUI Image — 阴影/模糊边距计算与 QGraphicsDropShadowEffect 应用。

阴影主要朝下扩散（offset_y > 0），上方仅留少量富余；
isBlurred 副本 scale 1.18 + translate-y 6 也需要四向不对称留白。
将这些纯计算抽到独立模块，主类只关心调用结果。
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from ._styling import resolve_shadow


def make_shadow_effect(
    parent: QWidget, shadow: str, remove_wrapper: bool
) -> Optional[QGraphicsDropShadowEffect]:
    """构造 QGraphicsDropShadowEffect，无阴影/移除 wrapper 时返回 None。"""
    cfg = resolve_shadow(shadow)
    if cfg["opacity"] <= 0 or remove_wrapper:
        return None
    eff = QGraphicsDropShadowEffect(parent)
    eff.setOffset(0, cfg["offset_y"])
    eff.setBlurRadius(cfg["blur"])
    eff.setColor(QColor(0, 0, 0, int(cfg["opacity"] * 255)))
    return eff


def shadow_margin(shadow: str, remove_wrapper: bool) -> int:
    """阴影向外扩散需要的预算像素（与 Card 同算式）。"""
    if remove_wrapper:
        return 0
    cfg = resolve_shadow(shadow)
    if cfg["opacity"] <= 0:
        return 0
    return int(cfg["blur"]) // 2 + abs(int(cfg["offset_y"])) + 2


def blur_margin(is_blurred: bool, remove_wrapper: bool) -> int:
    """isBlurred 副本向外溢出需要的预算像素。"""
    if remove_wrapper or not is_blurred:
        return 0
    # 副本 scale 1.18 + blur 半径 16 × 0.5
    return 18


def content_margins(
    shadow: str, is_blurred: bool, remove_wrapper: bool
) -> Tuple[int, int, int, int]:
    """图像可视区距 wrapper 边缘的四向 margin (top, right, bottom, left)。

    阴影主要向下扩散，因此顶/底/侧三向独立计算后再与 isBlurred 取最大值。
    多 shadow 档位水平排列时顶边能自然对齐。
    """
    if remove_wrapper:
        return (0, 0, 0, 0)
    cfg = resolve_shadow(shadow)
    if cfg["opacity"] > 0:
        blur_half = int(cfg["blur"]) // 2
        off_y = int(cfg["offset_y"])
        sh_top = max(2, blur_half - max(0, off_y) + 2)
        sh_bottom = blur_half + max(0, off_y) + 2
        sh_side = blur_half + 2
    else:
        sh_top = sh_bottom = sh_side = 0
    if is_blurred:
        bl_top, bl_bottom, bl_side = 12, 22, 18
    else:
        bl_top = bl_bottom = bl_side = 0
    top = max(sh_top, bl_top)
    bottom = max(sh_bottom, bl_bottom)
    side = max(sh_side, bl_side)
    return (top, side, bottom, side)


__all__ = [
    "make_shadow_effect",
    "shadow_margin",
    "blur_margin",
    "content_margins",
]
