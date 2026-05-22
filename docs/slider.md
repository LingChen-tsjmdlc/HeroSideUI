# Slider

基于 HeroUI v2 [slider](https://v2.heroui.com/docs/components/slider) 复刻的滑块组件。全 `QWidget` + `QPainter` 自绘；支持单/双 thumb（range）、水平/垂直、marks、show_steps、键盘/滚轮/拖拽多种交互。

样式来源对齐 `packages/core/theme/src/components/slider.ts`，所有 size 数值（thumb/track/inner-dot/字号）通过 `themes/component_presets/slider.py` 的 `SLIDER_SIZES` token 注入。

## 特性

- **6 种颜色**: foreground · primary · secondary · success · warning · danger（`default` 等价于 `foreground`）
- **3 种尺寸**: sm（thumb 20 / track 4） · md（thumb 24 / track 12，默认） · lg（thumb 28 / track 28）
- **5 种圆角**: none · sm · md · lg · **full**（默认）—— thumb 与 inner-dot 圆角同步缩放
- **range 双 thumb**: `value=(lo, hi)` 自动启用，两 thumb 不会交叉
- **垂直方向**: `orientation="vertical"`（视觉上："下=min / 上=max"）
- **marks**: 轨道下/右侧的刻度文字（in-range 高亮，out-of-range 50% 透明）
- **show_steps**: 沿轨道绘制 step 吸附点
- **show_outline**: thumb 多一圈 ring（背景色）
- **hide_value / hide_thumb / disable_thumb_scale / disable_animation**
- **start_content / end_content**: 任意 `QWidget`（图标/按钮等），位于 track 两侧（水平布局下 start 在左 / end 在右；vertical 下按 HeroUI “下=min/上=max”设 start 在底 / end 在顶）
- **fill_offset**: filler 起点（默认 = `min_value`，可设 0 实现双向条）
- **show_tooltip**: 拖拽 thumb 时在上方显示当前值（复用 `Tooltip` 组件；range 双 thumb 各自一个）
- **自定义 `value_formatter`**: 接收 `float` 或 `(lo, hi)`，返回字符串
- **拖拽 inner-dot scale-80**: 按下时中心白点收缩 20%（对齐 HeroUI `data-[dragging=true]:after:scale-80`）
- **键盘交互**: `←/→` 或 `↑/↓` step 步进，`PageUp/Down` 10% range 跳，`Home/End` 跳到极值；range 模式下 `Tab` 切换焦点 thumb
- **滚轮**: 一格 = 1 step
- **track 点击跳转**: 点击轨道任一点直接跳到该位置（range 模式自动选择最近的 thumb）
- **主题**: light / dark / **auto**（订阅 `ThemeProvider`）
- **disabled**: 50% 半透明 + 不响应交互

## 用法

```python
from hero_side_ui import Slider

# 最简
s = Slider(value=40, label="Volume")

# 带值显示 + 自定义 formatter
s2 = Slider(
    value=65, min_value=0, max_value=100, step=5,
    color="primary", size="md",
    label="Brightness",
    value_formatter=lambda v: f"{int(v)}%",
)

# Range（双 thumb）
s3 = Slider(
    value=(20, 80), color="success",
    label="Price Range",
    value_formatter=lambda v: f"${int(v[0])} – ${int(v[1])}",
)

# Marks（吸附点 + 文字）
s4 = Slider(
    value=50, color="warning",
    marks=[
        {"value": 0,   "label": "0%"},
        {"value": 50,  "label": "50%"},
        {"value": 100, "label": "100%"},
    ],
)

# 离散步长 + show_steps
s5 = Slider(
    value=30, min_value=0, max_value=100, step=10,
    show_steps=True, color="secondary",
)

# 垂直方向
s6 = Slider(value=60, orientation="vertical", color="primary")
s6.setFixedHeight(220)

# 信号
s.value_changed.connect(lambda v: print("now:", v))
s.change_end.connect(lambda v: print("released:", v))   # 鼠标抬起/键盘抬起一次性发射
```

## 参数

| 参数                      | 类型                                                            | 默认值           | 说明                                                                              |
| ------------------------- | --------------------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------- |
| `value`                   | `float` 或 `(float, float)`                                     | `min_value`      | 当前值；元组自动启用 range 双 thumb                                               |
| `min_value` / `max_value` | `float`                                                         | `0` / `100`      | 取值范围（必须 `max > min`）                                                      |
| `step`                    | `float`                                                         | `1`              | 步长（必须 `> 0`，所有值都会按步长 snap）                                         |
| `label`                   | `str`                                                           | `""`             | 顶部左侧文字（vertical 时位于侧栏顶部）                                           |
| `color`                   | `foreground / primary / secondary / success / warning / danger` | `primary`        | filler & thumb 主体色                                                             |
| `size`                    | `sm / md / lg`                                                  | `md`             | thumb / track / 字号 一组配置                                                     |
| `radius`                  | `none / sm / md / lg / full`                                    | `full`           | thumb（及 inner-dot）圆角；full = 圆形                                            |
| `orientation`             | `horizontal / vertical`                                         | `horizontal`     | 朝向                                                                              |
| `is_disabled`             | `bool`                                                          | `False`          | 禁用 + 50% 半透明                                                                 |
| `hide_value`              | `bool`                                                          | `False`          | 隐藏顶部 value 文字                                                               |
| `hide_thumb`              | `bool`                                                          | `False`          | 隐藏 thumb（track 仍可点击）                                                      |
| `show_outline`            | `bool`                                                          | `False`          | thumb 外加 ring（背景色）                                                         |
| `disable_thumb_scale`     | `bool`                                                          | `False`          | 关闭"按下 inner-dot 缩到 80%"                                                     |
| `disable_animation`       | `bool`                                                          | `False`          | 关闭所有过渡（拖拽 scale 等）                                                     |
| `show_steps`              | `bool`                                                          | `False`          | 沿 track 画 step 吸附点                                                           |
| `marks`                   | `Sequence[float \| tuple \| dict]`                              | `None`           | 刻度：`{"value":N,"label":"text"}` 或 `(N, "text")`                               |
| `start_content`           | `QWidget`                                                       | `None`           | track 起始侧（水平=左，垂直=底，靠近 min）的任意 widget，典型是装饰 icon          |
| `end_content`             | `QWidget`                                                       | `None`           | track 结束侧（水平=右，垂直=顶，靠近 max）的任意 widget                           |
| `value_formatter`         | `Callable[[ValueT], str]`                                       | `None`           | 自定义顶部 value 文字格式                                                         |
| `fill_offset`             | `float`                                                         | `None`（=`min`） | filler 起点；设 `0` 可让正负值从 0 开始填充（双向条）                             |
| `show_tooltip`            | `bool`                                                          | `False`          | 拖拽 thumb 时在上方显示当前值（复用 `Tooltip`）                                   |
| `tooltip_props`           | `dict`                                                          | `None`           | 透传给底层 `Tooltip` 的额外参数（placement / color / size / offset / show_arrow） |
| `theme`                   | `auto / light / dark`                                           | `auto`           | 主题；auto 注册 `ThemeProvider`                                                   |

## 信号

| 信号            | 参数               | 触发时机                               |
| --------------- | ------------------ | -------------------------------------- |
| `value_changed` | `float` 或 `tuple` | 值变化时即发（拖拽过程持续发射）       |
| `change_end`    | `float` 或 `tuple` | 鼠标抬起 / 键盘抬起 / 滚轮单步结束发射 |
| `valueChanged`  | 同 `value_changed` | 兼容别名                               |

## 动态 API

`set_value` / `set_range` / `set_step` / `set_label` / `set_color` / `set_size` / `set_radius` / `set_orientation` / `set_is_disabled` / `set_hide_value` / `set_hide_thumb` / `set_show_outline` / `set_disable_thumb_scale` / `set_disable_animation` / `set_show_steps` / `set_marks` / `set_value_formatter` / `set_fill_offset` / `set_show_tooltip` / `set_start_content` / `set_end_content` / `set_theme`

## 与 HeroUI 的差异

- Tailwind `bg-default-300/50` 用 `HEROUI_COLORS["default"][300/600]` + `setAlphaF(0.5)` 近似
- HeroUI 的 `data-[dragging=true]:after:scale-80` 用 `QVariantAnimation` 在 inner-dot 边长上插值（120ms OutCubic）
- HeroUI 的 `ring-2 ring-background` 用一圈 background 色 rounded-rect 模拟（`_RING_WIDTH=2`、`_RING_GAP=2`）
- HeroUI `border-x-transparent` 的"track 两端不画圆角"细节用 `track_radius = thickness / 2` 简化处理（视觉等效）
- HeroUI 的 `flex-col-reverse` 垂直布局通过组件内坐标翻转直接实现（"下=min / 上=max"）

## 设计 Token

| token           | 位置                                 | 备注                                   |
| --------------- | ------------------------------------ | -------------------------------------- |
| `SLIDER_SIZES`  | `themes/component_presets/slider.py` | sm/md/lg 的 thumb/track/字号一组数值   |
| `HEROUI_COLORS` | `themes/colors.py`                   | 颜色色阶 50–900                        |
| `RADIUS`        | `themes/radius.py`                   | sm=4 / md=8 / lg=14（用于 thumb 圆角） |
