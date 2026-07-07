# CodeBlock 代码块组件

> 带语法高亮、标题栏、复制按钮的代码块。复刻前端 `react-syntax-highlighter + atomDark` 风格。

`CodeBlock` = 圆角外壳 + 标题栏（文件名 / 多 tab、自动换行开关、复制按钮）+ 高亮代码区
（可选行号、可选行高亮）。语法高亮走 [Pygments](https://pygments.org/)；代码区恒用暗底
（对齐 atomDark），标题栏与外壳底色随主题走 `default` 色阶。主题自治，切换自动重刷。

## 依赖

- `pygments`：语法高亮（已加入 `pyproject.toml`，`uv sync` 即安装）。缺失时高亮
  降级为纯文本，内容不丢失。
- 代码字体默认用库内置的 **Maple Mono NF CN**（`resources/fonts/MapleMono-NF-CN-Medium.ttf`），
  首次使用时按需注册到 `QFontDatabase`；可用 `font` 参数传入自定义等宽字体路径。

## 快速上手

```python
from hero_side_ui import CodeBlock

# 单文件
cb = CodeBlock(code, language="python", filename="main.py")

# 高亮指定行（1 基）
cb = CodeBlock(code, language="python", filename="a.py", highlight_lines=[2, 3])

# 自定义代码字体
cb = CodeBlock(code, language="python", filename="a.py", font="C:/fonts/JetBrainsMono.ttf")

# 多 tab
cb = CodeBlock(tabs=[
    {"name": "main.py",  "code": code1, "language": "python"},
    {"name": "style.css","code": code2, "language": "css"},
])
```

## 构造参数

| 参数                | 类型                          | 必填 | 默认     | 说明                                                                                          |
| ------------------- | ----------------------------- | ---- | -------- | --------------------------------------------------------------------------------------------- |
| `code`              | `str`                         | 条件 | `""`     | 源码文本；单文件模式必填，传了 `tabs` 则忽略                                                  |
| `language`          | `str`                         | 是   | `"text"` | 语言名（Pygments lexer 名），用于语法高亮                                                     |
| `filename`          | `str`                         | 是   | `""`     | 标题栏文件名；空则显示语言名                                                                  |
| `highlight_lines`   | `list[int]`                   | 否   | `[]`     | 需高亮背景的行号（1 基）                                                                      |
| `font`              | `str`                         | 否   | `None`   | 代码字体文件路径；`None` 用内置 Maple Mono NF CN                                              |
| `font_size`         | `int`                         | 否   | `16`     | 代码字号（px）                                                                                |
| `tabs`              | `list[dict]`                  | 否   | `None`   | 多 tab；每项含 `name`/`code`，可选 `language`/`highlight_lines`。传了则忽略 `code`/`filename` |
| `show_line_numbers` | `bool`                        | 否   | `True`   | 是否显示行号（自动换行时仍保留）                                                              |
| `theme`             | `"auto" \| "light" \| "dark"` | 否   | `"auto"` | 主题模式，自动亮暗                                                                            |

## 交互

- **复制按钮**：点击把当前 tab 的源码写入剪贴板，图标临时变 ✓（success 色）2 秒。
- **自动换行开关**：切换超长行是否软换行；开启时隐藏行号并禁横向滚动，按钮变 primary 色。
- **Tab 切换**：多 tab 模式下点击 tab 名切换，选中态用 `flat` 变体表达。

## 在 Markdown 中

Markdown 组件的围栏代码块（` ```python `）已自动改用 `CodeBlock` 渲染，
info 串首词作为语言标记，无需额外配置。

## 设计说明

- 代码区底色**随主题切换**，用 Tailwind neutral 色系：亮色 `neutral-100`（`#f5f5f5`）、
  暗色 `neutral-800`（`#262626`）。标题栏 / 外壳底色走 `default` 色阶，同样随主题亮暗。
- 语法高亮配色见 `themes/component_presets/code_block.py` 的 `CODE_BLOCK_SYNTAX`（按主题分
  `light`/`dark` 两套，取 One Light / One Dark 的文字色），按 Pygments token 类型映射到语义色。
- 代码字体通过 `QFont` + `setFont` 落地——Qt 富文本 `<pre>` 的 CSS `font-family`
  不生效，必须设 QFont。每行用 `<div white-space:pre>` 渲染（`<pre>` 会被 Qt 强制套
  monospace 覆盖自定义字体）。QFont 显式锁 Normal 字重，避免挑到偏细的变体。加载逻辑
  独立于正文 `FontProvider`，见 `components/code_block/_font.py`。
- **高度自适应**：默认不限高、纵向不滚动，代码区随内容全展开。仅在超长行且未开启
  自动换行时出现横向滚动条。自动换行开启后行号依然保留。
