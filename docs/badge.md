# Badge 徽章组件

> 对齐 [HeroUI v2 Badge](https://v2.heroui.com/docs/components/badge)。
>
> - 样式锚点：`packages/core/theme/src/components/badge.ts`
> - 组件锚点：`packages/components/badge/src/{badge.tsx,use-badge.ts}`

`Badge` 包裹任意 `QWidget`（按钮、头像、图标等），并在其角上叠加一个角标。角标形态由 `content` 自动判定：空串 → 圆点，单字符 → 正方形，多字符 → 圆角矩形。

## 快速上手

```python
from hero_side_ui import Avatar, Badge, Button

Badge(Button("消息"), content="5", color="danger")      # 角标数字
Badge(Avatar(name="JW"), content="3", color="primary")  # 头像角标
Badge(widget, content="", color="success")              # 空内容 → 圆点
Badge(widget, content="99+", placement="top-left")      # 多字符 + 换角
```

## 构造参数

| 参数                | 类型                                                           | 默认          | 说明                                           |
| ------------------- | -------------------------------------------------------------- | ------------- | ---------------------------------------------- |
| `widget`            | `QWidget \| None`                                              | `None`        | 被包裹的内容（官方 `children`）                |
| `content`           | `str`                                                          | `""`          | 角标内容；空串圆点 / 单字符正方形 / 多字符矩形 |
| `color`             | `str`                                                          | `"default"`   | 语义色                                         |
| `variant`           | `str`                                                          | `"solid"`     | 视觉变体                                       |
| `size`              | `"sm" \| "md" \| "lg"`                                         | `"md"`        | 尺寸                                           |
| `shape`             | `"circle" \| "rectangle"`                                      | `"rectangle"` | 只影响锚点偏移（10% / 5%），两种都恒为全圆角   |
| `placement`         | `"top-right" \| "top-left" \| "bottom-right" \| "bottom-left"` | `"top-right"` | 角标所在角                                     |
| `show_outline`      | `bool`                                                         | `True`        | 2px 宿主背景色描边（官方 `showOutline`）       |
| `is_invisible`      | `bool`                                                         | `False`       | 隐藏角标（官方 `isInvisible`）                 |
| `disable_animation` | `bool`                                                         | `False`       | 关闭显隐过渡动画                               |
| `theme`             | `"auto" \| "light" \| "dark"`                                  | `"auto"`      | 主题模式；auto 跟随 `ThemeProvider`            |
| `parent`            | `QWidget \| None`                                              | `None`        | 父级                                           |

## 可选值

### color

`"default"` `"primary"` `"secondary"` `"success"` `"warning"` `"danger"`

### variant

| variant  | 视觉                  |
| -------- | --------------------- |
| `solid`  | 纯色背景 + 对比色文字 |
| `flat`   | 彩色浅底 + 无边框     |
| `faded`  | 浅底 + 彩色文字       |
| `shadow` | 纯色背景 + 彩色投影   |

### size

| size | 圆点 | 单字符 | 多字符高 | 文字 |
| ---- | ---- | ------ | -------- | ---- |
| `sm` | 12   | 16     | 16       | 10px |
| `md` | 14   | 20     | 20       | 14px |
| `lg` | 16   | 24     | 20       | 16px |

文字字号 sm 10 / md 14 / lg 16 为用户拍板的桌面档（对应官方 tiny/small/small 的相对关系）。

## 公共方法

| 方法                       | 说明                                 |
| -------------------------- | ------------------------------------ |
| `set_widget(widget)`       | 替换被包裹内容；旧控件脱离父级不销毁 |
| `widget()`                 | 当前被包裹控件                       |
| `set_content(content)`     | 更新角标内容（自动重判形态与尺寸）   |
| `content()`                | 当前角标内容                         |
| `set_color(color)`         | 切换语义色                           |
| `set_variant(variant)`     | 切换变体                             |
| `set_size(size)`           | 切换尺寸                             |
| `set_shape(shape)`         | 切换形状（影响锚点偏移）             |
| `set_placement(placement)` | 切换四角位置                         |
| `set_show_outline(bool)`   | 切换描边                             |
| `set_invisible(bool)`      | 切换角标显隐（默认 300ms 淡入淡出）  |
| `is_invisible()`           | 当前显隐状态                         |
| `set_disable_animation(b)` | 开关动画                             |
| `set_theme(theme)`         | `"auto" \| "light" \| "dark"`        |

## 定位规则

角标中心悬在被包裹内容边缘的锚点上（对应官方 translate ±1/2）：

| placement      | 锚点（内容宽高百分比）   |
| -------------- | ------------------------ |
| `top-right`    | x = w×(1-p)，y = h×p     |
| `top-left`     | x = w×p，y = h×p         |
| `bottom-right` | x = w×(1-p)，y = h×(1-p) |
| `bottom-left`  | x = w×p，y = h×(1-p)     |

其中 `p = 0.05`（rectangle）/ `0.10`（circle），token 见 `themes/component_presets/badge.py::BADGE_PLACEMENT_OFFSETS`。

**circle 的桌面端修正**：官方 10% 是矩形百分比锚点，对圆形内容角标咬合量 = 角标半径 − 0.27×内容半径，内容越大咬得越少直至悬空脱离（Avatar lg 56px + sm 角标时咬合为负）。桌面端 `shape="circle"` 改为 45° 对角线圆贴合模型：角标中心悬出内容外接圆边 0.65 倍角标半径，咬合恒为 0.35 倍角标半径，与内容尺寸无关。`rectangle` 保持官方百分比公式（方形内容咬角正确）。圆形内容（如 Avatar）应传 `shape="circle"`。

## 特殊行为

- **形态自动判定**：与官方 `String(content).length` 逻辑一致——空串为圆点（无文字），单字符锁正方形，多字符按文字实测宽 + `px-1`(4px×2) 撑开。
- **描边色**：`show_outline=True` 时描边为官方 `border-background`（light=#ffffff / dark=#000000）；关闭时连 faded 的边框也被官方 `border-0` 覆盖 → 完全无边框。
- **动画简化**：官方 `isInvisible` 切换是 scale-0 + opacity-0 弹性过渡；Qt 版简化为 300ms 透明度过渡（OutCubic），`disable_animation=True` 时直接显隐。
- **投影互斥**：shadow variant 在角标上挂 `QGraphicsDropShadowEffect`；显隐动画期间临时换成 opacity effect，结束后自动恢复。
- **faded 边框恒被覆盖**：官方 badge 的 showOutline variant 顺序在 faded 之后，faded 自带的 `border-medium` 永远不生效，Qt 版直接不产出。
- **悬出预留边距**：官方 Web 的角标是 `absolute` 定位，可悬出 children 边缘（HTML 默认 `overflow: visible`）；Qt 的子 widget 会被父容器裁剪，因此 Badge 在四周预留等于角标半径的边距（随 content/size 动态变化）。锚点始终相对**被包裹件的实际矩形**（父布局拉伸 Badge、内容不填满时角标仍贴合内容），无被包裹件时退回预留矩形；必要时角标位置钳制在容器内。组件整体占位相应比被包裹内容大一圈，属桌面端必要近似。

## 与 HeroUI 差异

1. HeroUI 用 `children`（ReactNode）包裹内容；Qt 版用 `widget` 参数接收任意 `QWidget`。
2. 官方 `isOneChar` / `isDot` 是显式 prop；Qt 版由 `content` 自动判定（str 长度 1 / 0），无需手动声明。
3. 官方 `disableOutline` 已 deprecated 被 `showOutline` 取代，Qt 版只保留 `show_outline`。
4. `classNames` 是 React tailwind-variants slot，Qt 版不需要。
5. shadow variant 的 CSS box-shadow 用 `QGraphicsDropShadowEffect`（blur 12 / offset 0,2 / alpha 0.45）还原。
6. 官方动画 `ease-soft-spring`（弹性）简化为 OutCubic 透明度过渡。

## 示例

`examples/badge/demo.py` 共 10 节：Usage / Variants / Colors / Sizes / Shape / Placement / Dot / One Char & Multi Char / Outline / Invisible（带交互切换）。
