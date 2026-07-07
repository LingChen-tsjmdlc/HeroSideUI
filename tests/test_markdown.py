"""Markdown 组件测试。

需要 markdown-it-py（已加入 pyproject 依赖）。覆盖：构造、set_markdown 动态更新、
主题切换不崩、各类块级语法生成对应 widget、空文本、行内富文本承载。
"""

import pytest

from hero_side_ui import Markdown
from hero_side_ui.components.text import Text
from hero_side_ui.components.divider import Divider
from hero_side_ui.components.table import Table
from hero_side_ui.components.markdown._blocks import _ListBlock, _QuoteBlock


def _block_widgets(md: Markdown):
    lay = md.layout()
    return [lay.itemAt(i).widget() for i in range(lay.count())]


def test_construct_empty(qtbot):
    md = Markdown("")
    qtbot.addWidget(md)
    assert md.markdown() == ""
    assert md.layout().count() == 0


def test_heading_and_paragraph(qtbot):
    md = Markdown("# Title\n\nbody text")
    qtbot.addWidget(md)
    ws = _block_widgets(md)
    assert len(ws) == 2
    assert all(isinstance(w, Text) for w in ws)


def test_hr_renders_divider(qtbot):
    md = Markdown("a\n\n---\n\nb")
    qtbot.addWidget(md)
    ws = _block_widgets(md)
    assert any(isinstance(w, Divider) for w in ws)


def test_lists(qtbot):
    md = Markdown("- a\n- b\n")
    qtbot.addWidget(md)
    ws = _block_widgets(md)
    assert any(isinstance(w, _ListBlock) for w in ws)

    md2 = Markdown("1. a\n2. b\n")
    qtbot.addWidget(md2)
    assert any(isinstance(w, _ListBlock) for w in _block_widgets(md2))


def test_blockquote(qtbot):
    md = Markdown("> quoted")
    qtbot.addWidget(md)
    assert any(isinstance(w, _QuoteBlock) for w in _block_widgets(md))


def test_table(qtbot):
    md = Markdown("| A | B |\n| - | - |\n| 1 | 2 |\n")
    qtbot.addWidget(md)
    tables = [w for w in _block_widgets(md) if isinstance(w, Table)]
    assert len(tables) == 1
    assert tables[0].columns()[0]["label"] == "A"


def test_inline_rich_text(qtbot):
    # 纯文字 + 粗斜删（无 code/link）→ 走富文本快路径，仍是单个 Text
    md = Markdown("a **b** *c* ~~d~~")
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, Text)
    html = para.text()
    assert "<b>" in html and "<i>" in html and "<s>" in html


def test_paragraph_with_code_default_richtext(qtbot):
    # 默认（不传 inline_widgets）：含行内 code 仍走富文本快路径，是单个 Text
    md = Markdown("run `uv sync` now")
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, Text)
    assert "<code" in para.text()


def test_paragraph_with_link_default_richtext(qtbot):
    # 默认：含链接仍走富文本，是单个 Text，内含 <a>
    md = Markdown("see [docs](https://x.com) please")
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, Text)
    assert "<a href=" in para.text()


def test_code_inline_widget_uses_flow(qtbot):
    from hero_side_ui.components.markdown._inline_flow import _InlineFlow
    from hero_side_ui.components.chip import Chip

    # 显式传 inline_widgets → 含 code 的段落降级 _InlineFlow，ctx.default() 得 Chip
    md = Markdown(
        "run `uv sync` now",
        inline_widgets={"code_inline": lambda c: c.default()},
    )
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, _InlineFlow)
    chips = para.findChildren(Chip)
    assert len(chips) == 1
    assert chips[0].text() == "uv sync"


def test_link_widget_uses_flow(qtbot):
    from hero_side_ui.components.markdown._inline_flow import _InlineFlow
    from hero_side_ui.components.link import Link

    md = Markdown(
        "see [docs](https://x.com) please",
        inline_widgets={"link": lambda c: c.default()},
    )
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, _InlineFlow)
    links = para.findChildren(Link)
    assert len(links) == 1
    assert links[0].children_text() == "docs"


