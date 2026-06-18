# Table

HeroUI v2 风格的表格组件。每个单元格都是独立的自绘 widget，可承载纯文本或任意自定义 widget（Chip、Button 等）。支持单选/多选、斑马纹、紧凑模式、排序、自定义渲染、空状态与 top/bottom 内容区。

## 快速开始

```python
from hero_side_ui import Table

t = Table()
t.set_columns([
    {"key": "name",   "label": "NAME"},
    {"key": "role",   "label": "ROLE"},
    {"key": "status", "label": "STATUS"},
])
t.set_rows([
    {"key": "1", "name": "Tony", "role": "CEO",  "status": "Active"},
    {"key": "2", "name": "Zoey", "role": "Lead", "status": "Paused"},
])
```

## API

### Table

| 参数 | 类型 / 取值 | 默认 | 说明 |
| --- | --- | --- | --- |
| `color` | `default` / `primary` / `secondary` / `success` / `warning` / `danger` | `default` | 选中行条与选中字色的配色 |
| `size` | `sm` / `md` / `lg` | `md` | 字号 + 行高 + padding 三档预设 |
| `radius` | `none` / `sm` / `md` / `lg` / `full` | `lg` | 表头与选中/hover 行条的圆角；`full` 时行条变药丸，外壳 Card 自动退回 `lg`（不跟随 full） |
| `shadow` | `none` / `sm` / `md` / `lg` | `sm` | wrapper 阴影（复用内置 Card 的阴影系统） |
| `layout` | `auto` / `fixed` | `auto` | 列宽策略 |
| `selection_mode` | `none` / `single` / `multiple` | `none` | 选择模式；`multiple` 时首列出现 checkbox 与全选 |
| `selected_keys` | `Iterable[str]` | `None` | 初始选中行 key |
| `disabled_keys` | `Iterable[str]` | `None` | 禁用行 key（不可选、半透明） |
| `disallow_empty_selection` | `bool` | `False` | 禁止取消最后一个选中项 |
| `is_striped` | `bool` | `False` | 斑马纹（奇数行行条底色） |
| `is_compact` | `bool` | `False` | 紧凑行高 |
| `hide_header` | `bool` | `False` | 隐藏表头行 |
| `full_width` | `bool` | `True` | 占满父容器宽度，数据列平分剩余空间 |
| `remove_wrapper` | `bool` | `False` | 不渲染外壳 Card（背景/阴影/圆角） |
| `empty_content` | `Optional[str]` | `None` | 无数据时显示的文案 |
| `top_content` / `bottom_content` | `QWidget` | `None` | 顶部 / 底部内容区（搜索框、分页器等） |
| `top_content_placement` / `bottom_content_placement` | `inside` / `outside` | `inside` | 内容区放卡片内还是卡片外（工具栏/分页通常用 `outside`） |
| `max_height` | `Optional[int]` | `None` | 表体最大高度（px），超出内部纵向滚动（套 ScrollShadow） |
| `is_header_sticky` | `bool` | `False` | 滚动时表头钉在顶部（实验性，需配合 `max_height`） |
| `is_virtualized` | `bool` | `False` | 虚拟化：只渲染可视区行，万行流畅滚动（需要 `max_height`，未给时兜底 420） |
| `disable_animation` | `bool` | `False` | 关闭行条过渡动画 |
| `theme` | `auto` / `light` / `dark` | `auto` | 主题 |

### 性能：行复用与虚拟化

- **行复用（默认）**：翻页 / `set_rows` 换数据时，列结构不变则不销毁重建单元格，
  而是复用已有行槽——cell 原地更新文本、改归属 key，多退少补。显著降低翻页开销。
- **虚拟化（`is_virtualized=True`）**：只为"可视区 + 缓冲"创建固定数量行槽，上下用
  spacer 撑出滚动总高，滚动时复用行槽重填内容。内存与渲染开销与可视行数成正比、
  与总行数无关，可承载上万行。代价：行高统一（取 token 行高），自定义高行内容会被
  按统一高度排布；适合规整数据表，不适合每行高度差异大的场景。

```python
t = Table(is_virtualized=True, is_header_sticky=True, max_height=460,
          selection_mode="multiple")
t.set_columns(cols)
t.set_rows(ten_thousand_rows)   # 流畅
```

### 装配 API

```python
t.set_columns([
    {"key": "name", "label": "NAME", "align": "start",
     "allows_sorting": False, "width": None},
])
t.add_row("1", {"name": "Tony", "role": "CEO", "status": "Active"})
t.add_row("2", ["Zoey", "Lead", "Paused"])   # list 形式按列顺序映射
t.set_rows([{ "key": "1", "name": "...", "_disabled": False }, ...])
t.clear()
t.columns()  # -> list[dict]
t.rows()     # -> list[str]  行 key 顺序
```

