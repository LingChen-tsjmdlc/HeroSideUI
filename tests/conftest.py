"""pytest 全局配置与 fixture。

本文件解决的问题：
1. Windows 下 PySide6 + pytest-qt 在**跨测试文件切换**时出现的
   access violation（`pytestqt/plugin.py:_process_events` 访问已释放
   的 C++ 对象）。
2. Accordion / Button / Input 里使用的 QPropertyAnimation、QTimer、
   RippleOverlay 等在测试结束时仍可能处于 active 状态，如果测试直接
   退出，定时器回调会在下一个测试期间 fire，访问已释放的 widget。

做法：
- 在每个测试前后，反复抽干 Qt 事件队列（含 deleteLater 和 Timer），
  最多 10 轮或 200ms。
- 主动停止所有 top-level widget 下的动画 / QTimer。
"""

from __future__ import annotations

import gc

import pytest

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def _drain_events(max_iterations: int = 10) -> None:
    """反复处理事件队列，直到不再有新事件或达到上限。"""
    app = QApplication.instance()
    if app is None:
        return
    for _ in range(max_iterations):
        # 处理常规事件
        app.processEvents()
        # 处理 deleteLater 队列
        app.sendPostedEvents(None, 0)  # 0 = QEvent.DeferredDelete 相关
        # 再给 GC 一次机会
        gc.collect()


def _stop_all_timers_and_animations() -> None:
    """扫描所有 top-level widget，停止其 QTimer 子对象和 QPropertyAnimation。"""
    app = QApplication.instance()
    if app is None:
        return
    try:
        from PySide6.QtCore import QPropertyAnimation
    except ImportError:
        QPropertyAnimation = None  # type: ignore[assignment]

    for widget in list(app.topLevelWidgets()):
        try:
            for timer in widget.findChildren(QTimer):
                timer.stop()
            if QPropertyAnimation is not None:
                for anim in widget.findChildren(QPropertyAnimation):
                    anim.stop()
        except RuntimeError:
            # widget 可能已经被 C++ 端销毁
            continue


@pytest.fixture(autouse=True)
def _cleanup_qt_state(qtbot):  # noqa: ARG001  qtbot 注入确保 QApplication 已就绪
    """每个测试前后彻底清理 Qt 状态，防止跨测试访问违规。"""
    _drain_events()
    yield
    _stop_all_timers_and_animations()
    _drain_events()
    gc.collect()
    _drain_events()
