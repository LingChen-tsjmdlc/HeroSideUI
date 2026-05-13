# Textarea 多行输入框

基于 [HeroUI v2 Textarea](https://v2.heroui.com/docs/components/textarea) 设计风格的多行输入组件，继承自 `QWidget`，内部嵌入 `QTextEdit` 作为实际多行输入控件，对外暴露 `Textarea.text_edit` 和常用代理方法，保持完整的 Qt 原生 API。

内置 **auto-resize**（内容驱动高度，在 `min_rows` 与 `max_rows` 之间自动伸缩，超出 `max_rows` 出现滚动条），以及与 [Input](./input.md) 一致的浮动 label 动画、清除按钮淡入缩放动画。

## 导入

```python
from hero_side_ui import Textarea
```

## 基本用法

```python
# 最简用法 — 默认 flat + default + md + inside label + min_rows=3, max_rows=8
ta = Textarea(label="Description", placeholder="Tell us a bit about yourself...")

# 指定颜色和变体
ta = Textarea(
    label="Bio",
    placeholder="Type here",
    color="primary",
    variant="bordered",
    size="md",
)

# 自定义 auto-resize 范围
ta = Textarea(label="Long text", min_rows=1, max_rows=12)

# 关闭 auto-resize（高度固定在 min_rows）
ta = Textarea(label="Fixed", min_rows=4, disable_autosize=True)

# 错误态
ta = Textarea(
    label="Description",
    is_invalid=True,
    error_message="描述不能为空",
)

# Qt 原生 API 仍可用
ta.text_edit.setTabStopDistance(40)
ta.text_changed.connect(lambda t: print(t))
ta.height_changed.connect(lambda h, r: print(f"new height={h}, row_h={r}"))
```

## 三个内容槽：top_right / center_right / bottom_right

Textarea 提供三个独立的内容槽用于摆放图标/按钮/计数器等附加 widget，每个槽对应一种位置语义：

| slot                    | 位置                                                                | 实现       | 典型用途                                  |
| ----------------------- | ------------------------------------------------------------------- | ---------- | ----------------------------------------- |
| `top_right_content`     | wrapper **右上角**（layout 内部 AlignTop，inside 模式下避开浮起 label） | layout 排版 | 字数徽章、关闭/清除自定义按钮             |
| `center_right_content`  | wrapper **垂直居中**（绝对定位，随 wrapper 高度变化实时居中）        | 绝对定位    | 始终居中的 Send 按钮                      |
| `bottom_right_content`  | wrapper **右下角**（绝对定位，距右/底偏移可配）                      | 绝对定位    | Chat 风格右下角 Send 按钮                 |

槽的内容支持三种值：

1. **字符串**：图标名（如 `"heroicons--paper-plane-solid"`）或 SVG 文件路径
2. **字符串 + on_xxx_click**：自动包成可点击 QPushButton
3. **任意 QWidget**：直接显示（典型如 HeroSideUI Button）

**槽不强制内部 widget 的尺寸** —— Button 用自身 sizeHint，所以 sm/md Button 直接塞进去都不会被压扁。

```python
# 1. top_right_content —— 右上角
send = Button("Send", size="sm", variant="flat", color="primary")
send.clicked.connect(do_send)
Textarea(label="Message", top_right_content=send)

# 2. center_right_content —— 垂直居中（随高度变化）
send2 = Button("Send", size="sm", variant="flat", color="primary")
Textarea(label="Message", center_right_content=send2,
         min_rows=3, max_rows=10)

# 3. bottom_right_content —— 右下角，类似 Tailwind absolute right-X bottom-X
send3 = Button("Send", size="sm", variant="solid", color="primary")
Textarea(label="Chat", bottom_right_content=send3,
         bottom_right_offset=(10, 10),  # 距右 10px、距底 10px
         min_rows=3, max_rows=10)

# 4. 字符串图标 + 点击回调
Textarea(label="Note",
         top_right_content="heroicons--x-circle-solid",
         on_top_right_content_click=lambda: print("clear!"))

# 5. 三槽并存
counter = Button("0/200", size="sm", variant="flat")
counter.setEnabled(False)
send_btn = Button("Send", size="sm", variant="solid", color="primary")
Textarea(label="Tweet",
         top_right_content=counter,
         bottom_right_content=send_btn,
         bottom_right_offset=(10, 10),
         min_rows=4, max_rows=8)
```

> **center_right / bottom_right 用绝对定位而不是 layout**：因为 wrapper 高度会随 auto-resize 不断变化，layout 内部很难维护"永远垂直居中"或"永远贴右下角"。绝对定位 + `wrapper.resizeEvent` 钩子才能做到实时跟随。
>
> **同时给文字让位**：绝对定位绕开 layout 后，文字 wrap 时本来会撞到按钮。组件内部在 wrapper layout 中插了一个透明 `_abs_spacer`，宽度 = `max(center_right_w + center_right_offset, bottom_right_w + bottom_right_offset.x) + 3px`。这样 inner 自然缩短，文字永远不会和按钮重叠 —— 你不需要任何手动调节。

---

## 构造参数

| 参数                     | 类型                     | 默认值      | 说明                                                                                  |
| ------------------------ | ------------------------ | ----------- | ------------------------------------------------------------------------------------- |
| `label`                  | `str`                    | `""`        | 标签文字                                                                              |
| `value`                  | `str`                    | `""`        | 初始文本值                                                                            |
| `placeholder`            | `str`                    | `""`        | 占位符                                                                                |
| `variant`                | `str`                    | `"flat"`    | 样式变体，见 [variant 可选值](#variant-可选值)。**Textarea 不支持 `underlined`**      |
| `color`                  | `str`                    | `"default"` | 颜色主题                                                                              |
| `size`                   | `str`                    | `"md"`      | 尺寸：`sm` / `md` / `lg`                                                              |
| `radius`                 | `str \| None`            | `None`      | 圆角，`None` 时跟随尺寸默认值                                                         |
| `label_placement`        | `str`                    | `"inside"`  | label 位置：`inside` / `outside` / `outside-top` / `outside-left`                     |
| `min_rows`               | `int`                    | `3`         | 最小行数（auto-resize 的下界，也是 disable_autosize=True 时的固定行数）              |
| `max_rows`               | `int`                    | `8`         | 最大行数。超过此行数时出现垂直滚动条                                                  |
| `disable_autosize`       | `bool`                   | `False`     | 关闭 auto-resize。固定高度为 `min_rows` 行                                            |
| `is_disabled`            | `bool`                   | `False`     | 禁用状态                                                                              |
| `is_invalid`             | `bool`                   | `False`     | 无效状态，边框/文字切换为 `danger` 色                                                 |
| `is_required`            | `bool`                   | `False`     | 必填，label 末尾追加红色 `*`                                                          |
| `is_readonly`            | `bool`                   | `False`     | 只读                                                                                  |
| `is_clearable`           | `bool`                   | `False`     | 显示清除按钮                                                                          |
| `full_width`             | `bool`                   | `True`      | 是否撑满父容器宽度                                                                    |
| `description`            | `str`                    | `""`        | 辅助说明文字                                                                          |
| `error_message`          | `str`                    | `""`        | 错误消息，`is_invalid=True` 时替代 description                                        |
| `resizable`              | `bool \| str`            | `False`     | 用户能否手动拖动右下角小手柄改变高度。默认 `False`（保持简洁）；可选值：`True`（=`"vertical"`，仅垂直）/ `"vertical"` / `"horizontal"` / `"both"`。bottom_right_content 存在时自动隐藏手柄避免重叠 |
| `start_content` 等老 API | — | — | **已移除** —— 替换为下方三槽 API                                                      |
| `top_right_content`      | `str \| QWidget \| None` | `None`      | wrapper 右上角内容（layout 内 AlignTop）                                              |
| `center_right_content`   | `str \| QWidget \| None` | `None`      | wrapper 垂直居中（右侧）内容（绝对定位，随高度实时居中）                              |
| `bottom_right_content`   | `str \| QWidget \| None` | `None`      | wrapper 右下角内容（绝对定位，类似 Tailwind absolute right-X bottom-X）              |
| `on_top_right_content_click`     | `Callable \| None` | `None`  | 字符串图标 + 此回调 → 自动变成可点击按钮                                              |
| `on_center_right_content_click`  | `Callable \| None` | `None`  | 同上                                                                                  |
| `on_bottom_right_content_click`  | `Callable \| None` | `None`  | 同上                                                                                  |
| `bottom_right_offset`    | `(int, int)`             | `(8, 8)`    | 右下角槽距 wrapper 右/底的偏移像素（`right_px, bottom_px`）                          |
| `center_right_offset`    | `int`                    | `8`         | 垂直居中槽距 wrapper 右边的偏移像素                                                   |
| `theme`                  | `str`                    | `"auto"`    | 主题模式：`"auto"`（跟随 ThemeProvider）/ `"light"` / `"dark"`                        |
| `parent`                 | `QObject \| None`        | `None`      | Qt 父对象                                                                             |

### variant 可选值

> 与 Input 一致的样式规则。**注意 Textarea 没有 `underlined`**——传入 `underlined` 会静默降级为 `flat`。

| 值         | 外观                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `flat`     | 浅色填充，无边框；亮色 hover 压暗，暗色 hover 提亮                                                                                    |
| `faded`    | 底色与 flat 一致 + 2px 边框；默认边框比底色深一档；hover/focus 边框变主色                                                             |
| `bordered` | 透明背景 + 2px 边框；默认边框 = flat 底色；hover/focus 渐变到主色                                                                     |

### color 可选值

`default` / `primary` / `secondary` / `success` / `warning` / `danger`

### label_placement 可选值

| 值             | 行为                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------ |
| `inside`       | label **始终浮起**在输入框顶部（详见下方"Textarea 与 Input 的 label 差异"）                |
| `outside`      | label **始终浮起**在输入框上方外部                                                         |
| `outside-top`  | label 始终**固定在输入框上方外部**                                                         |
| `outside-left` | label 在输入框**左侧顶部对齐**（多行场景下顶对齐而非垂直居中）                             |

#### Textarea 与 Input 的 label 差异

> Input（单行）的 inside/outside label 在"无焦点 + 无值 + 无 placeholder + 无 start_content"时，label 会停在输入框中线装作 placeholder；有焦点/有值后才浮起到顶部。
>
> **Textarea（多行）则始终保持浮起状态**——多行输入区本身就有一大片空白，让 label 停在第一行中间装 placeholder 视觉上不合理（下方一大片空白没有内容）。所以：
>
> - **Textarea 的 inside/outside label 永远在浮起位置**
> - 不会因焦点/值/placeholder 变化而切换
> - 等价于"始终当作有 placeholder"
>
> 如果你希望 label 完全独立于输入框作为标题展示，请使用 `outside-top`。

---

## 信号

| 信号             | 载荷             | 说明                                              |
| ---------------- | ---------------- | ------------------------------------------------- |
| `text_changed`   | `str`            | 文字变化时触发（代理 `QTextEdit.textChanged`）|
| `cleared`        | 无               | 点击清除按钮后触发                                |
| `height_changed` | `int, int`       | auto-resize 引发高度变化时触发：`(total_height, row_height)` |
| `focus_in`       | 无               | 输入框获得焦点                                    |
| `focus_out`      | 无               | 输入框失去焦点                                    |

也可以直接使用 Qt 原生信号，通过 `textarea.text_edit.xxx` 访问（如 `cursorPositionChanged`、`selectionChanged` 等）。

---

## 公共 API

| 方法                                        | 说明                                              |
| ------------------------------------------- | ------------------------------------------------- |
| `text()` / `set_text(text)`                 | 获取/设置当前文本                                 |
| `clear()`                                   | 清空文本                                          |
| `set_value(value)`                          | `set_text` 的别名                                 |
| `set_placeholder(text)`                     | 设置占位符                                        |
| `set_label(text)`                           | 设置 label                                        |
| `set_color(color)`                          | 动态切换颜色                                      |
| `set_variant(variant)`                      | 动态切换变体（`underlined` 会降级为 `flat`）      |
| `set_size(size)`                            | 动态切换尺寸                                      |
| `set_radius(radius)`                        | 动态切换圆角                                      |
| `set_label_placement(plc)`                  | 动态切换 label 位置                               |
| `set_min_rows(n)` / `set_max_rows(n)`       | 动态调整 auto-resize 范围（自动重算高度）         |
| `set_disable_autosize(bool)`                | 动态开关 auto-resize                              |
| `set_resizable(value)`                      | 动态开关/切换手动 grip 拖动（True/False/"vertical"/"horizontal"/"both"）|
| `reset_manual_height()`                     | 清除用户手动拖动设的高度，恢复 auto-resize 行为   |
| `set_theme(theme)`                          | 动态切换 `auto` / `light` / `dark` 主题           |
| `set_is_disabled/invalid/required/readonly/clearable(bool)` | 动态切换对应状态                  |
| `set_description(text)` / `set_error_message(text)`         | 设置描述/错误文字                  |
| `set_top_right_content(content, on_click=None)`    | 设置右上角内容                              |
| `set_center_right_content(content, on_click=None)` | 设置垂直居中（右侧）内容                    |
| `set_bottom_right_content(content, on_click=None)` | 设置右下角内容                              |
| `set_on_top_right_content_click(cb)` / `set_on_center_right_content_click(cb)` / `set_on_bottom_right_content_click(cb)` | 仅更新对应槽的点击回调 |
| `set_bottom_right_offset(right_px, bottom_px)`     | 动态调整右下角槽的偏移                      |
| `set_center_right_offset(right_px)`                | 动态调整垂直居中槽距右边的偏移              |
| `text_edit`                                 | 属性：内部 `QTextEdit` 实例                       |

---

## 手动 resize（grip 拖拽）

类似 HTML `<textarea>` 的 `resize: vertical` 属性 —— 用户可以从右下角拖动小手柄改变高度（**默认关闭**，传 `resizable=True` 开启）。

```python
# 默认关闭手柄（保持简洁）
Textarea(label="Bio")

# 开启垂直拖动
Textarea(label="Drag me", resizable=True)

# 双向（同时左右 + 上下）
Textarea(label="Free", resizable="both")
```

### 与 auto-resize 的关系

- 用户拖动后进入 **manual_height_mode**：组件高度直接用拖到的值，**绕过 auto-resize**。后续输入文字超过该高度时由 QTextEdit 自身滚动条承担
- 调 `textarea.reset_manual_height()` 清除手动模式，恢复 auto-resize

### 与 bottom_right_content 的冲突处理

`bottom_right_content`（按钮等）也贴右下角。当存在 `bottom_right_content` 时，**grip 自动隐藏**避免视觉重叠。这种场景下 textarea 由 auto-resize 控制，用户无法手动拖。

## Auto-Resize 实现细节

- 高度 = `pad_top + pad_bottom + label_reserve + row_height × clamp(content_rows, min_rows, max_rows)`
- `row_height` 由 `QFontMetrics(font).lineSpacing()` 计算（包含行间 leading）
- `content_rows` 通过遍历 `QTextDocument` 的每个 block + `QTextLayout.lineCount()` 累加得到，**正确处理 wrap**——同一段落 wrap 成多行时各算一行
- 宽度变化（`resizeEvent`）也会重算高度，因为 wrap 行数可能改变
- `disable_autosize=True` 时 `target_rows = min_rows`，高度锁死，超出内容由 `QTextEdit` 自身的滚动条承担
- 所有计算均在 `_update_textarea_height()` 一处完成，避免布局抖动

---

## 与 HeroUI 的差异

- HeroUI Textarea 默认 `min_rows=3, max_rows=8`，HeroSideUI 完全对齐
- HeroUI 暴露 `cacheMeasurements` prop（react-textarea-autosize 优化），HeroSideUI 不需要——QFontMetrics 调用本身极快
- HeroUI 不支持 `underlined` Textarea，HeroSideUI 同样限制（传入会降级）
- **滚动条颜色策略**：
  - `Textarea(color="default")`（默认）→ 滚动条用全局 ScrollStyle 默认色（`neutral`，纯灰中性色）
  - `Textarea(color="primary"/"success"/...)` → 滚动条跟随该语义色
  - 详见 [`ScrollStyle`](./scroll_style.md) 的 `set_bar_color`

---

## 示例

- [`examples/textarea/demo.py`](../examples/textarea/demo.py) — 完整功能演示（变体 / 颜色 / 尺寸 / 状态 / auto-resize）
