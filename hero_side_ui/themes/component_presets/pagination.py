"""Pagination 组件主题预设 (PAGINATION_SIZES)。

对齐 HeroUI v2 pagination.ts 源码:
  - sm: min-w-8 (32px) / h-8 / text-tiny (12px) / px-1 (4px)
  - md: min-w-9 (36px) / h-9 / text-small (13px) / px-2 (8px)
  - lg: min-w-10 (40px) / h-10 / text-medium (15px) / px-2 (8px)

字段:
  item_height       - 单个 item 的固定高度
  item_min_width    - 单个 item 的最小宽度（与高度一致即正方形）
  font_size         - 数字文字字号
  padding_x         - item 水平内边距
  list_gap          - 默认间距 (gap-1 = 4px)
  border_width      - bordered/faded 边框宽度 (border-medium = 2px)
  cursor_scale_max  - cursor 弹起最大倍数 (HeroUI: 1.1)
  cursor_anim_ms    - cursor 切换动画总时长 (HeroUI: 300ms)
  icon_size         - prev/next/dots 图标渲染尺寸
"""

PAGINATION_SIZES = {
    "sm": {
        "item_height": 32,
        "item_min_width": 32,
        "font_size": 12,
        "padding_x": 4,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 14,
    },
    "md": {
        "item_height": 36,
        "item_min_width": 36,
        "font_size": 13,
        "padding_x": 8,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 16,
    },
    "lg": {
        "item_height": 40,
        "item_min_width": 40,
        "font_size": 15,
        "padding_x": 8,
        "list_gap": 4,
        "border_width": 2,
        "cursor_scale_max": 1.1,
        "cursor_anim_ms": 300,
        "icon_size": 18,
    },
}

# 兼容长名称
PAGINATION_SIZES["small"] = PAGINATION_SIZES["sm"]
PAGINATION_SIZES["medium"] = PAGINATION_SIZES["md"]
PAGINATION_SIZES["large"] = PAGINATION_SIZES["lg"]

__all__ = ["PAGINATION_SIZES"]
