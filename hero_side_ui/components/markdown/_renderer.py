"""节点 → 原生 widget 渲染器：heading/段落→Text、列表→_ListBlock、
引用→_QuoteBlock、hr→Divider、表格→Table、图片→Image、代码块降级文本。
行内格式统一走 _inline.inline_to_html 不拆 widget。
"""

from __future__ import annotations

from collections.abc import Callable

from markdown_it.tree import SyntaxTreeNode
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

from ...themes import HEADING_SPEC, HEROUI_COLORS
from ..divider import Divider
from ..image import Image
from ..table import Table
from ..text import Text
from ._inline import InlineOverride, inline_to_html
from ._inline_flow import InlineWidget, _InlineFlow, paragraph_needs_flow
from ._inline_styles import InlineStyleSheet


def _plain_text(node: SyntaxTreeNode) -> str:
    """递归提取节点纯文本（表格单元格用）。"""
    if node.type == "text" or node.type == "code_inline":
        return node.content
    parts = [_plain_text(c) for c in node.children]
    return "".join(parts)


def _first_inline(node: SyntaxTreeNode) -> SyntaxTreeNode | None:
    """取节点第一个 inline 子节点（行内内容载体）。

    Returns:
        SyntaxTreeNode | None: 第一个 inline 节点，无则 None。
    """
    for c in node.children:
        if c.type == "inline":
            return c
    return None


class BlockContext:
    """传给 block_renderer 工厂的上下文。

    Attributes:
        node: 原始语法节点。
        parent: 应作为返回 widget 父级的容器。
        theme: 当前主题。
    """

    def __init__(
        self,
        node: SyntaxTreeNode,
        parent: QWidget,
        renderer: MarkdownRenderer,
    ):
        """构造块级渲染上下文。

        Args:
            node: 原始语法树节点。
            parent: 应作为返回 widget 父级的容器。
            renderer: 当前 MarkdownRenderer（提供主题与渲染能力）。
        """
        self.node = node
        self.parent = parent
        self.theme = renderer.theme
        self._renderer = renderer

    def render_children(self, parent: QWidget) -> list[QWidget]:
        """递归渲染本节点所有子节点（绕过 block override，走默认渲染）。

        Args:
            parent: 子 widget 的父容器。

        Returns:
            list[QWidget]: 渲染出的子 widget 列表。
        """
        out: list[QWidget] = []
        for child in self.node.children:
            w = self._renderer.render_node(child, parent)
            if w is not None:
                out.append(w)
        return out

    def inline_html(self) -> str:
        """渲染本节点 inline 子节点为 HTML 片段（应用 inline override/样式）。

        Returns:
            str: 行内 HTML。
        """
        inline = _first_inline(self.node)
        if inline is None:
            return ""
        return inline_to_html(
            inline, self.theme, self._renderer.inline_overrides, self._renderer.sheet
        )

    def default(self, parent: QWidget) -> QWidget | None:
        """调用内置默认渲染器（跳过 block override）。

        Args:
            parent: 默认渲染 widget 的父容器。

        Returns:
            QWidget | None: 默认渲染结果。
        """
        return self._renderer.render_node(self.node, parent, _skip_override=True)


BlockRenderer = Callable[[BlockContext], QWidget]


