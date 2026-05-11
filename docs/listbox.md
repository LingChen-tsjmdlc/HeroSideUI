# Listbox

HeroUI v2 风格的列表框组件，可作为独立菜单使用，也是 Autocomplete / Select 等组合组件的基础构件。

## 快速开始

```python
from hero_side_ui import Listbox

lb = Listbox()
lb.add_item("New file",   key="new",   description="Create a new file", shortcut="Ctrl+N")
lb.add_item("Copy link",  key="copy",  description="Copy item link",    shortcut="Ctrl+L")
lb.add_item("Delete",     key="del",   description="Delete this file",  shortcut="⌫")
lb.action.connect(lambda key: print(f"activated: {key}"))
```

## API

### Listbox

| 参数                             | 类型 / 取值                                                            | 默认          | 说明                                                                                     |
| -------------------------------- | ---------------------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------- |
| `variant`                        | `solid` / `shadow` / `bordered` / `flat` / `faded` / `light`           | `solid`       | item hover/选中外观                                                                      |
| `color`                          | `default` / `primary` / `secondary` / `success` / `warning` / `danger` | `default`     | item 高亮配色                                                                            |
| `size`                           | `sm` / `md` / `lg`                                                     | `md`          | 字号 + padding 三档预设                                                                  |
| `radius`                         | `none` / `sm` / `md` / `lg` / `full`                                   | `sm`          | item 自身圆角                                                                            |
| `selection_mode`                 | `none` / `single` / `multiple`                                         | `none`        | 选择模式                                                                                 |
| `selected_keys`                  | `Iterable[str]`                                                        |
| `None`                           | 初始选中 key 集合                                                      |
| `disabled_keys`                  | `Iterable[str]`                                                        | `None`        | 禁用 key 集合                                                                            |
| `empty_content`                  | `Optional[str]`                                                        | `None`        | 空集合时显示文案。`None`（默认）→ icon + 中英双语 (`Nothing to show / 暂无内容`)；非空 `str` → 单行文字 |
| `hide_selected_icon`             | `bool`                                                                 | `False`       | 隐藏选中态右侧勾标（默认显示；显示时会在右侧预留槽位，避免与 shortcut/end_content 重叠） |
| `should_highlight_on_focus`      | `bool`                                                                 | `False`       | 键盘聚焦时是否使用 hover 视觉                                                            |
| `disable_animation`              | `bool`                                                                 | `False`       | 关闭过渡动画                                                                             |
| `is_disabled`                    | `bool`                                                                 | `False`       | 整体禁用                                                                                 |
| `top_content` / `bottom_content` | `QWidget`                                                              | `None`        | 上 / 下方插入额外内容                                                                    |
| `theme`                          | `auto` / `light` / `dark`                                              | `auto`        | 主题；`auto` 跟随系统                                                                    |

#### 装配 API（插槽）

```python
lb.add_item("Title", key="key", description="...", shortcut="Ctrl+S", is_disabled=False)
lb.add_item(ListboxItem(...))              # 也可以传现成 item
lb.add_section(ListboxSection("Group"))    # 或 lb.add_section("Group")
lb.clear()
lb.items()              # -> list[ListboxItem]，含 section 内
lb.item_by_key("key")   # -> ListboxItem | None
```

#### 选中 / 禁用

```python
lb.set_selection_mode("single")      # none / single / multiple
lb.selected_keys()                   # -> set[str]
lb.set_selected_keys({"a", "b"})
lb.set_disabled_keys({"admin"})
lb.set_is_disabled(True)             # 整体灰禁
```

#### 信号

| 信号                     | 触发时机                                   | 参数       |
| ------------------------ | ------------------------------------------ | ---------- |
| `action(str)`            | 单击或 Enter 任意可用项                    | `key`      |
| `selection_changed(set)` | 选中集合变化（`single` / `multiple` 模式） | `set[str]` |

> 在 `selection_mode="none"` 下只有 `action` 触发，没有选中态变化。

