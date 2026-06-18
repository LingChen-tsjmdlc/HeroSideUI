"""Table 组件主题预设 (TABLE_SIZES)。

对齐 HeroUI v2 table.ts:
  - wrapper: p-4 (16) gap-4 (16), shadow-small, rounded-large (14)
  - th: h-10 (40), px-3 (12), text-tiny (12), font-semibold
  - td: py-2 (8) px-3 (12), text-small (14), font-normal
  - isCompact td: py-1 (4)
  -   selectedIcon / checkbox 列宽参考 HeroUI selection cell

数值定义（单位 px）：
  wrapper_padding      wrapper 内边距 (p-4)
  wrapper_gap          wrapper 内 topContent/table/bottomContent 间距 (gap-4)
  header_height        表头行高 (th h-10)
  header_gap           表头与首行内容的间距 (table.ts thead after:h-[5px])
  header_font_size     表头字号 (text-tiny)
  cell_padding_x       单元格水平 padding (px-3)
  cell_padding_y       单元格垂直 padding (py-2)
  compact_padding_y    isCompact 时垂直 padding (py-1)
  row_min_height       数据行最小高度
  font_size            单元格字号 (text-small)
  checkbox_col_width   多选模式 selection cell 列宽
  sort_icon_size       排序箭头尺寸
  cell_gap             单元格内多槽位间距
"""

TABLE_SIZES = {
    "sm": {
        "wrapper_padding": 12,
        "wrapper_gap": 12,
        "header_height": 32,
        "header_gap": 3,
        "header_font_size": 11,
        "cell_padding_x": 10,
        "cell_padding_y": 6,
        "compact_padding_y": 3,
        "row_min_height": 36,
        "font_size": 13,
        "checkbox_col_width": 36,
        "sort_icon_size": 12,
        "cell_gap": 6,
    },
    "md": {
        "wrapper_padding": 16,
        "wrapper_gap": 16,
        "header_height": 40,
        "header_gap": 4,
        "header_font_size": 12,
        "cell_padding_x": 12,
        "cell_padding_y": 8,
        "compact_padding_y": 4,
        "row_min_height": 44,
        "font_size": 14,
        "checkbox_col_width": 40,
        "sort_icon_size": 14,
        "cell_gap": 8,
    },
    "lg": {
        "wrapper_padding": 20,
        "wrapper_gap": 18,
        "header_height": 48,
        "header_gap": 4,
        "header_font_size": 13,
        "cell_padding_x": 14,
        "cell_padding_y": 10,
        "compact_padding_y": 5,
        "row_min_height": 52,
        "font_size": 15,
        "checkbox_col_width": 44,
        "sort_icon_size": 16,
        "cell_gap": 10,
    },
}

TABLE_SIZES["small"] = TABLE_SIZES["sm"]
TABLE_SIZES["medium"] = TABLE_SIZES["md"]
TABLE_SIZES["large"] = TABLE_SIZES["lg"]

__all__ = ["TABLE_SIZES"]
