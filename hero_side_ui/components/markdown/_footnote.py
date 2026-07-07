"""脚注渲染：行内引用角标（hover Tooltip）+ 文档底部脚注列表。

脚注引用 ``[^n]`` 渲染成上标角标 widget，hover 用 Tooltip 弹出脚注正文；
底部的 ``footnote_block`` 渲染成带序号的定义列表。两者都复用现成组件
（Text / Tooltip），子 widget 创建时显式传 parent，避免无父瞬间闪窗。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ...themes import HEROUI_COLORS, MARKDOWN_LIST, MARKDOWN_SPACING
from ..text import Text
from ..tooltip import Tooltip

if TYPE_CHECKING:
    from markdown_it.tree import SyntaxTreeNode
    from ._renderer import MarkdownRenderer


def footnote_label(node: "SyntaxTreeNode") -> str:
    """从 footnote_ref/footnote 节点取显示序号（meta.id 为 0 基，展示 +1）。"""
    meta = getattr(node, "meta", None) or {}
    if "id" in meta:
        try:
            return str(int(meta["id"]) + 1)
        except (TypeError, ValueError):
            pass
    return str(meta.get("label", "?"))


class _FootnoteRef(QWidget):
    """行内脚注角标：上标序号 + hover Tooltip 显示正文。"""

class _FootnoteRef(QWidget):
    """行内脚注角标：上标序号 chip + hover Tooltip 显示正文。

    Tooltip 用 **embedded 模式**（作为角标顶层窗口的子 widget，hover 走 Qt 原生父子
    事件，比顶层 Qt.Tool 在"小角标 + 滚动区"场景下可靠）。embedded 的 attach 会把
    tooltip reparent 到 ``trigger.window()``，需 widget 已入窗口树，故 attach 走两条
    路：showEvent（首次可见）+ 下一帧 QTimer 兜底——Markdown 切主题整树重建时新角标
    在 setUpdatesEnabled(False) 期间入树，showEvent 可能被抑制不补发，单靠它会漏挂。
    ``_tip_attached`` 守卫保证只挂一次；角标销毁时销毁 tooltip（它被 reparent 到 window，
    不会随角标自动死），避免切主题反复重建泄漏。
    """

    def __init__(self, label: str, body: str, theme: str, parent: QWidget = None):
        super().__init__(parent)
        self._theme = theme
        self._body = body
        self._tip: "Tooltip | None" = None
        self._tip_attached = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._chip = Text(
            size="md",
            theme=theme,
            rich_text=True,
            selectable=False,
            parent=self,
        )
        self._chip.setTextFormat(Qt.TextFormat.RichText)
        link = HEROUI_COLORS["primary"][500]
        self._chip.setText(f"<sup style='color:{link}'>[{label}]</sup>")
        self._chip.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(self._chip)

        if self._body:
            QTimer.singleShot(0, self._ensure_tip)

    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        self._ensure_tip()

    def _ensure_tip(self) -> None:
        """入窗口树后 attach embedded Tooltip；幂等，只挂一次。"""
        if not self._body or self._tip_attached:
            return
        # 尚未挂进真正的顶层窗口（window() 还是自己）时先不挂，等下次时机
        if self.window() is self:
            return
        self._tip = Tooltip(
            content=self._body,
            placement="top",
            show_arrow=True,
            embedded=True,
            theme=self._theme,
            parent=self,
        )
        self._tip.attach(self._chip)
        self._tip_attached = True
        # tooltip 被 attach 时 reparent 到 window，不随角标自动销毁 → 手动清理防泄漏
        tip = self._tip

        def _cleanup(*_a, _t=tip):
            try:
                _t.close()
                _t.deleteLater()
            except RuntimeError:
                pass

        self.destroyed.connect(_cleanup)


class _FootnoteList(QWidget):
    """文档底部脚注定义区：序号 + 正文，逐条纵向排列。"""

    def __init__(
        self,
        node: "SyntaxTreeNode",
        renderer: "MarkdownRenderer",
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self._renderer = renderer

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, MARKDOWN_SPACING["block_gap"], 0, 0)
        lay.setSpacing(MARKDOWN_SPACING["list_item_gap"])

        for item in node.children:
            if item.type != "footnote":
                continue
            lay.addWidget(self._build_item(footnote_label(item), item))

    def _build_item(self, marker: str, item: "SyntaxTreeNode") -> QWidget:
        row = QWidget(self)
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(MARKDOWN_LIST["marker_gap"])
        row_lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        marker_label = Text(f"{marker}.", size="sm", theme=self._renderer.theme, parent=row)
        marker_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        row_lay.addWidget(marker_label, 0, Qt.AlignmentFlag.AlignTop)

        content = QWidget(row)
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(MARKDOWN_SPACING["tight_gap"])
        for child in item.children:
            if child.type == "footnote_anchor":  # 回跳锚点：无正文，跳过
                continue
            w = self._renderer.render_node(child, content)
            if w is not None:
                content_lay.addWidget(w)
        row_lay.addWidget(content, 1)
        return row


def collect_footnote_texts(root: "SyntaxTreeNode") -> Dict[str, str]:
    """遍历语法树，收集 {显示序号: 脚注正文纯文本}，供行内角标 Tooltip 使用。"""
    from ._renderer import _plain_text

    out: Dict[str, str] = {}

    def walk(node: "SyntaxTreeNode") -> None:
        for child in node.children:
            if child.type == "footnote_block":
                for fn in child.children:
                    if fn.type != "footnote":
                        continue
                    parts = [
                        _plain_text(c).strip()
                        for c in fn.children
                        if c.type != "footnote_anchor"
                    ]
                    out[footnote_label(fn)] = " ".join(p for p in parts if p)
            walk(child)

    walk(root)
    return out


__all__ = ["_FootnoteRef", "_FootnoteList", "footnote_label", "collect_footnote_texts"]