class MarkdownRenderer:
    """把语法树渲染成块级 widget 列表。主题只读，由主组件在重建时传入。

    Args:
        theme:            当前主题
        inline_overrides: {type: callable(InlineContext)->str}，覆盖行内默认 HTML
        block_renderers:  {type: callable(BlockContext)->QWidget}，覆盖块级默认 widget
        inline_styles:    {type: {样式属性}}，声明式配置行内 strong/em/s/code/link 的样式
                          （颜色/下划线等），编译成富文本，全程连续框选
        inline_widgets:   {type: callable(InlineWidgetContext)->QWidget}，逃生舱：把行内元素
                          渲染成独立 QWidget（默认为空；仅极少数需交互的行内角标才用，
                          该处会打断连续选区）
    """

    def __init__(
        self,
        theme: str,
        inline_overrides: dict[str, InlineOverride] | None = None,
        block_renderers: dict[str, BlockRenderer] | None = None,
        inline_widgets: dict[str, InlineWidget] | None = None,
        inline_styles: dict[str, dict] | None = None,
    ):
        """构造渲染器：缓存主题、override、样式表与脚注文本。"""
        self.theme = theme
        self.inline_overrides = inline_overrides or {}
        self.block_renderers = block_renderers or {}
        self.inline_widgets = inline_widgets or {}
        self.sheet = InlineStyleSheet(theme, inline_styles)
        # {显示序号: 脚注正文}，render() 时按整树收集，供行内角标 Tooltip 使用
        self.footnote_texts: dict[str, str] = {}

    # ------------------------------------------------------------
    # 富文本 label 构造
    # ------------------------------------------------------------
    def _rich_label(self, html: str, parent: QWidget, *, size="md", weight="normal") -> Text:
        """构造一个富文本 Text（可选中、可打开外链、链接色锁定 primary）。

        Args:
            html: 富文本 HTML。
            parent: 父控件。
            size: 字号档位。
            weight: 字重档位。

        Returns:
            Text: 配置好的富文本标签。
        """
        label = Text(size=size, weight=weight, theme=self.theme, rich_text=True, parent=parent)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        # 链接色：HeroUI link 亮暗均用 primary-500，设一次即可
        pal = label.palette()
        pal.setColor(QPalette.ColorRole.Link, QColor(HEROUI_COLORS["primary"][500]))
        label.setPalette(pal)
        label.setText(html)
        return label

    # ------------------------------------------------------------
    # 顶层入口
    # ------------------------------------------------------------
    def render(self, root: SyntaxTreeNode, parent: QWidget) -> list[QWidget]:
        """渲染整棵语法树为块级 widget 列表（含脚注文本收集）。

        Args:
            root: 语法树根节点。
            parent: 顶层 widget 父容器。

        Returns:
            list[QWidget]: 渲染出的块级 widget 列表。
        """
        from ._footnote import collect_footnote_texts

        self.footnote_texts = collect_footnote_texts(root)
        widgets: list[QWidget] = []
        for node in root.children:
            w = self.render_node(node, parent)
            if w is not None:
                widgets.append(w)
        return widgets

    def render_node(
        self,
        node: SyntaxTreeNode,
        parent: QWidget,
        *,
        _skip_override: bool = False,
    ) -> QWidget | None:
        """按节点类型渲染单个节点为 widget。

        Args:
            node: 语法树节点。
            parent: 父容器。
            _skip_override: 为 True 时跳过 block_renderers（供 ctx.default 取默认）。

        Returns:
            QWidget | None: 渲染结果；无内容时返回 None。
        """
        # 用户块级 override 优先（_skip_override=True 时跳过，供 ctx.default 取默认）
        if not _skip_override:
            factory = self.block_renderers.get(node.type)
            if factory is not None:
                ctx = BlockContext(node, parent, self)
                try:
                    w = factory(ctx)
                    if w is not None:
                        if w.parent() is None:
                            w.setParent(parent)
                        return w
                except Exception:
                    pass  # 用户工厂出错退回默认渲染
        handler = getattr(self, f"_render_{node.type}", None)
        if handler is None:
            return self._render_fallback(node, parent)
        return handler(node, parent)

    # ------------------------------------------------------------
    # 块级 handler
    # ------------------------------------------------------------
    def _render_heading(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染标题：按级别取字号/字重，inline 内容转富文本。"""
        level = int(node.tag[1]) if node.tag and node.tag[1:].isdigit() else 1
        size, weight = HEADING_SPEC.get(level, HEADING_SPEC[6])
        inline = _first_inline(node)
        html = (
            inline_to_html(inline, self.theme, self.inline_overrides, self.sheet) if inline else ""
        )
        return self._rich_label(html, parent, size=size, weight=weight)

    def _render_paragraph(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget | None:
        """渲染段落：单张图→Image；含 widget 行内→_InlineFlow；否则富文本。"""
        inline = _first_inline(node)
        if inline is None:
            return None
        # 独立成段的单张图片 → 用 Image 组件
        img = self._sole_image(inline)
        if img is not None:
            src = img.attrs.get("src", "")
            return Image(src=src, parent=parent)
        # 逃生舱：仅当用户显式传 inline_widgets 指定的行内类型才降级；默认恒富文本。
        if paragraph_needs_flow(inline, self.inline_widgets):
            return _InlineFlow(
                inline,
                self.theme,
                self.inline_widgets,
                parent,
                self.sheet,
                self.footnote_texts,
            )
        html = inline_to_html(inline, self.theme, self.inline_overrides, self.sheet)
        return self._rich_label(html, parent)

    def _render_bullet_list(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染无序列表（委托 _ListBlock）。"""
        from ._blocks import _ListBlock

        return _ListBlock(node, self, parent)

    _render_ordered_list = _render_bullet_list

    def _render_blockquote(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染引用块（委托 _QuoteBlock）。"""
        from ._blocks import _QuoteBlock

        return _QuoteBlock(node, self, parent)

    def _render_hr(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染水平分隔线（Divider）。"""
        return Divider(orientation="horizontal", theme=self.theme, parent=parent)

    def _render_footnote_block(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染文档底部脚注定义区（委托 _FootnoteList）。"""
        from ._footnote import _FootnoteList

        return _FootnoteList(node, self, parent)

    def _render_table(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染 GFM 表格：解析 thead/tbody 为 Table 的列与行。"""
        table = Table(theme=self.theme, parent=parent)
        headers: list[str] = []
        aligns: list[str] = []
        rows: list[dict] = []
        for section in node.children:
            if section.type == "thead":
                for tr in section.children:
                    for cell in tr.children:
                        headers.append(_plain_text(cell))
                        aligns.append(self._cell_align(cell))
            elif section.type == "tbody":
                for ri, tr in enumerate(section.children):
                    row = {"key": str(ri)}
                    for ci, cell in enumerate(tr.children):
                        row[str(ci)] = _plain_text(cell)
                    rows.append(row)
        table.set_columns(
            [
                {"key": str(i), "label": h, "align": aligns[i] if i < len(aligns) else "start"}
                for i, h in enumerate(headers)
            ]
        )
        table.set_rows(rows)
        return table

    @staticmethod
    def _cell_align(cell: SyntaxTreeNode) -> str:
        """GFM 表头单元格 style="text-align:..." → Table 的 start/center/end。"""
        style = str(cell.attrs.get("style", "")).lower()
        if "center" in style:
            return "center"
        if "right" in style:
            return "end"
        return "start"

    def _render_fence(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget:
        """渲染围栏代码块（委托 CodeBlock，语言取首 token）。"""
        from ..code_block import CodeBlock

        # fence info 串首词为语言标记（```python → "python"）
        info = (node.info or "").strip()
        language = info.split()[0] if info else "text"
        return CodeBlock(
            node.content,
            language=language,
            filename="",
            theme=self.theme,
            parent=parent,
        )

    _render_code_block = _render_fence

    def _render_fallback(self, node: SyntaxTreeNode, parent: QWidget) -> QWidget | None:
        """未识别块：有 inline 子节点就当段落渲染，否则丢弃。"""
        inline = _first_inline(node)
        if inline is not None:
            return self._rich_label(
                inline_to_html(inline, self.theme, self.inline_overrides, self.sheet),
                parent,
            )
        return None

    # ------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------
    @staticmethod
    def _sole_image(inline: SyntaxTreeNode) -> SyntaxTreeNode | None:
        """inline 仅含单张图片（忽略纯空白文本）时返回该 image 节点。"""
        image = None
        for c in inline.children:
            if c.type == "image":
                if image is not None:
                    return None
                image = c
            elif (c.type == "text" and c.content.strip() == "") or c.type in (
                "softbreak",
                "hardbreak",
            ):
                continue
            else:
                return None
        return image


__all__ = ["BlockContext", "BlockRenderer", "MarkdownRenderer"]
