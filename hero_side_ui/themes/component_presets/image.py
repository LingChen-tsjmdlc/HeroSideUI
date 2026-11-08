"""IMAGE_SHADOWS：四档 QGraphicsDropShadowEffect 参数（offset/blur/opacity）。"""

# HeroUI v2 Image 阴影预设
IMAGE_SHADOWS = {
    "none": {"offset_y": 0, "blur": 0, "opacity": 0.0},
    "sm": {"offset_y": 2, "blur": 12, "opacity": 0.10},
    "md": {"offset_y": 8, "blur": 30, "opacity": 0.14},
    "lg": {"offset_y": 12, "blur": 40, "opacity": 0.20},
}

__all__ = ["IMAGE_SHADOWS"]
