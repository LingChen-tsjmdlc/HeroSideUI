"""Widget 生命周期工具：集中安全销毁写法，防 Windows 无父瞬间闪原生窗。"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QLayout, QWidget


def safe_delete(widget: QWidget | None) -> None:
    """安全销毁单个 widget：hide 后 deleteLater，绝不 setParent(None)。"""
    if widget is None:
        return
    widget.hide()
    widget.deleteLater()


def safe_delete_many(widgets: Iterable[QWidget | None]) -> None:
    """批量安全销毁。"""
    for w in widgets:
        safe_delete(w)


def clear_layout(layout: QLayout | None) -> None:
    """清空布局中的所有子 widget（安全销毁），保留布局本身。"""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget() if item is not None else None
        if w is not None:
            safe_delete(w)


__all__ = ["clear_layout", "safe_delete", "safe_delete_many"]
