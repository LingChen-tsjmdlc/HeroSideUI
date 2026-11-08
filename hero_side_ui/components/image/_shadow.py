"""Image 阴影/模糊边距纯计算：主朝下扩散，四向不对称留白。"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from ._styling import resolve_shadow


def make_shadow_effect(
    parent: QWidget, shadow: str, remove_wrapper: bool
) -> QGraphicsDropShadowEffect | None:
    """构造投影效果。

    Args:
        parent: 效果的 QObject 父对象。
        shadow: 阴影档位名。
        remove_wrapper: 是否移除 wrapper（此时不需要阴影）。

    Returns:
        已设 offset / blur / 颜色的 QGraphicsDropShadowEffect；
        无阴影或 remove_wrapper 时返回 None。
    """
    cfg = resolve_shadow(shadow)
    if cfg["opacity"] <= 0 or remove_wrapper:
        return None
    eff = QGraphicsDropShadowEffect(parent)
    eff.setOffset(0, cfg["offset_y"])
    eff.setBlurRadius(cfg["blur"])
    eff.setColor(QColor(0, 0, 0, int(cfg["opacity"] * 255)))
    return eff


def shadow_margin(shadow: str, remove_wrapper: bool) -> int:
    """阴影向外扩散需要的预算像素（与 Card 同算式）。

    Args:
        shadow: 阴影档位名。
        remove_wrapper: 是否移除 wrapper。

    Returns:
        blur 半径一半 + |offset_y| + 2；无阴影或 remove_wrapper 时为 0。
    """
    if remove_wrapper:
        return 0
    cfg = resolve_shadow(shadow)
    if cfg["opacity"] <= 0:
        return 0
    return int(cfg["blur"]) // 2 + abs(int(cfg["offset_y"])) + 2


def blur_margin(is_blurred: bool, remove_wrapper: bool) -> int:
    """isBlurred 副本向外溢出需要的预算像素。

    Args:
        is_blurred: 是否启用模糊副本。
        remove_wrapper: 是否移除 wrapper。

    Returns:
        固定 18px（副本 scale 1.18 + blur 半径 16×0.5）；不需要时为 0。
    """
    if remove_wrapper or not is_blurred:
        return 0
    # 副本 scale 1.18 + blur 半径 16 × 0.5
    return 18


def content_margins(
    shadow: str, is_blurred: bool, remove_wrapper: bool
) -> tuple[int, int, int, int]:
    """取图像可视区四向 margin。

    Args:
        shadow: 阴影档位名。
        is_blurred: 是否启用模糊副本。
        remove_wrapper: 是否移除 wrapper。

    Returns:
        (top, right, bottom, left)；阴影向下扩散，与 isBlurred
        需求逐向取最大值；remove_wrapper 时全 0。
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
    "blur_margin",
    "content_margins",
    "make_shadow_effect",
    "shadow_margin",
]
