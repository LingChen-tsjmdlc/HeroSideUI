"""Image 视觉 token：radius 用专属映射（比全局大一档），不扰其它组件。"""

from __future__ import annotations

from ...themes import IMAGE_SHADOWS

# Image 专属圆角档位——比全局 RADIUS 整体大一号
_IMAGE_RADIUS_PX = {
    "none": 0.0,
    "sm": 10.0,
    "md": 16.0,
    "lg": 24.0,
}
# 兼容长名称
_IMAGE_RADIUS_PX["no"] = _IMAGE_RADIUS_PX["none"]
_IMAGE_RADIUS_PX["small"] = _IMAGE_RADIUS_PX["sm"]
_IMAGE_RADIUS_PX["medium"] = _IMAGE_RADIUS_PX["md"]
_IMAGE_RADIUS_PX["large"] = _IMAGE_RADIUS_PX["lg"]


def resolve_radius_px(radius: str, w: int, h: int) -> float:
    """把 radius 字符串解析成像素。

    Args:
        radius: 圆角档位名（含 none/small/medium/large 长别名）。
        w: 图像可视区宽度。
        h: 图像可视区高度。

    Returns:
        full 用最短边一半；其余取 Image 专属映射（比全局 RADIUS 大一档），
        未知档位回退 lg。
    """
    if radius == "full":
        return min(w, h) / 2.0
    return _IMAGE_RADIUS_PX.get(radius, _IMAGE_RADIUS_PX["lg"])


def resolve_shadow(shadow: str) -> dict:
    """返回阴影规格。

    Args:
        shadow: 阴影档位名。

    Returns:
        含 offset_y / blur / opacity 的 dict；未知档位回退 none。
    """
    return IMAGE_SHADOWS.get(shadow, IMAGE_SHADOWS["none"])


__all__ = ["resolve_radius_px", "resolve_shadow"]
