# Popover

基于 HeroUI v2 [popover](https://v2.heroui.com/docs/components/popover) 复刻的浮层组件。和 `Card` 一样是**插槽容器**，里面什么都能放（Input、Button、Checkbox、CircularProgress……）。

## 特性

- **顶层弹出**：`Popover` 是独立的 `QWidget`（`Qt.Tool` 窗口），不进父布局；外部点击自动关闭
- **触发器绑定**：`popover.attach(any_widget)` 即可，自动监听点击
- **12 种 placement**：top / top-start / top-end / bottom / bottom-start / bottom-end / left / left-start / left-end / right / right-start / right-end
- **auto-flip**：屏幕边缘溢出时自动反向
- **6 种颜色**（default + 5 语义色）
- **3 种尺寸** / **5 种圆角**（`none/sm/md/lg/full`）/ **4 级阴影**（`none/sm/md/lg`）
- **backdrop**：`transparent` / `opaque`（黑色 50%）/ `blur`（黑色 30% 近似）
- **trigger_scale_on_open**：触发器在 popover 打开时透明度 0.7（视觉反馈）
- **打开/关闭动画**：纯文字内容走 pixmap scale + fade；自定义插槽（复合组件）只走 opacity fade
- **箭头**：自绘 10×10 三角形，跟随 placement 自动定位
- **主题**：`auto`（跟随 ThemeProvider）/ `light` / `dark`

## 快速开始

```python
from PySide6.QtWidgets import QLabel, QVBoxLayout
from hero_side_ui import Popover, PopoverContent, Button

trigger = Button("Open Popover", color="primary")

popover = Popover(placement="bottom", color="default", shadow="md")
content = PopoverContent()
content.layout().addWidget(QLabel("Popover Title"))
content.layout().addWidget(QLabel("Some helpful text in here."))
popover.set_content(content)

popover.attach(trigger)              # 默认 click 切换
```

## 插槽（任意内容）

`PopoverContent` 暴露原生 `layout()`，你可以塞任何 Qt widget：

```python
from hero_side_ui import Popover, PopoverContent, Input, Button, Checkbox

p = Popover(color="default", shadow="lg", placement="bottom-end")

c = PopoverContent()
c.layout().addWidget(Input(label="Email", placeholder="you@example.com"))
c.layout().addWidget(Checkbox("Subscribe to updates"))
btn = Button("Submit", color="primary", size="sm")
c.layout().addWidget(btn)

p.set_content(c)
p.attach(my_settings_button)
```

## 参数

| 参数                    | 类型                                                         | 默认值        | 说明                                     |
| ----------------------- | ------------------------------------------------------------ | ------------- | ---------------------------------------- |
| `color`                 | `default / primary / secondary / success / warning / danger` | `default`     | 背景色（default 即白/暗灰，对齐 HeroUI） |
| `size`                  | `sm / md / lg`                                               | `md`          | 内容字号                                 |
| `radius`                | `none / sm / md / lg / full`                                 | `md`          | 圆角                                     |
| `shadow`                | `none / sm / md / lg`                                        | `md`          | 阴影                                     |
| `placement`             | 12 种                                                        | `top`         | 弹出方向                                 |
| `backdrop`              | `transparent / opaque / blur`                                | `transparent` | 背景遮罩                                 |
| `trigger_scale_on_open` | `bool`                                                       | `True`        | 打开时触发器变淡                         |
| `trigger_variant`       | `str`                                                        | `"flat"`      | 绑定 trigger 时同步给 Button 的 variant  |
| `arrow`                 | `bool`                                                       | `False`       | 是否显示箭头                             |
| `is_disabled`           | `bool`                                                       | `False`       | 禁用                                     |
| `disable_animation`     | `bool`                                                       | `False`       | 关闭打开/关闭动画                        |
| `theme`                 | `auto / light / dark`                                        | `"auto"`      | 主题（auto 跟随 ThemeProvider）          |

## API

- `popover.attach(trigger, event="click" | "hover" | "manual")`：绑定触发器
- `popover.set_content(widget)`：替换内容
- `popover.content()`：获取当前内容控件
- `popover.open(near=None)` / `popover.close()` / `popover.toggle()`
- `popover.is_open() -> bool`
- 信号：`opened` / `closed`
- 动态：`set_color` / `set_size` / `set_radius` / `set_shadow` / `set_placement` / `set_backdrop` / `set_theme` / `set_is_disabled`

## 与 HeroUI 的差异

- `backdrop="blur"` 在 Qt 中没有真正的背景模糊滤镜，用半透明黑（α=76）近似；视觉接近但不会真模糊后面的内容
- 阴影由 `paintEvent` 多层半透明圆角矩形自绘（避免 `QGraphicsDropShadowEffect` 与子控件 `QGraphicsEffect` 嵌套冲突）
- `trigger_scale_on_open` 只调透明度（0.7），不缩放（避免和 Button 自带的 PressScaleEffect 打架）
- `attach()` 支持 `event="hover"` / `"manual"`，HeroUI 原版只有 click
- 自定义插槽（含复合组件如 Listbox/Input 等）只走 opacity fade 动画，不做 scale 或 squeeze（Qt 无 GPU compositor，raster scale 会糊字/冻结子动画）
