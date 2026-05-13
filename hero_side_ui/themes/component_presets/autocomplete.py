"""Autocomplete 组件主题预设 (AUTOCOMPLETE_SIZES)。

Autocomplete 本身大部分尺寸交给子组件（Input / Listbox / Popover），这里
只补 Autocomplete 自身特有的：

  - selector_icon_size       右侧 chevron-down 图标尺寸
  - clear_icon_size          右侧 x-mark 图标尺寸（默认比 selector 略小,
                             因为 x-mark 的 path 在 viewBox 内偏满 + round cap
                             会"长出"边缘,小尺寸渲染时给点 padding 避免截断）
  - end_btn_size             clear / selector 按钮自身的点击命中尺寸（正方形）
  - end_gap                  两个按钮之间的水平间距
  - rotate_duration          selector icon 旋转动画时长 (ms)
  - popover_max_height       popover 内 listbox 最大高度 (px) —— 超过会出滚动条
                             由 ScrollShadow 加渐变阴影
"""

AUTOCOMPLETE_SIZES = {
    "sm": {
        "selector_icon_size": 14,
        "clear_icon_size": 12,
        "end_btn_size": 18,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 220,
    },
    "md": {
        "selector_icon_size": 16,
        "clear_icon_size": 14,
        "end_btn_size": 20,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 260,
    },
    "lg": {
        "selector_icon_size": 18,
        "clear_icon_size": 16,
        "end_btn_size": 22,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 300,
    },
}

AUTOCOMPLETE_SIZES["small"] = AUTOCOMPLETE_SIZES["sm"]
AUTOCOMPLETE_SIZES["medium"] = AUTOCOMPLETE_SIZES["md"]
AUTOCOMPLETE_SIZES["large"] = AUTOCOMPLETE_SIZES["lg"]

__all__ = ["AUTOCOMPLETE_SIZES"]
