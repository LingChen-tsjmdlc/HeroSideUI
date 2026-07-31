# DatePicker 日期选择器

日期选择器组件，复刻 HeroUI v2 的 `DatePicker` / `DateRangePicker`。以 [DateInput](date-input.md) 为基底，在首尾槽位注入一个日历图标按钮；点击按钮弹出 [Calendar](calendar.md)（范围模式为 [RangeCalendar](calendar.md)），选择日期后写回输入框。

DateInput 的全部能力（分段输入、键盘编辑、locale/历法、粒度、值域、状态）都被保留，DatePicker 只是在其上叠加了"日历弹层"这一层交互。

## 基础用法

```python
from hero_side_ui import DatePicker, parse_date

dp = DatePicker(label="Birth date", value=parse_date("2000-01-01"))
dp.value_changed.connect(lambda v: print(v))
```

粒度不含时间时，选完日期弹层自动关闭；含时间时保持打开，便于继续选时刻。

## 范围选择

`DateRangePicker` 是一个输入框内放两组段（中间夹 `–` 分隔符），而不是两个独立输入框。点击日历按钮弹出的不是普通 `Calendar`，而是 [RangeCalendar](calendar.md)——**第一次点击选起点，第二次点击选终点，两次点击之间 hover 实时预览高亮范围**：

```python
from hero_side_ui import DateRangePicker, parse_date

drp = DateRangePicker(
    label="Stay period",
    start_value=parse_date("2024-04-01"),
    end_value=parse_date("2024-04-10"),
)
start, end = drp.value()          # (DateTimeValue, DateTimeValue)
drp.set_value((parse_date("2024-05-01"), parse_date("2024-05-10")))
```

结束端早于开始端时整体视为 invalid（红色提示），但不强制改写用户输入。

## 值的构造

值类型与 DateInput 完全一致，都是 `DateTimeValue`，用下列函数构造（语义对齐 `@internationalized/date`）：

| 函数                         | 说明                | 示例                                                            |
| ---------------------------- | ------------------- | --------------------------------------------------------------- |
| `parse_date(s)`              | 纯日期              | `parse_date("2024-04-04")`                                      |
| `parse_datetime(s)`          | 日期 + 时间，无时区 | `parse_datetime("2024-04-04T18:45:22")`                         |
| `parse_zoned_datetime(s)`    | 带时区              | `parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]")` |
| `parse_absolute_to_local(s)` | UTC 时刻转本机时区  | `parse_absolute_to_local("2021-04-07T18:45:22Z")`               |
| `today()`                    | 今天（纯日期）      | `today()`                                                       |
| `now(tz=None)`               | 当前时刻            | `now("America/New_York")`                                       |

## 参数

DatePicker 转发 DateInput 的全部参数，并新增日历 / 弹层相关参数；DateRangePicker 用 `start_value` / `end_value` 取代单值的 `value`。

