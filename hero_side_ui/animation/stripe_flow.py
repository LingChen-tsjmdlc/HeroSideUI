"""将公共循环进度换算为条纹偏移。"""

from PySide6.QtCore import Property, QEasingCurve

from .loop import LoopDriver


class StripeFlowAnimation(LoopDriver):
    """按图案周期换算斜纹流动偏移。"""
    def __init__(self, owner, period=32.0, duration=1000, parent=None):
        """初始化条纹循环。

        Args:
            owner: 接收重绘的 QWidget。
            period: 图案循环对应的像素偏移。
            duration: 一个周期的毫秒数。
            parent: Qt 父对象；省略时使用 owner。
        """
        self._period = period
        super().__init__(owner, duration, QEasingCurve.Type.Linear, parent)

    def _get_offset(self):
        return self.value() * self._period

    def _set_offset(self, value):
        self._set_phase(value / self._period if self._period else 0.0)

    offset = Property(float, _get_offset, _set_offset)

    def offset_value(self):
        """返回当前条纹像素偏移。"""
        return self.offset

    def period(self):
        """返回图案周期对应的像素长度。"""
        return self._period
