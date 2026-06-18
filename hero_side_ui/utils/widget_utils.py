"""Widget 生命周期工具。

集中处理 Qt widget 销毁 / 清空布局的安全写法，避免"无父 widget 在 Windows 上
瞬间被当成顶层窗口、闪出原生空白小窗"这一高频踩坑。

核心规律
    一个 widget 一旦处于"无父对象"状态（``setParent(None)`` 之后，或创建时未传
    parent 且尚未加入布局），在 Windows 上会被当作顶层窗口，立刻套上原生标题栏闪
    一帧。批量销毁 / 重建（表格翻页、分页器重排、列表重填）时表现为弹出一堆空白窗。

正确做法
    销毁子 widget：直接 ``hide() + deleteLater()``，**不要** 先 ``setParent(None)``。
    deleteLater 会自动解除父子关系，无需手动 reparent。
"""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtWidgets import QLayout, QWidget


def safe_delete(widget: Optional[QWidget]) -> None:
    """安全销毁单个 widget：hide 后 deleteLater。

    绝不调用 ``setParent(None)`` —— 那会让 widget 瞬间变顶层窗口在 Windows 闪原生 frame。
    deleteLater 自身会解除父子关系。``widget`` 为 None 时安全跳过。
    """
    if widget is None:
        return
    widget.hide()
    widget.deleteLater()


def safe_delete_many(widgets: Iterable[Optional[QWidget]]) -> None:
    """批量安全销毁。"""
    for w in widgets:
        safe_delete(w)


def clear_layout(layout: Optional[QLayout]) -> None:
    """清空布局中的所有子 widget（安全销毁），保留布局本身。"""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget() if item is not None else None
        if w is not None:
            safe_delete(w)


__all__ = ["safe_delete", "safe_delete_many", "clear_layout"]
