# Toast

基于 [HeroUI v2 Toast](https://v2.heroui.com/docs/components/toast) 复刻的轻提示。全局函数 `add_toast()` 一条即可弹出，自动管理堆叠、折叠、超时与进出场动画。

内部分三层，对应 HeroUI 的 `toast-provider` / `toast-region` / `toast`：

| 层       | 类                              | 职责                                                         |
| -------- | ------------------------------- | ------------------------------------------------------------ |
| 全局队列 | `add_toast()` / `ToastProvider` | 每个宿主窗口懒建一个 provider，管 key 与默认配置             |
| 堆叠区   | `ToastRegion`                   | 宿主窗口内的 overlay：6 方位定位、折叠展开、进出场与旧卡隐藏 |
| 单卡     | `Toast`                         | 自绘卡片：图标、标题、描述、关闭按钮、倒计时进度、拖拽       |

`ToastRegion` 是宿主窗口的**子 widget**（不是顶层窗口），因此不抢焦点、不闪白框，随窗口 resize 自动同步几何。卡片虽经 `add()` 挂载，实际父级是**宿主窗口**而非 region：region 自身鼠标透明（空白区点击透传给下层内容），而 Qt 命中测试会整树跳过鼠标透明 widget 的子树，卡片若挂在 region 内则内部按钮与拖拽收不到任何鼠标事件。

## 快速开始

```python
from hero_side_ui import add_toast, close_toast, clear_toasts

key = add_toast(
    title="已保存",
    description="草稿已写入本地",
    severity="success",
    color="success",
    parent=main_window,     # 省略时取当前活动窗口
)

close_toast(key)            # 提前关闭（走退出动画）
clear_toasts(main_window)   # 清空某窗口上的全部 toast
```

`add_toast()` 返回 key；需要运行中改文案或结束 loading 时，用 `get_toast_provider(window).card(key)` 取回卡片。

## API

### 全局函数

| 函数                                                                                   | 说明                             |
| -------------------------------------------------------------------------------------- | -------------------------------- |
| `add_toast(...) -> str`                                                                | 弹一条，返回 key                 |
| `close_toast(key)`                                                                     | 关闭指定一条                     |
| `clear_toasts(window=None)`                                                            | 清空指定窗口（默认当前活动窗口） |
| `get_toast_provider(window=None) -> ToastProvider`                                     | 取（必要时创建）窗口的 provider  |
| `configure_toasts(placement=, max_visible_toasts=, toast_offset=, disable_animation=)` | 改**后续新建** provider 的默认值 |

### ToastProvider

| 方法 / 属性                                                               | 说明                                               |
| ------------------------------------------------------------------------- | -------------------------------------------------- |
| `add(**props) -> str`                                                     | 等价于 `add_toast`，可覆盖构造期给的 `toast_props` |
| `card(key) -> Toast \| None`                                              | 取回卡片以改文案 / 结束 loading                    |
| `close(key)` / `clear()`                                                  | 关闭一条 / 全部                                    |
| `region -> ToastRegion`                                                   | 内部堆叠区                                         |
| `set_placement(p)` / `set_max_visible_toasts(n)` / `set_toast_offset(px)` | 运行时改配置                                       |

### ToastRegion

| 方法                         | 说明                                     |
| ---------------------------- | ---------------------------------------- |
| `add(card, key=None) -> str` | 挂载一张卡片，超配额的旧卡隐藏（不销毁） |
| `dismiss(key)` / `clear()`   | 移除一条 / 全部                          |
| `keys() -> list[str]`        | 当前（含正在退出的）key                  |
| `card(key) -> Toast \| None` | 按 key 取卡片                            |

一般不需要直接用 `ToastRegion`，交给 provider 即可；想把它塞进自己的窗口层级时可以手动构造。

### Toast 构造参数

| 参数                           | 类型                                                                      | 默认             | 说明                                          |
| ------------------------------ | ------------------------------------------------------------------------- | ---------------- | --------------------------------------------- |
| `title`                        | `str`                                                                     | `""`             | 标题，单行省略号截断                          |
| `description`                  | `str`                                                                     | `""`             | 描述，自动换行；为空时不占位                  |
| `color`                        | `default / foreground / primary / secondary / success / warning / danger` | `"default"`      | 配色                                          |
| `variant`                      | `flat / bordered / solid`                                                 | `"flat"`         | 变体                                          |
| `radius`                       | `none / sm / md / lg / full`                                              | `"md"`           | 圆角；`full` 取半高                           |
| `shadow`                       | `none / sm / md / lg`                                                     | `"sm"`           | 阴影档位                                      |
| `severity`                     | `default / primary / secondary / success / warning / danger`              | `None`           | 决定内置图标；`None` 时按 `color` 取          |
| `icon`                         | `str \| None`                                                             | `None`           | 自定义图标名，优先于 severity                 |
| `hide_icon`                    | `bool`                                                                    | `False`          | 隐藏图标                                      |
| `hide_close_button`            | `bool`                                                                    | `False`          | 隐藏右上角关闭按钮                            |
| `end_content`                  | `QWidget \| None`                                                         | `None`           | 右侧附加内容（按钮等）                        |
| `timeout`                      | `int \| None`                                                             | `None`           | 毫秒；`None` 用预设 6000，`0` 表示不自动关闭  |
| `should_show_timeout_progress` | `bool`                                                                    | `False`          | 显示倒计时进度覆层                            |
| `is_loading`                   | `bool`                                                                    | `False`          | 图标换 Spinner 并暂停倒计时                   |
| `on_close`                     | `Callable \| None`                                                        | `None`           | 关闭回调                                      |
| `disable_animation`            | `bool`                                                                    | `False`          | 关闭进出场动画                                |
| `placement`                    | `str`                                                                     | `"bottom-right"` | 单卡方位，由 region 统一下发                  |
| `theme`                        | `auto / light / dark`                                                     | `"auto"`         | `auto` 跟随 ThemeProvider                     |
| `parent`                       | `QWidget \| None`                                                         | `None`           | 父 widget                                     |

### Toast 方法与信号

| 方法                                                                | 说明                                                |
| ------------------------------------------------------------------- | --------------------------------------------------- |
| `set_title(text)` / `set_description(text)`                         | 改文案，堆叠区自动重排                              |
| `set_loading(loading)`                                              | 切 loading；`False` 时重启倒计时                    |
| `set_end_content(widget)`                                           | 换右侧附加内容                                      |
| `set_color / set_variant / set_radius / set_shadow`                 | 改外观                                              |
| `set_hide_icon / set_hide_close_button / set_show_timeout_progress` | 改显隐                                              |
| `set_paused(paused)`                                                | 暂停 / 恢复倒计时（hover 与展开由 region 自动调用） |
| `start_countdown() / stop_countdown()`                              | 手动起停倒计时                                      |

| 信号                                                                          | 说明         |
| ----------------------------------------------------------------------------- | ------------ |
| `closed`                                                                      | 点了关闭按钮 |
| `timeout_reached`                                                             | 倒计时走完   |
| `hover_changed(bool)`                                                         | 鼠标进出     |
| `drag_started` / `drag_moved(dx, dy)` / `drag_finished(dx, dy, should_close)` | 拖拽过程     |

## 行为说明

### placement

6 个方位：`top-left` / `top-center` / `top-right` / `bottom-left` / `bottom-center` / `bottom-right`。方位属于**堆叠区**而不是单卡，切换后已有卡片一起重排；`add_toast(placement=...)` 只是转发给当前 provider。

### 堆叠与折叠

- 同时最多显示 `max_visible_toasts`（默认 3）条；超配额的旧卡**只是隐藏、不销毁**，照常倒计时（HeroUI `visibleToasts` 语义），hover 展开时全部重新显示。
- 折叠态更早的卡片只露出 8px 边条并左右内缩（近似 HeroUI 的 `scaleX`）。
- 鼠标进入堆叠区展开全部并暂停倒计时，离开 120ms 后折叠。

### 超时与进度

`timeout` 毫秒后自动关闭；`should_show_timeout_progress=True` 时卡片上叠一层从左推进的半透明进度条。hover 或展开期间倒计时暂停，避免"看着看着没了"。

### 拖拽关闭

按住卡片拖动：左右方位按 X 轴判定（`swipe_threshold_x=100`），上下居中方位按 Y 轴（`swipe_threshold_y=20`）。拖过阈值松手即关闭，未过阈值弹回原位。拖动中卡片随位移淡出。

### loading

`is_loading=True` 时图标换成 Spinner 且不计时；拿到结果后 `card.set_loading(False)` 即可恢复倒计时，配合 `set_title` / `set_color` 就能表达"进行中 → 成功"。

### 主题

`theme="auto"`（默认）时卡片向 `ThemeProvider` 注册，跟随全局亮/暗切换；`flat` / `bordered` / `solid` 三套配色的每一档都按 HeroUI 的 compoundVariants 换算，暗色下语义色阶遵循 HeroUI 的 swap 规则。

## 与 HeroUI 的差异

- HeroUI 的 scaleX 折叠是整体缩放，这里改成背景左右内缩，避免文字被压扁。
- HeroUI 用 framer-motion 做弹簧动画，这里用 `QPropertyAnimation` 走固定时长（`duration_move=300ms`）。
- 不提供 HeroUI 的 promise 版 `addToast.promise(...)`，用 `is_loading` + `card(key)` 手动收尾达到同样效果。

## 示例与测试

- 示例：`examples/toast/demo.py`
- 测试：`tests/components/test_toast.py`
