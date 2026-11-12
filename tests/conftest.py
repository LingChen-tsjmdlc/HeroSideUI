"""pytest 全局配置与 fixture。

本文件解决的问题：
1. Windows 下 PySide6 + pytest-qt 在**跨测试文件切换**时出现的
   access violation（`pytestqt/plugin.py:_process_events` 访问已释放
   的 C++ 对象）。
2. Accordion / Button / Input 里使用的 QPropertyAnimation、QTimer、
   RippleOverlay 等在测试结束时仍可能处于 active 状态，如果测试直接
   退出，定时器回调会在下一个测试期间 fire，访问已释放的 widget。

做法：
- 在 pytest-qt 于 CALL 尾部处理事件之前，先停掉所有活跃动画 / QTimer。
- 在每个测试前后，反复抽干 Qt 事件队列（含 deleteLater 和 Timer），
  最多 10 轮或 200ms。
"""

from __future__ import annotations

import gc

import pytest
from PySide6.QtCore import QAbstractAnimation, QEvent, QTimer
from PySide6.QtWidgets import QApplication


def _drain_events(max_iterations: int = 10) -> None:
    """反复处理事件队列，直到不再有新事件或达到上限。"""
    app = QApplication.instance()
    if app is None:
        return
    for _ in range(max_iterations):
        # 处理常规事件
        app.processEvents()
        # 必须显式指定 DeferredDelete：传 0 时 Qt 按事件循环嵌套层级跳过
        # deleteLater 队列，顶层窗口会跨测试累积（真实 GUI 下都是原生窗口）。
        app.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
        # 再给 GC 一次机会
        gc.collect()


def _stop_all_timers_and_animations() -> None:
    """停止所有顶层 widget 与 app 自身子树里的 QTimer 和动画。"""
    app = QApplication.instance()
    if app is None:
        return
    for root in [*app.topLevelWidgets(), app]:
        try:
            for timer in root.findChildren(QTimer):
                timer.stop()
            # QAbstractAnimation 覆盖 QPropertyAnimation / QVariantAnimation /
            # QAnimationGroup；只找 QPropertyAnimation 会漏掉 tween_value 通道。
            for anim in root.findChildren(QAbstractAnimation):
                anim.stop()
        except RuntimeError:
            # root 可能已经被 C++ 端销毁
            continue


def _keep_toplevel_widgets_alive(item) -> None:
    """把当前全部顶层 widget 挂到 item 上保活，直到 qtbot teardown 完成删除。

    测试函数 return 后其局部顶层窗口（Python-owned，qtbot 只持 weakref）已不可
    达，而 qtbot 的 close+deleteLater 要等 teardown hook；此间隙的任何一次自动
    GC 都会在 GC 内析构原生窗口，~QWidget 发出的 Destroy 事件经 app 级 Python
    eventFilter 需要重建 wrapper，Shiboken 对半析构对象做 __dynamic_cast 会读
    到已退化的 RTTI/vtable（macOS Cocoa 崩 exit 139 的根因）。挂强引用后 GC
    不会碰这些 wrapper，析构改由 qtbot 的 deleteLater + teardown 尾部
    processEvents 驱动，此时 wrapper 仍然有效。
    """
    app = QApplication.instance()
    if app is None:
        return
    try:
        widgets = [w for w in app.topLevelWidgets() if w.parentWidget() is None]
    except RuntimeError:
        return
    item._hs_keepalive = widgets


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtest_call(item):
    """在 pytest-qt 恢复并调用 app.processEvents() 之前停掉活跃动画。

    Note:
        pytest-qt 的 pytest_runtest_call 是 tryfirst wrapper，yield 之后
        立刻处理事件队列；trylast wrapper 会先恢复，所以这里的清理赶在
        事件派发之前，动画 tick 不会跨测试访问已释放的 widget。

        测试函数返回后其局部 widget（顶层窗口，Python-owned）已不可达，
        qtbot 的 close+deleteLater 却要等 teardown 阶段；此间隙若自动 GC
        触发，会在 GC 内析构原生窗口，~QWidget 发出的 Destroy 事件经
        app 级 Python eventFilter 需要重建 wrapper，Shiboken 对半析构
        对象做 __dynamic_cast 读到退化 RTTI（macOS exit 139 根因）。
        故在此把顶层 widget 挂到 item 上保活，析构统一交给 qtbot 的
        close+deleteLater + teardown 尾部 processEvents，全程 wrapper 有效。
    """
    result = yield
    _stop_all_timers_and_animations()
    _keep_toplevel_widgets_alive(item)
    return result


@pytest.fixture(autouse=True)
def _cleanup_qt_state(qtbot):
    """每个测试前后彻底清理 Qt 状态，防止跨测试访问违规。"""
    _drain_events()
    yield
    _stop_all_timers_and_animations()
    _drain_events()
    gc.collect()
    _drain_events()
