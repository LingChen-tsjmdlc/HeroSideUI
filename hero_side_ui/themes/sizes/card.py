"""Card 组件尺寸配置。

对齐 HeroUI v2 的 Card 规范:
  - header/body/footer 的 padding 均为 p-3 (12px) —— 写死在组件里，不再暴露 size prop
  - shadow: none/sm/md/lg
  - radius: none/sm/md/lg (默认 lg)
"""

# Card 阴影配置: 对齐 HeroUI shadow-small / shadow-medium / shadow-large
CARD_SHADOWS = {
    "none": {"offset_y": 0, "blur": 0, "spread": 0, "opacity": 0.0},
    "sm": {"offset_y": 1, "blur": 8, "spread": 0, "opacity": 0.06},
    "md": {"offset_y": 4, "blur": 14, "spread": 0, "opacity": 0.08},
    "lg": {"offset_y": 8, "blur": 30, "spread": 0, "opacity": 0.12},
}

__all__ = ["CARD_SHADOWS"]
