"""CodeBlock 组件主题预设。

复刻前端 CodeBlock 的视觉：圆角容器 + 标题栏 + 高亮代码区。代码区底色随主题在
Tailwind zinc 浅/深之间切换（zinc 比 neutral 更冷、偏中性灰）；语法配色用
One Light / One Dark 的 token 色（仅文字着色，底色不用其背景）。

- CODE_BLOCK_SPEC：外壳圆角 / 内边距 / 默认字号 / 标题栏配色 token / 代码区底色
- CODE_BLOCK_SYNTAX：{theme: {pygments 语义 token → 颜色}}（One Light / One Dark）
"""

# 外壳 / 标题栏 / 代码区规格
CODE_BLOCK_SPEC = {
    "radius": 16,  # 外壳圆角（对齐前端 rounded-2xl）
    "header_pad_x": 12,  # 标题栏左右内边距
    "header_pad_y": 6,  # 标题栏上下内边距
    "code_pad_x": 16,  # 代码区左右内边距
    "code_pad_y": 12,  # 代码区上下内边距
    "font_size": 14,  # 默认代码字号(px)，可由 font_size 参数覆盖
    # 代码区底色：Tailwind zinc 浅/深（亮 zinc-100 / 暗 zinc-800）
    "code_bg_light": "#f4f4f5",
    "code_bg_dark": "#27272a",
    # 高亮行背景（叠加在代码底上的半透明）
    "highlight_line_bg_light": "rgba(0,0,0,0.05)",
    "highlight_line_bg_dark": "rgba(255,255,255,0.06)",
    # 外壳底色随主题（default 色阶，本身即 zinc）
    "shell_bg_shade": 50,
    "shell_bg_shade_dark": 900,
    # 标题栏底色：Tailwind zinc（亮 zinc-200 / 暗 zinc-850，介于 800~900）
    "header_bg_light": "#e4e4e7",
    "header_bg_dark": "#1f1f23",
    "filename_shade": 400,
}

# pygments 语义 token → 颜色。One Light（Atom One Light）/ One Dark（Atom One Dark）。
CODE_BLOCK_SYNTAX = {
    "light": {
        "text": "#383a42",
        "comment": "#a0a1a7",
        "keyword": "#a626a4",  # 紫
        "builtin": "#0184bc",  # 青
        "string": "#50a14f",  # 绿
        "number": "#986801",  # 橙棕
        "function": "#4078f2",  # 蓝
        "class": "#c18401",  # 金黄
        "operator": "#383a42",
        "punctuation": "#383a42",
        "name": "#e45649",  # 红（变量）
        "decorator": "#4078f2",
        "constant": "#986801",
        "error": "#e45649",
    },
    "dark": {
        "text": "#abb2bf",
        "comment": "#5c6370",
        "keyword": "#c678dd",  # 紫
        "builtin": "#56b6c2",  # 青
        "string": "#98c379",  # 绿
        "number": "#d19a66",  # 橙
        "function": "#61afef",  # 蓝
        "class": "#e5c07b",  # 黄
        "operator": "#abb2bf",
        "punctuation": "#abb2bf",
        "name": "#e06c75",  # 红（变量）
        "decorator": "#61afef",
        "constant": "#d19a66",
        "error": "#e06c75",
    },
}

__all__ = ["CODE_BLOCK_SPEC", "CODE_BLOCK_SYNTAX"]
