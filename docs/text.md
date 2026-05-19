# Text 文字组件

主题感知的统一文字组件，继承自 `QLabel`。HeroSideUI 内部所有"次级文字色"决策都通过 `Text` 封装，让 demo / 用户代码不再写 `setStyleSheet("color: #...")`，主题切换时文字色自动跟随。

向后兼容：旧的语义化别名 `Title / Subtitle / Caption / Body` 仍然导出，全部基于新的 `Text` 实现。

## 导入

```python
from hero_side_ui import Text
# 也可继续用语义化别名：
from hero_side_ui import Title, Subtitle, Caption, Body
```

## 基本用法

```python
# 默认: md (14px) / normal / 跟随主题正文色 / theme="auto"
Text("Hello World")

# Tailwind 风格的 size + weight
Text("Big Headline", size="3xl", weight="bold")
Text("Subtle hint",  size="xs",  weight="light")

# HeroUI token 颜色
Text("Brand",        color="primary")          # primary-500
Text("Deep brand",   color="primary-700")
Text("Danger",       color="danger")
Text("Success 300",  color="success-300")

# HEX / RGBA / QColor
Text("Custom hex",   color="#FF8800")
Text("Hex w/ alpha", color="#FF880080")        # 带 alpha 8 位
Text("RGBA tuple",   color=(255, 0, 0, 200))
Text("CSS rgba",     color="rgba(0, 111, 238, 0.8)")

# 整体透明度 (与 color 自身 alpha 相乘)
Text("Half opaque",  color="primary", transparency=0.5)

# 硬锁主题，不受 ThemeProvider 切换影响
Text("Always dark",  theme="dark")
```

## 构造参数

| 参数           | 类型                                                     | 默认       | 说明                                                          |
| -------------- | -------------------------------------------------------- | ---------- | ------------------------------------------------------------- |
| `text`         | `str`                                                    | `""`       | 文字内容                                                      |
| `size`         | `str` (`xs`~`9xl`) / `int` / `float`                     | `"md"`     | 字号；接受 Tailwind token 或像素数值                          |
| `weight`       | `str` (`thin`~`black`) / `QFont.Weight` / `int` (1~1000) | `"normal"` | 字重；接受 Tailwind token 或 Qt weight                        |
| `color`        | `str` / `QColor` / `tuple` / `None`                      | `None`     | 文字颜色；`None` 跟随主题默认正文色。详见下文                 |
| `transparency` | `float` `0.0~1.0`                                        | `1.0`      | 整体透明度；与 color 自身 alpha 相乘                          |
| `theme`        | `"auto"` / `"light"` / `"dark"`                          | `"auto"`   | 主题模式；`auto` 自动跟随 `ThemeProvider`，硬锁不参与全局切换 |
| `parent`       | `QWidget \| None`                                        | `None`     | Qt 父对象                                                     |

### `size` 值表（参考 Tailwind `text-*`）

| token | 像素 | token | 像素 |
| ----- | ---: | ----- | ---: |
| `xs`  |   12 | `3xl` |   30 |
| `sm`  |   13 | `4xl` |   36 |
| `md`  |   14 | `5xl` |   48 |
| `lg`  |   16 | `6xl` |   60 |
| `xl`  |   18 | `7xl` |   72 |
| `2xl` |   24 | `8xl` |   96 |
|       |      | `9xl` |  128 |

也可以直接传整数像素：`Text("Custom", size=22)`。

### `weight` 值表（参考 Tailwind `font-*`）

| token        | Qt Weight | token       | Qt Weight |
| ------------ | --------: | ----------- | --------: |
| `thin`       |       100 | `medium`    |       500 |
| `extralight` |       200 | `semibold`  |       600 |
| `light`      |       300 | `bold`      |       700 |
| `normal`     |       400 | `extrabold` |       800 |
| `regular`    |       400 | `black`     |       900 |

也接受 `QFont.Weight.Bold`、`int` (1-1000)。

### `color` 解析规则

按以下顺序匹配，第一个命中的格式生效：

1. **HeroUI token**：`"primary"` / `"primary-500"` / `"default-300"` …
   - 不带数字时默认走 500 档；可用色阶 50/100/200/300/400/500/600/700/800/900。
   - 可用色名：`default`、`primary`、`secondary`、`success`、`warning`、`danger`、`neutral`。
2. **HEX**：`"#FF8800"` (6 位 RGB)，`"#80FF8800"` (Qt 的 8 位 hex 是 `#AARRGGBB` 格式)。
   - 如果想用 RGBA，更直观的写法是 tuple `(255, 136, 0, 200)` 或 `"rgba(...)"` 字符串。