| 参数                            | 类型                     | 默认值            | 说明                                                                       |
| ------------------------------- | ------------------------ | ----------------- | -------------------------------------------------------------------------- |
| `label`                         | `str`                    | `""`              | 标签文本                                                                   |
| `value`                         | `DateTimeValue \| None`  | `None`            | DatePicker 当前值                                                         |
| `start_value` / `end_value`     | `DateTimeValue \| None`  | `None`            | DateRangePicker 的起 / 止值                                                |
| `separator`                     | `str`                    | `"–"`             | DateRangePicker 两组的分隔符                                              |
| `variant`                       | `str`                    | `"flat"`          | `flat` / `faded` / `bordered` / `underlined`                               |
| `color`                         | `str`                    | `"default"`       | `default` / `primary` / `secondary` / `success` / `warning` / `danger`    |
| `size`                          | `str`                    | `"md"`            | `sm` / `md` / `lg`                                                         |
| `radius`                        | `str \| None`            | `None`            | `none` / `sm` / `md` / `lg` / `full`；`None` 跟随 size                     |
| `label_placement`               | `str`                    | `"inside"`        | `inside` / `outside` / `outside-left` / `outside-top`                      |
| `granularity`                   | `str`                    | `"day"`           | `day` / `hour` / `minute` / `second`，含时间时选完不自动关弹层            |
| `selector_button_placement`     | `str`                    | `"end"`           | 日历按钮位置：`start` / `end`                                             |
| `min_value` / `max_value`       | `DateTimeValue \| None`  | `None`            | 值域约束；越界自动进入 invalid 视觉                                        |
| `locale` / `calendar`          | `str`                    | `en_US` / `gregorian` | ICU locale / 历法                                                      |
| `is_disabled` / `is_invalid` / `is_required` / `is_readonly` | `bool` | `False` | 状态                                                                       |
| `full_width`                    | `bool`                   | `True`            | 撑满父容器宽度                                                             |
| `description` / `error_message`| `str`                    | `""`              | 辅助 / 错误文本                                                            |
| `visible_months`                | `int`                    | `1`（范围 `2`）   | 日历同时显示的月份数                                                       |
| `first_day_of_week`            | `str \| None`            | `None`            | 每周起始日：`sun` / `mon` / ...；`None` 跟随 locale                        |
| `weekday_style`                 | `str`                    | `"narrow"`        | 星期名缩写宽度                                                             |
| `page_behavior`                 | `str`                    | `"visible"`       | 翻页行为                                                                   |
| `show_month_and_year_pickers`   | `bool`                   | DatePicker `False` / DateRangePicker `True` | 显示月 / 年选择器（仅单月生效）                       |
| `is_date_unavailable`          | `Callable[[CalendarDate], bool] \| None` | `None` | 某天不可选回调                                              |
| `calendar_top_content` / `calendar_bottom_content` | `QWidget \| None` | `None` | 日历内嵌内容                                |
| `calendar_header_default_expanded` | `bool` | `False` | 月 / 年选择器默认展开（仅在 `show_month_and_year_pickers=True` 且单月时生效） |
| `popover_placement`            | `str`                    | `"bottom-start"`  | 弹层相对按钮的方位                                                         |
| `disable_animation`            | `bool`                   | `False`           | 关闭日历翻页 / 弹层动画                                                    |
| `theme`                         | `str`                    | `"auto"`          | `auto` / `light` / `dark`                                                  |

## 信号

| 信号            | 参数                              | 触发时机                              |
| --------------- | --------------------------------- | ------------------------------------- |
| `value_changed` | DatePicker：`DateTimeValue \| None`<br>DateRangePicker：`(DateTimeValue \| None, DateTimeValue \| None)` | 值变化时                              |

## 方法

| 方法                              | 说明                                              |
| --------------------------------- | ------------------------------------------------- |
| `value()`                         | DatePicker 取当前值；DateRangePicker 取 `(start, end)` 元组 |
| `set_value(v)`                    | 设值（DateRangePicker 传 `(start, end)` 元组）    |
| `clear()`                         | 清空                                              |
| `open_calendar()` / `close_calendar()` | 手动开 / 关日历弹层                          |
| `is_calendar_open()`              | 弹层是否打开                                      |
| `is_disabled()` / `set_is_disabled(b)` | 查询 / 设置禁用（同时影响输入框与按钮）     |
| `date_input` / `date_field`      | 底层 DateInput（范围模式为 `_RangeDateField`）   |
| `calendar_widget`                | 底层 Calendar / RangeCalendar                     |

## 键盘操作

日历弹层内的键盘操作见 [Calendar](calendar.md)。输入框内的分段编辑（数字 / 上下键 / 左右键 / 滚轮等）与 [DateInput](date-input.md) 完全一致。

## 日期范围约束

`min_value` / `max_value` 约束会同时作用在输入框与日历上，越界自动显示为 invalid：

```python
from hero_side_ui import DatePicker, today

DatePicker(label="Date", value=today(), min_value=today())
```

## 示例

完整演示见 `examples/date_picker/demo.py`，分节对齐官方文档，并额外补了 Colors / Sizes / Radius / Selector Placement / Calendar Config 几节（官方文档无，但本库需覆盖全部 valid 维度）。

```bash
uv run python examples/date_picker/demo.py
```
