# Drawer

基于 [HeroUI v2 Drawer](https://v2.heroui.com/docs/components/drawer) 复刻的抽屉：侧滑面板 + 遮罩 + Esc 关闭。内容区就是一个普通 `QWidget`，可以往里放任何组件。

HeroUI 的 Drawer = Modal + use-drawer：`placement` 决定贴哪条边，`size` 决定宽度（left/right）或高度上限（top/bottom），动效是 `x`（左/右）或 `y`（上/下）的位移。本项目按同样的分工实现。

| 层   | 类                 | 职责                                                         |
| ---- | ------------------ | ------------------------------------------------------------ |
| 外壳 | `Drawer`           | 宿主窗口的子 widget，覆盖整个客户区；管开合、层级与 Esc       |
| 遮罩 | `_DrawerBackdrop`  | 私有。复用 Popover 的 `_Backdrop`，画 opaque / blur           |
| 面板 | `_DrawerPanel`     | 私有。QSS 背景 + 按 placement 削平的圆角 + 内容容器 + 关闭按钮 |

`Drawer` 是**宿主窗口的子 widget**，不是顶层窗口 —— 不抢焦点、不闪原生边框，跟随窗口 resize 自动同步几何。遮罩是 host 的**另一个**子 widget，用 `stackUnder` 压在 `Drawer` 下面，层级是 `宿主内容 < 遮罩 < Drawer < 面板`。绘制与模糊全部交给 `_Backdrop`，`Drawer` 自身不画东西，也不用 `QGraphicsEffect`，避免和 Button 自带的 `PressScaleEffect` 嵌套冲突。

## 快速开始

```python
from hero_side_ui import Drawer, Title, Body

drawer = Drawer(placement="right", size="md", parent=main_window)
drawer.add_widget(Title("设置", level=3))
drawer.add_widget(Body("内容区就是普通 QWidget，随便塞组件"))

drawer.open_drawer()      # 打开
drawer.close_drawer()     # 关闭（走退出动画）
drawer.toggle()

drawer.content_widget()   # 拿到内容容器，自己加 layout / 子组件
```

## API

### 构造参数

| 参数                            | 类型                       | 默认      | 说明                                          |
| ------------------------------- | -------------------------- | --------- | --------------------------------------------- |
| `size`                          | `str \| int`               | `"md"`    | 见下方 size 表；传数字表示 px                  |
| `radius`                        | `str`                      | `"lg"`    | `none` / `sm` / `md` / `lg`                   |
| `placement`                     | `str`                      | `"right"` | `left` / `right` / `top` / `bottom`           |
| `backdrop`                      | `str`                      | `"opaque"`| `transparent` / `opaque` / `blur`             |
| `is_open`                       | `bool`                     | `False`   | 构造即打开                                    |
| `is_dismissable`                | `bool`                     | `True`    | 点遮罩 / Esc 是否可关闭                       |
| `is_keyboard_dismiss_disabled`  | `bool`                     | `False`   | 单独禁掉 Esc（点遮罩仍可关）                  |
| `hide_close_button`             | `bool`                     | `False`   | 隐藏关闭按钮                                  |
| `close_button`                  | `QWidget \| None`          | `None`    | 自定义关闭按钮（有 `clicked` 的会自动连关闭） |
| `disable_animation`             | `bool`                     | `False`   | 跳过滑入滑出与遮罩淡入淡出                    |
| `on_open_change`                | `Callable[[bool], None]`   | `None`    | 开合状态变化回调                              |
| `on_close`                      | `Callable[[], None]`       | `None`    | 关闭完成回调                                  |
| `host`                          | `QWidget \| None`          | `None`    | 被覆盖的宿主窗口，缺省取 `parent` 的顶层窗口  |
| `theme`                         | `str`                      | `"auto"`  | `auto` / `light` / `dark`                     |
| `parent`                        | `QWidget \| None`          | `None`    | 只用于推导出宿主窗口                          |

### 公共方法

| 方法                                      | 说明                                     |
| ----------------------------------------- | ---------------------------------------- |
| `set_is_open(v)` / `is_open()`            | 开合（会触发信号与回调）                 |
| `open_drawer()` / `close_drawer()` / `toggle()` | 便捷别名                            |
| `content_widget() -> QWidget`             | 内容容器（已带 `QVBoxLayout`）           |
| `add_widget(w)` / `clear_content()`       | 追加 / 清空内容                          |
| `set_content(w)`                          | 用单个组件替换全部内容                   |
| `set_size(s)` / `set_radius(r)` / `set_placement(p)` | 运行时改规格，已打开会重排      |
| `set_backdrop(b)` / `backdrop()`    | 换遮罩（`transparent` / `opaque` / `blur`），已打开会立刻重建 |
| `set_is_dismissable(v)` / `set_is_keyboard_dismiss_disabled(v)` | 改关闭条件        |
| `set_hide_close_button(v)` / `set_close_button(w)` | 关闭按钮                       |
| `set_disable_animation(v)`                | 切动画开关                               |
| `set_host(w)` / `host()`                  | 换宿主窗口 / 读当前宿主                  |
| `set_theme(t)`                            | `auto` 跟随全局，或固定 `light` / `dark` |
| `size()` / `radius()` / `placement()`     | 读当前规格                               |

### 信号

| 信号                | 说明                       |
| ------------------- | -------------------------- |
| `open_changed(bool)`| 开合状态变化               |
| `closed()`          | 关闭动画结束后触发         |

## 视觉规格

### size

`size` 对两条 placement 轴的语义不同（对齐官方）：

- **left / right**：宽度**固定**为 size 值，高度铺满宿主（官方 `max-w-[20rem]` + `inset-y-0`）。
- **top / bottom**：高度**内容自适应**，size 是上限 —— 面板实际高度 = min(内容 sizeHint, size 上限, 宿主高)，空内容兜底 80px（内边距 x2 + 关闭按钮）。官方 `max-h-[20rem]` 无固定高度，面板由内容撑开。
- `full` 两轴都铺满且四角无圆角。

| size  | 值 (px) |
| ----- | --------- |
| `xs`  | 320       |
| `sm`  | 384       |
| `md`  | 448       |
| `lg`  | 512       |
| `xl`  | 576       |
| `2xl` | 672       |
| `3xl` | 768       |
| `4xl` | 896       |
| `5xl` | 1024      |
| `full`| 铺满宿主，圆角归零 |

`placement` 为 `left` / `right` 时值作用于宽度，`top` / `bottom` 时作用于高度上限。

**传数字**：**强制控制**滑出轴长度（不看内容，内容自适应只属于档位 size；会按宿主尺寸钳制）——`left` / `right` 时定宽，`top` / `bottom` 时定高：

| 调用                              | placement | 结果                            |
| --------------------------------- | --------- | ------------------------------- |
| `Drawer(size=600)`                | `right`   | 宽强制 600（贴右）              |
| `Drawer(size=600, placement="top")` | `top`   | 高强制 600，宽铺满              |
| `Drawer(size=2000)`               | `left`    | 宽被钳到宿主宽度                 |

数字会被归一化成 `int`（`250.9 → 250`），`size()` 原样返回。非正数、布尔值、其它类型一律抛 `ValueError`。

### backdrop

| 值            | 效果                                                       |
| ------------- | ---------------------------------------------------------- |
| `transparent` | 不建遮罩层，宿主内容原样可见                                |
| `opaque`      | 黑色 50%（HeroUI `bg-overlay/50`），默认                    |
| `blur`        | 宿主客户区快照做高斯模糊，再叠黑色 30%（HeroUI `backdrop-blur-md` + `bg-overlay/30`） |

与 Popover 共用同一套 `_Backdrop` 实现：淡入 260ms、淡出 200ms，`blur` 是**打开瞬间的静态快照**（打开期间宿主内容变化不会反映到模糊底图上）。

`transparent` 时不画任何东西，但 `Drawer` 仍然覆盖整个客户区并接收点击 —— 点面板外部照样关闭（受 `is_dismissable` 控制）。想让底层可交互就不要用 Drawer 的覆盖模型。

### placement 与圆角

贴边那一侧的圆角被削平（HeroUI `rounded-t-none` / `rounded-r-none` 等）：

| placement | 削平            |
| --------- | --------------- |
| `top`     | 上左、上右      |
| `right`   | 上右、下右      |
| `bottom`  | 下左、下右      |
| `left`    | 上左、下左      |

### 关闭途径

| 途径       | 受控于                                                |
| ---------- | ----------------------------------------------------- |
| 点遮罩     | `is_dismissable`                                      |
| Esc        | `is_dismissable` 且 `is_keyboard_dismiss_disabled=False` |
| 关闭按钮   | 始终有效                                              |

Esc 用 `QShortcut` + `WindowShortcut` 上下文实现，只在抽屉打开时启用；面板内部的点击不会冒泡到遮罩，所以面板里放输入框、按钮都正常。

### 动效

入场：面板从屏幕外滑到贴边位（200ms easeOut）+ 遮罩淡入（260ms）。
出场：面板滑出屏幕（100ms easeIn）+ 遮罩淡出（200ms），结束才 `hide()` 并销毁遮罩。
`disable_animation=True` 时直接跳到终态（遮罩直接推到不透明，不走淡入淡出）。
没有遮罩（`transparent`）时，出场按侧滑的 100ms 收尾。

## 设计说明

- **内容区不内置滚动**。内容超出面板时，把 `ScrollShadow` 作为 `set_content()` 的参数传进去即可获得滚动与边缘渐变。
- **上下抽屉高度内容自适应**（官方 `max-h` 只封顶不托底，仅档位 size）：面板高度 = min(内容 sizeHint, size 上限, 宿主高)，空内容兜底 80px；左右抽屉宽度固定为 size 档。数字 size 则强制控制对应轴长度，不看内容。
- **内容从顶部堆叠**（HeroUI 是 flex-start）：内容容器布局固定 `AlignTop`，不随面板高度垂直居中。
- **遮罩复用 Popover**：`_DrawerBackdrop` 只比 Popover 的 `_Backdrop` 多一个 `settle()`（`disable_animation` 时把淡入淡出进度直接推到终态）。改遮罩配色/模糊强度请改 `components/popover/_backdrop.py`，两边一起生效。创建遮罩前会先 `raise_()` 自己再 `stackUnder`，保证 Drawer 晚于 host 已有内容创建时遮罩仍盖在内容之上。
- **主题**：`theme="auto"` 时注册到 `ThemeProvider`，全局切换会同时刷新面板底色、边框与文字色；面板自身不注册，统一由 `Drawer` 转发，避免重复广播。
- **宿主**：`host` 缺省时取 `parent.window()`，都没有则延迟到首次打开时取当前活动窗口，仍取不到会抛 `ValueError`。
- **切换宿主 / 规格**：`set_host()` 与 `set_placement()` / `set_size()` 在打开状态下会直接重排面板（不播动画），不会把面板留在屏幕外。
