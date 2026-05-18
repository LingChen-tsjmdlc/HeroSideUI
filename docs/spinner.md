# Spinner

基于 HeroUI v2 [spinner](https://v2.heroui.com/docs/components/spinner) 1:1 复刻的 loading 指示器。提供 6 种视觉风格（variant），全部由 `QPainter` 自绘 + `QPropertyAnimation` 循环驱动，无需任何外部 SVG/iconify 资源。

## 特性

- **6 种 variant**: `default` / `simple` / `gradient` / `spinner` / `wave` / `dots`
- **6 种 color**: `default` / `primary` / `secondary` / `success` / `warning` / `danger`
- **3 种 size**: `sm` (≈20×20 / 24×24 px) · `md` (32×32 / 32×32 px，默认) · `lg` (40×40 / 48×48 px)
- **label**: 可选下方文字，**自动跟随 spinner 主色**（铁律 1：组件自管，不让用户决策）
- **theme="auto"** 主题感知，自动跟随 `ThemeProvider` 切换亮暗模式
- 永远在动画中（loading 指示器没有 indeterminate 概念）

## 用法

```python
from hero_side_ui import Spinner

Spinner()                                              # 默认 default / primary / md
Spinner(variant="dots", color="success")
Spinner(variant="spinner", size="lg", label="Loading...")
Spinner(variant="gradient", color="secondary", label="Please wait")
```

## Variants

| Variant    | 说明                                                                             | DOM 结构（HeroUI 官方）               |
| ---------- | -------------------------------------------------------------------------------- | ------------------------------------- |
| `default`  | 双圆弧：底边 90° solid 弧 + 半透明虚线 90° 弧，分别 ease / linear 旋转           | 2× `<i>` 圆环，三边透明只剩 b         |
| `simple`   | 整圈 25% 透明 + 1/4 实心扇形（75% 透明），整体 1s linear 旋转                    | 1× `<svg>` (circle + path)            |
| `gradient` | 圆环跑径向 conical 渐变（透明 → 主色），1s linear 旋转                           | 1× `<i>` mask 出圆环                  |
| `spinner`  | 12 根时钟刻度，每根 fade-out 1.2s linear，相位差 0.1s（iOS UIActivityIndicator） | 12× `<i>` rotate(30deg×i) + translate |
| `wave`     | 3 个圆点上下波动，sway 750ms ease，相位差 250ms                                  | 3× `<i>`                              |
| `dots`     | 3 个圆点闪烁，blink 1.4s 线性，相位差 200ms（0.2 → 1 → 0.2）                     | 3× `<i>`                              |

> Qt 复刻：所有 variant 都是单个 `Spinner` widget 内部 `QPainter` 自绘，每根棒/每个 dot 不再是单独 widget。`default` 用了两条 `PhaseDriver`（一条 ease、一条 linear），其余 variant 共用一条 phase 驱动器。

## 参数

| 参数      | 类型 / 取值                                                  | 默认值    |
| --------- | ------------------------------------------------------------ | --------- |
| `variant` | `default / simple / gradient / spinner / wave / dots`        | `default` |
| `color`   | `default / primary / secondary / success / warning / danger` | `primary` |
| `size`    | `sm / md / lg`                                               | `md`      |
| `label`   | `str`，可选下方文字（颜色自动跟随 `color`）                  | `""`      |
| `theme`   | `auto / light / dark`                                        | `auto`    |
| `parent`  | `QWidget`                                                    | `None`    |

## 公开 API

```python
sp.set_variant("dots")            # 切 variant，自动停启 driver_b
sp.set_color("success")           # spinner + label 一起换色
sp.set_size("lg")
sp.set_label("Uploading...")
sp.set_theme("auto")              # 或 "dark" / "light"

sp.variant() / sp.color() / sp.size() / sp.label()
```

## 与 HeroUI 的差异

- HeroUI CSS 动画（`spinner-ease-spin / sway / blink / fade-out`）改用 `QPropertyAnimation` 线性 phase 0→1 + 各 variant 内部相位换算。
- `simple` 没有用 SVG，而是直接 `QPainter` 画一个圆环 + `arcTo` 拼出的 1/4 环段（视觉等价）。
- `gradient` 用 `QConicalGradient` + 圆环裁剪复刻 mask 效果，避免 mask shader。
- 颜色完全沿用 `HEROUI_COLORS[*][500]`，`default` 走 `default-400`，`current` 取主题前景色。
