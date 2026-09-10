# NumberInput 数字输入

数值输入组件，复刻 HeroUI v2 的 `NumberInput`。在 Input 的完整外框（label 浮动 / 变体 / 颜色 / 尺寸 / clear 按钮 / 首尾内容）之上增加数值层：右侧垂直步进按钮组、上下键与滚轮步进、min/max 夹取、千分位分组与 percent/currency 格式化。

对齐官方实现：官方 NumberInput 复用 Input 的全部 slots，仅在 innerWrapper 末尾追加 stepperWrapper；本组件同样继承 [Input](input.md)，把 stepper 插入 wrapper 布局末尾。步进语义对齐 react-stately 的 `useNumberFieldState`。

## 基础用法

```python
from hero_side_ui import NumberInput

ni = NumberInput(label="Amount")
ni.value_changed.connect(lambda v: print(v))
```

## 参数

| 参数                            | 类型                     | 默认值      | 说明                                                                   |
| ------------------------------- | ------------------------ | ----------- | ---------------------------------------------------------------------- |
| `label`                         | `str`                    | `""`        | 标签文本                                                               |
| `value`                         | `float \| None`          | `None`      | 当前数值；`None` 表示空                                                |
| `placeholder`                   | `str`                    | `""`        | 占位文本                                                               |
| `min_value` / `max_value`       | `float \| None`          | `None`      | 值域约束；blur 提交与步进时夹取                                        |
| `step`                          | `float`                  | `1.0`       | 步进长度（上下键 / 滚轮 / 按钮）；`0` 抛 `ValueError`                  |
| `hide_stepper`                  | `bool`                   | `False`     | 隐藏右侧步进按钮组（上下键与滚轮仍可用）                               |
| `is_wheel_disabled`             | `bool`                   | `False`     | 关闭滚轮步进                                                           |
| `format_options`                | `dict \| None`           | `None`      | 格式化子集，见 [Format Options](#format-options)                       |
| `variant`                       | `str`                    | `"flat"`    | `flat` / `faded` / `bordered` / `underlined`                           |
| `color`                         | `str`                    | `"default"` | `default` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`                          | `str`                    | `"md"`      | `sm` / `md` / `lg`                                                     |
| `radius`                        | `str \| None`            | `None`      | `none` / `sm` / `md` / `lg` / `full`；`None` 跟随 size                 |
| `label_placement`               | `str`                    | `"inside"`  | `inside` / `outside` / `outside-left` / `outside-top`                  |
| `is_disabled`                   | `bool`                   | `False`     | 禁用（stepper 一并禁用）                                               |
| `is_invalid`                    | `bool`                   | `False`     | 无效态（用户显式指定，自动标红不会覆盖它）                             |
| `is_required`                   | `bool`                   | `False`     | 必填（label 后加红色 `*`）                                             |
| `is_readonly`                   | `bool`                   | `False`     | 只读（stepper 一并禁用）                                               |
| `is_clearable`                  | `bool`                   | `False`     | 显示清空按钮；聚焦时按 `Esc` 也可清空                                  |
| `full_width`                    | `bool`                   | `True`      | 撑满父容器宽度                                                         |
| `description`                   | `str`                    | `""`        | 描述文本                                                               |
| `error_message`                 | `str`                    | `""`        | 错误提示（`is_invalid=True` 时显示）                                   |
| `start_content` / `end_content` | `str \| QWidget \| None` | `None`      | 首尾内容；字符串按图标名解析                                           |
| `theme`                         | `str`                    | `"auto"`    | `auto` / `light` / `dark`                                              |

## 信号

| 信号            | 参数            | 触发时机                                  |
| --------------- | --------------- | ----------------------------------------- |
| `value_changed` | `float \| None` | 数值变化时；文本为空或不可解析时传 `None` |
| `text_changed`  | `str`           | 继承自 Input，任意文本变化                |
| `cleared`       | 无              | 继承自 Input，点击清空按钮时              |

`value_changed` 对齐官方 `onValueChange` 的数值语义：只发可解析的数字或 `None`，连续相同值去重。

## 方法

| 方法                                                     | 说明                                            |
| -------------------------------------------------------- | ----------------------------------------------- |
| `value() -> float \| None`                               | 当前数值；空或非法文本时为 `None`               |
| `set_value(value)`                                       | 设置数值；自动夹取并按格式回显，`None` 等价清空 |
| `set_step(step)`                                         | 修改步长；`0` 抛 `ValueError`                   |
| `set_min_value(v)` / `set_max_value(v)`                  | 修改值域；已有值越界时立即拉回界内              |
| `set_hide_stepper(hide)`                                 | 显隐步进按钮组                                  |
| `set_is_disabled` / `set_is_readonly` / `set_is_invalid` | 状态 setter，联动 stepper 可用性                |

其余外观与状态 setter（`set_variant` / `set_color` / `set_size` / `set_radius` / `set_label_placement` / `set_description` / `set_error_message` / `clear` 等）与 Input 一致，见 [Input 文档](input.md)。

## 键盘与滚轮交互

| 操作           | 行为                                                                  |
| -------------- | --------------------------------------------------------------------- |
| `↑` / `↓`      | ±`step` 步进；禁用 / 只读时空转                                       |
| 滚轮           | 输入框**聚焦时** ±`step`（对齐 react-aria）；`is_wheel_disabled` 关闭 |
| `Esc`          | `is_clearable=True` 时清空                                            |
| `Enter` / 失焦 | 提交：合法值夹取到值域并按格式回显                                    |

## 步进语义

- 空值步进从 `0` 起步；若 `0` 不在值域内（如 `min_value=10`），从最近边界起步（10 → 11）。
- 浮点累积误差按 10 位小数收敛：`0.1 + 0.2` 步进结果为 `0.3` 而非 `0.30000000000000004`。
- 步进结果同样受 min/max 夹取。

## 非法输入

非法文本（如 `abc`）在 blur / 回车提交时**标红提示但不改写用户输入**；用户把文本修正后红色自动撤除。显式传入的 `is_invalid=True` 优先级更高，不会被自动状态覆盖。

## Format Options

`format_options` 取官方 `formatOptions` 的常用子集：

| 键                        | 类型   | 说明                                                                  |
| ------------------------- | ------ | --------------------------------------------------------------------- |
| `style`                   | `str`  | `decimal`（默认）/ `percent` / `currency`                             |
| `currency`                | `str`  | 货币代码，见下方货币符号映射表；未收录的代码回退为「代码 + 空格」前缀 |
| `minimum_fraction_digits` | `int`  | 最小小数位；默认 `currency` 为 2，其余为 0（对齐 Intl 默认）          |
| `maximum_fraction_digits` | `int`  | 最大小数位；默认 `currency` 为 2，其余为 3                            |
| `use_grouping`            | `bool` | 千分位分组，默认 `True`                                               |

内置货币符号映射（`_CURRENCY_SYMBOLS`，共 29 种）：覆盖 SWIFT 2025-02 全球支付占比前 20（合计约 99%），另补 INR / BRL / RUB / TWD / PHP / IDR / VND / ILS 等主要经济体货币。

| 代码  | 符号  | 代码  | 符号  | 代码  | 符号  |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `USD` | `$`   | `CHF` | `CHF` | `HUF` | `Ft`  |
| `EUR` | `€`   | `SEK` | `kr`  | `MYR` | `RM`  |
| `GBP` | `£`   | `PLN` | `zł`  | `KRW` | `₩`   |
| `CNY` | `¥`   | `NOK` | `kr`  | `INR` | `₹`   |
| `JPY` | `¥`   | `DKK` | `kr`  | `RUB` | `₽`   |
| `CAD` | `C$`  | `NZD` | `NZ$` | `TRY` | `₺`   |
| `HKD` | `HK$` | `ZAR` | `R`   | `BRL` | `R$`  |
| `AUD` | `A$`  | `THB` | `฿`   | `TWD` | `NT$` |
| `SGD` | `S$`  | `MXN` | `MX$` | `PHP` | `₱`   |

未收录的代码（如 `AED`、`SAR`，符号为阿拉伯文字不便通用显示）回退为「代码 + 空格」前缀（如 `AED 5.00`）。

显示时尾随 0 收敛到 min/max 之间自适应（对齐 `Intl.NumberFormat` 行为）。

`percent` 语义为**值即显示数字**：`50` 显示为 `50%`，不做 0-1 换算（与官方 v2 文档示例一致）。

```python
NumberInput(label="Percent", value=50, format_options={"style": "percent"})
# → 50%

NumberInput(label="Price", value=1234.5,
            format_options={"style": "currency", "currency": "CNY"})
# → ¥1,234.50
```

## 实现

继承 `Input`（`_object_name = "heroNumberInput"`），stepper 为独立的 `_NumberStepper`（两个透明小按钮，hover/pressed 用透明度反馈），插入 wrapper 布局末尾。图标使用资源库 `teenyicons--up-solid` / `teenyicons--down-solid`；图标色随 `color` 与明暗主题切换（default 色用灰阶 400/500，语义色用主色 DEFAULT）。stepper 按钮尺寸随 `label_placement` 收缩（outside 系 14px，inside 18px）。

整体最小宽度不复用文本输入的 240/260/300（数字内容短，用不了那么宽），走 NumberInput 专属 token `NUMBER_INPUT_MIN_WIDTHS`：sm=60 / md=70 / lg=80。用户 `setFixedWidth` / `setMinimumWidth` / `set_width` 显式接管宽度后 token 不再生效。

## 示例

完整演示见 `examples/number_input/demo.py`，分节对齐官方文档，并额外补了 Colors / Sizes / Radius 三节（官方文档无，但本库需覆盖全部 valid 维度）。

```bash
uv run python examples/number_input/demo.py
```
