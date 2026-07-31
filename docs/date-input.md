# DateInput 日期输入

分段日期输入组件，复刻 HeroUI v2 的 `DateInput`。日期被拆成月 / 日 / 年（以及可选的时 / 分 / 秒 / AM-PM / 时区）多个独立段，每段可单独聚焦、用键盘逐位输入或上下键增减。

段的**顺序与分隔符由 locale 和历法自动决定**：`en_US` 得到 `mm/dd/yyyy`，`de_DE` 得到 `dd.mm.yyyy`，`ja_JP` 得到 `yyyy/mm/dd`，无需手写格式串。

外框视觉（背景 / 边框 / 圆角 / hover / focus / 浮动 label）与 [Input](input.md) 完全同源。

## 基础用法

```python
from hero_side_ui import DateInput, parse_date

di = DateInput(label="Birth date", placeholder_value=parse_date("1995-11-06"))
di.value_changed.connect(lambda v: print(v))
```

未填满所有段时 `value()` 返回 `None`（与 HeroUI 的 `null` 语义一致）。

## 值的构造

组件的值类型是 `DateTimeValue`。用下列函数构造，语义对齐 `@internationalized/date`：

| 函数                         | 说明                | 示例                                                            |
| ---------------------------- | ------------------- | --------------------------------------------------------------- |
| `parse_date(s)`              | 纯日期              | `parse_date("2024-04-04")`                                      |
| `parse_datetime(s)`          | 日期 + 时间，无时区 | `parse_datetime("2024-04-04T18:45:22")`                         |
| `parse_zoned_datetime(s)`    | 带时区              | `parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]")` |
| `parse_absolute_to_local(s)` | UTC 时刻转本机时区  | `parse_absolute_to_local("2021-04-07T18:45:22Z")`               |
| `today()`                    | 今天（纯日期）      | `today()`                                                       |
| `now(tz=None)`               | 当前时刻            | `now("America/New_York")`                                       |

```python
from hero_side_ui import DateInput, parse_zoned_datetime

DateInput(
    label="Event date",
    granularity="minute",
    value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
)
```

## 参数