3. **CSS rgb()/rgba()**：`"rgb(255, 0, 0)"`、`"rgba(0, 111, 238, 0.8)"`（alpha 0~1 浮点或 0~255 整数都接受）。
4. **元组**：`(r, g, b)` 或 `(r, g, b, a)`（a 为 0~255 整数）。
5. **QColor**：直接使用。

不传 / 传 `None` 时使用主题感知的默认正文色：

| 主题  | 默认色    | 来源          |
| ----- | --------- | ------------- |
| light | `#27272a` | `default-800` |
| dark  | `#e4e4e7` | `default-200` |

### `transparency`

整体透明度 0.0 ~ 1.0，会乘到最终颜色 alpha 上：

```python
Text("a", color="primary")                       # alpha = 1.0
Text("b", color="primary", transparency=0.5)     # alpha = 0.5
Text("c", color="rgba(255,0,0,0.8)", transparency=0.5)  # alpha = 0.4
```

## 鼠标框选高亮

`Text` 默认开启文本选择（`TextBrowserInteraction`）。鼠标框选时高亮底色根据主题自动适配，不会因为亮暗模式变化或自定义文字色而出现"看不清"的情况：

| 主题  | 选区底色                      | 选区文字色                             |
| ----- | ----------------------------- | -------------------------------------- |
| light | `primary-500` (#006FEE) ×0.22 | 原文字色；对比度不足时回退到 `#18181b` |
| dark  | `primary-500` (#006FEE) ×0.35 | 原文字色；对比度不足时回退到 `#FFFFFF` |

实现：每个 `Text` 实例独占一份 `QPalette`，仅设置 `Highlight` / `HighlightedText` 两个 role，不会污染父级 palette。

如需关闭选择交互：

```python
from PySide6.QtCore import Qt
t = Text("Read only")
t.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
```

## 动态 setter

| 方法                      | 说明                                          |
| ------------------------- | --------------------------------------------- |
| `set_size(size)`          | 切换字号（接受 token 或像素整数）             |
| `set_weight(weight)`      | 切换字重                                      |
| `set_color(color)`        | 切换文字色，传 `None` 恢复主题默认            |
| `set_transparency(value)` | 切换整体透明度                                |
| `set_theme(theme)`        | 切换主题模式：`"auto"` / `"light"` / `"dark"` |

## 只读访问器

| 属性         | 类型     | 说明                                     |
| ------------ | -------- | ---------------------------------------- |
| `text_color` | `QColor` | 当前实际渲染色（已叠加 transparency）    |
| `theme`      | `str`    | 当前实际生效的主题：`"light"` / `"dark"` |

## 与 `ThemeProvider` 配合

```python
from hero_side_ui import ThemeProvider, Text

# theme="auto"（默认）会自动注册到 provider，全局切换时自动刷新
t = Text("Hello", color="primary")

ThemeProvider.instance().toggle()
# t 的文字色 / 选区底色都会自动适配新主题
```

硬锁主题不参与全局切换：

```python
t_dark = Text("永远暗色", theme="dark")  # 不受 toggle 影响
```

## 向后兼容：语义化别名

下面三个组件都是 `Text` 的薄包装，提供更短的语义化 API。颜色 token 经过亮暗双向校准，**不传 color 时**自动跟随主题：

| 组件       | size | weight | 默认色（light / dark） | 适用场景             |
| ---------- | ---- | ------ | ---------------------- | -------------------- |
| `Title`    | 见下 | bold   | `#18181b` / `#fafafa`  | 主标题               |
| `Subtitle` | sm   | normal | `#71717a` / `#a1a1aa`  | 副标题、说明语       |
| `Caption`  | xs   | normal | `#a1a1aa` / `#71717a`  | 辅助提示，最低对比度 |
| `Body`     | md   | normal | `#27272a` / `#e4e4e7`  | 正文                 |

`Title` 还支持 `level` 参数：

| level | size token | 像素 |
| ----: | ---------- | ---: |
|     1 | `2xl`      |   24 |
|     2 | `xl`       |   18 |
|     3 | `lg`       |   16 |

```python
Title("Welcome back")                # level=1 → 24px Bold
Title("Section title", level=2)      # 18px Bold
Title("Card title",   level=3)       # 16px Bold

Subtitle("Log in to your account.")
Caption("Tip: click to toggle.")
Body("Make beautiful UIs without writing CSS.")
```

任何旧组件都可以无痛迁移到 `Text`，例如：

```python
# 旧：
Title("Hi", color="#006FEE")

# 等价新写法：
Text("Hi", size="2xl", weight="bold", color="primary")
```

## 完整示例

参见 [`examples/text/demo.py`](../examples/text/demo.py)：

- 全 13 档字号
- 全 9 档字重
- HeroUI 7 套语义色 × 10 色阶
- HEX / RGBA / 自定义色
- 透明度滑梯
- 主题感知与 hard-lock
- 选区高亮自动适配
