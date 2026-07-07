# Markdown 渲染组件

> 把 Markdown 文本渲染成 HeroSideUI 原生 widget 树，**不依赖 QWebEngine**。

`Markdown` 解析 CommonMark + GFM 表格，遍历语法树生成原生组件纵向堆叠：块级元素
复用现成组件（`Title`/`Body`/`Table`/`Image`/`Divider`），行内格式（粗/斜/删除线/
行内 code/链接/图片）拼成 Qt 富文本由段落 `Text` 一次渲染，主题、字体、选区全部
自动跟随现有体系。

## 依赖

需要 [`markdown-it-py`](https://github.com/executablebooks/markdown-it-py)（已加入
`pyproject.toml` 依赖，`uv sync` 即可安装）。

## 快速上手

```python
from hero_side_ui import Markdown

md = Markdown("# 标题\n\n正文 **粗体**、*斜体*、`code` 与 [链接](https://x.com)")
md.set_markdown("...")   # 动态替换内容，整树重建
```

## 构造参数

| 参数               | 类型                                  | 默认     | 说明                          |
| ------------------ | ------------------------------------- | -------- | ----------------------------- |
| `text`             | `str`                                 | `""`     | 初始 Markdown 文本            |
| `theme`            | `"auto" \| "light" \| "dark"`         | `"auto"` | 主题模式                      |
| `inline_overrides` | `dict[str, callable]`                 | `None`   | 覆盖**行内**默认 HTML（样式） |
| `block_renderers`  | `dict[str, callable]`                 | `None`   | 覆盖**块级**默认 widget       |
| `inline_widgets`   | `dict[str, callable]`                 | `None`   | 把**行内**元素渲染成独立 QWidget |

## 公共方法

| 方法                          | 说明                              |
| ----------------------------- | --------------------------------- |
| `set_markdown(text)`          | 替换内容并重建整棵 widget 树      |
| `markdown() -> str`           | 返回当前 Markdown 源文本          |
| `set_theme(theme)`            | 切换主题（`auto`/`light`/`dark`） |
| `set_inline_styles(d)`        | 替换行内样式配置并重建            |
| `set_inline_overrides(d)`     | 替换行内 override 并重建          |
| `set_block_renderers(d)`      | 替换块级 renderer 并重建          |
| `set_inline_widgets(d)`       | 替换行内 widget 映射并重建        |

## 自定义渲染（插槽 / override）

思路对齐 react-markdown 的 `components`：按节点类型覆盖渲染，未覆盖的走默认。
**核心原则：行内只改"样式"、块级才换"组件"**，原因是二者在 Qt 里本质不同：

- **行内元素**（`strong`/`em`/`s`/`code_inline`/`link`/`image`）在一行文字里随文字流动、
  需要连续排版与自动换行 —— **永不拆独立 QWidget**（拆了就断框选、换行还会被挤乱）。
  自定义只改"样式"：优先用声明式 `inline_styles`，需要更自由时用 `inline_overrides`
  返回 HTML。整段始终是单个富文本 `Text`，**全程连续框选**。
- **块级元素**（`paragraph`/`heading`/`blockquote`/`bullet_list`/`ordered_list`/
  `table`/`hr`/`fence`）独占整行 —— 可整块替换成你返回的**任意 QWidget**（如带复制按钮
  的代码块组件），独占整行不碍行内框选。

### 行内样式 inline_styles（声明式，推荐）

一次配置、流式文本自动套用。值用 HeroUI 语义 token（`primary` / `default-100`）或 HEX，
随主题解析：

```python
from hero_side_ui import Markdown

md = Markdown(text, inline_styles={
    "strong": {"color": "danger", "weight": "bold"},   # 粗体染红
    "em":     {"color": "secondary", "italic": True},  # 斜体染紫
    "s":      {"strike": True},                          # 删除线
    "code":   {"bg": "default-100", "fg": "default-700", "radius": 4},
    "link":   {"color": "primary", "underline": "always"},  # none / always
})
```

不传的 key 用内置默认（`code` 对齐 `Chip(variant="flat")`、`link` 对齐 `Link(primary)`）。

### 行内 override（返回 HTML，底层入口）

`inline_styles` 表达不了的样式，用 `inline_overrides` 返回原始 HTML 片段：

```python
from hero_side_ui import Markdown

md = Markdown(
    "正文 **粗体** 和 *斜体*",
    inline_overrides={
        # ctx.children = 已渲染的内层 HTML；ctx.content = 纯文本；ctx.href = 链接地址
        "strong": lambda c: f"<span style='color:#f31260; font-weight:700'>{c.children}</span>",
        "em":     lambda c: f"<span style='color:#7828c8'>{c.children}</span>",
        "link":   lambda c: f"<a href='{c.href}' style='color:#17c964'>{c.children}</a>",
    },
)
```

`InlineContext` 字段：`type` / `children`(内层HTML) / `content`(纯文本) / `href` /
`src` / `alt` / `theme`；方法 `default()` 退回内置默认 HTML。回调抛异常会自动退回默认。

### 块级 override（返回 QWidget）

```python
from hero_side_ui import Markdown, Card, CardBody

def quote_as_card(ctx):
    card = Card(parent=ctx.parent)
    body = CardBody()
    for child in ctx.render_children(body):   # 插槽 children（已渲染的子 widget 列表）
        body.layout().addWidget(child)
    card.add_body(body)
    return card

md = Markdown(text, block_renderers={"blockquote": quote_as_card})
```

把代码块（` ``` `）换成你自己的带复制按钮的代码组件，也走这条：

```python
md = Markdown(text, block_renderers={
    "fence": lambda c: MyCodeSnippet(c.node.content, parent=c.parent),
})
```

`BlockContext` 字段：`node`(原始节点) / `parent`(应作父级的容器) / `theme`；方法：

| 方法                       | 返回            | 说明                                       |
| -------------------------- | --------------- | ------------------------------------------ |
| `render_children(parent)`  | `list[QWidget]` | 子节点渲染成的 widget 列表（插槽 children）|
| `inline_html()`            | `str`           | 本节点行内内容的 HTML（段落/标题类）       |
| `default(parent)`          | `QWidget`       | 退回内置默认 widget（只想包外壳时用）      |

> **注意**：块级 override 内创建的子 widget 务必传 `parent`（用 `ctx.parent` 或你
> 自己的容器），否则会触发 Windows 无父瞬间闪原生窗。`render_children(parent)` 已
> 自动处理子节点的父级。

### 行内 widget 逃生舱（返回 QWidget，慎用）

极少数需要**行内交互**的特例（如可点击弹卡的 citation 角标）才用 `inline_widgets`
把某类行内元素换成真 QWidget。**代价：该 widget 处打断连续框选**，故不是默认路径：

```python
from hero_side_ui import Markdown, Chip, Link

md = Markdown(
    "运行 `uv sync` 后见 [文档](https://x.com)",
    inline_widgets={
        "code_inline": lambda c: Chip(c.text, variant="bordered", radius="sm"),
        "link":        lambda c: Link(c.text, href=c.href),
    },
)
```

`ctx.default()` 退回内置默认：`code_inline`→`Chip(variant="flat")`、`link`→`Link`、
`image`→`Image`。`InlineWidgetContext` 字段：`type` / `content`(=`text`) / `href` /
`src` / `alt` / `theme` / `parent`。含此类元素的段落降级为流式布局：只有真 widget 处
断选，widget 之间的连续文字仍合并成一个可框选的富文本块。**99% 场景请用 `inline_styles`。**


## 支持的语法

| 语法              | 渲染为                          |
| ----------------- | ------------------------------- |
| `# h1` ~ `###### h6` | `Text`（字号/字重按级别分级）  |
| 段落              | `Text`                          |
| `**粗** *斜* ~~删~~ `code`` | 段落内 Qt 富文本（`code` 默认为带浅底 `<code>`，视觉同 flat Chip）|
| `[文本](url)`     | 富文本 `<a>`（可点击、可框选；样式由 `inline_styles["link"]` 配）|
| 无序 / 有序列表   | 私有 `_ListBlock`（支持嵌套）   |
| `> 引用`          | 私有 `_QuoteBlock`（左侧竖条）  |
| `---`             | `Divider`                       |
| GFM 表格          | `Table`（支持 `:---`/`:--:`/`---:` 列对齐） |
| `![alt](src)`（独立成段） | `Image`                  |
| 代码块 ` ``` `    | 等宽降级文本块（首版不做高亮）  |

## 设计要点

- **块级用 widget，行内一律富文本**：所有行内格式（粗斜删/行内 code/链接/图片）拼成
  富文本交给 `Text` 一次渲染 —— **整段连续框选、换行正常、快**。行内样式由 `inline_styles`
  声明式配置。真组件只出现在块级（`block_renderers`，独占整行、不碍行内框选）。行内真
  widget 仅作逃生舱（`inline_widgets`，慎用）。
- **列表 / 引用是"容器节点"**：内部可递归嵌套任意块级内容，库里无对应组件，故新写
  两个轻量私有容器，只负责缩进 / 符号或竖条 / 把子节点回调渲染器递归渲染。
- **主题自治**：子组件各自注册到 `ThemeProvider`；主题切换时主组件整树重建，保证
  行内 code 底色、引用竖条等随主题刷新。
- **样式集中**：所有 Markdown 独有视觉常量在 `themes/component_presets/markdown.py`，
  组件内不硬编码颜色/尺寸。

## 已知限制（首版）

- 代码块无语法高亮（等宽降级显示）。
- 不支持数学公式、Mermaid 图、脚注、任务列表。
- 表格单元格内的行内格式（粗体/链接等）按纯文本处理；列对齐支持。
- 网络图片由 Qt 富文本能力决定，加载不出时退回 `alt` 文本。
- 原始内嵌 HTML 默认不解析（`html=False`），避免脚本注入。
