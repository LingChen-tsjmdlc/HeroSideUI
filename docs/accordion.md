# Accordion 手风琴

基于 [HeroUI v2](https://heroui.com/) 设计风格的手风琴折叠面板组件。

由 `Accordion`（容器）和 `AccordionItem`（子项）组合使用，支持展开/收起动画、箭头指示器旋转、亮暗主题。

## 导入

```python
from hero_side_ui import Accordion, AccordionItem
```

## 基本用法

```python
accordion = Accordion()

accordion.add_item(AccordionItem(
    title="第一项",
    content_text="这里是折叠的内容",
))

accordion.add_item(AccordionItem(
    title="第二项",
    subtitle="带副标题",
    content_text="更多内容...",
))
```

---

## Accordion（容器）参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `str` | `"light"` | 外观变体，见 [variant 可选值](#variant-可选值) |
| `allow_multiple` | `bool` | `False` | 是否允许同时展开多项 |
| `size` | `str` | `"md"` | 尺寸 (`sm` / `md` / `lg`) |
| `radius` | `str` | `"md"` | 圆角 (`none` / `sm` / `md` / `lg`)，仅 shadow/bordered/splitted 生效，light 固定无圆角 |
| `theme` | `str` | `"light"` | 主题 (`light` / `dark`) |
| `show_divider` | `bool` | `True` | 是否显示子项之间的分割线（最后一项不显示） |

## AccordionItem（子项）参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `str` | `""` | 标题文字 |
| `subtitle` | `str` | `""` | 副标题（可选，显示在标题下方） |
| `content_widget` | `QWidget \| None` | `None` | 折叠内容区的自定义控件 |
| `content_text` | `str` | `""` | 简单文本内容（与 `content_widget` 二选一） |
| `expanded` | `bool` | `False` | 初始是否展开 |
| `is_disabled` | `bool` | `False` | 禁用状态 |
| `start_icon` | `str \| None` | `None` | 标题左侧图标，内置图标名如 `"chevron-right"` 或 SVG 文件路径 |
| `end_icon` | `str \| None` | `None` | 替换右侧指示器箭头，默认 `chevron-right`，传入其他图标名或 SVG 路径可自定义 |

---

## variant 可选值

4 种外观变体，对标 HeroUI v2：

| 值 | 说明 | 容器外观 | 子项之间 |
|----|------|----------|----------|
| `light` | 极简（默认） | 透明，无边框无圆角 | 分割线分隔 |
| `shadow` | 卡片阴影 | 白色背景 + 圆角（像一张 Card 垫底） | 分割线分隔 |
| `bordered` | 边框 | 透明背景 + 边框 + 圆角 | 分割线分隔 |
| `splitted` | 独立卡片 | 透明容器 | 每项独立 Card（白底+圆角），间距分隔，无分割线 |

---

## 圆角

通过 `radius` 参数控制，仅 `shadow`/`bordered`/`splitted` 变体生效，`light` 始终无圆角。

| 值 | 像素 |
|----|------|
| `none` | 0px |
| `sm` | 4px |
| `md` | 8px（默认） |
| `lg` | 14px |

---

## 尺寸

| 值 | 标题字号 | 内容字号 |
|----|----------|----------|
| `sm` | 14px | 13px |
| `md` | 16px | 14px |
| `lg` | 18px | 16px |

---

## 图标

- `start_icon`：标题左侧的装饰图标
- `end_icon`：**替换**右侧默认的箭头指示器（默认 `chevron-right`）

支持两种方式传入：

```python
# 内置图标名（从库的 resources/icons/ 加载）
AccordionItem(title="设置", start_icon="chevron-right")

# 任意 SVG 文件路径
AccordionItem(title="收藏", start_icon="C:/project/icons/star.svg")

# 替换默认箭头为自定义图标
AccordionItem(title="自定义箭头", end_icon="C:/project/icons/plus.svg")
```

布局顺序：`[start_icon] [标题/副标题] [指示器(end_icon)]`

---

## 动画

动画封装在 `animation/collapse.py` 中，独立于组件可复用。

- **内容区展开**: 高度 450ms `OutCubic` + 透明度 350ms `OutQuad`（同时启动，透明度稍短让高度先撑开）
- **内容区收起**: 高度 400ms `InOutCubic` + 透明度 250ms `InQuad`（透明度更快，文字先淡出）
- **箭头旋转**: 400ms `OutCubic`，展开时顺时针旋转 90°
- **trigger 按压反馈**: 按下时透明度降至 0.7，松开恢复

---

## 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `AccordionItem.expanded_changed` | `bool` | 展开/收起状态变化时触发 |

---

## 动态方法

### Accordion

```python
accordion.set_theme("dark")        # 切换主题
accordion.set_variant("bordered")  # 切换变体
accordion.set_size("lg")           # 切换尺寸
accordion.set_radius("sm")         # 切换圆角
accordion.expand_all()             # 展开全部
accordion.collapse_all()           # 收起全部
```

### AccordionItem

```python
item.toggle()                      # 切换展开/收起
item.expand()                      # 展开
item.collapse()                    # 收起
item.set_title("新标题")            # 修改标题
item.set_subtitle("副标题")         # 修改副标题
item.set_content(my_widget)        # 设置自定义内容控件
item.set_start_icon("star")        # 设置左侧图标
item.set_end_icon("badge")         # 设置右侧图标
item.is_expanded()                 # 获取当前状态
```

---

## 自定义内容

除了简单文本，可以放任何 QWidget 作为折叠内容：

```python
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from hero_side_ui import Button

content = QWidget()
content_layout = QVBoxLayout(content)
content_layout.addWidget(QLabel("这是自定义内容"))
content_layout.addWidget(Button("操作按钮", color="primary", size="sm"))

item = AccordionItem(
    title="带自定义内容的项",
    content_widget=content,
)
```

---

## 完整示例

```python
import sys
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from hero_side_ui import Accordion, AccordionItem

app = QApplication(sys.argv)

window = QWidget()
layout = QVBoxLayout(window)

accordion = Accordion(variant="bordered", radius="lg", theme="light")

accordion.add_item(AccordionItem(
    title="什么是 HeroSideUI？",
    content_text="PySide6 组件库，复刻 HeroUI v2 设计系统。",
))

accordion.add_item(AccordionItem(
    title="如何安装？",
    subtitle="使用 uv 包管理器",
    content_text="运行 uv sync 即可。",
))

accordion.add_item(AccordionItem(
    title="禁用项",
    content_text="这项被禁用了。",
    is_disabled=True,
))

layout.addWidget(accordion)
window.show()
sys.exit(app.exec())
```

---

## 示例文件

查看 [examples/accordion/](../examples/accordion/) 目录：

- **[light_mode.py](../examples/accordion/light_mode.py)** — 亮色模式下四种变体 + 不同圆角展示
- **[dark_mode.py](../examples/accordion/dark_mode.py)** — 暗色模式下四种变体展示
