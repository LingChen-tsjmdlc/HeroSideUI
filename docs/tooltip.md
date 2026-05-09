# Tooltip

基于 HeroUI v2 [tooltip](https://v2.heroui.com/docs/components/tooltip) 复刻的悬浮提示组件。本质是 Popover 的 hover-only 简化版，无 Backdrop，自动 hover 触发显隐。

## 特性

- **hover 触发**：鼠标进入 trigger 自动打开，离开自动关闭（可配置延迟）
- **无 Backdrop**：不遮挡其他内容，不拦截点击
- **不抢焦点**：`WA_ShowWithoutActivating + NoFocus`，不会中断用户当前操作
- **12 种 placement**：top / top-start / top-end / bottom / bottom-start / bottom-end / left / left-start / left-end / right / right-start / right-end
- **auto-flip**：屏幕边缘溢出时自动反向
- **6 种颜色**（default + 5 语义色）
- **3 种尺寸** / **5 种圆角**（`none/sm/md/lg/full`）/ **4 级阴影**（`none/sm/md/lg`）
- **offset**：控制 tooltip 与 trigger 的距离（默认 7px）
- **open_delay / close_delay**：打开/关闭延迟（默认 0ms / 150ms）
- **箭头**：可选，自绘三角形跟随 placement 自动定位（start 靠上/左，end 靠下/右）
- **打开/关闭动画**：opacity + scale `0.9↔1`，200ms/150ms
- **动态内容**：`set_content` 支持运行时替换文字或 widget，自动刷新尺寸和位置

## 快速开始

```python
from hero_side_ui import Tooltip, Button

trigger = Button("Hover me", color="primary")

tooltip = Tooltip(content="Hello tooltip!", placement="top")
tooltip.attach(trigger)
```

## 自定义 widget 内容

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from hero_side_ui import Tooltip, Button

trigger = Button("Rich tooltip", color="secondary")

widget = QWidget()
layout = QVBoxLayout(widget)
layout.setContentsMargins(10, 8, 10, 8)
layout.addWidget(QLabel("标题"))
layout.addWidget(QLabel("描述文字"))

tooltip = Tooltip(color="secondary", placement="bottom", show_arrow=True)
tooltip.set_content(widget)
tooltip.attach(trigger)
```

## 动态更新内容

```python
tooltip = Tooltip(content="初始内容", color="warning")
tooltip.attach(my_button)

# 运行时替换（自动刷新尺寸和位置）
tooltip.set_content("新的内容文字")
```

## 参数

| 参数                    | 类型                                                         | 默认值    | 说明                                     |
| ----------------------- | ------------------------------------------------------------ | --------- | ---------------------------------------- |
| `content`               | `str / QWidget / None`                                       | `None`    | tooltip 显示内容（文字或自定义 widget）  |
| `color`                 | `default / primary / secondary / success / warning / danger` | `default` | 背景色（default 即白/暗灰，对齐 HeroUI） |
| `size`                  | `sm / md / lg`                                               | `md`      | 内容字号和 padding                       |
| `radius`                | `none / sm / md / lg / full`                                 | `md`      | 圆角                                     |
| `shadow`                | `none / sm / md / lg`                                        | `sm`      | 阴影                                     |
| `placement`             | 12 种                                                        | `top`     | 弹出方向                                 |
| `offset`                | `int`                                                        | `7`       | tooltip 与 trigger 的距离（px）          |
| `open_delay`            | `int`                                                        | `0`       | 打开延迟（ms）                           |
| `close_delay`           | `int`                                                        | `150`     | 关闭延迟（ms）                           |
| `show_arrow`            | `bool`                                                       | `False`   | 是否显示箭头                             |
| `trigger_scale_on_open` | `bool`                                                       | `True`    | 打开时给 trigger 设 tooltipOpen 动态属性 |
| `is_disabled`           | `bool`                                                       | `False`   | 禁用                                     |
| `disable_animation`     | `bool`                                                       | `False`   | 关闭打开/关闭动画                        |
| `theme`                 | `light / dark`                                               | `light`   | 主题                                     |

## API

- `tooltip.attach(trigger)`：绑定触发器（hover 自动触发）
- `tooltip.set_content(str_or_widget)`：替换内容（运行时可调用，自动刷新）
- `tooltip.open()` / `tooltip.close()`：手动控制
- `tooltip.is_open() -> bool`
- 信号：`opened` / `closed`
- 动态：`set_color` / `set_size` / `set_radius` / `set_shadow` / `set_placement` / `set_offset` / `set_open_delay` / `set_close_delay` / `set_show_arrow` / `set_theme` / `set_is_disabled`

## 与 Popover 的差异

| 特性     | Tooltip                   | Popover                      |
| -------- | ------------------------- | ---------------------------- |
| 触发方式 | hover（始终）             | click / hover / manual       |
| Backdrop | 无                        | transparent / opaque / blur  |
| 焦点     | 不抢焦点                  | 获取焦点                     |
| offset   | 可配（默认 7px）          | 固定 6px gap                 |
| 延迟     | open_delay + close_delay  | 仅 hover 模式有 120ms 防闪烁 |
| 默认阴影 | `sm`                      | `md`                         |
| 内容     | 通常纯文字，也支持 widget | 插槽容器，什么都能放         |
| 动画时长 | in=200ms / out=150ms      | in=280ms / out=200ms         |

## 与 HeroUI 的差异

- 阴影由 `paintEvent` 多层半透明圆角矩形自绘
- `trigger_scale_on_open` 仅设置动态属性 `tooltipOpen`，不直接缩放（避免和 Button 的 PressScaleEffect 冲突）
- `close_delay` 默认 150ms（HeroUI 原版是 500ms），桌面端 hover 更精确，无需那么长的延迟
