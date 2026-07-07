"""行内真 widget 的逃生舱容器 ``_InlineFlow``（默认不启用）。

**仅当用户显式传 ``inline_widgets``** 指定某类行内元素要渲染成独立 QWidget（如 citation
角标这类需要点击/hover 的特例）时，含该类元素的段落才降级为本容器。默认 99% 场景走单个
富文本 ``Text``，连续框选、换行正常，根本不进这里。

选区取舍
    只有真 widget 会打断选区。两个 widget 之间的连续文字合并成一个富文本 ``Text``（其内部
    连续可选），仅跨 widget 边界断开（Qt 选区依赖单一 QTextControl，不跨独立 widget）。
    文字块 ``WordWrap=False``：在 FlowLayout 里按自然宽度摆放、由 FlowLayout 在块之间换行，
    避免开 WordWrap 后被 FlowLayout 挤成又窄又高的一列。子项创建全部显式传 parent。
"""

from __future__ import annotations

from html import escape
from typing import Callable, Dict, List, Optional

from markdown_it.tree import SyntaxTreeNode
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

from ...themes import HEROUI_COLORS
from ...utils import FlowLayout
from ..text import Text
from ._inline_styles import InlineStyleSheet

# 默认按 widget 渲染的行内类型：footnote_ref 必须是真 widget（要挂 Tooltip）。
# 其余行内格式默认走富文本快路径（可连续框选）；仅当用户显式传 inline_widgets
# 时，才对指定类型降级为本流式布局。含 footnote_ref 的段落自动进流式布局。
_DEFAULT_WIDGET_TYPES = ("footnote_ref",)

_FORMAT_TYPES = ("strong", "em", "s")


class InlineWidgetContext:
    """传给 inline_widget 工厂的上下文。

    属性：
        type:    节点类型（code_inline / link / image / ...）
        content: 节点纯文本（= text 别名）
        text:    节点纯文本
        href:    链接地址（仅 link）
        src/alt: 图片地址 / 替代文本（仅 image）
        theme:   当前主题
        parent:  应作为返回 widget 父级的容器
    方法：
        default(): 退回该类型的内置默认 QWidget
    """

    def __init__(
        self,
        node: SyntaxTreeNode,
        plain: str,
        theme: str,
        parent: QWidget,
        default_fn: Callable[[], QWidget],
    ):
        self.type = node.type
        self.content = plain
        self.text = plain
        attrs = node.attrs
        self.href = str(attrs.get("href", ""))
        self.src = str(attrs.get("src", ""))
        self.alt = node.content or ""
        self.theme = theme
        self.parent = parent
        self._default_fn = default_fn

    def default(self) -> QWidget:
        return self._default_fn()


InlineWidget = Callable[[InlineWidgetContext], QWidget]


def _plain_text(node: SyntaxTreeNode) -> str:
    if node.type in ("text", "code_inline"):
        return node.content
    return "".join(_plain_text(c) for c in node.children)


def widget_types_for(inline_widgets: Optional[Dict[str, InlineWidget]]) -> tuple:
    """默认 widget 类型 + 用户覆盖类型的并集。"""
    extra = tuple(inline_widgets.keys()) if inline_widgets else ()
    return tuple(dict.fromkeys(_DEFAULT_WIDGET_TYPES + extra))


def paragraph_needs_flow(
    inline: SyntaxTreeNode,
    inline_widgets: Optional[Dict[str, InlineWidget]],
) -> bool:
    """段落是否含 widget 型行内元素（决定走 FlowLayout 而非 HTML 快路径）。"""
    wtypes = widget_types_for(inline_widgets)
    if not wtypes:
        return False

    def walk(node: SyntaxTreeNode) -> bool:
        for c in node.children:
            if c.type in wtypes:
                return True
            if c.type in _FORMAT_TYPES and walk(c):
                return True
        return False

    return walk(inline)


