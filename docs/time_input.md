# TimeInput 时间输入

分段时间输入组件，复刻 HeroUI v2 的 `TimeInput`。只显示 时 / 分 / 秒（以及可选的 AM-PM / 时区）多个独立段，每段可单独聚焦、用键盘逐位输入或上下键增减。

`TimeInput` 是 [DateInput](date-input.md) 的时间粒度特化：外框视觉、键盘交互、公共 API 完全一致，差异仅在于无年 / 月 / 日段，且 `granularity` 只允许 `hour` / `minute` / `second`（默认 `minute`，对齐 react-aria 的 `useTimeFieldState`）。

## 基础用法

```python
from hero_side_ui import TimeInput

ti = TimeInput(label="Event time")
ti.value_changed.connect(lambda v: print(v))
```

未填满所有段时 `value()` 返回 `None`（与 HeroUI 的 `null` 语义一致）。

## 值的构造

值类型与 DateInput 相同为 `DateTimeValue`，但组件只关心时刻部分——`min_value` / `max_value` 的日期部分不参与越界判定，比较的只有 (时, 分, 秒)：

```python
from hero_side_ui import TimeInput
from hero_side_ui.components.date_input._value import parse_datetime

ti = TimeInput(
    label="Event time",
    value=parse_datetime("2024-04-04T18:45:00"),
)
```

## 参数

| 参数                            | 类型                     | 默认值      | 说明                                                                   |
| ------------------------------- | ------------------------ | ----------- | ---------------------------------------------------------------------- |
| `label`                         | `str`                    | `""`        | 标签文本                                                               |
| `value`                         | `DateTimeValue \| None`  | `None`      | 当前值                                                                 |
| `placeholder_value`             | `DateTimeValue \| None`  | `None`      | 占位起点；默认当前时刻（对齐 react-aria），且不触发时区段              |
| `variant`                       | `str`                    | `"flat"`    | `flat` / `faded` / `bordered` / `underlined`                           |
| `color`                         | `str`                    | `"default"` | `default` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`                          | `str`                    | `"md"`      | `sm` / `md` / `lg`                                                     |
| `radius`                        | `str \| None`            | `None`      | `none` / `sm` / `md` / `lg` / `full`；`None` 跟随 size                 |
| `label_placement`               | `str`                    | `"inside"`  | `inside` / `outside` / `outside-left` / `outside-top`                  |
| `granularity`                   | `str`                    | `"minute"`  | `hour` / `minute` / `second`，决定显示到哪一级时间段                   |
| `hour_cycle`                    | `int \| None`            | `None`      | `12` / `24`；`None` 跟随 locale 习惯                                   |
| `hide_time_zone`                | `bool`                   | `False`     | 隐藏时区段                                                             |
| `should_force_leading_zeros`    | `bool`                   | `True`      | 数字段补前导零                                                         |
| `min_value` / `max_value`       | `DateTimeValue \| None`  | `None`      | 时刻范围约束；越界自动进入 invalid 视觉（只比较时刻）                  |
| `locale`                        | `str`                    | `"en_US"`   | ICU locale，决定段顺序与分隔符                                         |
| `calendar`                      | `str`                    | `"gregorian"` | ICU 历法（段序随历法变化）                                           |
| `is_disabled`                   | `bool`                   | `False`     | 禁用                                                                   |
| `is_invalid`                    | `bool`                   | `False`     | 无效态                                                                 |
| `is_required`                   | `bool`                   | `False`     | 必填（label 后加红色 `*`）                                             |
| `is_readonly`                   | `bool`                   | `False`     | 只读                                                                   |
| `full_width`                    | `bool`                   | `True`      | 撑满父容器宽度                                                         |
| `description`                   | `str`                    | `""`        | 描述文本                                                               |
| `error_message`                 | `str`                    | `""`        | 错误提示（`is_invalid=True` 时显示）                                   |
| `start_content` / `end_content` | `str \| QWidget \| None` | `None`      | 首尾内容；字符串按图标名解析                                           |
| `theme`                         | `str`                    | `"auto"`    | `auto` / `light` / `dark`                                              |

注意：`granularity="day"` 在 TimeInput 中是非法值，传入会抛 `ValueError`（DateInput 才支持日期粒度）。

## 信号

| 信号            | 参数                    | 触发时机                      |
| --------------- | ----------------------- | ----------------------------- |
| `value_changed` | `DateTimeValue \| None` | 值变化时；段未填满时传 `None` |

## 方法

与 DateInput 完全一致（`value` / `set_value` / `clear` / `set_granularity` / `set_hour_cycle` / `set_hide_time_zone` / `set_min_value` / `set_max_value` / 外观与状态 setter 等），见 [DateInput 文档](date-input.md#方法)。`set_granularity` 同样只接受时间粒度。

## 键盘操作

与 DateInput 完全一致：数字键逐位输入输满自动跳段、`↑`/`↓` 增减并回绕、`←`/`→` 移动焦点、`Backspace` 清段、`A`/`P` 切换上午 / 下午、滚轮增减。

## 粒度

```python
TimeInput(label="Hour", granularity="hour")    # hh AM
TimeInput(label="Minute", granularity="minute")  # hh:mm AM（默认）
TimeInput(label="Second", granularity="second")  # hh:mm:ss AM
```

## 小时制

```python
TimeInput(label="Time", hour_cycle=24, value=v)  # 09:30
TimeInput(label="Time", hour_cycle=12, value=v)  # 09:30 AM
```

`hour_cycle=None` 时跟随 locale 习惯（`en_US` 默认 12 小时制）。

## 时刻范围

`min_value` / `max_value` 只按时刻比较，日期部分任意：

```python
from hero_side_ui.components.date_input._value import parse_datetime

TimeInput(
    label="Event time",
    value=parse_datetime("2024-04-04T20:00:00"),
    min_value=parse_datetime("2000-01-01T09:00:00"),   # 日期无所谓
    max_value=parse_datetime("2000-01-01T18:00:00"),
)  # 20:00 越界 → 自动 invalid
```

## 时区

带时区的值（`parse_zoned_datetime` 或带 `tz` 的 `now()`）会自动多出时区段；`hide_time_zone=True` 隐藏。默认占位值是**无时区**的当前时刻，因此默认外观不含时区文本（对齐 HeroUI）。

## 实现

继承 `DateInput`，通过四个类属性特化：`_object_name = "heroTimeInput"`、`_valid_granularities = ("hour", "minute", "second")`、`_default_granularity = "minute"`、`_include_date = False`。段序由 ICU `DateTimePatternGenerator` 按纯时间 skeleton（`j` / `jm` / `jms`）推导，不拼日期前缀；主题复用 DateInput 的 token（官方同款做法）。

## 示例

完整演示见 `examples/time_input/demo.py`，分节对齐官方文档，并额外补了 Colors / Sizes / Radius 三节（官方文档无，但本库需覆盖全部 valid 维度）。

```bash
uv run python examples/time_input/demo.py
```
