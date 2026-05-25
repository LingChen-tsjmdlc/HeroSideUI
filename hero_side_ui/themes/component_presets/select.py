"""Select 组件主题预设 (SELECT_SIZES)。

Select 大部分尺寸交给子组件（Input 触发钮 / Listbox / Popover），这里
只补 Select 自身特有的：

  - selector_icon_size       右侧 chevron-down 图标尺寸
  - clear_icon_size          右侧 x-mark 图标尺寸
  - end_btn_size             clear / selector 按钮自身的命中尺寸（正方形）
  - end_gap                  两个按钮之间的水平间距
  - rotate_duration          selector icon 旋转动画时长 (ms)
  - popover_max_height       popover 内 listbox 最大高度 (px)
  - chip_max                 multiple 模式下，trigger 内最多展示几个 chip 文本，
                             超出后用 "+N" 折叠
"""

SELECT_SIZES = {
    "sm": {
        "selector_icon_size": 14,
        "clear_icon_size": 12,
        "end_btn_size": 18,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 220,
        "chip_max": 2,
    },
    "md": {
        "selector_icon_size": 16,
        "clear_icon_size": 14,
        "end_btn_size": 20,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 260,
        "chip_max": 3,
    },
    "lg": {
        "selector_icon_size": 18,
        "clear_icon_size": 16,
        "end_btn_size": 22,
        "end_gap": 4,
        "rotate_duration": 150,
        "popover_max_height": 300,
        "chip_max": 3,
    },
}

SELECT_SIZES["small"] = SELECT_SIZES["sm"]
SELECT_SIZES["medium"] = SELECT_SIZES["md"]
SELECT_SIZES["large"] = SELECT_SIZES["lg"]

__all__ = ["SELECT_SIZES"]
