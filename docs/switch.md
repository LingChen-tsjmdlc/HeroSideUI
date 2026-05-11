# Switch

基于 HeroUI v2 [switch](https://v2.heroui.com/docs/components/switch) 复刻的开关组件。继承 `QAbstractButton`（`checkable=True`），保留原生 API（`toggled` / `clicked` / `setChecked` / `isChecked`），外观全部通过 `paintEvent` 自绘，以完美对齐 HeroUI 的胶囊滑块视觉。

## 特性

- **6 种颜色**：`default` · `primary` · `secondary` · `success` · `warning` · `danger`
- **3 种尺寸**：`sm`（40×24 wrapper + thumb 16）· `md`（48×28 + thumb 20，默认）· `lg`（56×32 + thumb 24）
- **isSelected / isDisabled / isReadOnly**：三种核心状态
- **startContent / endContent**：wrapper 内左右两端的图标（SVG 字符串）
  - `startContent` = "开"时图标（选中时显现，`opacity 0→1` + `scale 0.5→1`）
  - `endContent` = "关"时图标（未选中显现，选中时 `opacity 1→0` + `translate-x 0→12px` 淡出）
- **thumbIcon**：跟随 thumb 一起移动的图标
- **label**：放在 wrapper 右侧，`ms-2 = 8px` 间距，自动继承主题前景色
- **theme**：`auto` / `light` / `dark`（auto 时自动注册到 `ThemeProvider`，跟随全局切换）
- **按压反馈**：thumb 横向拉长（`w-4 → w-5` 等），视觉更带感
- **动画**：`250ms` thumb 位移与背景色过渡；可用 `disable_animation=True` 一键关闭

## 快速开始

```python
from hero_side_ui import Switch

switch = Switch("Auto sync", is_selected=True, color="success")
switch.toggled.connect(lambda on: print("on?", on))
# 或使用语义更明确的 selected_changed 信号
switch.selected_changed.connect(lambda on: print("on?", on))
```

## 参数

| 参数                | 类型                                                                          | 默认值      | 说明                                                             |
| ------------------- | ----------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------- |
| `text`              | `str`                                                                         | `""`        | 右侧 label 文字                                                  |
| `is_selected`       | `bool`                                                                        | `False`     | 初始选中（等同 `setChecked(True)`）                              |
| `color`             | `"default" \| "primary" \| "secondary" \| "success" \| "warning" \| "danger"` | `"primary"` | 选中态 wrapper 背景色                                            |
| `size`              | `"sm" \| "md" \| "lg"`                                                        | `"md"`      | 组件尺寸                                                         |
| `is_disabled`       | `bool`                                                                        | `False`     | 禁用（半透明 + 不响应鼠标 + 不可切换）                           |
| `is_read_only`      | `bool`                                                                        | `False`     | 只读（视觉不变暗，但鼠标点击/键盘操作都不切换 `checked`）        |
| `disable_animation` | `bool`                                                                        | `False`     | 关闭所有过渡动画（位移 / bg 颜色 / 按压拉长）                    |
| `theme`             | `"auto" \| "light" \| "dark"`                                                 | `"auto"`    | `auto` 跟随全局 `ThemeProvider`                                  |
| `start_content`     | `str \| None`                                                                 | `None`      | 开时图标 SVG（原生 `<svg>` 字符串，`currentColor` 会被自动替换） |
| `end_content`       | `str \| None`                                                                 | `None`      | 关时图标 SVG                                                     |
| `thumb_icon`        | `str \| None`                                                                 | `None`      | thumb 内部图标 SVG（随 thumb 移动）                              |

## 信号

- `toggled(bool)` / `clicked(bool)` / `pressed()` / `released()`：所有 `QAbstractButton` 原生信号。
- `selected_changed(bool)`：与 `toggled` 等价的语义别名，对齐 HeroUI 的 `onValueChange`。

## 动态 API

```python
switch.set_color("success")
switch.set_size("lg")
switch.set_is_disabled(True)
switch.set_is_read_only(True)
switch.set_disable_animation(False)
switch.set_start_content(sun_svg)
switch.set_end_content(moon_svg)
switch.set_thumb_icon(check_svg)
switch.set_theme("dark")         # 或 "light" / "auto"

# 选中状态
switch.setChecked(True)          # 原生
switch.set_is_selected(True)     # 别名
switch.is_selected()             # 别名 isChecked()
```

## 图标用法

`start_content` / `end_content` / `thumb_icon` 都直接接收 SVG 字符串。SVG 中所有 `currentColor` 会被组件在渲染时自动替换为合适的对比色（`startContent` 跟随前景对比色；`endContent` 使用 `default-600`；`thumbIcon` 使用黑色）。

```python
SUN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path fill="currentColor" d="..."/>
</svg>"""
MOON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path fill="currentColor" d="..."/>
</svg>"""

Switch(
    "日间 / 夜间",
    is_selected=True,
    color="primary",
    size="lg",
    start_content=SUN,
    end_content=MOON,
)
```

## 尺寸规格

| size | wrapper | thumb（静态 / 按压） | 选中位移 | 字号 |
| ---- | ------- | -------------------- | -------- | ---- |
| `sm` | 40×24   | 16 / 20              | 16px     | 13   |
| `md` | 48×28   | 20 / 24              | 20px     | 14   |
| `lg` | 56×32   | 24 / 28              | 24px     | 16   |

wrapper 圆角始终为胶囊（高度 ÷ 2），与 HeroUI 一致。

## 与 Checkbox / Button 的区别

- `Checkbox` 是方形、带 check 图标、在表单中单选多选；`Switch` 是胶囊滑块，通常用于"立即生效"的二态切换（开关类设置，比如 WiFi、飞行模式、暗色主题）。
- `Button` 是动作，`Switch` 是状态。

## 主题感知

`theme="auto"`（默认）下，组件会自动注册到 `ThemeProvider`，跟随全局亮暗切换；`light` / `dark` 则硬锁，不参与全局切换。详见 [ThemeProvider](./theme_provider.md) 与 [ThemeSwitcher](./theme_switcher.md)。
