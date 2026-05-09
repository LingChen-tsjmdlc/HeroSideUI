"""Tabs 组件主题预设 (TABS_SIZES)。

对齐 HeroUI v2 tabs.ts 源码：
  - sm: tab h-7 (28px) / text-tiny (12px) / size 默认 radius=md(8px) (tabList rounded-medium, tab rounded-small)
  - md: tab h-8 (32px) / text-small (13px)
  - lg: tab h-9 (36px) / text-medium (15px)

数值定义（单位 px）:
  - tabList padding = 4 (p-1)
  - tab padding = 12 (px-3) / 4 (py-1)
  - tabList gap = 8 (gap-2)
  - panel padding 水平 = 4 (px-1) / 垂直 = 12 (py-3)
  - placement=start/end 时 panel 切换为 py-0 px-12 (px-3)
  - underlined cursor 高度 = 2px / 宽度 = 80%
  - bordered border-width = 2px (border-medium)

字段:
  tab_height        - 单个 tab 的固定高度
  tab_font_size     - tab 文字字号
  tab_padding_x     - tab 内边距水平
  tab_padding_y     - tab 内边距垂直
  list_padding      - tabList 容器 padding
  list_gap          - tab 间距
  panel_padding_v   - 面板默认垂直 padding (top/bottom)
  panel_padding_h   - 面板默认水平 padding (top/bottom)
  panel_padding_v_side - placement=start/end 下面板垂直 padding
  panel_padding_h_side - placement=start/end 下面板水平 padding
  underline_h       - underlined cursor 高度
  underline_ratio   - underlined cursor 宽度比例 (0~1)
  border_width      - bordered 变体的边框宽度
"""

TABS_SIZES = {
    "sm": {
        "tab_height": 28,
        "tab_font_size": 12,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 36,
    },
    "md": {
        "tab_height": 32,
        "tab_font_size": 13,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 44,
    },
    "lg": {
        "tab_height": 36,
        "tab_font_size": 15,
        "tab_padding_x": 12,
        "tab_padding_y": 4,
        "list_padding": 4,
        "list_gap": 8,
        "panel_padding_v": 12,
        "panel_padding_h": 4,
        "panel_padding_v_side": 0,
        "panel_padding_h_side": 12,
        "underline_h": 2,
        "underline_ratio": 0.8,
        "border_width": 2,
        "tab_min_width": 52,
    },
}

# 兼容长名称
TABS_SIZES["small"] = TABS_SIZES["sm"]
TABS_SIZES["medium"] = TABS_SIZES["md"]
TABS_SIZES["large"] = TABS_SIZES["lg"]

__all__ = ["TABS_SIZES"]
