"""pytest 全局配置与 fixture。

1. 跨测试文件切换时，PySide6 + pytest-qt 在 Windows 下会访问已释放的 C++ 对象；
2. 动画 / QTimer / RippleOverlay 在用例结束时仍可能 active，回调会落到下一个用例。

做法：CALL 尾部处理事件前先停掉活跃动画与 QTimer；每个用例前后抽干事件队列。

诊断（环境变量，CI 默认开启）：
- HS_TRACE_FILE：逐阶段写追踪日志（无缓冲，崩溃不丢），含 Qt 消息、GC 起止、进程快照
- HS_DISABLE_GC=1：关闭自动 GC，回收只在用例边界进行
"""

from __future__ import annotations

import gc
import os
import sys
import threading
import time

import pytest
from PySide6.QtCore import QAbstractAnimation, QEvent, QTimer, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

_T0 = time.monotonic()
_TRACE_FD: int | None = None
_QT_HANDLER = None  # 保持引用，避免回调被回收
_ENV_LOGGED = False


def _trace(msg: str) -> None:
    """追加一行带时间与线程号的追踪记录。"""
    if _TRACE_FD is None:
        return
    line = f"{time.monotonic() - _T0:9.3f} T{threading.get_ident() % 100000:<5} {msg}\n"
    try:
        os.write(_TRACE_FD, line.encode("utf-8", "replace"))
    except OSError:
        pass


def _fd_count() -> int:
    """当前进程打开的文件句柄数。"""
    for path in ("/dev/fd", "/proc/self/fd"):
        try:
            return len(os.listdir(path))
        except OSError:
            continue
    return -1


def _peak_rss_mb() -> float:
    """进程峰值常驻内存（MB）。"""
    try:
        import resource
    except ImportError:
        return -1.0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1048576 if sys.platform == "darwin" else 1024)


def _app_filters() -> str:
    """app 级事件过滤器的安装状态。"""
    try:
        from hero_side_ui.core.scroll_style import ScrollStyle
        from hero_side_ui.core.smooth_scroll import SmoothScroll

        style = getattr(ScrollStyle.peek(), "_app_filter_installed", None)
        return f"filters(style={style} smooth={SmoothScroll._global_filter is not None})"
    except Exception as exc:
        return f"filters(?{type(exc).__name__})"


def _state() -> str:
    """进程与 Qt 的快照：GC、顶层窗口、线程、句柄、内存。"""
    top = -1
    app = QApplication.instance()
    if app is not None:
        try:
            top = len(app.topLevelWidgets())
        except RuntimeError:
            top = -2
    return (
        f"gc={'on' if gc.isenabled() else 'off'}{gc.get_count()} top={top} "
        f"threads={threading.active_count()} fds={_fd_count()} "
        f"rss_peak={_peak_rss_mb():.0f}MB {_app_filters()}"
    )


_GC_T0 = 0.0


def _gc_trace(phase: str, info: dict) -> None:
    """GC 回调：只记录会改变对象状态的回收（回收了对象、有不可回收对象，或耗时超 50ms）。"""
    global _GC_T0
    if phase == "start":
        _GC_T0 = time.monotonic()
        return
    cost = time.monotonic() - _GC_T0
    if info["collected"] or info["uncollectable"] or cost > 0.05:
        _trace(
            f"  GC gen={info['generation']} collected={info['collected']} "
            f"uncollectable={info['uncollectable']} cost={cost * 1000:.0f}ms"
        )


def _qt_message(msg_type, context, message) -> None:
    """Qt 消息写入追踪文件。"""
    try:
        where = ""
        if context is not None and getattr(context, "file", None):
            where = f" @ {context.file}:{context.line} {context.function}"
        name = getattr(msg_type, "name", str(msg_type))
        _trace(f"  QT {name} [{getattr(context, 'category', '')}] {message}{where}")
    except Exception:
        pass


def _route_qt_messages(item) -> None:
    """pytest-qt 的处理器只记录不转发，这里包一层让消息同时进追踪文件。"""
    global _QT_HANDLER
    if _TRACE_FD is None:
        return
    inner = getattr(getattr(item, "qt_log_capture", None), "_handle_with_context", None)

    def handler(msg_type, context, message):
        _qt_message(msg_type, context, message)
        if inner is not None:
            inner(msg_type, context, message)

    _QT_HANDLER = handler
    qInstallMessageHandler(handler)


