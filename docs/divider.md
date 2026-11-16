# Divider 分割线

基于 [HeroUI v2](https://heroui.com/) 设计风格的分割线组件，继承自 `QFrame`，保持完整的 Qt 原生 API。

## 导入

```python
from hero_side_ui import Divider
```

## 基本用法

```python
# 水平分割线（默认）
divider = Divider()

# 垂直分割线
divider = Divider(orientation="vertical")

# 暗色模式
divider = Divider(theme="dark")

# 自定义颜色
divider = Divider(color="#006FEE")
```

---

## 构造参数

| 参数          | 类型              | 默认值         | 说明                                              |
| ------------- | ----------------- | -------------- | ------------------------------------------------- |
| `orientation` | `str`             | `"horizontal"` | 方向：`"horizontal"` 水平 / `"vertical"` 垂直     |
| `theme`       | `str`             | `"light"`      | 主题模式：`"light"` 亮色 / `"dark"` 暗色          |
| `color`       | `str \| None`     | `None`         | 自定义颜色（十六进制），`None` 时跟随主题默认颜色 |
| `text`        | `str \| None`     | `None`         | 中间文字（仅水平方向生效，留空/None 则为纯线）    |
| `text_size`   | `int`             | `12`           | 中间文字字号（像素）                              |
| `parent`      | `QWidget \| None` | `None`         | Qt 父对象                                         |

---

## orientation 可选值

| 值           | 说明                                 |
| ------------ | ------------------------------------ |
| `horizontal` | 水平分割线，宽度 Expanding，高度 1px |
| `vertical`   | 垂直分割线，高度 Expanding，宽度 1px |

---

## 主题模式

| 主题    | 默认颜色                  |
| ------- | ------------------------- |
| `light` | `default-200` (`#e4e4e7`) |
| `dark`  | `default-700` (`#3f3f46`) |

---

## 动态方法

| 方法                      | 参数          | 说明                               |
| ------------------------- | ------------- | ---------------------------------- |
| `set_orientation(orient)` | `str`         | 切换方向                           |
| `set_theme(theme)`        | `str`         | 切换主题                           |
| `set_color(color)`        | `str \| None` | 设置自定义颜色，`None` 恢复默认    |
| `set_text(text)`          | `str \| None` | 设置中间文字，`None`/`""` 恢复纯线 |
| `set_text_size(size)`     | `int`         | 设置中间文字字号（像素）           |

### 访问器

| 方法          | 返回类型 | 说明         |
| ------------- | -------- | ------------ |
| `text()`      | `str`    | 当前中间文字 |
| `text_size()` | `int`    | 当前文字字号 |

---

## 带文字的水平分割线

水平方向且 `text` 非空时，Divider 会切换为**自绘模式**：中央显示文字，左右两段线条各画到文字边距为止。这是常用的 "OR 继续…" 分隔样式。

```python
# 最常见的 OR 分割线
divider = Divider(text="OR")

# 自定义字号
divider = Divider(text="Continue with Email", text_size=13)

# 暗色 + 中间文字
divider = Divider(text="或", theme="dark", text_size=14)
```

实现细节：

- Divider 的高度会自动 = `fontMetrics.height() + 8`，字号越大越高；
- 文字左右各留 8px `gap` 再接线条；
- 文字颜色跟随主题（亮色 `default-500`、暗色 `default-400`）；
- 线条颜色跟随 `color` 或主题默认；
- 垂直方向设置 `text` 会被**忽略**（仍是纯线），避免视觉混乱；
- 运行时 `set_text(None)` / `set_text("")` 可把自绘模式退回为原始 1px 纯线。

---

## 继承关系

```
QFrame
  └── Divider
```

Divider 继承自 `QFrame`，所有 Qt 原生方法均可正常使用。

---

## 在 Card 中使用

Divider 常与 Card 配合使用，在 header / body / footer 之间添加分割线：

```python
from hero_side_ui import Card, CardHeader, CardBody, CardFooter, Divider

card = Card(shadow="md", radius="lg")

header = CardHeader()
card.add_header(header)

card.add_divider()  # Card 内置方法，自动创建 Divider

body = CardBody()
card.add_body(body)

card.add_divider()

footer = CardFooter()
card.add_footer(footer)
```

---

## 已知设计限制与修复建议

### 1. 布局里的宽度（已修复，对齐官方 `w-full` / `h-full`）

官方 Divider 自带 `w-full`（水平）/ `h-full`（垂直），占父容器 100%。Qt 没有百分比，以前 Divider 没有首选长度，在布局里会塌成 0：

```python
layout.addWidget(divider, 0, Qt.AlignmentFlag.AlignHCenter)   # 以前：线消失
hbox.addWidget(divider); hbox.addStretch(1)                    # 以前：宽度 0
```

现在 `sizeHint` 沿长边给全库统一的建议长度 320（`themes/width.py` 的 `SUGGESTED_WIDTH`），所以这两种写法都能看到线（320）；放进竖排（水平线）或横排（垂直线）时仍然铺满。窄容器里照旧会被压窄，你设宽直接生效。

和官方的差别：横排加弹簧时水平线是 320，不是整行（Qt 里弹簧和它抢空间，没有"独占"）。想要整行，放进竖排或去掉弹簧。

---

## 示例文件

查看 [examples/divider/](../examples/divider/) 目录：

- **[light_mode.py](../examples/divider/light_mode.py)** — 亮色模式示例
- **[dark_mode.py](../examples/divider/dark_mode.py)** — 暗色模式示例
