# Card 卡片

基于 [HeroUI v2](https://heroui.com/) 设计风格的卡片容器组件，继承自 `QWidget`，保持完整的 Qt 原生 API。

Card 是一个三层结构的容器，包含 `CardHeader`（标题区）、`CardBody`（内容区）、`CardFooter`（底部区），支持阴影、圆角、悬停、按压、模糊等特性。

## 导入

```python
from hero_side_ui import Card, CardHeader, CardBody, CardFooter
```

## 基本用法

```python
from PySide6.QtWidgets import QLabel
from hero_side_ui import Card, CardHeader, CardBody, CardFooter

# 创建卡片（shadow 默认 sm，radius 默认 lg）
card = Card()

# Header
header = CardHeader()
header.layout().addWidget(QLabel("Card Title"))
card.add_header(header)

card.add_divider()              # 分割线（按调用顺序放在 Header 和 Body 之间）

# Body
body = CardBody()
body.layout().addWidget(QLabel("Card content goes here."))
card.add_body(body)

card.add_divider()

# Footer
footer = CardFooter()
footer.layout().addWidget(QLabel("Footer text"))
card.add_footer(footer)
```

> **调用顺序就是视觉顺序**。`add_header / add_body / add_footer / add_divider` 都是按顺序追加（`addWidget`），不会自动排序。

---

## Card 构造参数

| 参数                | 类型              | 默认值    | 说明                                                          |
| ------------------- | ----------------- | --------- | ------------------------------------------------------------- |
| `shadow`            | `str`             | `"sm"`    | 阴影级别，见 [shadow 可选值](#shadow-可选值)                  |
| `radius`            | `str`             | `"lg"`    | 圆角级别，见 [radius 可选值](#radius-可选值)                  |
| `is_hoverable`      | `bool`            | `False`   | 启用悬停效果（背景色 300ms 过渡）                             |
| `is_pressable`      | `bool`            | `False`   | 启用按压效果（水波纹 + 97% 缩放 + `pressed` 信号 + 手形光标） |
| `is_disabled`       | `bool`            | `False`   | 禁用状态（半透明 + 禁止图标光标 + 不响应交互）                |
| `is_blurred`        | `bool`            | `False`   | 整卡模糊效果（半透明底色，配渐变背景模拟磨砂玻璃）            |
| `is_footer_blurred` | `bool`            | `False`   | 仅 footer 模糊                                                |
| `full_width`        | `bool`            | `False`   | 是否水平撑满父容器（垂直仍按内容高度）                        |
| `theme`             | `str`             | `"light"` | 主题：`"light"` / `"dark"`                                    |
| `parent`            | `QWidget \| None` | `None`    | Qt 父对象                                                     |

> **注意**：Card **没有** `size` prop 。padding 固定 12px，字号由你在插入的子控件上自行设置（`QLabel.setFont()` 或 QSS）。Card 只负责结构和视觉，不干涉内容排版。

---

## 宽度 / 高度控制

Card **不帮你决定尺寸**。你写多大就多大，shadow 永远画在卡外面，不挤占内容区。

| 方式                                     | 用途                     | 示例                          |
| ---------------------------------------- | ------------------------ | ----------------------------- |
| `setFixedSize(w, h)`                     | 锁死可视 Card 尺寸       | `card.setFixedSize(360, 200)` |
| `setFixedWidth(w)` / `setFixedHeight(h)` | 只锁一边                 | `card.setFixedWidth(360)`     |
| `setMinimumWidth` / `setMaximumWidth` 等 | 限制自适应范围           | `card.setMinimumWidth(280)`   |
| 不调尺寸 API                             | 由内容 sizeHint 自然撑开 | —                             |

这些 setter 在 Card 内部被**代理到内层 `_content`**，所以你写的数字就是**可视 Card 尺寸**——Card 外壳会自动向外扩 `2 × shadow_margin` 来容纳阴影空间。换句话说：

```python
card = Card(shadow="lg")
card.setFixedWidth(360)
# 可视 Card 宽度 = 360（不管 shadow 多大）
# 外壳实际宽度 = 360 + 2×shadow_margin（例如 lg 下 ≈ 410）
```

### sizePolicy

Card 的 sizePolicy 默认：

- 水平：`Preferred`（或 `Expanding` 当 `full_width=True`）
- 垂直：**始终 `Fixed`**（等于 sizeHint）

垂直锁为 Fixed 的目的是：放进 `QHBoxLayout` 时，不会因为同行有其他更大 shadow 的 Card 而被等高拉伸，从而挤压自身内容区。

---

## shadow 可选值

| 值     | 说明   | 模糊半径 | 偏移 Y | 不透明度 |
| ------ | ------ | -------- | ------ | -------- |
| `none` | 无阴影 | 0        | 0      | 0        |
| `sm`   | 小阴影 | 8px      | 1px    | 6%       |
| `md`   | 中阴影 | 14px     | 4px    | 8%       |
| `lg`   | 大阴影 | 30px     | 8px    | 12%      |

阴影由 `paintEvent` 用多层半透明圆角矩形**自绘**实现（没有使用 `QGraphicsDropShadowEffect`）。这样做是为了避免和子控件自带的 `QGraphicsEffect`（如 Button 的 `PressScaleEffect`）嵌套渲染冲突，否则子控件会整片消失。

---

## radius 可选值

| 值     | 像素 | 说明   |
| ------ | ---- | ------ |
| `none` | 0px  | 直角   |
| `sm`   | 4px  | 小圆角 |
| `md`   | 8px  | 中圆角 |
| `lg`   | 14px | 大圆角 |

---

## 三层结构

### CardHeader

水平布局（`QHBoxLayout`），适合标题文字、头像、操作按钮。

```python
header = CardHeader()
header.layout().addWidget(QLabel("Title"))
header.layout().addStretch()
header.layout().addWidget(QLabel("Subtitle"))
card.add_header(header)
```

### CardBody

垂直布局（`QVBoxLayout`），`Expanding` 撑满剩余高度。

```python
body = CardBody()
body.layout().addWidget(QLabel("Main content"))
card.add_body(body)
```

### CardFooter

水平布局（`QHBoxLayout`），适合按钮、链接。

```python
from hero_side_ui import Button

footer = CardFooter()
footer.layout().addStretch()
footer.layout().addWidget(Button("Cancel", variant="light"))
footer.layout().addWidget(Button("Submit", color="primary"))
card.add_footer(footer)
```

### 装配 API

| 方法                    | 参数         | 说明                                      |
| ----------------------- | ------------ | ----------------------------------------- |
| `add_header(header)`    | `CardHeader` | 追加 header 插槽                          |
| `add_body(body)`        | `CardBody`   | 追加 body 插槽                            |
| `add_footer(footer)`    | `CardFooter` | 追加 footer 插槽                          |
| `add_divider()`         | —            | 追加水平分割线，返回 `Divider` 实例       |
| `insert_divider(index)` | `int`        | 在指定位置插入分割线，返回 `Divider` 实例 |

> `add_*` 按调用顺序追加到内部 layout 末尾。用户调用顺序就是视觉顺序，**不会**按 header → body → footer 的固定顺序自动排列。

---

## 交互效果

### 悬停 (Hoverable)

```python
card = Card(is_hoverable=True)
```

鼠标悬停时背景色 300ms 平滑过渡：

- 亮色：`#ffffff` → `default-100`
- 暗色：`default-900` → `default-800`

由 `QPropertyAnimation` 驱动 `hover_progress`，每帧 `_lerp_color` 插值刷新 QSS。

### 按压 (Pressable)

```python
card = Card(is_pressable=True)
card.pressed.connect(lambda: print("Card pressed!"))
```

- **水波纹**：点击位置扩散（`RippleOverlay`）
- **缩放动画**：按下 97%、松开复位（`PressScaleEffect`，对齐 HeroUI 的 `scale-[0.97]`）
- **手形光标**
- **`pressed` 信号**：鼠标松开且仍在 Card 范围内时触发

### 禁用 (Disabled)

```python
card = Card(is_disabled=True)
```

- 整体透明度 50%
- 禁止图标光标
- 不响应任何交互

### 模糊 (Blurred)

```python
# 整卡半透明
card = Card(is_blurred=True)

# 仅 footer 半透明（带上边分隔线）
card = Card(is_footer_blurred=True)
```

Qt QSS 不支持 `backdrop-filter`，改用半透明背景色模拟磨砂玻璃效果——需要配合渐变/图片父背景才能看出效果。

| 状态  | 亮色 alpha | 暗色 alpha |
| ----- | ---------- | ---------- |
| 正常  | 45%        | 20%        |
| hover | 55%        | 30%        |

---

## 信号

| 信号      | 参数 | 说明                                        |
| --------- | ---- | ------------------------------------------- |
| `pressed` | 无   | 仅 `is_pressable=True` 时，鼠标点击松开触发 |

---

## 动态 API

创建后可以随时切换属性，样式自动刷新：

```python
card = Card()

card.set_shadow("lg")
card.set_radius("sm")
card.set_theme("dark")
card.set_is_hoverable(True)
card.set_is_pressable(True)
card.set_is_disabled(False)
card.set_is_blurred(True)
card.set_is_footer_blurred(True)
card.set_full_width(True)
```

| 方法                             | 参数   | 说明             |
| -------------------------------- | ------ | ---------------- |
| `set_shadow(shadow)`             | `str`  | 切换阴影级别     |
| `set_radius(radius)`             | `str`  | 切换圆角         |
| `set_theme(theme)`               | `str`  | 切换主题         |
| `set_is_hoverable(hoverable)`    | `bool` | 切换悬停效果     |
| `set_is_pressable(pressable)`    | `bool` | 切换按压效果     |
| `set_is_disabled(disabled)`      | `bool` | 切换禁用状态     |
| `set_is_blurred(blurred)`        | `bool` | 切换背景模糊     |
| `set_is_footer_blurred(blurred)` | `bool` | 切换 footer 模糊 |
| `set_full_width(full)`           | `bool` | 切换水平撑满     |

### 访问器

| 方法       | 返回类型             | 说明               |
| ---------- | -------------------- | ------------------ |
| `header()` | `CardHeader \| None` | 获取 header 子组件 |
| `body()`   | `CardBody \| None`   | 获取 body 子组件   |
| `footer()` | `CardFooter \| None` | 获取 footer 子组件 |

---

## 主题模式

| 主题    | 背景色 (正常)             | 边框                    |
| ------- | ------------------------- | ----------------------- |
| `light` | `#ffffff`                 | 无                      |
| `dark`  | `default-900` (`#18181b`) | `1px solid default-800` |

---

## 继承关系

```
QWidget
  ├── Card           (外壳：paintEvent 自绘阴影 + 尺寸 setter 代理)
  │     └── _content (内层：QSS 背景、QPropertyAnimation hover、装配槽位)
  ├── CardHeader
  ├── CardBody
  └── CardFooter
```

`Card` 对外就是一个普通 `QWidget`，但内部使用**外壳 + 内层 `_content` 双层结构**：

- 外壳负责 `paintEvent` 自绘阴影；
- 内层 `_content` 承载 QSS 背景、圆角、边框、`hover_progress` 动画、以及全部装配槽位；
- 所有尺寸 setter 被代理到 `_content`，外壳自动向外扩出阴影空间。

这样做是为了避免 `QGraphicsDropShadowEffect` 离屏渲染和子控件自带 `QGraphicsEffect`（如 Button 的按压缩放）嵌套冲突。

---

## 完整示例：带表单的登录卡片

```python
import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtGui import QFont
from hero_side_ui import Card, CardHeader, CardBody, CardFooter, Button, Input

app = QApplication(sys.argv)
window = QWidget()
layout = QVBoxLayout(window)
layout.setContentsMargins(24, 24, 24, 24)

card = Card(shadow="md", radius="lg")
card.setFixedWidth(360)

# Header
header = CardHeader()
col = QVBoxLayout(); col.setSpacing(2); col.setContentsMargins(0, 0, 0, 0)
title = QLabel("Welcome back"); title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
subtitle = QLabel("Log in to your account to continue.")
subtitle.setStyleSheet("color: #71717a; font-size: 13px;")
col.addWidget(title); col.addWidget(subtitle)
header.layout().addLayout(col)
card.add_header(header)

card.add_divider()

# Body
body = CardBody()
body.layout().setSpacing(14)
email = Input(label="Email", placeholder="you@example.com",
              variant="bordered", color="primary",
              is_required=True, is_clearable=True)
password = Input(label="Password", placeholder="Enter your password",
                 variant="bordered", color="primary",
                 is_required=True, end_content="heroicons--eye-slash-solid")
password.line_edit.setEchoMode(password.line_edit.EchoMode.Password)
body.layout().addWidget(email)
body.layout().addWidget(password)

extras = QHBoxLayout()
remember = QLabel("Remember me"); remember.setStyleSheet("color:#52525b; font-size:13px;")
forgot = Button("Forgot password?", color="primary", variant="light", size="sm")
extras.addWidget(remember); extras.addStretch(); extras.addWidget(forgot)
body.layout().addLayout(extras)

card.add_body(body)

card.add_divider()

# Footer
footer = CardFooter()
no_account = QLabel("No account?"); no_account.setStyleSheet("color:#71717a; font-size:13px;")
signup = Button("Sign up", color="primary", variant="light", size="sm")
footer.layout().addWidget(no_account)
footer.layout().addWidget(signup)
footer.layout().addStretch()
footer.layout().addWidget(Button("Cancel", color="default", variant="light", size="sm"))
footer.layout().addWidget(Button("Sign in", color="primary", variant="solid", size="sm"))
card.add_footer(footer)

layout.addWidget(card)
layout.addStretch()

window.show()
sys.exit(app.exec())
```

---

## 示例文件

查看 [examples/card/](../examples/card/)：

- **[light_mode.py](../examples/card/light_mode.py)** — 亮色模式（含登录表单、Shadow/Radius 变体、Hoverable/Pressable、Blurred 等）
- **[dark_mode.py](../examples/card/dark_mode.py)** — 暗色模式
