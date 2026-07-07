"""行内节点 → Qt 富文本 HTML 片段。

Markdown 的行内格式（粗/斜/删除线/行内 code/链接/图片/换行）**永不拆成独立
widget**，而是拼成一段 Qt rich-text HTML，由承载段落的 ``Text`` 一次性渲染。这样换行、
基线对齐交给 Qt 自己排版，整段可连续框选、可复制。

样式来源分两层：
- ``inline_styles``（声明式配置，见 ``_inline_styles.InlineStyleSheet``）：默认路径，
  一次配置到处套用（strong/em/s/code/link 的颜色、下划线等）。
- ``inline_overrides``（返回原始 HTML 片段的回调）：底层入口，``inline_styles`` 表达不了
  时用；回调出错自动退回默认。
"""

from __future__ import annotations

from html import escape
from typing import Callable, Dict, Optional

from markdown_it.tree import SyntaxTreeNode

from ._inline_styles import InlineStyleSheet


class InlineContext:
    """传给 inline_override 回调的上下文。

    属性：
        type:      节点类型（strong / em / s / code_inline / link / image）
        children:  已渲染的内层 HTML 字符串（已转义，可直接拼）
        content:   节点纯文本（code_inline / image 用）
        href:      链接地址（仅 link）
        src/alt:   图片地址 / 替代文本（仅 image）
    方法：
        default(): 退回该节点的内置默认 HTML（只想微调时用）
    """

    def __init__(
        self,
        node: SyntaxTreeNode,
        children_html: str,
        theme: str,
        default_fn: Callable[[], str],
    ):
        self.type = node.type
        self.children = children_html
        self.content = node.content or ""
        attrs = node.attrs
        self.href = str(attrs.get("href", ""))
        self.src = str(attrs.get("src", ""))
        self.alt = node.content or ""
        self.theme = theme
        self._default_fn = default_fn

    def default(self) -> str:
        return self._default_fn()


InlineOverride = Callable[[InlineContext], str]


def _render_children(
    node: SyntaxTreeNode,
    theme: str,
    sheet: InlineStyleSheet,
    overrides: Optional[Dict[str, InlineOverride]],
    fmt: frozenset = frozenset(),
) -> str:
    """递归把一个行内容器节点的 children 拼成 HTML，并应用用户 override。

    fmt 累积祖先链上的 strong/em/s 格式：无 override 的这几类不各自包 span，
    而是把标记并入 fmt，到 text 叶子时由 sheet.wrap() 一次性合成单 span，
    避免嵌套 span 里内层 font-weight 覆盖外层导致加粗斜体反而变细。
    """
    parts: list[str] = []
    for child in node.children:
        t = child.type
        if t == "text":
            parts.append(sheet.wrap(escape(child.content), fmt))
            continue
        if t == "softbreak":
            parts.append(" ")
            continue
        if t == "hardbreak":
            parts.append("<br/>")
            continue
        if t == "html_inline" or t == "html_block":
            # html=False 下不渲染原始 HTML（如 tasklists 注入的 <input>）为字面文本
            continue

        ov = overrides.get(t) if overrides else None
        # strong/em/s 且无 override：并入 fmt 继续下探，text 叶子处统一合成单 span
        if t in ("strong", "em", "s") and ov is None:
            parts.append(_render_children(child, theme, sheet, overrides, fmt | {t}))
            continue

        inner = _render_children(child, theme, sheet, overrides, fmt)
        default_fn = _make_default_fn(child, theme, sheet, inner)

        if ov is not None:
            ctx = InlineContext(child, inner, theme, default_fn)
            try:
                result = ov(ctx)
                parts.append(result if isinstance(result, str) else default_fn())
            except Exception:
                # 用户回调出错不该让整篇渲染崩，退回默认
                parts.append(default_fn())
        else:
            parts.append(default_fn())
    return "".join(parts)


def _make_default_fn(
    child: SyntaxTreeNode, theme: str, sheet: InlineStyleSheet, inner: str
) -> Callable[[], str]:
    """返回某个行内节点的"内置默认 HTML"生成器（走 inline_styles 配置）。"""
    t = child.type

    def build() -> str:
        if t == "strong":
            return sheet.strong(inner)
        if t == "em":
            return sheet.em(inner)
        if t == "s":
            return sheet.s(inner)
        if t == "code_inline":
            return sheet.code(escape(child.content))
        if t == "link":
            href = escape(child.attrs.get("href", ""), quote=True)
            return sheet.link(inner, href)
        if t == "image":
            src = escape(child.attrs.get("src", ""), quote=True)
            alt = escape(child.content or "")
            return f'<img src="{src}" alt="{alt}"/>'
        # 未知行内节点：尽量保留内容
        if inner:
            return inner
        if child.content:
            return escape(child.content)
        return ""

    return build


def inline_to_html(
    inline_node: SyntaxTreeNode,
    theme: str,
    overrides: Optional[Dict[str, InlineOverride]] = None,
    sheet: Optional[InlineStyleSheet] = None,
) -> str:
    """把一个 ``inline`` 节点（或含 children 的节点）渲染成 HTML 字符串。

    sheet 为空时用主题默认样式（对齐 Chip flat / Link primary）。
    """
    if sheet is None:
        sheet = InlineStyleSheet(theme)
    return _render_children(inline_node, theme, sheet, overrides)


__all__ = ["inline_to_html", "InlineContext", "InlineOverride"]
