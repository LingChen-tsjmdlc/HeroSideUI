"""pygments → Qt 富文本 HTML；用 <div white-space:pre> 而非 <pre>（后者会
强制 monospace 覆盖 QFont）。缺失时降级纯文本。
"""

from __future__ import annotations

from html import escape

from ..._shared.code import token_color
from ...themes import CODE_BLOCK_SPEC, CODE_BLOCK_SYNTAX


def highlight_to_lines(code: str, language: str, syntax: dict[str, str]) -> list[str]:
    """把源码高亮成「每行一个 HTML 片段」的列表。

    Args:
        code: 源码文本。
        language: pygments lexer 名；空串时自动猜测。
        syntax: 主题的语法配色字典。

    Returns:
        每行已着色的 HTML 列表（不含行号与行容器）；
        pygments 不可用、lexer 识别失败或任何异常时，
        每行退化为 HTML 转义的纯文本。
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

        lines: list[str] = [""]
        for ttype, value in lex(code, lexer):
            color = token_color(ttype, syntax)
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
    highlight_lines: list[int] | None = None,
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

    Returns:
        整段富文本 HTML 字符串。

    Note:
        行号用真实空格右对齐、由 white-space:pre 保留；
        highlight_lines 中的行额外加背景色。
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

    rows: list[str] = []
    for idx, line_html in enumerate(lines, start=1):
        prefix = ""
        if show_line_numbers:
            num = str(idx).rjust(width)
            prefix = f'<span style="color:{num_color}">{num}</span>  '
        bg = f"background-color:{hl_bg};" if idx in highlight_lines else ""
        rows.append(f'<div style="white-space:{ws}; {bg}">{prefix}{line_html or " "}</div>')

    body = "".join(rows)
    return f'<div style="color:{fg};">{body}</div>'


__all__ = ["build_code_html", "highlight_to_lines"]
