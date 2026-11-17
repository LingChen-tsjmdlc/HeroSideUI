"""测试里的等待辅助：只允许等条件成立，不允许等一段固定时长。

CI 机器的快慢不可预测，固定时长要么偏短（偶发失败）要么偏长（白白变慢）。
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

# 条件等待的上限：只是防止卡死，正常情况下条件一成立就立刻返回
LIMIT_MS = 15000


def until(qtbot, condition, timeout: int = LIMIT_MS) -> None:
    """等 condition() 为真；超时抛 AssertionError。

    Args:
        qtbot: pytest-qt 夹具。
        condition: 无参可调用，返回是否已成立。
        timeout: 超时毫秒数，仅用于防卡死。
    """
    qtbot.waitUntil(condition, timeout=timeout)


def flush(qtbot, rounds: int = 3) -> None:
    """让已经投递的事件（布局、延迟回调、deleteLater）各处理 rounds 轮。

    Args:
        qtbot: pytest-qt 夹具，用来拿到事件循环。
        rounds: 处理轮数；不是时长，一轮处理完当前队列就结束。
    """
    app = QApplication.instance()
    for _ in range(rounds):
        app.processEvents()
        app.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))


def popup_ready(popover) -> bool:
    """弹层已打开且淡入动画走完。

    Args:
        popover: Popover 或 Tooltip 实例。
    """
    opened = (
        popover.is_open() if hasattr(popover, "is_open") else getattr(popover, "_is_open", False)
    )
    if not opened:
        return False
    fade = getattr(popover, "_fade", None)
    return fade is None or fade.progress >= 0.99


def widget_settled(widget) -> bool:
    """控件的几何已经稳定（布局完成）：尺寸有效且没有待处理的布局请求。

    Args:
        widget: 任意 QWidget。
    """
    return widget.width() > 0 and widget.height() > 0