def _log_environment(config) -> None:
    """首个用例 setup 后记录一次运行环境。"""
    global _ENV_LOGGED
    if _ENV_LOGGED or _TRACE_FD is None:
        return
    _ENV_LOGGED = True
    try:
        import platform

        import PySide6
        from PySide6.QtCore import qVersion

        _trace(f"ENV python={sys.version.split()[0]} {platform.platform()} {platform.machine()}")
        _trace(f"ENV PySide6={PySide6.__version__} Qt={qVersion()} pytest={pytest.__version__}")
        app = QApplication.instance()
        if app is not None:
            _trace(f"ENV platform={app.platformName()} style={app.style().objectName()}")
            for screen in app.screens():
                geo, avail = screen.geometry(), screen.availableGeometry()
                _trace(
                    f"ENV screen {screen.name()} geo={geo.getRect()} avail={avail.getRect()} "
                    f"dpr={screen.devicePixelRatio()}"
                )
        keys = ("QT_", "Malloc", "PYTHON", "HS_", "CI", "GITHUB_RUN")
        env = {k: v for k, v in sorted(os.environ.items()) if k.startswith(keys)}
        _trace(f"ENV vars={env}")
        plugins = [n for n, _ in config.pluginmanager.list_name_plugin() if n and n[0] != "_"]
        _trace(f"ENV plugins={sorted(plugins)}")
    except Exception as exc:
        _trace(f"ENV log failed: {type(exc).__name__}: {exc}")


def pytest_configure(config) -> None:
    """按环境变量开启追踪与关闭自动 GC。"""
    global _TRACE_FD
    path = os.environ.get("HS_TRACE_FILE")
    if path:
        _TRACE_FD = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        gc.callbacks.append(_gc_trace)
        qInstallMessageHandler(_qt_message)
        _trace(f"CONFIGURE argv={sys.argv[1:]}")
    if os.environ.get("HS_DISABLE_GC") == "1":
        gc.disable()


def pytest_unconfigure(config) -> None:
    """恢复 GC 并关闭追踪文件。"""
    global _TRACE_FD
    gc.enable()
    if _gc_trace in gc.callbacks:
        gc.callbacks.remove(_gc_trace)
    if _TRACE_FD is not None:
        fd, _TRACE_FD = _TRACE_FD, None
        os.close(fd)


def pytest_collection_finish(session) -> None:
    """记录收集到的用例数。"""
    _trace(f"COLLECTED {len(session.items)} items")


def pytest_sessionfinish(session, exitstatus) -> None:
    """正常结束的标记；追踪里缺这一行说明进程崩溃或被杀。"""
    _trace(f"SESSION FINISH exit={exitstatus}")


def pytest_runtest_logstart(nodeid, location) -> None:
    """用例分隔线。"""
    _trace(f"==== TEST {nodeid}")


def pytest_runtest_logreport(report) -> None:
    """各阶段的结果与耗时。"""
    _trace(f"  report {report.when:<8} {report.outcome:<7} {report.duration:.3f}s")


def pytest_warning_recorded(warning_message, when, nodeid, location) -> None:
    """pytest 捕获的警告（含未处理异常）。"""
    _trace(
        f"  WARN[{when}] {warning_message.category.__name__}: {str(warning_message.message)[:300]}"
    )


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    """记录 setup 阶段的起止。"""
    _trace(f"BEGIN setup    {item.nodeid} | {_state()}")
    try:
        return (yield)
    finally:
        _route_qt_messages(item)
        _log_environment(item.config)
        _trace(f"END   setup    {item.nodeid}")


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_teardown(item, nextitem):
    """记录 teardown 阶段的起止。"""
    _trace(f"BEGIN teardown {item.nodeid} | {_state()}")
    try:
        return (yield)
    finally:
        _trace(f"END   teardown {item.nodeid}")


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
    _route_qt_messages(item)
    _trace(f"BEGIN call     {item.nodeid} | {_state()}")
    try:
        result = yield
    finally:
        _trace(f"END   call     {item.nodeid}")
    _stop_all_timers_and_animations()
    _keep_toplevel_widgets_alive(item)
    return result


@pytest.fixture(autouse=True)
def _cleanup_qt_state(qtbot):
    """每个测试前后彻底清理 Qt 状态，防止跨测试访问违规。"""
    _trace("  fixture pre-drain")
    _drain_events()
    yield
    _trace("  fixture post-test: stop timers + drain + gc.collect")
    _stop_all_timers_and_animations()
    _drain_events()
    gc.collect()
    _drain_events()
    _trace("  fixture done")
