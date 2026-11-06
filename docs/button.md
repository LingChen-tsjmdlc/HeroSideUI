# Button 按钮

基于 [HeroUI v2](https://heroui.com/) 设计风格的按钮组件，继承自 `QPushButton`，保持完整的 Qt 原生 API。

内置水波纹点击动画和按压缩放效果。

## 导入

```python
from hero_side_ui import Button
```

## 基本用法

```python
# 最简用法 — 默认 primary + solid
btn = Button("Click me")

# 指定颜色和变体
btn = Button("Submit", color="success", variant="solid")

# 暗色模式
btn = Button("Dark", color="primary", variant="flat", theme="dark")
```

---

## 构造参数

| 参数             | 类型                    | 默认值      | 说明                                                              |
| ---------------- | ----------------------- | ----------- | ----------------------------------------------------------------- |
| `text`           | `str`                   | `""`        | 按钮文字                                                          |
| `color`          | `str`                   | `"primary"` | 颜色主题，见下方 [color 可选值](#color-可选值)                    |
| `variant`        | `str`                   | `"solid"`   | 样式变体，见下方 [variant 可选值](#variant-可选值)                |
| `size`           | `str`                   | `"md"`      | 尺寸，见下方 [size 可选值](#size-可选值)                          |
| `radius`         | `str \| None`           | `None`      | 圆角，`None` 时跟随尺寸默认值。见 [radius 可选值](#radius-可选值) |
| `is_disabled`    | `bool`                  | `False`     | 禁用状态，禁用后样式变灰且不响应交互                              |
| `full_width`     | `bool`                  | `False`     | 是否撑满父容器宽度（`QSizePolicy.Expanding`）                     |
| `icon_only`      | `bool`                  | `False`     | 纯图标模式：锁成正方形，详见 [icon_only 模式](#icon_only-模式)    |
| `icon`           | `str \| None`           | `None`      | 内置图标名或 SVG 路径，颜色随变体/主题/hover 自动适配             |
| `icon_size`      | `int \| None`           | `None`      | 显式指定 icon 渲染尺寸（px）                                      |
| `icon_color`     | `str \| QColor \| None` | `None`      | 显式指定 icon 颜色（覆盖自动配色）                                |
| `theme`          | `str`                   | `"auto"`    | 主题模式：`"auto"` 跟随 ThemeProvider / `"light"` / `"dark"`      |
| `parent`         | `QObject \| None`       | `None`      | Qt 父对象                                                         |
| `disable_ripple` | `bool`                  | `False`     | 设为 `True` 关闭水波纹效果                                        |

---

## color 可选值

6 种语义颜色，每种颜色有 50-900 共 10 个色阶（来自 HeroUI v2 官方色板）。

| 值          | 色系          | 说明                 | 亮色 solid 示例色 |
| ----------- | ------------- | -------------------- | ----------------- |
| `default`   | 灰色 (zinc)   | 中性色，适合次要操作 | `#71717a`         |
| `primary`   | 蓝色 (blue)   | 主色调，适合主要操作 | `#006FEE`         |
| `secondary` | 紫色 (purple) | 辅助色               | `#7828c8`         |
| `success`   | 绿色 (green)  | 成功/确认            | `#17c964`         |
| `warning`   | 黄色 (yellow) | 警告（文字为黑色）   | `#f5a524`         |
| `danger`    | 红色 (red)    | 危险/删除            | `#f31260`         |

> **暗色模式差异**: `default` 颜色在暗色模式下 solid 底色更深（`#3f3f46`），文字为中灰色而非纯白。

---

## variant 可选值

6 种样式变体，控制按钮的填充、边框、背景透明度。

| 值         | 说明                     | 亮色表现            | 暗色差异                   |
| ---------- | ------------------------ | ------------------- | -------------------------- |
| `solid`    | 实心填充                 | 主色底 + 白字       | 无变化                     |
| `bordered` | 边框描边，背景透明       | 主色边框 + 主色字   | 文字更亮(300色阶)          |
| `flat`     | 半透明背景填充           | 主色15%透明度底     | 文字更亮，背景20%透明度    |
| `light`    | 全透明，悬停显色         | 透明底 + 主色字     | 文字更亮                   |
| `faded`    | 灰底 + 灰边框            | 浅灰底(#f4f4f5)     | 深灰底(#27272a) + 深灰边框 |
| `ghost`    | 边框描边，悬停时反转填充 | 透明底 → hover 填充 | 文字更亮                   |

### 悬停 (hover) 行为

所有变体在 hover 时都有视觉反馈：

- `solid`: 底色加深一档 (500→600)
- `bordered`/`flat`: 背景透明度增加
- `light`: 出现淡色背景
- `faded`: 底色和边框各加深一档
- `ghost`: 从透明变为实心填充

---

## size 可选值

3 种尺寸，同时兼容长名称（`small`/`medium`/`large`）。

| 值   | 别名     | 字号 | 字重 | 内边距    | 最小宽度 |
| ---- | -------- | ---- | ---- | --------- | -------- |
| `sm` | `small`  | 13px | 500  | 6px 12px  | 36px     |
| `md` | `medium` | 16px | 500  | 10px 16px | 52px     |
| `lg` | `large`  | 19px | 600  | 14px 20px | 66px     |

> 每种尺寸有自己的默认圆角：sm→sm(4px), md→md(8px), lg→lg(14px)。

---

## radius 可选值

5 种圆角等级。不设置 `radius` 参数时跟随 `size` 的默认圆角。

| 值     | 别名     | 像素 | 说明                                      |
| ------ | -------- | ---- | ----------------------------------------- |
| `none` | —        | 0px  | 直角                                      |
| `sm`   | `small`  | 4px  | 小圆角                                    |
| `md`   | `medium` | 8px  | 中圆角（默认）                            |
| `lg`   | `large`  | 14px | 大圆角                                    |
| `full` | —        | 动态 | 胶囊形（高度÷2），额外增加 8px 水平内边距 |

---

## icon_only 模式

`icon_only=True` 时按钮锁成正方形（边长 = 尺寸高度 + 2×纵向 padding，sm 为 30、md 为 46），适合纯图标按钮（工具栏、rail、输入框内嵌按钮）。

```python
btn = Button(icon_only=True, variant="flat")          # 自动边长（sm → 30x30）
btn.set_icon_only_side(36)                            # 显式锁定边长
btn.setIcon(QIcon("my.png"))                          # 传 QIcon = 自己管颜色
btn.set_icon("heroicons--eye-solid")                  # 传字符串 = 自动配色
btn.set_icon_color("#d4af37")                         # 覆盖自动配色
btn.set_icon_size(20)                                 # 覆盖 icon 渲染尺寸
```

### 尺寸规则（重要）

Button 的几何（sizePolicy / 固定尺寸）与视觉（QSS / 字体）是拆开维护的：

- `set_color` / `set_variant` / `set_theme` / `set_radius` 只重刷视觉，**不会碰任何几何**——构造后用 `setFixedSize` 做的外部定制对这四个 setter 天然安全
- `set_size` / `set_icon_only` / `set_icon_only_side` 会重新应用几何（size 影响 icon_only 边长），外部固定尺寸会被覆盖
- `icon_only` 模式下仍推荐用 `set_icon_only_side(side)` 锁边长——它是持久 override，样式重建永远尊重它

### 方形保证

QSS 盒模型属性会覆盖 `setFixedSize` 的显式最小值（实测 minimumWidth 从 46 掉到 12），因此 icon_only 模式下 `_build_qss` 会直接输出四向 `min/max-width/height`（content-box 口径：side − 2×padding，带边框变体再减 2×border），保证任何布局挤压下按钮都是正方形。边长由 `_resolve_icon_only_side()` 统一解析（外部 override 优先），几何、QSS、icon 尺寸三处同源。

---

## 设计保证（原「已知缺陷」，已全部修复）

以下是实战踩坑后落实的三项设计保证：

### 1. 外部几何定制不会被样式 setter 冲掉

几何（sizePolicy / 固定尺寸）与视觉（QSS / 字体）拆分为 `_apply_geometry()` 和 `_apply_styles()`：
`set_color` / `set_variant` / `set_theme` / `set_radius` 只重跑视觉，构造后用 `setFixedSize`
做的外部定制对它们天然安全。只有 `set_size` / `set_icon_only` / `set_icon_only_side`
会重新应用几何。

### 2. icon_only 正方形由 QSS 四向约束内置保证

icon_only 模式下 `_build_qss` 直接输出四向 `min/max-width/height`（content-box 口径），
不依赖使用方追加；边长统一由 `_resolve_icon_only_side()` 解析，几何 / QSS / icon 尺寸同源。

### 3. 构造签名严格校验未知参数

`disable_ripple` 是显式构造参数，构造签名不含 `**kwargs`——传错参数名（如
`is_icon_only=True`）会直接抛 `TypeError`，而不是静默不生效。

---

## 主题模式

通过 `theme` 参数控制亮色/暗色模式。

```python
# auto（构造默认值）：跟随 ThemeProvider 全局主题
btn_auto = Button("Auto", color="primary", variant="flat")

# 显式固定
btn_light = Button("Light", color="primary", variant="flat", theme="light")
btn_dark = Button("Dark", color="primary", variant="flat", theme="dark")
```

暗色模式下的主要差异：

- **文字颜色**: 使用更浅的色阶 (300/200)，确保在深色背景上可读
- **flat/light 背景**: 透明度稍高 (0.2 vs 0.15)
- **faded**: 灰底从浅灰改为深灰
- **disabled**: 背景改为深色半透明
- **default solid**: 前景改为中灰，不再使用纯白

---

## 动画效果

### 水波纹 (Ripple)

点击时从鼠标位置扩散的半透明圆形动画，仿照 HeroUI / Material Design 的 ripple 效果。

- **solid 变体**: 白色水波纹（warning/亮色default 用黑色）
- **其他变体**: 使用对应主色
- 动画时长: 500-900ms，`OutQuad` 缓动
- 可通过 `disable_ripple=True` 关闭

### 按压缩放 (Press Scale)

仿照 HeroUI 的 `scale-[0.97]` 效果：

- **按下**: 80ms 缩小到 97%
- **松开**: 150ms 恢复到 100%
- 缓动: `OutCubic`

---

## 动态方法

创建后可以随时切换各项属性，自动刷新样式：

```python
btn = Button("Click me", color="primary")

btn.set_color("danger")       # 切换颜色
btn.set_variant("bordered")   # 切换变体
btn.set_size("lg")            # 切换尺寸
btn.set_radius("full")        # 切换圆角
btn.set_theme("dark")         # 切换主题
```

| 方法                   | 参数  | 说明            |
| ---------------------- | ----- | --------------- |
| `set_color(color)`     | `str` | 切换颜色主题    |
| `set_variant(variant)` | `str` | 切换样式变体    |
| `set_size(size)`       | `str` | 切换尺寸        |
| `set_radius(radius)`   | `str` | 切换圆角        |
| `set_theme(theme)`     | `str` | 切换亮/暗色主题 |

---

## 继承关系

```
QPushButton
  └── Button
```

Button 继承自 `QPushButton`，所有 Qt 原生方法均可正常使用：

```python
btn = Button("Click me", color="primary")

# Qt 原生 API 正常使用
btn.clicked.connect(lambda: print("clicked!"))
btn.setToolTip("这是一个按钮")
btn.setIcon(QIcon("icon.png"))
btn.setShortcut("Ctrl+S")
```

---

## 完整示例

```python
import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from hero_side_ui import Button

app = QApplication(sys.argv)

window = QWidget()
layout = QVBoxLayout(window)

# 各种颜色的 solid 按钮
for color in ["primary", "secondary", "success", "warning", "danger"]:
    layout.addWidget(Button(color.capitalize(), color=color))

# 不同变体
for variant in ["solid", "bordered", "flat", "light", "faded", "ghost"]:
    layout.addWidget(Button(variant.capitalize(), color="primary", variant=variant))

# 不同尺寸
for size in ["sm", "md", "lg"]:
    layout.addWidget(Button(f"Size {size}", color="primary", size=size))

# 禁用按钮
layout.addWidget(Button("Disabled", color="primary", is_disabled=True))

# 胶囊形按钮
layout.addWidget(Button("Capsule", color="success", radius="full"))

# 全宽按钮
layout.addWidget(Button("Full Width", color="danger", full_width=True))

window.show()
sys.exit(app.exec())
```

---

## 示例文件

查看 [examples/button/](../examples/button/) 目录：

- **[light_mode.py](../examples/button/light_mode.py)** — 亮色模式下所有变体/颜色/尺寸展示
- **[dark_mode.py](../examples/button/dark_mode.py)** — 暗色模式下所有变体/颜色/尺寸展示
