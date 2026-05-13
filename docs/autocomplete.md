# Autocomplete

基于 [HeroUI v2 Autocomplete](https://v2.heroui.com/docs/components/autocomplete) 复刻的输入即过滤下拉补全框。内部组合现成的 `Input` + `Popover` + `ScrollShadow` + `Listbox`，零修改既有组件。

## 快速开始

```python
from hero_side_ui import Autocomplete

ac = Autocomplete(
    label="Favorite Animal",
    placeholder="Search an animal",
    items=[
        {"key": "cat", "label": "Cat", "description": "Domestic feline"},
        {"key": "dog", "label": "Dog"},
        {"key": "elephant", "label": "Elephant"},
    ],
    default_selected_key="cat",
)
ac.selection_changed.connect(lambda key: print(f"selected: {key}"))
ac.input_changed.connect(lambda text: print(f"typing: {text}"))
```

## API

### 构造参数

| 参数                             | 类型                                    | 默认      | 说明                                                                                               |
| -------------------------------- | --------------------------------------- | --------- | -------------------------------------------------------------------------------------------------- |
| **数据**                         |                                         |           |                                                                                                    |
| `items`                          | `Iterable[dict \| tuple \| ListboxItem]` | `None`    | 选项列表（dict 支持 label/key/description/start_content/end_content/shortcut/is_disabled 字段）    |
| `input_value` / `default_input_value` | `str`                             | `None`    | 输入框初始文本                                                                                     |
| `selected_key` / `default_selected_key` | `Optional[str]`                 | `None`    | 初始选中项 key                                                                                     |
| `disabled_keys`                  | `Iterable[str]`                         | `None`    | 禁用项 key 集合                                                                                    |
| **行为**                         |                                         |           |                                                                                                    |
| `default_filter`                 | `Callable[[str, str], bool]`            | contains  | 过滤函数 `(item_label, query) -> bool`。默认大小写不敏感 contains                                  |
| `allows_custom_value`            | `bool`                                  | `False`   | `True` 允许输入列表外的值；`False` 时关闭 popover 自动回退到 selected_key 对应 label（或清空）     |
| `is_clearable`                   | `bool`                                  | `True`    | 右侧 clear 按钮（有值时显示）                                                                      |
| `menu_trigger`                   | `"focus" \| "input" \| "manual"`        | `"focus"` | popover 打开触发方式                                                                               |
| **视觉**                         |                                         |           |                                                                                                    |
| `selector_icon` / `clear_icon`   | `str`                                   | 内置      | svg 名或路径                                                                                       |
| `disable_selector_icon_rotation` | `bool`                                  | `False`   | `False` 时打开 popover 旋转 180°                                                                   |
| `empty_content`                  | `Optional[str]`                         | `None`    | `None` → Listbox 默认 icon + 中英双语；非空 str → 单行文字                                          |
| **Input 透传**                   |                                         |           |                                                                                                    |
| `label` / `placeholder` / `description` | `str`                            | `""`      | 标签 / 占位符 / 辅助描述                                                                           |
| `variant`                        | `flat \| faded \| bordered \| underlined` | `"flat"`  | Input 变体                                                                                         |
| `color`                          | `default / primary / secondary / success / warning / danger` | `"default"` | 同时驱动 Input 着色和 Listbox 高亮色                         |
| `size`                           | `sm / md / lg`                          | `"md"`    | 三档预设                                                                                           |
| `radius`                         | `none / sm / md / lg / full`            | `None`    | Input 圆角                                                                                         |
| `label_placement`                | `inside / outside / outside-left / outside-top` | `"inside"` | label 位置                                                                              |
| `start_content`                  | `str \| QWidget`                        | `None`    | Input 左侧内容（icon 名 / 自定义 widget）                                                          |
| `is_disabled` / `is_invalid` / `is_required` / `is_readonly` | `bool`          | `False`   | 状态标记                                                                                           |
| **Listbox 透传**                 |                                         |           |                                                                                                    |
| `listbox_variant`                | `solid / shadow / bordered / flat / faded / light` | `"flat"` | 列表行 hover 样式                                                                   |
| `listbox_color`                  | 同 `color` 枚举                         | `None`    | `None` 跟随 `color`；显式传可以让 input 着色和列表 hover 色分开                                    |
| **其他**                         |                                         |           |                                                                                                    |
| `disable_animation`              | `bool`                                  | `False`   | 关闭所有过渡动画                                                                                   |
| `theme`                          | `auto \| light \| dark`                 | `"auto"`  | `auto` 跟随 ThemeProvider                                                                          |

### 信号

| 信号                         | 触发时机                             | 参数                  |
| ---------------------------- | ------------------------------------ | --------------------- |
| `selection_changed(Optional[str])` | 选中 key 变化（含 clear → None） | 新 key 或 `None`      |
| `input_changed(str)`         | 输入框文本变化（用户输入或选中触发） | 新文本                |
| `open_changed(bool, str)`    | popover 开关变化                     | `(is_open, trigger)`  |
| `cleared()`                  | clear 按钮点击                       | —                     |

### 常用方法

| 方法                                      | 说明                                                                               |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| `set_items(items)`                        | 重置 items                                                                         |
| `items()` / `item_by_key(key)`            | 访问当前所有 item / 按 key 查                                                       |
| `selected_key()` / `set_selected_key(k)`  | 读取 / 设置选中项                                                                   |
| `input_value()` / `set_input_value(t)`    | 读取 / 设置输入框文本                                                               |
| `is_open()` / `open()` / `close()` / `toggle()` | popover 控制                                                                  |
| `set_default_filter(fn)`                  | 动态替换过滤函数                                                                   |
| `set_disabled_keys(keys)`                 | 动态设置禁用项                                                                     |
| `set_empty_content(text)`                 | 动态设置空状态文案                                                                 |
| `set_variant / set_color / set_size / set_radius / set_label_placement` | 动态更新 Input 样式（自动透传）                         |
| `set_is_disabled / set_is_invalid / set_is_required / set_is_readonly` | 动态状态                                              |
| `set_is_clearable / set_allows_custom_value / set_disable_selector_icon_rotation` | 动态行为开关                                       |

### 键盘

- `↓` / `↑`：在可见项之间移动焦点；popover 未开时先打开
- `Enter`：选中当前焦点项
- `Escape`：关闭 popover
- 字符输入：触发过滤，popover 自动打开（除非 `menu_trigger="manual"`）

## 过滤行为

默认使用 **大小写不敏感 contains 匹配**（对齐 HeroUI / react-aria 的 `useFilter` 默认）：

```python
lambda label, query: not query or query.lower() in label.lower()
```

自定义 filter 例子（只匹配开头）：

```python
def starts_with(label: str, q: str) -> bool:
    return label.lower().startswith(q.lower()) if q else True

ac = Autocomplete(items=[...], default_filter=starts_with)
```

## 设计对照（HeroUI v2）

| HeroUI slot            | HeroSideUI 实现                                           |
| ---------------------- | --------------------------------------------------------- |
| `base`                 | `Autocomplete` 自身 QVBoxLayout                            |
| `popoverContent`       | `Popover` 的 content QWidget                               |
| `listboxWrapper`       | `ScrollShadow`（纵向滚动 + 渐变阴影）                       |
| `listbox`              | `Listbox(selection_mode="single")`                         |
| `endContentWrapper`    | `_EndContentWidget` QHBoxLayout                            |
| `clearButton`          | `Button(variant="light", color="default", size="sm", icon_only=True)`（hover/focus 时显示） |
| `selectorButton`       | `_SelectorButton`（chevron-down + QTransform 旋转动画）    |

Slots variants 对齐：
- `isClearable=True / False` → clear 按钮显隐
- `disableSelectorIconRotation=True / False` → selector 图标 open 时是否旋转 180°
- `disableAnimation=True / False` → 关闭 rotate tween / popover fade

## 典型场景

### 受控 + allows_custom_value

```python
ac = Autocomplete(
    label="Tag",
    items=EXISTING_TAGS,
    allows_custom_value=True,         # 允许用户输入新 tag
    placeholder="Existing or new tag",
)
ac.input_changed.connect(save_tag)
```

### 动态 items（远程搜索）

```python
ac = Autocomplete(label="User", menu_trigger="input")
ac.input_changed.connect(lambda q: ac.set_items(fetch_users(q)))
```

### 分开 input 色与列表 hover 色

```python
ac = Autocomplete(
    items=[...],
    color="primary",        # input focus 蓝色
    listbox_color="success", # 列表行 hover 绿色
)
```

### 禁用特定选项

```python
ac = Autocomplete(
    items=PLANS,
    disabled_keys={"enterprise", "custom"},
)
```
