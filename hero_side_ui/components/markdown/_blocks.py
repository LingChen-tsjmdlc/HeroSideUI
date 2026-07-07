"""Markdown 私有块级容器：列表、引用块。

这两类是 Markdown 中唯二的"容器节点"——内部可递归嵌套任意块级内容
（段落、子列表、引用），库里没有现成组件可对应，故新写两个轻量容器。

职责只有三件：缩进 / 符号或竖条 / 把子节点回调 renderer 递归渲染。
不含业务逻辑、不发信号；引用竖条颜色随主题，取自 ``MARKDOWN_QUOTE``。
所有子 widget 创建时显式传 parent，避免无父瞬间触发 Windows 闪窗。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ...themes import HEROUI_COLORS, MARKDOWN_LIST, MARKDOWN_QUOTE, MARKDOWN_SPACING
from ..checkbox import Checkbox
from ..text import Body, Text

if TYPE_CHECKING:
    from markdown_it.tree import SyntaxTreeNode
    from ._renderer import MarkdownRenderer


def _task_state(item: "SyntaxTreeNode") -> Optional[bool]:
    """列表项是否为任务项：是则返回勾选状态(True/False)，否则 None。

    tasklists 插件把 task 项标 class=task-list-item，并在其 inline 首个
    html_inline 注入 ``<input ... checked ...>``；据此判定并读勾选态。
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


def _safe_has_attrs(node: "SyntaxTreeNode") -> bool:
    try:
        _ = node.attrs
        return True
    except Exception:
        return False


class _ReadonlyCheckbox(Checkbox):
    """只读任务勾选框：复用 Checkbox 默认外观，仅屏蔽点击/键盘/焦点切换。

    不传 size/radius/disable_animation —— 全用组件默认样式。不用 is_disabled
    （会置灰），只拦截交互事件保持正常配色。
    """

    def __init__(self, checked: bool, theme: str, parent: QWidget = None):
        super().__init__(
            is_selected=checked,
            theme=theme,
            parent=parent,
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def mousePressEvent(self, event):  # type: ignore[override]
        event.ignore()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        event.ignore()

    def keyPressEvent(self, event):  # type: ignore[override]
        event.ignore()


class _ListBlock(QWidget):
    """有序 / 无序列表容器。

    每个列表项 = 左侧符号(•)或序号(1.) + 右侧内容区；内容区把列表项的子节点
    交回 renderer 递归渲染，从而支持项内嵌套段落 / 子列表。任务项(- [x]/- [ ])
    的左侧符号换成只读 Checkbox。
    """

    def __init__(
        self,
        node: "SyntaxTreeNode",
        renderer: "MarkdownRenderer",
        parent: QWidget = None,
    ):
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

    def _build_item(
        self, marker: str, item: "SyntaxTreeNode", task: Optional[bool]
    ) -> QWidget:
        row = QWidget(self)
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(MARKDOWN_LIST["indent"], 0, 0, 0)
        # 任务项：勾选框与文字贴近些（普通列表沿用默认 marker_gap）
        row_lay.setSpacing(
            MARKDOWN_LIST["task_marker_gap"]
            if task is not None
            else MARKDOWN_LIST["marker_gap"]
        )
        row_lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        if task is not None:
            marker_widget = _ReadonlyCheckbox(task, self._renderer.theme, parent=row)
        else:
            marker_widget = Body(marker, parent=row)
            marker_widget.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
            )
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
    """引用块：左侧主题色竖条 + 半透明黑/白底，右侧递归渲染子内容。

    底色用半透明（亮色叠黑、暗色叠白），嵌套引用是层层子 widget，各自画一层
    半透明底叠加在父底上，故越深层视觉越暗，天然区分嵌套层级。无边框。
    """

    def __init__(
        self,
        node: "SyntaxTreeNode",
        renderer: "MarkdownRenderer",
        parent: QWidget = None,
    ):
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
        shade = (
            MARKDOWN_QUOTE["bar_shade_dark"]
            if self._theme == "dark"
            else MARKDOWN_QUOTE["bar_shade"]
        )
        return QColor(HEROUI_COLORS["default"][shade])

    def _bg_color(self) -> QColor:
        r, g, b = (
            MARKDOWN_QUOTE["overlay_dark"]
            if self._theme == "dark"
            else MARKDOWN_QUOTE["overlay_light"]
        )
        c = QColor(r, g, b)
        c.setAlphaF(MARKDOWN_QUOTE["overlay_alpha"])
        return c

    def paintEvent(self, event):  # type: ignore[override]
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
