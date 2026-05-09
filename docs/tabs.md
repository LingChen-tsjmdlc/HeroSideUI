# Tabs

基于 HeroUI v2 [tabs](https://v2.heroui.com/docs/components/tabs) 复刻的标签页组件。完整对齐 [HeroUI 源码](https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/tabs.ts)。

## 特性

- **4 种 variant**：`solid` / `bordered` / `light` / `underlined`
- **6 种 color**：`default` / `primary` / `secondary` / `success` / `warning` / `danger`
- **3 种 size**：`sm`（h28/12px）/ `md`（h32/13px）/ `lg`（h36/15px）
- **5 种 radius**：`none` / `sm` / `md` / `lg` / `full`（`underlined` 强制 `none`）
- **4 种 placement**：`top` / `bottom` / `start` / `end`（左右两侧）
- **light/dark 双主题**
- **`full_width`**：tabList 占满父容器
- **`is_disabled`**：整体禁用（50% 透明 + 屏蔽点击）
- **`disable_animation`**：关闭 cursor 几何动画 + 文字色过渡
- **cursor 动画**：250ms `OutCubic`，几何过渡（`left/top/width/height`），首次选中不动画
- **hover 行为**：未选中 tab hover 时整体 50% 透明，对齐 HeroUI `hover-unselected:opacity-disabled`
- **选中文字色平滑过渡**：150ms OutCubic（QVariantAnimation 驱动 QColor 插值）
- **下划线 cursor**：`underlined` variant 时画底部 2px、宽度 80% 的彩色线条

## 快速开始

```python
from hero_side_ui import Tabs

tabs = Tabs(["Photos", "Music", "Videos"])
tabs.show()
```

## 用 widget 作为 panel 内容

```python
from PySide6.QtWidgets import QLabel
from hero_side_ui import Tabs, Card, CardBody

tabs = Tabs(variant="bordered", color="primary")
tabs.add_tab("Login", QLabel("登录表单"))
tabs.add_tab("Sign Up", QLabel("注册表单"))
tabs.add_tab("Forgot", QLabel("忘记密码"), key="forgot")
```

## 监听切换

```python
tabs.selection_changed.connect(
    lambda idx, key: print(f"切到 #{idx} key={key}")
)
```

## 4 种 variant 对照

```python
Tabs(["a", "b", "c"], variant="solid")       # 默认：底色 default-100
Tabs(["a", "b", "c"], variant="light")       # 透明底，纯填充 cursor
Tabs(["a", "b", "c"], variant="bordered")    # 透明底 + 边框
Tabs(["a", "b", "c"], variant="underlined")  # 透明底 + 底部 2px 下划线
```

## 4 种 placement 布局

| placement | tabList 位置 | 列表方向 |
| --------- | ------------ | -------- |
| `top`     | 内容上方     | 水平     |
| `bottom`  | 内容下方     | 水平     |
| `start`   | 内容左侧     | 垂直     |
| `end`     | 内容右侧     | 垂直     |

```python
tabs = Tabs(["a", "b"], placement="start")
```

## 参数

| 参数                | 类型                                                         | 默认值    | 说明                                                                                                |
| ------------------- | ------------------------------------------------------------ | --------- | --------------------------------------------------------------------------------------------------- |
| `items`             | `List[str / tuple / dict]`                                   | `None`    | 初始 tab。tuple `(title, content)` 或 `(title, content, key)`，dict 含 `title/content/key/disabled` |
| `variant`           | `solid / bordered / light / underlined`                      | `solid`   | 视觉变体                                                                                            |
| `color`             | `default / primary / secondary / success / warning / danger` | `default` | 主色                                                                                                |
| `size`              | `sm / md / lg`                                               | `md`      | 尺寸                                                                                                |
| `radius`            | `none / sm / md / lg / full`                                 | `md`      | 圆角；`underlined` 时强制 `none`                                                                    |
| `placement`         | `top / bottom / start / end`                                 | `top`     | tabList 相对内容面板的位置                                                                          |
| `theme`             | `light / dark`                                               | `light`   | 主题                                                                                                |
| `full_width`        | `bool`                                                       | `False`   | tabList 是否占满父容器                                                                              |
| `is_disabled`       | `bool`                                                       | `False`   | 整体禁用                                                                                            |
| `disable_animation` | `bool`                                                       | `False`   | 关闭 cursor 几何动画 + 文字色过渡                                                                   |

## 方法

| 方法                                                                                                             | 说明                                                                             |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `add_tab(title, content=None, key=None, disabled=False, start_icon=None, end_icon=None, custom=None) -> TabItem` | 追加一个 tab，返回 TabItem。`start_icon/end_icon` 触发档 2；传 `custom` 触发档 3 |
| `remove_tab(index)`                                                                                              | 移除指定 index 的 tab                                                            |
| `clear()`                                                                                                        | 清空所有 tab                                                                     |
| `count() -> int`                                                                                                 | 当前 tab 数量                                                                    |
| `tab_at(index) -> TabItem`                                                                                       | 获取 TabItem                                                                     |
| `panel_at(index) -> QWidget`                                                                                     | 获取对应 panel widget                                                            |
| `current_index() -> int`                                                                                         | 当前选中的 index                                                                 |
| `current_key() -> str`                                                                                           | 当前选中的 key                                                                   |
| `set_selected(index_or_key, animate=True)`                                                                       | 切换到指定 tab（支持 index 或 key）                                              |
| `set_variant / set_color / set_size / set_radius`                                                                | 动态更换变体/颜色/尺寸/圆角                                                      |
| `set_placement / set_theme / set_full_width`                                                                     | 动态更换布局/主题/宽度                                                           |
| `set_disabled / set_disable_animation`                                                                           | 整体禁用 / 关闭动画                                                              |

## 信号

| 信号                          | 触发参数       | 说明                |
| ----------------------------- | -------------- | ------------------- |
| `selection_changed(int, str)` | `(index, key)` | 选中 tab 改变时触发 |

## TabItem

`TabItem` 继承自 `QAbstractButton`，由 `add_tab(...)` 返回。**支持三档插槽**：

### 档 1 — 纯文本（默认）

```python
tabs.add_tab("Photos")
```

### 档 2 — icon + 文本

```python
tabs.add_tab(
    "Photos",
    start_icon="heroicons--eye-solid",         # 内置 heroicons 名（不含 .svg）
    end_icon="/path/to/external.svg",          # 也支持外部 SVG 路径
)
```

icon 由 `hero_side_ui.utils.icon_utils.load_svg_icon` 加载，**自动跟随当前文字色着色** —— 选中/hover/暗色模式下颜色会和文字同步过渡。`start_icon`/`end_icon` 也可直接传一个已加载的 `QPixmap`。

### 档 3 — 完全自定义 tab 标签

```python
my_widget = QWidget()  # 自己拼的任何 widget（红点徽标、avatar、迷你 chart...）
...
tabs.add_tab(custom=my_widget, content=panel)
```

- TabItem 把 `custom` widget 作为子控件填满，不再画文字/图标
- hover-unselected (50%) 与 disabled (30%) 透明度仍然通过 `QGraphicsOpacityEffect` 套在整个 custom widget 上
- **选中态**由 custom widget 自管：监听 `TabItem.selected_changed(bool)` 信号即可
- `title` 此时仅作为 `key` 的 fallback

### TabItem 单独操作

```python
tab = tabs.add_tab("Photos")
tab.set_disabled(True)
tab.set_title("照片")
tab.set_start_icon("heroicons--check-solid")
tab.set_end_icon(None)            # 清掉
tab.set_custom(my_widget)         # 切换到档 3
tab.set_custom(None)              # 回退到档 1/2
tab.selected_changed.connect(lambda checked: print("now", checked))
```

## 设计对齐说明

- 文件 `hero_side_ui/themes/component_presets/tabs.py` 中 `TABS_SIZES` 收纳了 sm/md/lg 全部尺寸常量。
- `compoundSlots` 规则 `underlined → rounded-none` 已在构造与 `set_variant/set_radius` 中强制实现。
- HeroUI 的 `text-default-foreground / text-{color}-foreground` 文字对比色映射，写死在 `_resolve_selected_text(...)`：
  - `default`：light=`#000000`，dark=`#FFFFFF`
  - `warning`：`#000000`（冷色调用黑字）
  - 其他色：`#FFFFFF`
- `solid` 变体下 `default` 色 cursor 在亮色画白底 + 轻量 `shadow-small`（自绘多层半透阴影模拟），暗色画 `default-700` 块。
- `disable_animation=True` 时按 HeroUI `compoundVariants` 规则**直接写死选中态颜色**（不走过渡）。