def test_inline_widgets_override(qtbot):
    from PySide6.QtWidgets import QLabel

    md = Markdown(
        "run `x`",
        inline_widgets={"code_inline": lambda c: QLabel(f"CODE:{c.text}")},
    )
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    labels = [w for w in para.findChildren(QLabel) if w.text() == "CODE:x"]
    assert len(labels) == 1


def test_inline_styles_link_color(qtbot):
    # inline_styles 配置 link 颜色 → 编入富文本，段落仍是单个可框选 Text
    md = Markdown(
        "see [docs](https://x.com)",
        inline_styles={"link": {"color": "success", "underline": "always"}},
    )
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, Text)
    html = para.text()
    # success-500 = #17c964 → rgba(23, 201, 100, ...)
    assert "23, 201, 100" in html
    assert "underline" in html


def test_inline_styles_strong_color(qtbot):
    md = Markdown("a **b** c", inline_styles={"strong": {"color": "danger"}})
    qtbot.addWidget(md)
    para = _block_widgets(md)[0]
    assert isinstance(para, Text)
    # danger-500 = #f31260 → rgba(243, 18, 96, ...)
    assert "243, 18, 96" in para.text()


def test_set_markdown_rebuilds(qtbot):
    md = Markdown("# one")
    qtbot.addWidget(md)
    assert md.layout().count() == 1
    md.set_markdown("# one\n\n# two\n\n# three")
    assert md.layout().count() == 3
    assert md.markdown().count("#") == 3


def test_theme_switch_no_crash(qtbot):
    md = Markdown("# t\n\n> q\n\n- i", theme="light")
    qtbot.addWidget(md)
    md.set_theme("dark")
    assert md.theme == "dark"
    md.set_theme("light")
    assert md.theme == "light"


def test_nested_list(qtbot):
    md = Markdown("- a\n  - a1\n  - a2\n- b\n")
    qtbot.addWidget(md)
    assert any(isinstance(w, _ListBlock) for w in _block_widgets(md))


def test_inline_override(qtbot):
    md = Markdown(
        "**bold** and *em*",
        inline_overrides={
            "strong": lambda c: f"<span class='x'>{c.children}</span>",
        },
    )
    qtbot.addWidget(md)
    html = _block_widgets(md)[0].text()
    assert "<span class='x'>" in html
    # em 未覆盖 → 仍走默认 <i>
    assert "<i>" in html


def test_inline_override_default_escape(qtbot):
    # 用户 override 出错应退回默认，不崩
    def boom(c):
        raise RuntimeError("boom")

    md = Markdown("**bold**", inline_overrides={"strong": boom})
    qtbot.addWidget(md)
    assert "<b>" in _block_widgets(md)[0].text()


def test_block_renderer(qtbot):
    from PySide6.QtWidgets import QLabel

    def custom_quote(ctx):
        lbl = QLabel("CUSTOM", ctx.parent)
        return lbl

    md = Markdown("> quoted", block_renderers={"blockquote": custom_quote})
    qtbot.addWidget(md)
    from PySide6.QtWidgets import QLabel as _QL

    ws = _block_widgets(md)
    assert any(isinstance(w, _QL) and w.text() == "CUSTOM" for w in ws)
    # 默认 _QuoteBlock 不应再出现
    assert not any(isinstance(w, _QuoteBlock) for w in ws)


def test_block_renderer_render_children(qtbot):
    captured = {}

    def custom(ctx):
        from PySide6.QtWidgets import QWidget as _W, QVBoxLayout

        box = _W(ctx.parent)
        lay = QVBoxLayout(box)
        children = ctx.render_children(box)
        captured["n"] = len(children)
        for c in children:
            lay.addWidget(c)
        return box

    md = Markdown("> p1\n>\n> p2", block_renderers={"blockquote": custom})
    qtbot.addWidget(md)
    # 引用块内两段 → render_children 返回 2 个 widget
    assert captured["n"] == 2

