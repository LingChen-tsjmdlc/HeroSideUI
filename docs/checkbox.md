# Checkbox

基于 HeroUI v2 [checkbox](https://v2.heroui.com/docs/components/checkbox) 复刻的多选框。继承 `QCheckBox`，保留原生 API（`stateChanged` / `toggled` / `setChecked` / `isChecked`），外观全部通过 `paintEvent` 自绘，以完美对齐 HeroUI 的视觉表现。

## 特性

- **6 种颜色**: `default` · `primary` · `secondary` · `success` · `warning` · `danger`
- **3 种尺寸**: `sm`（16×16 box + text-small）· `md`（20×20 + text-medium，默认）· `lg`（24×24 + text-large）
- **5 种圆角**: `none` · `sm` · `md` · `lg` · `full`（未指定时跟随 size 自动计算）
- **lineThrough**: 选中时给 label 画动态延伸的删除线，label 不透明度降至 0.6
- **indeterminate**: 未定态（画 `-` 图标）
- **isDisabled / isInvalid / disableAnimation**: 状态切换
- **theme**: `light` / `dark` 双主题
- **动画**:
  - 选中填充：`scale 0.5 → 1`、`opacity 0 → 1`，200ms 线性
  - check 图标：淡入
  - 按压：scale 0.95
  - lineThrough：下划线宽度从 0 展开到 100%

## 快速开始

```python
from hero_side_ui import Checkbox

cb = Checkbox("Remember me", color="primary")
cb.toggled.connect(lambda ok: print("checked:", ok))
```

## 参数

| 参数                | 类型                                                                          | 默认值      | 说明                                                    |
| ------------------- | ----------------------------------------------------------------------------- | ----------- | ------------------------------------------------------- |
| `text`              | `str`                                                                         | `""`        | label 文字（也可用 `setText` 动态修改）                 |
| `is_selected`       | `bool`                                                                        | `False`     | 初始选中（等同 `setChecked(True)`）                     |
| `color`             | `"default" \| "primary" \| "secondary" \| "success" \| "warning" \| "danger"` | `"primary"` | 选中态填充色                                            |
| `size`              | `"sm" \| "md" \| "lg"`                                                        | `"md"`      | 组件尺寸                                                |
| `radius`            | `"none" \| "sm" \| "md" \| "lg" \| "full" \| None`                            | `None`      | `None` 时使用默认 md (8px)；显式可传 none/sm/md/lg/full |
| `line_through`      | `bool`                                                                        | `False`     | 选中时 label 加删除线                                   |
| `is_disabled`       | `bool`                                                                        | `False`     | 禁用（半透明 + 不响应鼠标）                             |
| `is_invalid`        | `bool`                                                                        | `False`     | 无效态（边框 / label 变 `danger`）                      |
| `is_indeterminate`  | `bool`                                                                        | `False`     | 未定态（总是画填充，图标为 `-`）                        |
| `disable_animation` | `bool`                                                                        | `False`     | 关闭填充/删除线/按压动画                                |
| `theme`             | `"light" \| "dark"`                                                           | `"light"`   | 主题                                                    |
| `value`             | `str \| None`                                                                 | `text`      | 在 `CheckboxGroup` 中使用的唯一标识                     |

## 信号

- 所有 `QCheckBox` 原生信号（`stateChanged(int)` / `toggled(bool)` / `clicked(bool)` / `pressed()` / `released()`）原样可用。

## 动态 API

```python
cb.set_color("success")
cb.set_size("lg")
cb.set_radius("full")
cb.set_theme("dark")
cb.set_line_through(True)
cb.set_is_disabled(True)
cb.set_is_invalid(True)
cb.set_is_indeterminate(True)
cb.set_disable_animation(True)
cb.setChecked(True)        # 原生
cb.set_is_selected(True)   # 别名
cb.is_selected()           # 别名 isChecked()
```

## CheckboxGroup

包装多个 `Checkbox`，统一管理颜色/尺寸/圆角/主题/方向，并提供 `label` / `description` / `errorMessage`、必填标记、以及 `value_changed` 信号返回当前选中的 `value` 列表。

```python
from hero_side_ui import CheckboxGroup

group = CheckboxGroup(
    label="Pick your stack",
    description="选择你喜欢的技术",
    color="primary",
    orientation="vertical",      # 或 "horizontal"
    default_value=["react"],
)
group.create_checkbox("React", value="react")
group.create_checkbox("Vue", value="vue")
group.create_checkbox("Svelte", value="svelte")

group.value_changed.connect(lambda vals: print(vals))
print(group.value())   # ["react"]
group.set_value(["vue", "svelte"])
```

### CheckboxGroup 参数

| 参数                                                   | 类型                         | 默认值       | 说明                     |
| ------------------------------------------------------ | ---------------------------- | ------------ | ------------------------ |
| `label`                                                | `str`                        | `""`         | 顶部 label               |
| `description`                                          | `str`                        | `""`         | 帮助文字                 |
| `error_message`                                        | `str`                        | `""`         | `is_invalid=True` 时展示 |
| `orientation`                                          | `"horizontal" \| "vertical"` | `"vertical"` | 子 checkbox 排布方向     |
| `color` / `size` / `radius` / `line_through` / `theme` |                              | —            | 应用到全部子 checkbox    |
| `is_disabled` / `is_invalid` / `is_required`           | `bool`                       | `False`      | 状态                     |
| `default_value`                                        | `list[str]`                  | `[]`         | 初始选中值集合           |

### CheckboxGroup 方法

- `add_checkbox(cb)`：添加已构造的 `Checkbox`（会继承 group 的样式）
- `create_checkbox(text, value=None)`：便利方法，一步到位
- `value()` / `set_value(list)`：读写选中值
- 动态 API：`set_color` / `set_size` / `set_radius` / `set_theme` / `set_orientation` / `set_is_disabled` / `set_is_invalid` / `set_is_required` / `set_label` / `set_description` / `set_error_message` / `set_line_through`

信号：

- `value_changed(list[str])`：任一子 checkbox 选中状态变化时发射当前选中值列表

## 与 HeroUI 的差异

- HeroUI 使用 tailwind `before` / `after` 伪元素叠加，这里用 `QPainter` 自绘两层（边框层 + 填充层）复现。
- HeroUI 的 hover `group-data-[hover=true]:before:bg-default-100` 改为直接在 box 下方多绘制一个淡色圆角矩形。
- 动画曲线对齐 HeroUI：fill 使用线性 200ms（`!ease-linear !duration-200`），其他过渡用 `OutCubic`。
- 按压缩放使用 Qt `QPainter.translate + scale` 实现（整 box 绕中心 0.95x），避免与嵌套 `QGraphicsEffect` 冲突。
