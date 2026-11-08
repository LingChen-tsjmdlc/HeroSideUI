"""Markdown 私有块级容器：_ListBlock 与 _QuoteBlock。

只负责缩进/符号/竖条并回调 renderer 递归渲染子节点；子 widget 显式传
parent 防 Windows 无父闪窗。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ...themes import HEROUI_COLORS, MARKDOWN_LIST, MARKDOWN_QUOTE, MARKDOWN_SPACING
from ..checkbox import Checkbox
from ..text import Body, Text

if TYPE_CHECKING:
    from markdown_it.tree import SyntaxTreeNode

    from ._renderer import MarkdownRenderer


def _task_state(item: SyntaxTreeNode) -> bool | None:
    """判断列表项是否任务项：是则返回勾选状态，否则 None。

    按 tasklists 插件注入的 class 与 <input checked> 判定。
    """
    cls = str(item.attrs.get("class", "")) if _safe_has_attrs(item) else ""
    if "task-list-item" not in cls:
        return None
    for para in item.children:
        for inline in para.children:
            if inline.type != "inline":
                continue
            for c in inline.children:
                if c.type == "html_inline" and "task-list-item-checkbox" in c.content:
                    return "checked" in c.content
    return None


def _safe_has_attrs(node: SyntaxTreeNode) -> bool:
    """安全探测节点是否带 attrs（部分节点读 attrs 会抛异常）。

    Returns:
        bool: True 表示可安全访问 node.attrs。
    """
    try:
        _ = node.attrs
        return True
    except Exception:
        return False


class _ReadonlyCheckbox(Checkbox):
    """只读任务勾选框：复用 Checkbox 外观，仅拦截交互事件保持正常配色。"""

    def __init__(self, checked: bool, theme: str, parent: QWidget = None):
        """构造只读勾选框。

        Args:
            checked: 初始勾选状态。
            theme: 主题（light/dark）。
            parent: 父控件。
        """
        super().__init__(
            is_selected=checked,
            theme=theme,
            parent=parent,
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def mousePressEvent(self, event):  # type: ignore[override]
        """拦截按下事件，保持只读（不触发 toggle）。"""
        event.ignore()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        """拦截释放事件，保持只读。"""
        event.ignore()

    def keyPressEvent(self, event):  # type: ignore[override]
        """拦截键盘事件，保持只读。"""
        event.ignore()


class _ListBlock(QWidget):
    """有序/无序列表容器：符号或序号 + 内容区递归渲染；任务项换只读 Checkbox。"""

    def __init__(
        self,
        node: SyntaxTreeNode,
        renderer: MarkdownRenderer,
        parent: QWidget = None,
    ):
        """构建列表块：遍历 list_item 生成「符号/序号 + 递归渲染内容」行。

        Args:
            node: 语法树中的 ordered_list / bullet_list 节点。
            renderer: MarkdownRenderer，用于递归渲染子节点。
            parent: 父控件。
        """
        super().__init__(parent)
        self._ordered = node.type == "ordered_list"
        self._renderer = renderer

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(MARKDOWN_SPACING["list_item_gap"])

        start = 1
        if self._ordered:
            try:
                start = int(node.attrs.get("start", 1))
            except (TypeError, ValueError):
                start = 1

        for i, item in enumerate(node.children):
            if item.type != "list_item":
                continue
            task = _task_state(item)
            marker = f"{start + i}." if self._ordered else MARKDOWN_LIST["bullet"]
            lay.addWidget(self._build_item(marker, item, task))

    def _build_item(self, marker: str, item: SyntaxTreeNode, task: bool | None) -> QWidget:
        """构建单行：左侧 marker（序号/符号/只读 Checkbox）+ 右侧递归渲染内容。

        Args:
            marker: 序号或项目符号文本。
            item: list_item 语法树节点。
            task: 任务勾选状态；None 表示非任务项。

        Returns:
            QWidget: 一行（marker + 内容）的容器。
        """
        row = QWidget(self)
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(MARKDOWN_LIST["indent"], 0, 0, 0)
        # 任务项：勾选框与文字贴近些（普通列表沿用默认 marker_gap）
        row_lay.setSpacing(
            MARKDOWN_LIST["task_marker_gap"] if task is not None else MARKDOWN_LIST["marker_gap"]
        )
        row_lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        if task is not None:
            marker_widget = _ReadonlyCheckbox(task, self._renderer.theme, parent=row)
        else:
            marker_widget = Body(marker, parent=row)
            marker_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        row_lay.addWidget(marker_widget, 0, Qt.AlignmentFlag.AlignTop)

        content = QWidget(row)
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(MARKDOWN_SPACING["list_item_gap"])
        for child in item.children:
            w = self._renderer.render_node(child, content)
            if w is not None:
                # 文字降到 60% 透明度（弱化观感）
                if task is True and isinstance(w, Text):
                    w.set_transparency(MARKDOWN_LIST["task_done_opacity"])
                content_lay.addWidget(w)
        row_lay.addWidget(content, 1)
        return row


class _QuoteBlock(QWidget):
    """引用块：主题色竖条 + 半透明底，嵌套层层叠加天然区分层级。"""

    def __init__(
        self,
        node: SyntaxTreeNode,
        renderer: MarkdownRenderer,
        parent: QWidget = None,
    ):
        """构建引用块：半透明底容器 + 左侧主题色竖条，内部递归渲染子节点。

        Args:
            node: blockquote 语法树节点。
            renderer: MarkdownRenderer，用于递归渲染子节点。
            parent: 父控件。
        """
        super().__init__(parent)
        self._renderer = renderer
        self._theme = renderer.theme
        # 半透明底要能透出父层已画的底色（嵌套叠加），故关闭自身不透明填充
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

        bar_w = MARKDOWN_QUOTE["bar_width"]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(
            bar_w + MARKDOWN_QUOTE["pad_left"],
            MARKDOWN_QUOTE["pad_v"],
            MARKDOWN_QUOTE["pad_right"],
            MARKDOWN_QUOTE["pad_v"],
        )
        lay.setSpacing(0)

        content = QWidget(self)
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(MARKDOWN_QUOTE["content_gap"])
        for child in node.children:
            w = self._renderer.render_node(child, content)
            if w is not None:
                content_lay.addWidget(w)
        lay.addWidget(content, 1)

    def _bar_color(self) -> QColor:
        """返回左侧竖条颜色。

        Returns:
            QColor: 当前主题对应的竖条色。
        """
        shade = (
            MARKDOWN_QUOTE["bar_shade_dark"]
            if self._theme == "dark"
            else MARKDOWN_QUOTE["bar_shade"]
        )
        return QColor(HEROUI_COLORS["default"][shade])

    def _bg_color(self) -> QColor:
        """返回半透明背景色。

        Returns:
            QColor: 带 alpha 的叠加底色。
        """
        r, g, b = (
            MARKDOWN_QUOTE["overlay_dark"]
            if self._theme == "dark"
            else MARKDOWN_QUOTE["overlay_light"]
        )
        c = QColor(r, g, b)
        c.setAlphaF(MARKDOWN_QUOTE["overlay_alpha"])
        return c

    def paintEvent(self, event):  # type: ignore[override]
        """重绘：绘制圆角半透明底与左缘竖条。"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = MARKDOWN_QUOTE["radius"]
        rect = self.rect()
        # 半透明底（圆角，无边框）
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color())
        painter.drawRoundedRect(rect, radius, radius)
        # 左缘竖条
        bar_w = MARKDOWN_QUOTE["bar_width"]
        painter.setBrush(self._bar_color())
        painter.drawRect(0, radius, bar_w, self.height() - 2 * radius)
        painter.end()


__all__ = ["_ListBlock", "_QuoteBlock"]