列定义字段：

| 字段 | 说明 |
| --- | --- |
| `key` | 列唯一标识（与行数据 dict 的键对应） |
| `label` | 表头文字 |
| `align` | `start` / `center` / `end` 单元格内容对齐 |
| `allows_sorting` | 是否可排序（表头 hover 显示箭头、点击发 `sort_changed`） |
| `width` | 固定列宽（px）；不设则参与等宽平分 |

### 自定义单元格

设置 `render_cell` 回调，对每个单元格返回 `str`（自动包 Text）或任意 `QWidget`：

```python
def render_cell(row_key, col_key, value):
    if col_key == "status":
        return Chip(value, color="success", variant="flat", size="sm")
    if col_key == "actions":
        return my_action_buttons()
    return value

t.set_render_cell(render_cell)
t.set_rows(rows)
```

### 选中 / 禁用

```python
t.set_selection_mode("multiple")     # none / single / multiple
t.selected_keys()                    # -> set[str]
t.set_selected_keys({"1", "3"})
t.set_disabled_keys({"2"})
t.set_disallow_empty_selection(True)
```

### 排序

排序在三状态间循环——**无排序 → 升序 → 降序 → 无排序**。组件只维护并广播 `sort_descriptor`，实际数据重排由使用者在槽里完成（`direction` 为 `None` 表示恢复无排序）：

```python
def on_sort(column, direction):    # direction: "ascending" / "descending" / None
    if direction is None:
        t.set_rows(original_rows)  # 恢复原始顺序
        return
    rows = sorted(data, key=lambda r: r[column], reverse=(direction == "descending"))
    t.set_rows(rows)

t.sort_changed.connect(on_sort)
```

### 信号

| 信号 | 签名 | 触发时机 |
| --- | --- | --- |
| `selection_changed` | `set` | 选中集合变化时发出新集合 |
| `row_action` | `str` | 行被点击时发出行 key（任何选择模式） |
| `sort_changed` | `(object, object)` | 点击可排序列头，发出 `(column_key, direction)`；三状态循环，无排序时为 `(None, None)` |

### 动态属性 setter

```python
t.set_color("primary")
t.set_size("lg")
t.set_radius("md")
t.set_shadow("lg")
t.set_is_striped(True)
t.set_is_compact(True)
t.set_hide_header(True)
t.set_theme("dark")
```

## 设计对照（HeroUI v2）

对齐 [`table.ts`](https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/table.ts) 与 [components/table](https://github.com/heroui-inc/heroui/tree/main/packages/components/table)：

| HeroUI slot / variant | HeroSideUI 实现 |
| --- | --- |
| `wrapper`（bg-content1, shadow, rounded） | 复用内置 **Card** 组件（自带阴影系统 + content1 背景 + 圆角 + 主题自治） |
| `th`（bg-default-100, text-tiny font-semibold） | `_TableColumnHeader` 自绘底色 + 首尾列圆角 |
| `td`（py-2 px-3, text-small） | `_TableCell` 内容槽位 + padding |
| `td::before`（选中/hover 行条） | `_TableCell.paintEvent` 自绘 before 行条；单选每行独立药丸，多选/hover 整块连续（仅表首行上圆角、表尾行下圆角、中行直角，对齐 `isMultiSelectable`） |
| `color` variants（before:bg-*/选中字色） | `_palette.selected_before_bg` / `selected_text` |
| `isStriped` / `isCompact` / `hideHeader` | 对应 props，行为一致 |
| disabled 行（text-foreground-300） | `_palette.cell_text_disabled` 灰一档 |
| `sortIcon`（chevron, ascending rotate-180） | `_SortIcon` chevron-down，ascending 旋转 180°；三状态循环 |
| select-all checkbox / 行 checkbox | 复用 `Checkbox` 组件，多选时首列注入 |

与 React 版差异：排序数据重排交由使用者（受控），组件不持有 collection；虚拟化（isVirtualized）暂未实现。

## 主题

`theme="auto"`（默认）跟随 `ThemeProvider` 全局主题自动切换 light/dark；也可硬锁 `"light"` / `"dark"`。所有颜色走 `_palette` 纯函数解析自 `HEROUI_COLORS`，主题切换时行条/表头/字色整体重刷。

## 用法范例

### 多选 + 全选

```python
t = Table(color="secondary", selection_mode="multiple")
t.set_columns(columns)
t.set_rows(rows)
t.set_selected_keys({"1", "3"})
t.selection_changed.connect(lambda keys: print("selected:", keys))
```

### 搭配分页器（bottom_content）

```python
from hero_side_ui import Pagination

pager = Pagination(total=10, initial_page=1)
t = Table(bottom_content=pager)
t.set_columns(columns)
t.set_rows(page_rows)
pager.page_changed.connect(load_page)
```
