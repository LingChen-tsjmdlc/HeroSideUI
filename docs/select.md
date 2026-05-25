# Select

基于 [HeroUI v2 Select](https://v2.heroui.com/docs/components/select) 复刻的下拉选择框。点击触发钮展开 popover 列表，**不允许键入**——可以理解为 `Autocomplete` 的"降级版"，复用相同的 Input 视觉容器，但 line_edit 永久 readOnly + PointingHandCursor。

内部组合：`Input`（trigger） + `Popover` + `ScrollShadow` + `Listbox`，零修改既有组件。

## 快速开始

```python
from hero_side_ui import Select

sel = Select(
    label="Favorite Animal",
    placeholder="Select an animal",
    items=[
        {"key": "cat", "label": "Cat", "description": "Domestic feline"},
        {"key": "dog", "label": "Dog"},
        {"key": "elephant", "label": "Elephant"},
    ],
    default_selected_keys={"cat"},
)
sel.selection_changed.connect(lambda key: print(f"selected: {key}"))
```

## 与 Autocomplete 的差异

| 行为                  | Autocomplete | Select                     |
| --------------------- | ------------ | -------------------------- |
| 键入过滤              | ✅           | ❌                         |
| 多选                  | 单选         | `single` / `multiple`      |
| 触发钮可输入          | ✅           | ❌（强制 readOnly + 手型） |
| `is_clearable`        | 默认 `True`  | 默认 `False`               |
| `allows_custom_value` | 有           | 无（必须从 items 选）      |

## API

### 构造参数

| 参数                                                         | 类型                                                         | 默认                 | 说明                                                                                            |
| ------------------------------------------------------------ | ------------------------------------------------------------ | -------------------- | ----------------------------------------------------------------------------------------------- |
| **数据**                                                     |                                                              |                      |                                                                                                 |
| `items`                                                      | `Iterable[dict \| tuple \| ListboxItem]`                     | `None`               | 选项列表（dict 支持 label/key/description/start_content/end_content/shortcut/is_disabled 字段） |
| **选中**                                                     |                                                              |                      |                                                                                                 |
| `selection_mode`                                             | `"single" \| "multiple"`                                     | `"single"`           | 单选 / 多选                                                                                     |
| `selected_keys` / `default_selected_keys`                    | `Iterable[str]`                                              | `None`               | 受控 / 非受控初始选中集合                                                                       |
| `disabled_keys`                                              | `Iterable[str]`                                              | `None`               | 禁用项 key 集合                                                                                 |
| `disallow_empty_selection`                                   | `bool`                                                       | `False`              | `True` 时不允许从有→空（撤销最后一个选中会被还原）                                              |
| **行为**                                                     |                                                              |                      |                                                                                                 |
| `is_clearable`                                               | `bool`                                                       | `False`              | 右侧 clear 按钮（有值 + hover/focus 时显示）                                                    |
| **视觉**                                                     |                                                              |                      |                                                                                                 |
| `selector_icon` / `clear_icon`                               | `str`                                                        | 内置                 | svg 名或路径                                                                                    |
| `disable_selector_icon_rotation`                             | `bool`                                                       | `False`              | `False` 时打开 popover 旋转 180°                                                                |
| `empty_content`                                              | `Optional[str]`                                              | `None`               | `None` → Listbox 默认 icon + 中英双语；非空 str → 单行文字                                      |
| `placeholder`                                                | `str`                                                        | `"Select an option"` | 触发钮无值时的占位文案                                                                          |
| **Input 透传**                                               |                                                              |                      |                                                                                                 |
| `label` / `description`                                      | `str`                                                        | `""`                 | 标签 / 辅助描述                                                                                 |
| `variant`                                                    | `flat \| faded \| bordered \| underlined`                    | `"flat"`             | trigger 变体                                                                                    |
| `color`                                                      | `default / primary / secondary / success / warning / danger` | `"default"`          | 同时驱动 trigger 着色 + listbox 高亮 + selector 图标颜色                                        |
| `size`                                                       | `sm / md / lg`                                               | `"md"`               | 三档预设                                                                                        |
| `radius`                                                     | `none / sm / md / lg / full`                                 | `None`               | trigger 圆角                                                                                    |
| `label_placement`                                            | `inside / outside / outside-left / outside-top`              | `"inside"`           | label 位置                                                                                      |
| `start_content`                                              | `str \| QWidget`                                             | `None`               | 触发钮左侧内容（icon 名 / 自定义 widget）                                                       |
| `is_disabled` / `is_invalid` / `is_required` / `is_readonly` | `bool`                                                       | `False`              | 状态标记。`is_readonly=True` 时 popover 仍可打开浏览，但所有 item 都不可选（对齐 HeroUI 语义）  |
| **Listbox 透传**                                             |                                                              |                      |                                                                                                 |
| `listbox_variant`                                            | `solid / shadow / bordered / flat / faded / light`           | `"flat"`             | 列表行 hover 样式                                                                               |
| `listbox_color`                                              | 同 `color` 枚举                                              | `None`               | `None` 跟随 `color`；显式传可以让 trigger 着色和列表 hover 色分开                               |
| **其他**                                                     |                                                              |                      |                                                                                                 |
| `disable_animation`                                          | `bool`                                                       | `False`              | 关闭所有过渡动画                                                                                |
| `theme`                                                      | `auto \| light \| dark`                                      | `"auto"`             | `auto` 跟随 ThemeProvider                                                                       |

### 信号

| 信号                         | 触发时机         | 参数                                            |
| ---------------------------- | ---------------- | ----------------------------------------------- |
| `selection_changed(payload)` | 选中变化         | single → `Optional[str]`；multiple → `set[str]` |
| `open_changed(bool)`         | popover 开关变化 | `is_open`                                       |
| `closed()`                   | popover 关闭     | —                                               |
| `cleared()`                  | clear 按钮点击   | —                                               |

### 常用方法

| 方法                                                                    | 说明                            |
| ----------------------------------------------------------------------- | ------------------------------- |
| `set_items(items)`                                                      | 重置 items                      |
| `items()` / `item_by_key(key)`                                          | 访问当前所有 item / 按 key 查   |
| `selected_keys()` / `selected_key()`                                    | 读取选中 keys / single 便捷读取 |
| `set_selected_keys(keys)` / `set_selected_key(key)`                     | 设置选中                        |
| `is_open()` / `open()` / `close()` / `toggle()`                         | popover 控制                    |
| `set_selection_mode(mode)`                                              | 动态切换 single / multiple      |
| `set_disabled_keys(keys)`                                               | 动态设置禁用项                  |
| `set_disallow_empty_selection(v)`                                       | 动态切换"不允许空"              |
| `set_empty_content(text)`                                               | 动态设置空状态文案              |
| `set_variant / set_color / set_size / set_radius / set_label_placement` | 动态更新 trigger 样式           |
| `set_is_disabled / set_is_invalid / set_is_required / set_is_readonly`  | 动态状态                        |
| `set_is_clearable / set_disable_selector_icon_rotation`                 | 动态行为开关                    |

### 键盘

- `↓` / `↑`：popover 未开时打开并聚焦第一个可用项；已开时移动焦点
- `Home` / `End`：跳到首/尾可用项
- `Enter` / `Space`：popover 未开时打开；已开时激活当前焦点项
- `Escape`：关闭 popover

## 多选行为

`selection_mode="multiple"` 下：

- 选中**不会**自动关闭 popover（对齐 HeroUI），方便连续多选
- trigger 文本按 items 顺序拼接成 `"Apple, Banana, Cherry"`
- 超过 `SELECT_SIZES[size].chip_max`（sm=2, md/lg=3）时折叠为 `"Apple, Banana, Cherry, +N"`
- `selection_changed` 发出 `set[str]`

```python
sel = Select(
    items=FRUITS,
    selection_mode="multiple",
    default_selected_keys={"apple", "banana"},
)
sel.selection_changed.connect(lambda keys: print(keys))  # set
```

## 设计对照（HeroUI v2）

| HeroUI slot      | HeroSideUI 实现                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------- |
| `base`           | `Select` 自身 QVBoxLayout                                                                   |
| `trigger`        | 复用 `Input`（line_edit setReadOnly + PointingHandCursor + 拦点击事件）                     |
| `value`          | `Input.line_edit`（show 选中文本 / placeholder）                                            |
| `popoverContent` | `Popover` 的 content QWidget                                                                |
| `listboxWrapper` | `ScrollShadow`（纵向滚动 + 渐变阴影）                                                       |
| `listbox`        | `Listbox(selection_mode=…)`                                                                 |
| `clearButton`    | `Button(variant="light", color="default", size="sm", icon_only=True)`（hover/focus 时显示） |
| `selectorIcon`   | `_SelectorButton`（chevron-down + QTransform 旋转动画）                                     |

Slot variants 对齐：

- `selectionMode=single/multiple` → 选中后是否关闭 popover；trigger 文本单个 / 拼接 + N
- `disallowEmptySelection=True/False` → 撤销最后一个选中是否被还原
- `isClearable=True/False` → clear 按钮显隐
- `disableSelectorIconRotation=True/False` → selector 图标 open 时是否旋转 180°
- `disableAnimation=True/False` → 关闭 rotate tween / popover fade

## 典型场景

### 单选 + clearable

```python
sel = Select(
    label="Country",
    items=COUNTRIES,
    color="primary",
    is_clearable=True,
)
```

### 多选 + 强制非空

```python
sel = Select(
    label="Permissions",
    items=PERMS,
    selection_mode="multiple",
    disallow_empty_selection=True,
    default_selected_keys={"read"},
    color="success",
)
```

### 禁用特定选项

```python
sel = Select(
    items=PLANS,
    disabled_keys={"enterprise", "custom"},
)
```

### 分开 trigger 色与列表 hover 色

```python
sel = Select(
    items=[...],
    color="primary",        # trigger 蓝色
    listbox_color="success", # 列表行 hover 绿色
)
```
