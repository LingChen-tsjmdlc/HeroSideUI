"""pygments 语法高亮 → Qt 富文本 HTML。

把源码按语言 token 化，每个 token 包成带颜色的 ``<span>``，整段拼成外层 ``<div>``
富文本供 Text 渲染。配色随主题走 ``CODE_BLOCK_SYNTAX``（One Light / One Dark）。
pygments 缺失或语言无法识别时降级为纯文本（保留内容不丢失）。

字体注意：**不能用 ``<pre>``**——Qt 富文本会给 ``<pre>`` 强制套 monospace 覆盖
掉 setFont 设的字体（表现为字体没生效）。改用 ``<div white-space:pre>`` 既保留
换行/缩进，又让 CodeBlock 的 ``setFont`` 生效。只产出 HTML 字符串，不碰 Qt widget。
"""

from __future__ import annotations

from html import escape
from typing import Dict, List, Optional

from ...themes import CODE_BLOCK_SPEC, CODE_BLOCK_SYNTAX


def _token_color(ttype, syntax: Dict[str, str]) -> str:
    """pygments token 类型 → 十六进制色（映射到语义键）。"""
    from pygments.token import (
        Comment,
        Error,
        Keyword,
        Name,
        Number,
        Operator,
        Punctuation,
        String,
        Token,
    )

    if ttype in Comment:
        return syntax["comment"]
    if ttype in String:
        return syntax["string"]
    if ttype in Number:
        return syntax["number"]
    if ttype in Keyword:
        return syntax["keyword"]
    if ttype in Name.Function:
        return syntax["function"]
    if ttype in Name.Class:
        return syntax["class"]
    if ttype in Name.Decorator:
        return syntax["decorator"]
    if ttype in Name.Builtin:
        return syntax["builtin"]
    if ttype in Name.Constant:
        return syntax["constant"]
    if ttype in Operator:
        return syntax["operator"]
    if ttype in Punctuation:
        return syntax["punctuation"]
    if ttype in Error:
        return syntax["error"]
    if ttype in Name:
        return syntax["name"]
    if ttype in Token:
        return syntax["text"]
    return syntax["text"]


def highlight_to_lines(code: str, language: str, syntax: Dict[str, str]) -> List[str]:
    """把源码高亮成"每行一个 HTML 片段"的列表（不含行号 / 行容器）。

    返回每行已着色的 HTML；pygments 不可用或识别失败时，每行退化为转义纯文本。
    """
    code = code.rstrip("\n")
    try:
        from pygments import lex
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.util import ClassNotFound

        try:
            lexer = get_lexer_by_name(language, stripnl=False) if language else guess_lexer(code)
        except ClassNotFound:
            try:
                lexer = guess_lexer(code)
            except Exception:
                return [escape(line) for line in code.split("\n")]

        lines: List[str] = [""]
        for ttype, value in lex(code, lexer):
            color = _token_color(ttype, syntax)
            segments = value.split("\n")
            for i, seg in enumerate(segments):
                if i > 0:
                    lines.append("")
                if seg:
                    lines[-1] += f'<span style="color:{color}">{escape(seg)}</span>'
        if lines and lines[-1] == "":
            lines.pop()
        return lines or [""]
    except Exception:
        return [escape(line) for line in code.split("\n")]


def build_code_html(
    code: str,
    language: str,
    theme: str,
    *,
    show_line_numbers: bool = True,
    wrap: bool = False,
    highlight_lines: Optional[List[int]] = None,
) -> str:
    """把源码渲染成整段 ``<div>`` 富文本 HTML（随主题配色）。

    每行一个 ``<div white-space:pre|pre-wrap>``，保留缩进/空格且不触发 Qt 的
    monospace 强制覆盖（<pre> 会）。行号用真实空格右对齐，由 white-space:pre 保留。

    Args:
        code:              源码文本
        language:          语言名（pygments lexer 名），空则自动猜测
        theme:             "light" / "dark"，决定 One Light / One Dark 配色
        show_line_numbers: 是否在每行前加行号
        wrap:              是否对超长行软换行（行号仍可与之共存）
        highlight_lines:   需高亮背景的行号（1 基）
    """
    highlight_lines = highlight_lines or []
    syntax = CODE_BLOCK_SYNTAX["dark" if theme == "dark" else "light"]
    fg = syntax["text"]
    num_color = syntax["comment"]
    hl_bg = (
        CODE_BLOCK_SPEC["highlight_line_bg_dark"]
        if theme == "dark"
        else CODE_BLOCK_SPEC["highlight_line_bg_light"]
    )
    lines = highlight_to_lines(code, language, syntax)
    width = len(str(len(lines)))
    ws = "pre-wrap" if wrap else "pre"

    rows: List[str] = []
    for idx, line_html in enumerate(lines, start=1):
        prefix = ""
        if show_line_numbers:
            num = str(idx).rjust(width)
            prefix = f'<span style="color:{num_color}">{num}</span>  '
        bg = f"background-color:{hl_bg};" if idx in highlight_lines else ""
        rows.append(
            f'<div style="white-space:{ws}; {bg}">{prefix}{line_html or " "}</div>'
        )

    body = "".join(rows)
    return f'<div style="color:{fg};">{body}</div>'


__all__ = ["build_code_html", "highlight_to_lines"]
