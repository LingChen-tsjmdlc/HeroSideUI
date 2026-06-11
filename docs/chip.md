# Chip 标签组件

> 对齐 [HeroUI v2 Chip](https://v2.heroui.com/docs/components/chip)。
>
> - 样式锚点：`packages/core/theme/src/components/chip.ts`
> - 组件锚点：`packages/components/chip/src/{chip.tsx,use-chip.ts}`

`Chip` 用于展示标签、属性、状态或可移除的小型实体。支持 7 种 variant、6 种语义色、3 档尺寸、5 档圆角，并可附加头像、关闭按钮、小圆点。

## 快速上手

```python
from hero_side_ui import Chip

Chip("Chip")                                          # 默认 solid + full 圆角
Chip("Primary", color="primary", variant="flat")
Chip("可关闭", color="danger", is_closable=True, on_close=lambda: print("closed"))
Chip("New", color="success", variant="dot")           # 带小圆点
Chip("A", color="primary")                            # 单字符 → 圆形
```

## 构造参数

| 参数            | 类型                                       | 默认        | 说明                                   |
| --------------- | ------------------------------------------ | ----------- | -------------------------------------- |
| `text`          | `str`                                      | `""`        | 标签文本                               |
| `color`         | `str`                                      | `"default"` | 语义色                                 |
| `variant`       | `str`                                      | `"solid"`   | 视觉变体                               |
| `size`          | `"sm" \| "md" \| "lg"`                     | `"md"`      | 尺寸                                   |
| `radius`        | `"none" \| "sm" \| "md" \| "lg" \| "full"` | `"full"`    | 圆角；`full` 按高度一半动态算          |
| `avatar`        | `QWidget \| None`                          | `None`      | 左侧头像控件（自动锁定为对应尺寸方形） |
| `start_content` | `QWidget \| None`                          | `None`      | 左侧自定义内容                         |
| `end_content`   | `QWidget \| None`                          | `None`      | 右侧自定义内容                         |
| `is_disabled`   | `bool`                                     | `False`     | 禁用态（半透明 + 不可交互）            |
| `is_closable`   | `bool`                                     | `False`     | 显示关闭按钮                           |
| `on_close`      | `Callable[[], None] \| None`               | `None`      | 关闭回调；传入即视为可关闭             |
| `theme`         | `"auto" \| "light" \| "dark"`              | `"auto"`    | 主题模式；auto 跟随 `ThemeProvider`    |
| `parent`        | `QWidget \| None`                          | `None`      | 父级                                   |

## 可选值

### color

`"default"` `"primary"` `"secondary"` `"success"` `"warning"` `"danger"`

### variant

| variant    | 视觉                         |
| ---------- | ---------------------------- |
| `solid`    | 纯色背景 + 对比色文字        |
| `bordered` | 透明底 + 彩色边框            |
| `light`    | 透明底 + 彩色文字，无边框    |
| `flat`     | 彩色浅底 + 无边框            |
| `faded`    | 浅底 + 浅色细边框            |
| `shadow`   | 纯色背景 + 彩色投影          |
| `dot`      | 透明底 + 灰边框 + 彩色小圆点 |

### radius

`"none"` `"sm"` `"md"` `"lg"` `"full"`

### size

`"sm"`(h=24) `"md"`(h=28) `"lg"`(h=32)

## 信号

| 信号     | 说明               |
| -------- | ------------------ |
| `closed` | 点击关闭按钮时触发 |

## 公共方法

| 方法                   | 说明                          |
| ---------------------- | ----------------------------- |
| `set_text(text)`       | 重设文本                      |
| `text()`               | 当前文本                      |
| `set_color(color)`     | 切换语义色                    |
| `set_variant(variant)` | 切换变体                      |
| `set_size(size)`       | 切换 sm / md / lg             |
| `set_radius(radius)`   | 切换圆角                      |
| `set_disabled(bool)`   | 切换禁用态                    |
| `set_closable(bool)`   | 切换关闭按钮显隐              |
| `set_theme(theme)`     | `"auto" \| "light" \| "dark"` |

## 特殊行为

- **单字符圆形**：`text` 长度为 1 且无头像/关闭按钮/附加内容、且 `variant != "dot"` 时，自动锁成正方形（sm=20 / md=24 / lg=28），文字居中。
- **关闭按钮**：内部复用 `Button(icon_only=True, icon="heroicons--x-mark-16-solid")`，图标色随 variant 配色自动切换，用户无需接触 `QIcon`。
- **shadow / disabled 图形效果互斥**：Qt 单个 widget 只能挂一个 `QGraphicsEffect`，因此禁用态（半透明）优先于 shadow 投影。

## 示例

`examples/chip/demo.py` 共 10 节：Usage / Colors / Variants / Sizes / Radius / Disabled / Closable / Dot / Avatar / One Char。

## 与 HeroUI 差异

1. HeroUI 的 `classNames`（base/content/dot/avatar/closeButton）是 React tailwind-variants slot；Qt 版改为内部子控件，外部用户无需关心 slot 名。
2. HeroUI 用 `startContent`/`endContent`/`avatar` 接收 React 节点；Qt 版接收任意 `QWidget`。
3. shadow variant 在 Web 端是 CSS box-shadow，Qt 版用 `QGraphicsDropShadowEffect` 还原。
4. `avatar` 传入的控件会被自动锁定为当前 size 对应的方形尺寸（sm=16 / md=20 / lg=24）。
