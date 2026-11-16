"""Image 模糊副本边距纯计算：向下溢出，四向不对称留白（阴影不占位）。"""

from __future__ import annotations


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


def content_margins(is_blurred: bool, remove_wrapper: bool) -> tuple[int, int, int, int]:
    """取图像可视区四向 margin。

    Args:
        is_blurred: 是否启用模糊副本。
        remove_wrapper: 是否移除 wrapper。

    Returns:
        (top, right, bottom, left)；只为模糊副本溢出留白，阴影由公共阴影层画、不占位；
        remove_wrapper 时全 0。
    """
    if remove_wrapper or not is_blurred:
        return (0, 0, 0, 0)
    return (12, 18, 22, 18)


__all__ = [
    "blur_margin",
    "content_margins",
]
