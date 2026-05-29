# Pagination 分页器

> HeroSideUI 的分页器组件，对齐 [HeroUI v2 Pagination](https://v2.heroui.com/docs/components/pagination)。
>
> 招牌动效：active item 切换时，光标（cursor）会**滑动 + 弹起 + 回落**（scale 1.0 → 1.1 → 1.0）。

## 快速开始

```python
from hero_side_ui import Pagination

pag = Pagination(total=10, initial_page=3)
pag.page_changed.connect(lambda page: print("Now at:", page))
```

## 构造参数

| 参数                       | 类型            | 默认值      | 说明                                                                   |
| -------------------------- | --------------- | ----------- | ---------------------------------------------------------------------- |
| `total`                    | `int`           | 必填        | 总页数（≥1）                                                           |
| `initial_page`             | `int`           | `1`         | 初始选中页                                                             |
| `page`                     | `Optional[int]` | `None`      | 受控页码（提供时覆盖 `initial_page`）                                  |
| `siblings`                 | `int`           | `1`         | active 两侧显示的相邻页数                                              |
| `boundaries`               | `int`           | `1`         | 首尾固定显示的边界页数                                                 |
| `dots_jump`                | `int`           | `5`         | 点击 `...` 时跳跃的页数                                                |
| `variant`                  | `str`           | `"flat"`    | `flat` / `bordered` / `light` / `faded`                                |
| `color`                    | `str`           | `"primary"` | `default` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`                     | `str`           | `"md"`      | `sm` / `md` / `lg`                                                     |
| `radius`                   | `str`           | `"md"`      | `none` / `sm` / `md` / `lg` / `full`                                   |
| `is_compact`               | `bool`          | `False`     | 紧凑模式：item 之间无 gap，首尾连体                                    |
| `is_disabled`              | `bool`          | `False`     | 整体禁用（半透明 + 不可点）                                            |
| `show_controls`            | `bool`          | `False`     | 是否显示 prev/next 方向按钮                                            |
| `loop`                     | `bool`          | `False`     | 边界循环（next 在末页跳到首页）                                        |
| `disable_animation`        | `bool`          | `False`     | 关闭所有动画（press scale + cursor 动画 + 淡入）                       |
| `disable_cursor_animation` | `bool`          | `False`     | 仅关闭 cursor 滑动动画（active item 改用自填充）                       |
| `theme`                    | `str`           | `"auto"`    | `auto` / `light` / `dark`                                              |
| `parent`                   | `QWidget`       | `None`      | Qt 父组件                                                              |

## 信号

| 信号           | 参数  | 触发时机                                               |
| -------------- | ----- | ------------------------------------------------------ |
| `page_changed` | `int` | 当前页发生改变（程序内 `set_page` 与用户点击都会触发） |

## 方法

### 翻页

| 方法                     | 说明                                    |
| ------------------------ | --------------------------------------- |
| `set_page(page: int)`    | 跳到指定页（自动钳制到 `[1, total]`）   |
| `current_page() -> int`  | 返回当前页                              |
| `total() -> int`         | 返回总页数                              |
| `go_next()`              | 下一页（边界时若 `loop=True` 跳到首页） |
| `go_previous()`          | 上一页（边界时若 `loop=True` 跳到末页） |
| `go_first()`             | 跳到首页                                |
| `go_last()`              | 跳到末页                                |
| `set_total(total: int)`  | 修改总页数                              |
| `set_dots_jump(n: int)`  | 修改 `...` 跳跃页数                     |
| `set_siblings(n: int)`   | 修改 siblings                           |
| `set_boundaries(n: int)` | 修改 boundaries                         |

### 视觉变体

| 方法                                          |
| --------------------------------------------- |
| `set_variant(variant: str)`                   |
| `set_color(color: str)`                       |
| `set_size(size: str)`                         |
| `set_radius(radius: str)`                     |
| `set_compact(compact: bool)`                  |
| `set_disabled(disabled: bool)`                |
| `set_show_controls(show: bool)`               |
| `set_loop(loop: bool)`                        |
| `set_disable_animation(disable: bool)`        |
| `set_disable_cursor_animation(disable: bool)` |
| `set_theme(theme: str)`                       |

## 变体一览

### variant

- **`flat`**（默认）：item 底色 `default-100`，hover `default-200`，pressed `default-300`
- **`bordered`**：透明底 + 2px `default-300/700` 边框，hover `default-100`
- **`light`**：完全透明，hover `default-100`
- **`faded`**：底色 `default-100` + 2px `default-300/700` 边框（= flat 底 + bordered 边框）

> 暗色模式下 `default-N` 自动镜像（`50↔900` / `100↔800` / `200↔700` / `300↔600` / `400↔500`），由 `_palette._default_token(n, theme)` 统一处理。

### color

cursor 填充色直接对应：

- `default` → light 模式 `default-300`，dark 模式 `default-100`
- `primary/secondary/success/warning/danger` → 各色 `500` 主色

### size

| size | 高度 | 最小宽度 | 字号 | 图标 |
| ---- | ---- | -------- | ---- | ---- |
| `sm` | 32px | 32px     | 12px | 14px |
| `md` | 36px | 36px     | 13px | 16px |
| `lg` | 40px | 40px     | 15px | 18px |

### radius

`none / sm / md / lg / full` —— `full` 用 `height/2` 算成圆形。

## 关键动效（Cursor 弹簧动画 + 数字方向化滚动）

切换 active 页时:

1. **阶段一 (300ms)**: cursor 从旧位置 迁移到新位置 + scale 从 `1.0` 动画到 `1.1`
2. **阶段二 (300ms)**: scale 从 `1.1` 回落到 `1.0` (位置锁定)

总动画时长 **600ms**，对齐 HeroUI v2 `CURSOR_TRANSITION_TIMEOUT * 2`。

同步在阶段一里执行**数字方向化交叉滚动**:

- 页码增大 (next/向后跳) → 旧字向上滚出 + 新字从下方滚入
- 页码减小 (prev/向前跳) → 旧字向下滚出 + 新字从上方滚入

文字状态由切页路径独占管理（`set_page` 记录 direction → `start_text_swap` 消费一次），任何"重建/重配置"路径不会覆盖动画起点。

由 [`hero_side_ui/animation/cursor_slide.py`](../hero_side_ui/animation/cursor_slide.py) 的 `start_cursor_slide(...)` 函数封装：`QSequentialAnimationGroup` 串两个 `QVariantAnimation` 贯穿两阶段。

首次出现时 cursor 有 200ms 的淡入效果（`QGraphicsOpacityEffect`）。

> 关闭动画：传 `disable_cursor_animation=True` 让 cursor 不显示，active item 自填充 cursor 颜色；传 `disable_animation=True` 同时关闭 press scale 0.97 与所有过渡。

## 算法（range 计算）

公式：`totalPageNumbers = siblings * 2 + 3 + boundaries * 2`

- 当 `total ≤ totalPageNumbers`：全展开
- 否则按 `leftSibling / rightSibling` 决定省略号位置：
  - 仅右省略：`[1..leftItemCount, …, total-(boundaries-1)..total]`
  - 仅左省略：`[1..boundaries, …, total-rightItemCount..total]`
  - 双省略：`[1..boundaries, …, leftSibling..rightSibling, …, total-boundaries+1..total]`

`...` 项支持点击跳跃 `dots_jump` 页；hover/focus 时切换为双 chevron 图标。

实现见 [`_range.py`](../hero_side_ui/components/pagination/_range.py) 的 `compute_pagination_range`。

## 紧凑模式（`is_compact`）

- 所有 item 之间 `gap=0`，连成一整条胶囊
- 首 item 仅左侧两角圆角，末 item 仅右侧两角圆角，中间 item 无圆角
- 紧凑下禁用 hover/pressed 底色变化，所有 item 共享一致底色（避免视觉分割）
- `bordered`/`faded` 紧凑下只画外侧边框：首项画上+左+下、末项画上+右+下、中间仅上下两横，避免相邻 item 边框相撞产生双线

## 与 HeroUI v2 差异

| 项                            | HeroUI v2                           | HeroSideUI                                                        |
| ----------------------------- | ----------------------------------- | ----------------------------------------------------------------- |
| `transform: translateX/scale` | CSS 硬件加速，SS transition 300ms×2 | Qt `setGeometry` 驱动 widget x; `start_cursor_slide` 二阶段 600ms |
| RTL 支持                      | `useLocale`                         | 暂不支持                                                          |
| `renderItem` 自定义渲染       | React 函数                          | 暂不支持                                                          |
| `as` polymorphic              | `<a>`/`<nav>`                       | 仅 `QWidget`                                                      |
| `scrollIntoView`              | 浏览器 API                          | 暂不支持                                                          |
| 焦点环                        | `useFocusRing`                      | 自绘 2px ring（`focus-visible` 等价键盘 focus）                   |

## 文件结构

```
hero_side_ui/components/pagination/
├── __init__.py            导出 Pagination
├── _constants.py          枚举与 token
├── _range.py              range 算法（纯函数）
├── _palette.py            颜色 / 圆角解析
├── _ellipsis_icon.py      DOTS 图标 widget（hover 切换）
├── _cursor.py             _CursorWidget 自绘
├── _item.py               _PaginationItem 自绘按钮
└── pagination.py          公共 Pagination 主类
```

动画依赖：`hero_side_ui/animation/cursor_slide.py` 的 `start_cursor_slide`（二阶段 translateX+scale 1.1 / scale→1.0）。

## 示例

完整示例见 [`examples/pagination/demo.py`](../examples/pagination/demo.py)。

自定义方向控件示例见 [`examples/pagination/demo_custom_controls.py`](../examples/pagination/demo_custom_controls.py)：用 `Button` 配合 `set_page` / `go_next` / `go_previous` / `go_first` / `go_last` 完全替代自带的 `show_controls`，方向语义保持不变（增大向上滚、减小向下滚）。

```python
from hero_side_ui import Button, Pagination

pag = Pagination(total=12, initial_page=1, show_controls=False)
prev = Button(icon="heroicons--chevron-left", icon_only=True, variant="flat")
nxt = Button(icon="heroicons--chevron-right", icon_only=True, variant="flat")
prev.clicked.connect(pag.go_previous)
nxt.clicked.connect(pag.go_next)
```
