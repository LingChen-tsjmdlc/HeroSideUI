# Progress / CircularProgress

基于 HeroUI v2 [progress](https://v2.heroui.com/docs/components/progress) 和 [circular-progress](https://v2.heroui.com/docs/components/circular-progress) 复刻的进度指示器。全 `QWidget` + `QPainter` 自绘，动画由 `QPropertyAnimation` 驱动。

## Progress（线性）

### 特性

- **6 种颜色**: default / primary / secondary / success / warning / danger
- **3 种尺寸**: sm（4px track）· md（12px，默认）· lg（20px）
- **3 种圆角**: `none` / `sm` / **`full`**（默认，胶囊形）
- **is_striped**: indicator 叠加 45° 白色半透明斜纹
- **is_indeterminate**: 40% 宽滑块左右来回循环（1.5s，InOutSine）
- **is_disabled**: 50% 半透明
- **disable_animation**: 关闭 500ms 过渡
- **label / value_label**: 顶部 labelWrapper 的左/右两栏
- 支持自定义 `value_label_formatter`，默认显示百分比

### 用法

```python
from hero_side_ui import Progress

# 简单
p = Progress(value=65, label="Loading...", show_value_label=True)

# 斜纹 + 自定义 formatter
p2 = Progress(
    value=3, min_value=0, max_value=10,
    label="Files", show_value_label=True,
    is_striped=True, color="success",
    value_label_formatter=lambda v, mn, mx: f"{int(v)}/{int(mx)}",
)

# 不确定态
p3 = Progress(is_indeterminate=True, label="Fetching...", color="secondary")
```

### 参数

| 参数                      | 类型                                                         | 默认值      | 说明               |
| ------------------------- | ------------------------------------------------------------ | ----------- | ------------------ |
| `value`                   | `float`                                                      | `0`         | 当前进度           |
| `min_value` / `max_value` | `float`                                                      | `0` / `100` | 进度范围           |
| `label`                   | `str`                                                        | `""`        | 顶部左边文字       |
| `show_value_label`        | `bool`                                                       | `False`     | 是否显示右侧进度值 |
| `value_label_formatter`   | `Callable[(value, min, max), str]`                           | `None`      | 自定义值显示格式   |
| `color`                   | `default / primary / secondary / success / warning / danger` | `primary`   | indicator 颜色     |
| `size`                    | `sm / md / lg`                                               | `md`        | track 高度         |
| `radius`                  | `none / sm / full`                                           | `full`      | 圆角               |
| `is_striped`              | `bool`                                                       | `False`     | 斜纹填充           |
| `is_indeterminate`        | `bool`                                                       | `False`     | 未定态滚动         |
| `is_disabled`             | `bool`                                                       | `False`     | 禁用               |
| `disable_animation`       | `bool`                                                       | `False`     | 关闭过渡动画       |
| `theme`                   | `light / dark`                                               | `light`     | 主题               |

### 动态 API

`set_value` / `set_range` / `set_color` / `set_size` / `set_radius` / `set_theme` / `set_is_striped` / `set_is_indeterminate` / `set_is_disabled` / `set_label` / `set_show_value_label`

## CircularProgress（圆形）

### 特性

- **6 种颜色** 同 Progress
- **3 种尺寸**: sm（32×32 + stroke 3.5）/ md（44×44 + stroke 5，默认）/ lg（56×56 + stroke 7）— 环粗细随直径同步放大
- **is_indeterminate**: 30% 弧持续旋转（900ms 一圈，Linear）
- **stroke_width**: 可覆盖，默认由 size 决定
- **show_value_label** + 中心 value 文字
- **label**: 下方文字

### 用法

```python
from hero_side_ui import CircularProgress

cp = CircularProgress(
    value=75,
    color="success",
    size="lg",
    show_value_label=True,
    label="Upload",
)

spinner = CircularProgress(is_indeterminate=True, size="md", color="primary")
```

### 参数

| 参数                                                               | 类型            | 默认值          |
| ------------------------------------------------------------------ | --------------- | --------------- |
| `value` / `min_value` / `max_value`                                | 同 Progress     | `0/0/100`       |
| `label` / `show_value_label` / `value_label_formatter`             | 同 Progress     | `""/False/None` |
| `color`                                                            | 同 Progress     | `primary`       |
| `size`                                                             | `sm / md / lg`  | `md`            |
| `stroke_width`                                                     | `float \| None` | `None`          |
| `is_indeterminate` / `is_disabled` / `disable_animation` / `theme` | 同 Progress     | —               |

## 便捷别名：Spinner

> **已迁移**：Spinner 现在是独立组件，提供 `default / simple / gradient / spinner / wave / dots` 6 种 variant，详见 [`docs/spinner.md`](./spinner.md)。
>
> 仍想要"环形 indeterminate"的视觉？直接用 `CircularProgress(is_indeterminate=True)` 即可。

## 与 HeroUI 的差异

- Tailwind 的 `bg-stripe-gradient-*` 通过 QPainter 用 45° 平行四边形 + 白色 α 叠加近似
- `animate-indeterminate-bar` / `animate-spinner-ease-spin` 改用 `QPropertyAnimation` 循环
- track 背景用 default-300/50（light）或 default-600/50（dark）近似 `bg-default-300/50`
