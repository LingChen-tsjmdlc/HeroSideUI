"""Image 组件视觉 token 辅助。

radius 像素使用 Image 专属映射（比全局 RADIUS 整体大一号），
避免影响 Card/Button 等其它组件。
"""

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
    """把 radius 字符串解析成像素，full 用最短边一半。"""
    if radius == "full":
        return min(w, h) / 2.0
    return _IMAGE_RADIUS_PX.get(radius, _IMAGE_RADIUS_PX["lg"])


def resolve_shadow(shadow: str) -> dict:
    """返回阴影规格 dict（offset_y/blur/opacity）。"""
    return IMAGE_SHADOWS.get(shadow, IMAGE_SHADOWS["none"])


__all__ = ["resolve_radius_px", "resolve_shadow"]