class _InlineFlow(QWidget):
    """含真 widget 的段落容器：连续文字合并成富文本块，widget 处断开。"""

    def __init__(
        self,
        inline: SyntaxTreeNode,
        theme: str,
        inline_widgets: Optional[Dict[str, InlineWidget]],
        parent: Optional[QWidget] = None,
        sheet: Optional[InlineStyleSheet] = None,
        footnote_texts: Optional[Dict[str, str]] = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._inline_widgets = inline_widgets or {}
        self._wtypes = widget_types_for(inline_widgets)
        self._sheet = sheet or InlineStyleSheet(theme)
        self._footnote_texts = footnote_texts or {}

        self._flow = FlowLayout(self, h_spacing=0, v_spacing=4)
        self._html_buf: List[str] = []
        self._emit_children(inline, fmt=frozenset())
        self._flush_text()

    # ---- 遍历：非 widget 累积 HTML，widget 处 flush ----
    def _emit_children(self, node: SyntaxTreeNode, fmt: frozenset) -> None:
        for child in node.children:
            t = child.type
            if t in self._wtypes:
                self._flush_text()
                self._add_widget(child)
            elif t in _FORMAT_TYPES:
                self._emit_children(child, fmt | {t})
            elif t == "text":
                self._html_buf.append(self._wrap_fmt(escape(child.content), fmt))
            elif t in ("softbreak", "hardbreak"):
                self._html_buf.append(" ")
            elif t == "code_inline":
                self._html_buf.append(self._sheet.code(escape(child.content)))
            elif t == "link":
                inner = self._render_inline_html(child, fmt)
                href = escape(child.attrs.get("href", ""), quote=True)
                self._html_buf.append(self._sheet.link(inner, href))
            else:
                self._emit_children(child, fmt)

    def _wrap_fmt(self, inner: str, fmt: frozenset) -> str:
        return self._sheet.wrap(inner, fmt)

    def _render_inline_html(self, node: SyntaxTreeNode, fmt: frozenset) -> str:
        parts: List[str] = []
        for c in node.children:
            if c.type == "text":
                parts.append(self._wrap_fmt(escape(c.content), fmt))
            elif c.type in _FORMAT_TYPES:
                parts.append(self._render_inline_html(c, fmt | {c.type}))
            elif c.type == "code_inline":
                parts.append(self._sheet.code(escape(c.content)))
        return "".join(parts)

    def _flush_text(self) -> None:
        # 累积的 HTML 刷成一个富文本 Text；空白缓冲跳过。WordWrap 关，交 FlowLayout 换行。
        if not self._html_buf:
            return
        html = "".join(self._html_buf).strip()
        self._html_buf = []
        if not html:
            return
        label = Text(
            size="md", theme=self._theme, selectable=True, rich_text=True, parent=self
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(False)
        label.setOpenExternalLinks(True)
        pal = label.palette()
        pal.setColor(QPalette.ColorRole.Link, QColor(HEROUI_COLORS["primary"][500]))
        label.setPalette(pal)
        label.setText(html)
        self._flow.addWidget(label)

    # ---- widget 型行内 ----
    def _add_widget(self, node: SyntaxTreeNode) -> None:
        plain = _plain_text(node)
        default_fn = self._make_default_fn(node, plain)
        override = self._inline_widgets.get(node.type)
        widget: Optional[QWidget] = None
        if override is not None:
            ctx = InlineWidgetContext(node, plain, self._theme, self, default_fn)
            try:
                widget = override(ctx)
            except Exception:
                widget = None
        if widget is None:
            widget = default_fn()
        if widget.parent() is None:
            widget.setParent(self)
        self._flow.addWidget(widget)

    def _make_default_fn(
        self, node: SyntaxTreeNode, plain: str
    ) -> Callable[[], QWidget]:
        t = node.type
        theme = self._theme

        def build() -> QWidget:
            if t == "footnote_ref":
                from ._footnote import _FootnoteRef, footnote_label

                label = footnote_label(node)
                body = self._footnote_texts.get(label, "")
                return _FootnoteRef(label, body, theme, parent=self)
            if t == "code_inline":
                from ..chip import Chip

                return Chip(
                    plain,
                    variant="flat",
                    radius="md",
                    is_text_selectable=True,
                    theme=theme,
                    parent=self,
                )
            if t == "link":
                from ..link import Link

                href = str(node.attrs.get("href", ""))
                return Link(
                    plain,
                    href=href,
                    is_external=True,
                    is_text_selectable=True,
                    theme=theme,
                    parent=self,
                )
            if t == "image":
                from ..image import Image

                src = str(node.attrs.get("src", ""))
                return Image(src=src, parent=self)
            # 兜底：未知 widget 类型退化为纯文字（可选中）
            label = Text(size="md", theme=theme, selectable=True, parent=self)
            label.setText(plain)
            return label

        return build


__all__ = ["_InlineFlow", "InlineWidgetContext", "InlineWidget", "paragraph_needs_flow"]
