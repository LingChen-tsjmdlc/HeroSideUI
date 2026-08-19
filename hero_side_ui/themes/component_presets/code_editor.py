"""CodeEditor 组件主题预设。

编辑器与 CodeBlock 视觉同源：圆角外壳 + 代码区底色随主题走 zinc 浅/深、
语法配色复用 One Light / One Dark 的 token 色（由 ``CODE_BLOCK_SYNTAX``
直接引用，不重复定义）。这里只补编辑器特有的 token：行号栏、当前行高亮、
光标、选区、边框与外壳。

- CODE_EDITOR_SPEC：规格（圆角/边距/字号/边框/底色）
- CODE_EDITOR_LINE：行号栏与当前行高亮（亮暗两套）
"""

from .code_block import CODE_BLOCK_SYNTAX

# 编辑器复用 CodeBlock 的语法配色（One Light / One Dark）
CODE_EDITOR_SYNTAX = CODE_BLOCK_SYNTAX

# 外壳 / 边框 / 代码区规格
CODE_EDITOR_SPEC = {
    "radius": 12,                # 外壳圆角（编辑器比展示块略收敛）
    "font_size": 14,             # 默认代码字号(px)
    "border_width": 1,           # 外壳描边宽
    "border_shade": 300,         # 亮色描边取 default 色阶 300
    "border_shade_dark": 700,    # 暗色描边取 default 色阶 700
    "code_pad_x": 12,            # 代码区左右内边距
    "code_pad_y": 10,            # 代码区上下内边距
    # 代码区底色：与 CodeBlock 相同的 zinc 浅/深
    "code_bg_light": "#f4f4f5",
    "code_bg_dark": "#27272a",
    "tab_width": 4,              # Tab 转空格的宽度
    "max_lines": 10000,          # 默认最大行数上限
}

# 行号栏 / 光标 / 选区（背景色以 (r,g,b,a) 元组给出——QColor 解析不了
# CSS 的 rgba() 字符串，会静默落成不透明黑）
CODE_EDITOR_LINE = {
    "light": {
        "gutter_width": 44,           # 行号栏宽(px)
        "gutter_pad_x": 10,           # 行号栏右对齐内边距
        "gutter_text": "#a0a1a7",     # 普通行号（One Light comment 色）
        "gutter_current": "#383a42",  # 当前行行号（正文色）
        "cursor": "#383a42",          # 光标色
        "selection_bg": (56, 132, 242, 56),   # 选区（One Light 蓝 低透明）
    },
    "dark": {
        "gutter_width": 44,
        "gutter_pad_x": 10,
        "gutter_text": "#5c6370",
        "gutter_current": "#abb2bf",
        "cursor": "#abb2bf",
        "selection_bg": (97, 175, 239, 64),
    },
}

__all__ = ["CODE_EDITOR_SPEC", "CODE_EDITOR_LINE", "CODE_EDITOR_SYNTAX"]
