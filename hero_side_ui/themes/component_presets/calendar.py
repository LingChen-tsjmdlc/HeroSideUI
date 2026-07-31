"""Calendar 组件主题预设 (CALENDAR_SIZES)。

对齐 HeroUI v2 calendar.ts：
  - cell: w-8 h-8 (32px)，圆角 full
  - gridHeaderCell: w-8，font text-small
  - header: px-4 py-2；gridHeaderRow: px-4 pb-2
  - --calendar-width 默认 256（由 calendar_width prop 覆盖）
  - --picker-height 224（showMonthAndYearPickers 展开高度）

字段:
  calendar_width    - 单月列宽（总宽 = 该值 × visible_months）
  cell_size         - 单个日期格子的宽高（正方形）
  cell_gap_y        - 行间距（py-0.5 = 2px 上下）
  header_pad_x/y    - 顶部标题栏内边距
  grid_pad_x        - 星期表头 / 周行的水平内边距
  weekday_font      - 星期表头字号
  title_font        - 月份标题字号
  day_font          - 日期数字字号
  picker_height     - 月/年选择器展开高度
  picker_item_font  - picker 项字号 (text-large)
  nav_icon_size     - 上/下月箭头图标尺寸
"""

CALENDAR_SIZES = {
    "calendar_width": 256,
    "cell_size": 32,
    "cell_gap_y": 2,
    "header_pad_x": 16,
    "header_pad_y": 8,
    "grid_pad_x": 16,
    "weekday_font": 13,
    "title_font": 13,
    "day_font": 14,
    "picker_height": 224,
    "picker_item_font": 18,
    "picker_empty_offset": 3,
    "nav_icon_size": 16,
}

__all__ = ["CALENDAR_SIZES"]
