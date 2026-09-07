# Dropdown

基于 [HeroUI v2 Dropdown](https://v2.heroui.com/docs/components/dropdown) 复刻的触发式下拉菜单。任意 widget 都能当触发器，点击弹出浮层菜单，菜单项点击后发出动作并按需关闭。

内部组合：`trigger`（默认 `Button`） + `Popover` + `ScrollShadow` + `Listbox`，零修改既有组件。菜单项复用 `ListboxItem`（`DropdownItem` 是它的别名），因此描述、图标、快捷键、分割线、禁用等能力开箱可用。

## 快速开始

```python
from hero_side_ui import Dropdown, Button

dd = Dropdown(
    trigger=Button("Open Menu", variant="bordered"),
    items=[
        {"key": "new", "label": "New file", "shortcut": "Ctrl+N"},
        {"key": "copy", "label": "Copy link", "shortcut": "Ctrl+C"},
        {"key": "edit", "label": "Edit file"},
        {"key": "delete", "label": "Delete file", "color": "danger"},
    ],
)
dd.action.connect(lambda key: print(f"action: {key}"))
layout.addWidget(dd)  # Dropdown 自身是 QWidget，直接进布局
```

不传 `trigger` 时组件自建一个 `Button("Open Menu")`，其 `variant` / `color` / `size` 与菜单保持一致 —— 但 `shadow` 是菜单专属变体，Button 没有，此时触发器回落到 `solid`。`set_variant()` 同样会同步触发器。

## API

### 构造参数

| 参数                                       | 类型                                          | 默认            | 说明                                                                     |
| ------------------------------------------ | --------------------------------------------- | --------------- | ------------------------------------------------------------------------ |
| **数据**                                   |                                               |                 |                                                                          |
| `trigger`                                  | `QWidget \| None`                              | `None`          | 触发器；`None` 时自建默认 Button                                         |
| `items`                                    | `Iterable[dict \| tuple \| str \| DropdownItem]` | `None`        | 菜单项列表，字段见「菜单项数据」                                         |
| **开合**                                   |                                               |                 |                                                                          |
| `placement`                                | `str`                                         | `"bottom"`      | 12 种方位：`bottom/top/left/right` 与各自的 `-start` / `-end`           |
| `close_on_select`                          | `bool`                                        | `True`          | 点击菜单项后是否关闭                                                     |
| `min_width`                                | `int \| None`                                 | `None`          | 菜单最小宽度；`None` 用 size token（sm 180 / md 200 / lg 220）           |
| `max_height`                               | `int \| None`                                 | `None`          | 菜单固定高度；`None` 时高度完全由内容撑开（只被屏幕剩余空间截断）        |
| **选中**                                   |                                               |                 |                                                                          |
| `selection_mode`                           | `none / single / multiple`                     | `"none"`       | 纯动作菜单用 `none`；需要勾选态时改 `single` / `multiple`                |
| `selected_keys` / `default_selected_keys`  | `Iterable[str]`                               | `None`          | 受控 / 非受控初始选中集合                                                |
| `disabled_keys`                            | `Iterable[str]`                               | `None`          | 禁用项 key 集合                                                          |
| `disallow_empty_selection`                 | `bool`                                        | `False`         | `True` 时不允许从有到空                                                  |
| **视觉**                                   |                                               |                 |                                                                          |
| `variant`                                  | `solid / shadow / bordered / flat / faded / light` | `"solid"`  | 菜单项 hover 变体（`shadow` 只有菜单支持，触发器会回落到 `solid`）      |
| `color`                                    | `default / primary / secondary / success / warning / danger` | `"default"` | 菜单项 hover 配色                                   |
| `size`                                     | `sm / md / lg`                                | `"md"`          | 三档预设（同时驱动菜单项与默认 Button 触发器）                           |
| `radius`                                   | `none / sm / md / lg / full`                  | `"md"`          | 圆角，作用于浮层与菜单项；`full` 时浮层退化为 `lg`（菜单项仍是全圆）     |
| `shadow`                                   | `str`                                         | `"md"`          | 浮层阴影档位（透传 Popover）                                             |
| `backdrop`                                 | `str`                                         | `"transparent"` | 浮层遮罩类型（透传 Popover）                                             |
| `empty_content`                            | `str \| None`                                 | `None`          | `None` → 默认空态（图标 + 双语文案）；非空 str → 单行文字                |
| `hide_selected_icon`                       | `bool`                                        | `False`         | 隐藏选中项右侧的对勾                                                     |
| `top_content` / `bottom_content`           | `QWidget \| None`                             | `None`          | 菜单顶部 / 底部附加内容（透传 Listbox）                                  |
| **其他**                                   |                                               |                 |                                                                          |
| `is_disabled`                              | `bool`                                        | `False`         | 禁用触发器并禁止展开                                                     |
| `disable_animation`                        | `bool`                                        | `False`         | 关闭浮层与菜单项动画                                                     |
| `theme`                                    | `auto / light / dark`                         | `"auto"`        | `auto` 跟随 ThemeProvider 全局切换                                       |
| `parent`                                   | `QWidget \| None`                             | `None`          | 父 widget                                                                |

### 公共方法

| 方法                                        | 说明                                                     |
| ------------------------------------------- | -------------------------------------------------------- |
| `open()` / `close()` / `toggle()`           | 展开 / 收起 / 切换                                       |
| `is_open() -> bool`                         | 当前是否展开                                             |
| `set_trigger(widget)`                       | 换触发器（旧触发器为组件自建时销毁，否则只摘出布局）     |
| `trigger_widget() -> QWidget`               | 当前触发器                                               |
| `menu() -> Listbox`                         | 内部菜单（Listbox 本体，只读式访问）                     |
| `add_item(item_or_title, **kwargs)`         | 追加一项；额外支持 `color` / `close_on_select`            |
| `add_section(title, *, show_divider=False)` | 追加一个分组，返回 `DropdownSection`                     |
| `set_items(items)`                          | 重置菜单项                                               |
| `items() -> list[DropdownItem]`             | 当前菜单项                                               |
| `item_by_key(key)`                          | 按 key 取菜单项                                          |
| `selected_keys() -> set[str]`               | 当前选中集合                                             |
| `selected_key() -> str \| None`             | single 模式便捷取值                                      |
| `set_selected_keys(keys)` / `set_selected_key(key)` | 设置选中                                          |
| `set_disabled_keys(keys)`                   | 设置禁用项                                               |
| `set_selection_mode(mode)`                  | 切换 `none` / `single` / `multiple`                      |
| `set_close_on_select(v)`                    | 点击后是否关闭                                           |
| `set_placement(p)` / `set_radius(r)` / `set_shadow(s)` / `set_backdrop(k)` | 浮层外观           |
| `set_min_width(w)` / `set_max_height(h)`    | 菜单尺寸覆盖                                             |
| `set_variant(v)` / `set_color(c)` / `set_size(s)` | 菜单项外观                                          |
| `set_hide_selected_icon(v)`                 | 选中对勾显隐                                             |
| `set_empty_content(text)`                   | 空态文案                                                 |
| `set_top_content(w)` / `set_bottom_content(w)` | 菜单附加内容                                          |
| `set_is_disabled(v)` / `is_disabled()`      | 禁用开关                                                 |
| `set_theme(theme)`                          | 切主题（`"auto"` 重新注册 ThemeProvider）                |

### 信号

| 信号                | 载荷                | 触发                                        |
| ------------------- | ------------------- | ------------------------------------------- |
| `action`            | `str`（菜单项 key） | 点击任意可用菜单项                          |
| `selection_changed` | `str \| set[str]`   | 选中变化（single 给 key，multiple 给集合）  |
| `open_changed`      | `bool`              | 菜单开合                                    |
| `opened` / `closed` | 无                  | 菜单展开 / 收起                              |

## 菜单项数据

`items` 支持四种写法：

```python
items=[
    "New file",                                              # str：key 与文案相同
    ("copy", "Copy link"),                                   # tuple：(key, 文案)
    {"key": "edit", "label": "Edit file", "shortcut": "Ctrl+E"},   # dict：完整字段
    DropdownItem("Delete", key="delete"),                    # 直接给实例
]
```

> `color` / `close_on_select` 只有 **dict 写法**与 `add_item()` 支持 —— `DropdownItem`
> 本身是 `ListboxItem`，构造参数里没有这两项（要单项配色请用
> `dd.add_item("Delete", key="delete", color="danger")`）。

dict 可用字段：

| 字段              | 类型              | 说明                                                    |
| ----------------- | ----------------- | ------------------------------------------------------- |
| `key`             | `str`             | 唯一标识，`action` 信号回传它                           |
| `label` / `title` | `str`             | 主文案                                                  |
| `description`     | `str`             | 副标题（有值时主副文案上下排布）                        |
| `shortcut`        | `str`             | 右侧快捷键标注，如 `"Ctrl+N"`                           |
| `start_content`   | `str \| QWidget`  | 左侧图标（内置 svg 名或自定义 widget）                  |
| `end_content`     | `str \| QWidget`  | 右侧附加内容                                            |
| `is_disabled`     | `bool`            | 禁用该项                                                |
| `show_divider`    | `bool`            | 该项下方画分割线                                        |
| `color`           | `str`             | **单项配色覆盖**，如 `"danger"` 做危险操作              |
| `close_on_select` | `bool`            | 单项覆盖全局的 `close_on_select`（如多选筛选场景）      |

## 分组菜单

用 `add_section()` / `add_item()` 增量构建：

```python
dd = Dropdown(trigger=Button("Actions"))
sec = dd.add_section("Styles", show_divider=True)
sec.add_item("Bold", key="bold")
sec.add_item("Italic", key="italic")
dd.add_item("Delete", key="delete", color="danger")
```

`DropdownSection` 是 `ListboxSection` 的别名，可自行构造后 `add_section(sec)`。
分组内的项走 `section.add_item()`（ListboxSection 的参数），**不带** `color` 能力；
需要单项配色就放在分组外的 `dd.add_item()`。

## 键盘交互

| 按键                | 行为                                  |
| ------------------- | ------------------------------------- |
| `Space` / `Enter`   | 触发器是 Button 时展开菜单            |
| `Down` / `Up`       | 触发器聚焦时展开；菜单内上下移动焦点  |
| `Home` / `End`      | 菜单内跳到首个 / 末个可用项           |
| `Enter`             | 激活当前焦点项                        |
| `Esc`               | 关闭菜单并把焦点还给触发器            |

菜单展开时组件自动把焦点交给首个可用项，关闭时若焦点仍在菜单内则归还给展开前的焦点 widget。

## 与 Select 的差异

| 行为           | Dropdown                       | Select                    |
| -------------- | ------------------------------ | ------------------------- |
| 触发器         | 任意 widget（默认 Button）     | 固定是 Input 视觉容器     |
| 菜单语义       | 动作（`action`）为主           | 选择（`selection`）为主   |
| 默认选中模式   | `none`                         | `single`                  |
| 触发器文本同步 | 无（触发器外观由用户自管）     | 自动显示选中项文案        |
| 单项配色       | 支持（`items` 里给 `color`）   | 无（整表统一配色）        |

## 设计说明

- **触发器不吞事件**：触发器是 `QAbstractButton` 时走 `clicked` 连接，用户自己的 `clicked` 回调照常触发；非按钮 widget 走鼠标释放事件。
- **浮层不缩放触发器**：`trigger_scale_on_open=False`，避免 Button 被放大导致菜单锚点抖动。
- **菜单宽度**：取 `max(触发器宽度, min_width)`，短触发器也能撑出可读的菜单。
- **菜单高度**：默认完全由内容撑开（只被触发器到屏幕底的可用高度截断）。传入 `max_height` 后固定为该高度，内容更高时滚动。浮层高度上下限都锁死在同一个值上 —— 只设下限的话，Qt 的 `QScrollArea` 会拿自己缓存的 `sizeHint` 参与布局，把浮层撑高并在底部留出一截空白。
- **高度只按内容算一次**：内容高度由可见子项的 `sizeHint` 累加得出，不读 `Listbox.minimumSizeHint()` —— 后者在首次 show 前后会变化（布局激活 + 滚动区拉伸），会让首开与后续打开的高度不一致。展开后组件还会再校一次并按需重定位浮层。
- **单项配色**：Listbox 统一下发样式会覆盖单项颜色，因此组件在每次样式变更后重新下发带 `color` 的菜单项。
