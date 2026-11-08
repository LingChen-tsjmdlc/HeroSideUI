"""将公共循环进度换算为未定进度条位置或旋转角度。"""

from PySide6.QtCore import Property, QEasingCurve

from .loop import LoopDriver


class IndeterminateBarAnimation(LoopDriver):
    """驱动未定进度条的滑块位置。

    Attributes:
        position: 从负滑块宽度比例到 1 的位置。
    """

    def __init__(
        self,
        owner,
        duration=1500,
        bar_ratio=0.4,
        easing=QEasingCurve.Type.InOutSine,
        parent=None,
    ):
        """初始化滑块循环。

        Args:
            owner: 接收重绘的 QWidget。
            duration: 一个周期的毫秒数。
            bar_ratio: 滑块宽度占轨道总长的比例。
            easing: 进度缓动曲线。
            parent: Qt 父对象；省略时使用 owner。
        """
        self._bar_ratio = bar_ratio
        super().__init__(owner, duration, easing, parent)

    def _get_pos(self):
        """由循环进度换算当前滑块位置。"""
        return -self._bar_ratio + self.value() * (1.0 + self._bar_ratio)

    def _set_pos(self, value):
        """由滑块位置反推循环进度。"""
        self._set_phase((value + self._bar_ratio) / (1.0 + self._bar_ratio))

    position = Property(float, _get_pos, _set_pos)

    def bar_ratio(self):
        """返回滑块宽度比例。"""
        return self._bar_ratio


class SpinAnimation(LoopDriver):
    """将循环进度换算为旋转角度。

    Attributes:
        angle: 当前角度，单位为度。
    """

    def __init__(self, owner, duration=900, easing=QEasingCurve.Type.Linear, parent=None):
        """初始化旋转循环。

        Args:
            owner: 接收重绘的 QWidget。
            duration: 一个周期的毫秒数。
            easing: 进度缓动曲线。
            parent: Qt 父对象；省略时使用 owner。
        """
        super().__init__(owner, duration, easing, parent)

    def _get_angle(self):
        """由循环进度换算当前旋转角度。"""
        return self.value() * 360.0

    def _set_angle(self, value):
        """由旋转角度反推循环进度。"""
        self._set_phase(value / 360.0)

    angle = Property(float, _get_angle, _set_angle)

    def angle_value(self):
        """返回当前旋转角度，单位为度。"""
        return self.angle
