# CodeEditor 代码编辑器

可编辑的代码编辑器。与 CodeBlock（纯展示）互补：CodeBlock 负责"看代码"，CodeEditor 负责"写代码"。

## 依赖

- 高亮统一走 pygments（lexer 短名与 CodeBlock 一致："python" / "json" / "sql" / "javascript"…），配色复用 CodeBlock 同一套语义 token 映射；编辑停顿 150ms 后全文重扫，识别失败降级纯文本。

## 快速上手

```python
from hero_side_ui import CodeEditor

ed = CodeEditor()
ed.set_value("def hello():\n    print('hi')\n")
ed.text_changed.connect(lambda text: print("changed"))
layout.addWidget(ed)
```

值 API 与 Input / Textarea 同构：构造参数 `value` 预填内容、`value()` 取值、`set_value()` 赋值（`text()` / `set_text()` 为别名）、`clear()` 清空、`text_changed(str)` 变化信号。

## 构造参数

| 参数        | 类型              | 默认       | 说明                                                                                                        |
| ----------- | ----------------- | ---------- | ----------------------------------------------------------------------------------------------------------- |
| `value`     | `str`             | `""`       | 预填内容                                                                                                    |
| `language`  | `str`             | `"python"` | pygments lexer 短名，任意语言；识别失败按纯文本编辑（不报错）                                               |
| `font`      | `str \| None`     | `None`     | 代码字体 ttf 路径；None 用内置 Maple Mono NF CN                                                             |
| `font_size` | `int \| None`     | `None`     | 代码字号(px)；None 用默认 14                                                                                |
| `tab_width` | `int \| None`     | `None`     | Tab 转空格宽度；None 用默认 4                                                                               |
| `min_lines` | `int`             | `8`        | 编辑区最小可见行数（决定最小高度）                                                                          |
| `max_lines` | `int \| None`     | `None`     | 最大行数上限；None 用默认 10000。超限输入（键入/粘贴/set_value）自动截断到上限，并发射 `max_lines_exceeded` |
| `theme`     | `str`             | `"auto"`   | `"auto"` / `"light"` / `"dark"`                                                                             |
| `parent`    | `QWidget \| None` | `None`     | 父 widget                                                                                                   |

## 公共方法

| 方法                                                 | 说明                                              |
| ---------------------------------------------------- | ------------------------------------------------- |
| `value() -> str`                                     | 返回全文                                          |
| `set_value(value: str)`                              | 整体替换全文（进撤销栈，光标移到文首）            |
| `text()` / `set_text(text)`                          | 上两者的别名（对齐 Input）                        |
| `clear()`                                            | 清空                                              |
| `set_read_only(ro: bool)` / `is_read_only() -> bool` | 只读开关                                          |
| `insert_at_cursor(text: str)`                        | 在光标处插入文本                                  |
| `set_max_lines(n)` / `max_lines() -> int`            | 行数上限；改小后当前内容立即截断                  |
| `set_language(language)`                             | 切换语言高亮（pygments 短名；切换后立即重扫一次） |
| `set_font_size(size_px: int)`                        | 改字号（行号栏行高同步）                          |
| `set_theme(theme: str)`                              | 切主题（`"auto"` 重新注册 ThemeProvider）         |

## 信号

| 信号                 | 载荷                  | 触发                          |
| -------------------- | --------------------- | ----------------------------- |
| `text_changed`       | `str`（全文）         | 文本变化时                    |
| `max_lines_exceeded` | `int`（被截掉的行数） | 输入超出 `max_lines` 被截断时 |

## 编辑行为（内置，无需配置）

- Tab 插入 `tab_width` 个空格（不做真 tab）；有选区时选区行整体右移一级
- Shift+Tab 选区行整体左移一级（删行首最多 `tab_width` 个空格或 1 个 tab）
- 回车保持当前缩进；冒号结尾的行自动多缩进一级（class/def/if/for/while/try/with 等）
- 当前行由行号栏变色标识（当前行号用正文色）；编辑区不加任何行背景

## 设计说明

- **视觉与 CodeBlock 同源**：代码区底色同 zinc 浅/深、语法配色同 One Light / One Dark（`CODE_EDITOR_SYNTAX` 直接引用 `CODE_BLOCK_SYNTAX`）。编辑器特有 token（行号栏、当前行、选区、边框）在 `themes/component_presets/code_editor.py` 的 `CODE_EDITOR_SPEC` / `CODE_EDITOR_LINE`。
- **高亮统一 pygments**：复用 `code_block/_highlight.py` 的 `_token_color` 语义配色（与 CodeBlock 完全同源）；全文 lex → 按 block 缓存着色片段 → `highlightBlock` 查缓存上色；编辑停顿 150ms（QTimer 防抖）后重扫。超过 20000 行的文档不重扫（保留旧着色），防超大粘贴卡 UI。
- **主题切换不重建编辑区**：文本、光标、撤销栈、滚动位置全部保留，只重设 QSS 与高亮配色。
- **外壳圆角由 `paintEvent` 绘制**，编辑区与行号栏透明底叠在其上（同 CodeBlock 的分层做法）。
- **明确不做**（v1 范围外）：自动补全、括号匹配、代码折叠、查找替换、多光标。
