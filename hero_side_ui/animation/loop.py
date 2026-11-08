"""提供可见性感知的公共循环进度驱动。"""

import weakref

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Slot,
)
from shiboken6 import isValid


class LoopDriver(QObject):
    """为自绘效果提供独立的循环进度。

    Note:
        宿主持有 Python 驱动包装器以保留事件过滤器状态；Qt 父对象负责 C++ 所有权。

    Attributes:
        phase: 0 到 1 的当前循环进度。
    """

    def __init__(self, owner, duration=1200, easing=QEasingCurve.Type.Linear, parent=None):
        """初始化循环驱动。

        Args:
            owner: 接收重绘的 QWidget。
            duration: 一个周期的毫秒数。
            easing: 进度缓动曲线。
            parent: Qt 父对象；省略时使用 owner。
        """
        super().__init__(owner if parent is None else parent)
        self._owner_ref = weakref.ref(owner)
        self._phase = 0.0
        self._requested = False
        self._anim = QPropertyAnimation(self, b"phase", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(easing)
        self._anim.setLoopCount(-1)

        drivers = getattr(owner, "_hs_loop_drivers", None)
        if drivers is None:
            drivers = []
            owner._hs_loop_drivers = drivers
        drivers.append(self)

        def release_wrapper():
            if self in drivers:
                drivers.remove(self)

        self.destroyed.connect(release_wrapper)
        owner.installEventFilter(self)
        owner.destroyed.connect(self.stop)

    def _get_phase(self):
        return self._phase

    def _set_phase(self, value):
        self._phase = float(value)
        owner = self._owner_ref()
        if owner is not None and isValid(owner):
            owner.update()

    phase = Property(float, _get_phase, _set_phase)

    def value(self):
        """返回当前循环进度。"""
        return self._phase

    def set_duration(self, ms):
        """调整周期；正在运行时从周期起点重启。

        Args:
            ms: 新的周期毫秒数。
        """
        running = self.is_running()
        self._anim.stop()
        self._anim.setDuration(ms)
        if running:
            self._sync()

    def start(self):
        """请求运行；宿主显示后实际启动。"""
        self._requested = True
        self._sync()

    @Slot()
    def stop(self):
        """停止循环并取消运行请求，保留当前进度。"""
        self._requested = False
        self._anim.stop()

    def is_running(self):
        """返回当前是否正在推进进度。"""
        return self._anim.state() == self._anim.State.Running

    def _sync(self):
        owner = self._owner_ref()
        if self._requested and owner is not None and isValid(owner) and owner.isVisible():
            if not self.is_running():
                self._set_phase(0.0)
                self._anim.start()
        else:
            self._anim.stop()

    def eventFilter(self, watched, event):
        """在宿主显示或隐藏时同步循环状态。"""
        if event.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            self._sync()
        return super().eventFilter(watched, event)
