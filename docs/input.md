# Input 输入框

基于 [HeroUI v2](https://heroui.com/) 设计风格的输入框组件，继承自 `QWidget`，内部嵌入 `QLineEdit` 作为实际输入控件，对外暴露 `Input.line_edit` 和常用代理方法，保持完整的 Qt 原生 API。

内置浮动 label 动画、`underlined` 变体的下划线展开动画、清除按钮的淡入缩放动画，完整复刻 HeroUI v2 的 Input 交互体验。

## 导入

```python
from hero_side_ui import Input
```

## 基本用法

```python
# 最简用法 — 默认 flat + default + md + inside label
inp = Input(label="Email", placeholder="you@example.com")

# 指定颜色和变体
inp = Input(
    label="Username",
    placeholder="Type here",
    color="primary",
    variant="bordered",
    size="md",
)

# 可清除 + 带描述
inp = Input(
    label="Search",
    placeholder="关键词",
    is_clearable=True,
    description="支持模糊匹配",
)

# 错误态
inp = Input(
    label="Password",
    variant="faded",
    color="danger",
    is_invalid=True,
    error_message="密码不能为空",
)

# Qt 原生 API 仍可用
inp.line_edit.setMaxLength(32)
inp.text_changed.connect(lambda t: print(t))
```

## start_content / end_content 的三种用法

```python
# 1. 静态图标（字符串）
Input(label="Search", start_content="heroicons--chevron-right-solid")

# 2. 字符串图标 + 点击回调 -> 自动变成可点击按钮
# 典型场景: 密码框眼睛切显隐
pwd = Input(label="Password", variant="bordered",
            end_content="heroicons--eye-solid")
pwd.line_edit.setEchoMode(pwd.line_edit.EchoMode.Password)

def toggle():
    visible = pwd.line_edit.echoMode() == pwd.line_edit.EchoMode.Normal
    pwd.line_edit.setEchoMode(pwd.line_edit.EchoMode.Password if visible
                              else pwd.line_edit.EchoMode.Normal)
    pwd.set_end_content(
        "heroicons--eye-solid" if visible else "heroicons--eye-slash-solid",
        on_click=toggle,
    )
pwd.set_on_end_content_click(toggle)

# 3. 直接塞任意 QWidget（比如另一个 HeroSideUI Button）
go_btn = Button("GO", size="sm", variant="flat", color="primary")
go_btn.clicked.connect(do_search)
Input(label="Query", end_content=go_btn)
```

---

## 构造参数

| 参数                     | 类型                     | 默认值      | 说明                                                                                |
| ------------------------ | ------------------------ | ----------- | ----------------------------------------------------------------------------------- |
| `label`                  | `str`                    | `""`        | 标签文字。为空时自动不显示 label                                                    |
| `value`                  | `str`                    | `""`        | 初始文本值                                                                          |
| `placeholder`            | `str`                    | `""`        | 占位符                                                                              |
| `variant`                | `str`                    | `"flat"`    | 样式变体，见 [variant 可选值](#variant-可选值)                                      |
| `color`                  | `str`                    | `"default"` | 颜色主题，见 [color 可选值](#color-可选值)                                          |
| `size`                   | `str`                    | `"md"`      | 尺寸，见 [size 可选值](#size-可选值)                                                |
| `radius`                 | `str \| None`            | `None`      | 圆角，`None` 时跟随尺寸默认值。见 [radius 可选值](#radius-可选值)                   |
| `label_placement`        | `str`                    | `"inside"`  | label 位置，见 [label_placement 可选值](#label_placement-可选值)                    |
| `is_disabled`            | `bool`                   | `False`     | 禁用状态，整体半透明且不响应交互                                                    |
| `is_invalid`             | `bool`                   | `False`     | 无效状态，边框/文字切换为 `danger` 色                                               |
| `is_required`            | `bool`                   | `False`     | 必填，label 末尾追加红色 `*`                                                        |
| `is_readonly`            | `bool`                   | `False`     | 只读，文字可选可复制但不可编辑                                                      |
| `is_clearable`           | `bool`                   | `False`     | 显示清除按钮。有文本时按钮淡入，点击清空                                            |
| `full_width`             | `bool`                   | `True`      | 是否撑满父容器宽度                                                                  |
| `description`            | `str`                    | `""`        | 辅助说明文字，显示在输入框下方                                                      |
| `error_message`          | `str`                    | `""`        | 错误消息，`is_invalid=True` 时替代 description 显示                                 |
| `start_content`          | `str \| QWidget \| None` | `None`      | 输入框左侧内容。可以是内置图标名/SVG 路径，或直接传入任意 `QWidget`（比如 Button）  |
| `end_content`            | `str \| QWidget \| None` | `None`      | 输入框右侧内容，同上                                                                |
| `on_start_content_click` | `Callable \| None`       | `None`      | 左侧图标的点击回调。**仅当 `start_content` 是字符串时生效** —— 会自动包成可点击按钮 |
| `on_end_content_click`   | `Callable \| None`       | `None`      | 右侧图标的点击回调，同上（典型用途：密码框眼睛切显隐）                              |
| `theme`                  | `str`                    | `"light"`   | 主题模式：`"light"` 亮色 / `"dark"` 暗色                                            |
| `parent`                 | `QObject \| None`        | `None`      | Qt 父对象                                                                           |

### variant 可选值

> HeroSideUI 对 HeroUI 的样式做了些定制化偏离（关键不同点已标 ★）。

| 值           | 外观                                                                                                                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `flat`       | 浅色填充（彩色时彩底，`default` 时灰底），无边框；**亮色 hover 压暗**（`-100→-200`），**暗色 hover 提亮**（透明度 0.15→0.25）           |
| `faded`      | ★ **底色与 flat 一致**（同样的亮压暗/暗提亮），2px 边框；**默认边框比底色深一档**（同色系 `-200`，暗色 `-700`）；hover/focus 边框变主色 |
| `bordered`   | ★ 透明背景 + 2px 边框；**默认边框 = flat 的底色**（浅彩/浅灰）；hover → `{color}-400`（暗色 `-600`），focus → `{color}-500`（边框归宿） |
| `underlined` | 透明背景 + 底部 2px 线；focus 时底部从中心展开一条主色彩条                                                                              |

### color 可选值

`default` / `primary` / `secondary` / `success` / `warning` / `danger`

### size 可选值

| 值   | outside 高度 | inside 高度 | 说明         |
| ---- | ------------ | ----------- | ------------ |
| `sm` | 32px         | 48px        | 小号         |
| `md` | 40px         | 56px        | 中号（默认） |
| `lg` | 48px         | 64px        | 大号         |

### radius 可选值

`none` / `sm` / `md` / `lg` / `full`（胶囊形，依高度动态计算）

### label_placement 可选值

| 值             | 行为                                                                                                  |
| -------------- | ----------------------------------------------------------------------------------------------------- |
| `inside`       | label 在输入框**内部**。未聚焦且无值时居中（像 placeholder），聚焦/有值后浮起到输入框内顶部（带动画） |
| `outside`      | label 在输入框**内部**作为 placeholder 显示。聚焦/有值后**飞出输入框**到上方外部（带动画）            |
| `outside-top`  | label 始终**固定在输入框上方外部**，无动画                                                            |
| `outside-left` | label 位于输入框左侧，始终固定                                                                        |

---

## 信号

| 信号               | 载荷  | 说明                                 |
| ------------------ | ----- | ------------------------------------ |
| `text_changed`     | `str` | 文字变化时触发（代理 `textChanged`） |
| `editing_finished` | 无    | 编辑完成（失焦/回车）                |
| `returned`         | 无    | 回车触发                             |
| `cleared`          | 无    | 点击清除按钮后触发                   |

也可以直接使用 Qt 原生信号，通过 `input.line_edit.xxx` 访问。

---

## 公共 API

| 方法                                        | 说明                                               |
| ------------------------------------------- | -------------------------------------------------- |
| `text()` / `set_text(text)`                 | 获取/设置当前文本                                  |
| `clear()`                                   | 清空文本                                           |
| `set_value(value)`                          | 设置值（`set_text` 的别名）                        |
| `set_placeholder(text)`                     | 设置占位符                                         |
| `set_label(text)`                           | 设置 label                                         |
| `set_color(color)`                          | 动态切换颜色                                       |
| `set_variant(variant)`                      | 动态切换变体                                       |
| `set_size(size)`                            | 动态切换尺寸                                       |
| `set_radius(radius)`                        | 动态切换圆角                                       |
| `set_label_placement(plc)`                  | 动态切换 label 位置                                |
| `set_theme(theme)`                          | 动态切换亮暗主题                                   |
| `set_is_disabled(bool)`                     | 动态启用/禁用                                      |
| `set_is_invalid(bool)`                      | 动态切换无效态                                     |
| `set_is_required(bool)`                     | 动态切换必填                                       |
| `set_is_readonly(bool)`                     | 动态切换只读                                       |
| `set_is_clearable(bool)`                    | 动态切换清除按钮                                   |
| `set_description(text)`                     | 设置描述文字                                       |
| `set_error_message(text)`                   | 设置错误消息                                       |
| `set_start_content(content, on_click=None)` | 设置左侧内容（字符串图标或 QWidget；可选点击回调） |
| `set_end_content(content, on_click=None)`   | 设置右侧内容，同上                                 |
| `set_on_start_content_click(cb)`            | 仅更新左侧点击回调                                 |
| `set_on_end_content_click(cb)`              | 仅更新右侧点击回调                                 |
| `line_edit`                                 | 属性：内部 `QLineEdit` 实例                        |

---

## 动画细节

- **浮动 label**（`inside` 模式）：聚焦或有值时 label 上移、字号缩至 ~85%、颜色插值到"浮起色"。用 `QPropertyAnimation` 驱动一个 `progress` 浮点属性，在回调中手动插值 `geometry/fontSize/color`，时长 250ms `OutCubic`。
- **下划线展开**（`underlined` 变体）：聚焦时底部 2px 主色条从中心向两侧展开到 100% 宽度，失焦时收回。由 `UnderlineBar`（自定义 QWidget + QPainter）承载。
- **清除按钮**：用 `QGraphicsOpacityEffect` 做淡入淡出，默认显示时 opacity=0.7，hover 时 opacity=1.0，隐藏时 opacity=0，时长 150ms。

---

## 示例

- [`examples/input/light_mode.py`](../examples/input/light_mode.py) — 亮色模式
- [`examples/input/dark_mode.py`](../examples/input/dark_mode.py) — 暗色模式