| 参数                            | 类型                     | 默认值        | 说明                                                                   |
| ------------------------------- | ------------------------ | ------------- | ---------------------------------------------------------------------- |
| `label`                         | `str`                    | `""`          | 标签文本                                                               |
| `value`                         | `DateTimeValue \| None`  | `None`        | 当前值                                                                 |
| `placeholder_value`             | `DateTimeValue \| None`  | `None`        | 占位起点，决定空段首次增减时的基准值                                   |
| `variant`                       | `str`                    | `"flat"`      | `flat` / `faded` / `bordered` / `underlined`                           |
| `color`                         | `str`                    | `"default"`   | `default` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`                          | `str`                    | `"md"`        | `sm` / `md` / `lg`                                                     |
| `radius`                        | `str \| None`            | `None`        | `none` / `sm` / `md` / `lg` / `full`；`None` 跟随 size                 |
| `label_placement`               | `str`                    | `"inside"`    | `inside` / `outside` / `outside-left` / `outside-top`                  |
| `granularity`                   | `str`                    | `"day"`       | `day` / `hour` / `minute` / `second`，决定显示到哪一级时间段           |
| `hour_cycle`                    | `int \| None`            | `None`        | `12` / `24`；`None` 跟随 locale 习惯                                   |
| `hide_time_zone`                | `bool`                   | `False`       | 隐藏时区段                                                             |
| `should_force_leading_zeros`    | `bool`                   | `True`        | 数字段补前导零                                                         |
| `min_value` / `max_value`       | `DateTimeValue \| None`  | `None`        | 值域约束；越界自动进入 invalid 视觉                                    |
| `locale`                        | `str`                    | `"en_US"`     | ICU locale，决定段顺序与分隔符                                         |
| `calendar`                      | `str`                    | `"gregorian"` | ICU 历法：`indian` / `buddhist` / `japanese` 等                        |
| `is_disabled`                   | `bool`                   | `False`       | 禁用                                                                   |
| `is_invalid`                    | `bool`                   | `False`       | 无效态                                                                 |
| `is_required`                   | `bool`                   | `False`       | 必填（label 后加红色 `*`）                                             |
| `is_readonly`                   | `bool`                   | `False`       | 只读                                                                   |
| `full_width`                    | `bool`                   | `True`        | 撑满父容器宽度                                                         |
| `description`                   | `str`                    | `""`          | 描述文本                                                               |
| `error_message`                 | `str`                    | `""`          | 错误提示（`is_invalid=True` 时显示）                                   |
| `start_content` / `end_content` | `str \| QWidget \| None` | `None`        | 首尾内容；字符串按图标名解析                                           |
| `theme`                         | `str`                    | `"auto"`      | `auto` / `light` / `dark`                                              |

## 信号

| 信号            | 参数                    | 触发时机                      |
| --------------- | ----------------------- | ----------------------------- |
| `value_changed` | `DateTimeValue \| None` | 值变化时；段未填满时传 `None` |

## 方法

| 方法                                                                         | 说明                             |
| ---------------------------------------------------------------------------- | -------------------------------- |
| `value()`                                                                    | 取当前值；有段未填返回 `None`    |
| `set_value(v)`                                                               | 设置值，`None` 表示清空          |
| `clear()`                                                                    | 清空所有段回到占位态             |
| `set_granularity(g)`                                                         | 切换粒度（会重建段）             |
| `set_hour_cycle(n)`                                                          | 切换 12 / 24 小时制              |
| `set_hide_time_zone(b)`                                                      | 显隐时区段                       |
| `set_locale(s)` / `set_calendar(s)`                                          | 切换 locale / 历法（会重建段）   |
| `set_min_value(v)` / `set_max_value(v)`                                      | 调整值域                         |
| `set_label` / `set_color` / `set_variant` / `set_size` / `set_radius`        | 外观                             |
| `set_label_placement(p)`                                                     | 标签位置                         |
| `set_is_disabled` / `set_is_invalid` / `set_is_required` / `set_is_readonly` | 状态                             |
| `set_description` / `set_error_message`                                      | 辅助文本                         |
| `set_start_content` / `set_end_content`                                      | 首尾内容                         |
| `set_width(w)`                                                               | 接管宽度（等价 `setFixedWidth`） |
| `set_theme(t)`                                                               | 主题                             |

## 键盘操作

| 按键                   | 行为                               |
| ---------------------- | ---------------------------------- |
| 数字键                 | 在当前段逐位输入，输满自动跳下一段 |
| `↑` / `↓`              | 当前段递增 / 递减，越界回绕        |
| `←` / `→`              | 在可编辑段之间移动焦点             |
| `Backspace` / `Delete` | 清空当前段                         |
| `A` / `P`              | 在 AM/PM 段直接切换上午 / 下午     |
| 滚轮                   | 当前段递增 / 递减                  |

## 粒度

`granularity` 控制显示到哪一级：

```python
DateInput(label="Date", granularity="day")     # mm/dd/yyyy
DateInput(label="Time", granularity="minute")  # mm/dd/yyyy, hh:mm AM
DateInput(label="Time", granularity="second")  # mm/dd/yyyy, hh:mm:ss AM
```

## 国际历法

`locale` 决定段顺序与语言，`calendar` 决定历法：

```python
DateInput(
    label="Appointment date",
    locale="hi_IN",
    calendar="indian",
    value=parse_absolute_to_local("2021-04-07T18:45:22Z"),
)
```

带纪元的历法（印度历、佛历、日本年号）会自动多出一个 era 段。

## 日期范围

超出 `min_value` / `max_value` 的值会自动显示为 invalid，无需手动设 `is_invalid`：

```python
from hero_side_ui import DateInput, today, parse_date

DateInput(label="Date", value=parse_date("2024-04-03"), min_value=today())
```

## 与 Input 的差异

- 内容区是段列表而非 `QLineEdit`，没有 `text()` / `placeholder` / `is_clearable`。
- label 恒定浮起：段永远渲染占位符（`mm/dd/yyyy`），内容区从不为空。
- 最小宽度按段文本实测撑开，不套用 Input 的 240/260/300。

## 已知问题

- **TODO（低优先级，仅控制台噪音）**：使用带非拉丁字形的历法（如 `calendar="indian"`，纪元名为天城文 `शक`）时，部分环境下 Qt 会打印 `qt.text.font.db: OpenType support missing for "...", script 11`。原因是库把字体锁定为思源黑体，它不含天城文 shaping 表，Qt 遂沿系统字体链逐个回退并每个都告警一次。**不影响功能与显示**（文字仍由 Nirmala UI 等系统字体正确渲染）。彻底消除需给 `make_qfont` 补 `QFont.setFamilies()` 回退链，或扩展 `core/_libpng_filter.py` 的过滤前缀。

## 示例

完整演示见 `examples/date_input/demo.py`，分节对齐官方文档，并额外补了 Colors / Sizes / Radius 三节（官方文档无，但本库需覆盖全部 valid 维度）。

```bash
uv run python examples/date_input/demo.py
```
