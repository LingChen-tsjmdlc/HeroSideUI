"""Markdown 组件主题预设。

Markdown 大量复用现成组件（Title/Body/Link/Table/Image/Divider），它们各自的
preset 已管好样式；这里只放 Markdown 独有、其它组件没有的视觉规格：

- HEADING_SPEC：h1-h6 → (size token, weight)，喂给 Text
- MARKDOWN_SPACING：块级元素垂直间距
- MARKDOWN_LIST：列表缩进与无序符号
- MARKDOWN_QUOTE：引用块左侧竖条与缩进
- MARKDOWN_INLINE_CODE：行内 code 的底色/文字色 token（走 default 色阶 + alpha）

颜色一律引用 colors.py 的 default 色阶，不写死 HEX。
"""

# h1-h6 → (字号 token, 字重)；token 取自 core.text_style.SIZE_MAP
# 最小标题 h6 = md(16)，与正文同号但加粗以区分；整体自 h6 起逐级放大。
HEADING_SPEC = {
    1: ("4xl", "bold"),  # 36
    2: ("3xl", "bold"),  # 30
    3: ("2xl", "bold"),  # 24
    4: ("xl", "bold"),  # 20
    5: ("lg", "bold"),  # 18
    6: ("md", "bold"),  # 16
}

# 块级元素垂直间距 (px)
MARKDOWN_SPACING = {
    "block_gap": 12,  # 相邻块级元素之间
    "heading_top": 8,  # 标题上方额外留白（首块不加）
    "list_item_gap": 4,  # 列表项之间
    "tight_gap": 2,  # 紧凑列表项之间
}

# 列表
MARKDOWN_LIST = {
    "indent": 24,  # 每级缩进
    "marker_gap": 8,  # 符号/序号 与 内容 之间
    "task_marker_gap": 4,  # 任务勾选框与文字之间（比默认更贴近）
    "task_done_opacity": 0.6,  # 已完成任务项文字透明度
    "bullet": "\u2022",  # 无序符号 •
}

# 引用块（左侧竖条 + 半透明黑/白底，嵌套叠加越深，无边框）
MARKDOWN_QUOTE = {
    "bar_width": 3,  # 竖条宽度
    "bar_shade": 300,  # default 色阶（亮色用，暗色自动取深一档）
    "bar_shade_dark": 600,
    "pad_left": 12,  # 竖条到内容
    "pad_v": 8,  # 内容上下内边距
    "pad_right": 12,  # 内容右侧内边距
    "content_gap": 6,  # 引用块内部块间距
    "radius": 6,  # 底色圆角
    # 底色：亮色叠黑、暗色叠白，半透明——嵌套引用逐层叠加会越来越深
    "overlay_light": (0, 0, 0),  # 亮色主题叠加基色（黑）
    "overlay_dark": (255, 255, 255),  # 暗色主题叠加基色（白）
    "overlay_alpha": 0.05,  # 单层透明度
}

# 行内 code 底色 / 文字色 / 边框（default 色阶 token）
# 底色刻意比正文明显：亮色走 200（比原 100 深一档），暗色走 800 实底并配边框。
MARKDOWN_INLINE_CODE = {
    "bg_shade": 200,  # 亮色底（加深，更醒目）
    "bg_shade_dark": 800,  # 暗色底
    "fg_shade": 700,  # 亮色字
    "fg_shade_dark": 200,  # 暗色字
    "border_shade": 300,  # 亮色边框
    "border_shade_dark": 600,  # 暗色边框
    "pad_x": 4,  # 左右内边距（em-based 由 html 控制）
    "radius": 4,
}

__all__ = [
    "HEADING_SPEC",
    "MARKDOWN_SPACING",
    "MARKDOWN_LIST",
    "MARKDOWN_QUOTE",
    "MARKDOWN_INLINE_CODE",
]
