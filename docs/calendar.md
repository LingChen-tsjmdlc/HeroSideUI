# Calendar 日历 / RangeCalendar 范围日历

> HeroSideUI 的日历组件，对齐 [HeroUI v2 Calendar](https://v2.heroui.com/docs/components/calendar)。
>
> 底层日期系统基于 PyICU。逻辑层（日期算术 / 状态机 / 网格切分）与 Qt 渲染层完全分离，可脱离界面单元测试。

## 快速开始

```python
from hero_side_ui import Calendar, RangeCalendar
from hero_side_ui.components.calendar._date import CalendarDate

# 单选
cal = Calendar(value=CalendarDate(2026, 7, 15))
cal.change.connect(lambda d: print("selected:", d))

# 范围
rng = RangeCalendar()
rng.change.connect(lambda pair: print("range:", pair))  # (start, end)
```

## 日期对象 CalendarDate

`Calendar` 的 `value` / `min_value` / `max_value`，以及信号回传的日期都是
`CalendarDate`（不可变）。

```python
from hero_side_ui.components.calendar._date import CalendarDate

d = CalendarDate(2026, 7, 15)          # 年, 月(1-based), 日
CalendarDate.today()                    # 今天
d.add(months=1)                         # 月末进位安全
d.with_fields(day=1)                    # 替换字段
d.year / d.month / d.day / d.weekday    # 字段（weekday: 周日=1..周六=7）
```

## 构造参数（Calendar）

| 参数                             | 类型                                       | 默认值        | 说明                                                                                  |
| -------------------------------- | ------------------------------------------ | ------------- | ------------------------------------------------------------------------------------- |
| `value`                          | `Optional[CalendarDate]`                   | `None`        | 选中日期                                                                              |
| `min_value` / `max_value`        | `Optional[CalendarDate]`                   | 1900 / 2099   | 可选范围下界 / 上界（越界日期禁用，且决定翻页与年份选择器范围）                       |
| `color`                          | `str`                                      | `"primary"`   | `foreground` / `primary` / `secondary` / `success` / `warning` / `danger`             |
| `visible_months`                 | `int`                                      | `1`           | 同时显示的月数（1~3，多月时禁用月/年选择器）                                          |
| `first_day_of_week`              | `Optional[str]`                            | locale 默认   | `sun`/`mon`/`tue`/`wed`/`thu`/`fri`/`sat`                                             |
| `weekday_style`                  | `str`                                      | `"narrow"`    | 星期名样式：`narrow`(S) / `short`(Sun) / `long`(Sunday)                               |
| `page_behavior`                  | `str`                                      | `"visible"`   | 翻页步长：`visible`(翻 visible_months 个月) / `single`(每次翻 1 月)                   |
| `show_month_and_year_pickers`    | `bool`                                     | `False`       | 点标题展开月/年滚动选择器（仅 `visible_months==1` 生效）                              |
| `is_header_default_expanded`     | `bool`                                     | `False`       | 初始即展开月/年选择器                                                                 |
| `is_disabled`                    | `bool`                                     | `False`       | 整体禁用                                                                              |
| `is_readonly`                    | `bool`                                     | `False`       | 只读（可浏览不可选）                                                                  |
| `is_invalid`                     | `bool`                                     | `False`       | 无效态：红色边框，配合 `error_message` 显示错误提示                                   |
| `error_message`                  | `Optional[str]`                            | `None`        | 底部错误提示文字（`is_invalid=True` 时显示）                                          |
| `is_date_unavailable`            | `Optional[Callable[[CalendarDate], bool]]` | `None`        | 返回 True 的日期不可选（显示删除线）                                                  |
| `disable_animation`              | `bool`                                     | `False`       | 关闭翻页滑动动画                                                                      |
| `top_content` / `bottom_content` | `Optional[QWidget]`                        | `None`        | 日历上方 / 下方的自定义内容（超宽时横向滚动，不撑宽日历）                             |
| `identifier`                     | `str`                                      | `"gregorian"` | ICU 历法标识。当前完整支持公历；其他历法（`buddhist` 等）为实验性，纪年本地化尚未完成 |
| `theme`                          | `str`                                      | `"auto"`      | `auto` / `light` / `dark`                                                             |

`RangeCalendar` 参数与 `Calendar` 相同，仅 `value` 为 `(start, end)` 元组。

## 信号

| 信号                     | 参数                                           | 触发时机                                 |
| ------------------------ | ---------------------------------------------- | ---------------------------------------- |
| `change`                 | `CalendarDate`（单选）/ `(start, end)`（范围） | 选中值确定时（范围在选完第二端点时触发） |
| `focus_change`           | `CalendarDate`                                 | 焦点日期移动（翻页 / 键盘导航）          |
| `header_expanded_change` | `bool`                                         | 月/年选择器展开 / 收起                   |

## 方法

| 方法                        | 说明                                                |
| --------------------------- | --------------------------------------------------- |
| `value()`                   | 当前选中值（单选返回 `CalendarDate`，范围返回元组） |
| `set_value(date)`           | 编程设置选中值                                      |
| `set_color(color)`          | 运行时改颜色                                        |
| `is_header_expanded()`      | 月/年选择器是否展开                                 |
| `set_header_expanded(bool)` | 展开 / 收起月/年选择器                              |
| `set_theme(theme)`          | 切换主题（`auto`/`light`/`dark`）                   |

## 交互

- **翻页**：点头部左右箭头，网格横向滑动切换（`disable_animation=True` 关闭）。
- **月/年选择器**：`show_month_and_year_pickers=True` 时点标题展开，两列滚动
  （中国习惯**年在左、月在右**），中央高亮条吸附选中，`Esc` 收起。
- **范围选择**（RangeCalendar）：第一次点击锚定起点，移动鼠标实时预览，第二次
  点击确定终点（自动排序）。起止端点为实底圆、中间为浅色连接背景。

## 设计说明

- 卡片浮起用边框（`border`）而非 `QGraphicsDropShadowEffect`——后者会让含交互子
  控件的容器走离屏渲染，导致子按钮错位。
- 星期名行是独立固定组件，翻月不重绘。
- 日期区（`default-50`）与顶部标题/星期名区（`content1`）靠色差分层。