#### 键盘导航 (未完善)

- `↑` / `↓`：在可用项之间移动焦点
- `Home` / `End`：跳到第一个 / 最后一个可用项
- `Enter` / `Space`：触发当前焦点项（等同点击）

### ListboxItem

```python
ListboxItem(
    title="Hello",
    key="hello",                # 缺省取 title
    description="optional",
    start_content=None,         # str (svg 名/路径) 或 QWidget
    end_content=None,
    shortcut="Ctrl+H",
    is_disabled=False,
    show_divider=False,
)
```

`ListboxItem` 是 `QAbstractButton` 的子类，自带 `clicked` 等原生信号；选中态通过 `set_selected(bool)` 控制，并会发 `selected_changed(bool)`。同时新增的 `activated(key)` 信号在用户点击时发出。

> ⚠️ 不要手动调 `apply_style(...)` —— 父 `Listbox` 会在添加 / 设置变化时自动重刷整套样式给所有 item。

### ListboxSection

```python
sec = ListboxSection(title="Actions", show_divider=True)
sec.add_item("Copy",  key="copy",  shortcut="Ctrl+C")
sec.add_item("Paste", key="paste", shortcut="Ctrl+V")
lb.add_section(sec)
```

`heading` 字号 = `desc_font_size`（12 / md）、颜色 = `default-500`。`show_divider=True` 时在 section 底部画一条分隔线（mb-2 + mt-2 视觉间距）。

## 设计对照（HeroUI v2）

源样式定义来自 HeroUI v2 [`menu.ts`](https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/menu.ts)（listbox 与 menu 共享样式）。我们对齐了：

- `slots`: `base / list / emptyContent`（Listbox）；`base / wrapper / title / description / selectedIcon / shortcut`（ListboxItem）；`base / heading / group / divider`（ListboxSection）。
- `variants`: `variant × color × showDivider × isDisabled × disableAnimation` 完整组合（30 个 compoundVariants 已通过 `_hover_bg / _hover_border / _text_hover` 解析函数还原）。
- `defaults`: `variant=solid / color=default / showDivider=false`。

## 主题

- `theme="auto"` 默认注册到 `ThemeProvider`，跟随系统亮 / 暗主题。Card 等容器底色变化时也会自动跟（通过 `palette.Window` 传播）。
- 显式 `theme="light"` / `theme="dark"` 时会硬锁不参与全局切换。
- 主题切换时所有子项自动用 `tween_value` 平滑插值字色 / 背景色（150ms OutCubic）。

## 用法范例

### 单选 + 主题感知

```python
from hero_side_ui import Listbox, Card, CardBody

lb = Listbox(variant="flat", color="primary", selection_mode="single")
lb.add_item("Read",  key="read")
lb.add_item("Write", key="write")
lb.add_item("Admin", key="admin", is_disabled=True)
lb.set_selected_keys({"read"})

# 套到 Card 里 ScrollShadow 自动跟随 Card 底色
card = Card()
body = CardBody()
body.layout().addWidget(lb)
card.add_body(body)
```

### 分组 + showDivider + shortcut

```python
from hero_side_ui import Listbox, ListboxSection

lb = Listbox(variant="flat", color="primary", selection_mode="single")

actions = ListboxSection("Actions", show_divider=True)
actions.add_item("Copy",  key="copy",  shortcut="Ctrl+C")
actions.add_item("Paste", key="paste", shortcut="Ctrl+V")
lb.add_section(actions)

danger = ListboxSection("Danger zone")
danger.add_item("Delete", key="del", shortcut="⌫", description="Permanently remove")
lb.add_section(danger)
```

### 多选 + emptyContent

```python
multi = Listbox(variant="flat", color="success", selection_mode="multiple",
                empty_content="🍂 Nothing here.")
multi.add_item("Free",       key="free")
multi.add_item("Pro",        key="pro")
multi.add_item("Enterprise", key="ent")

multi.selection_changed.connect(lambda keys: print("selected:", keys))
```
