"""基于公共循环驱动实现骨架扫光进度。"""

from PySide6.QtCore import Property, QEasingCurve

from .loop import LoopDriver


class SkeletonShimmerAnimation(LoopDriver):
    """使用 InOutCubic 曲线的骨架扫光效果。"""
    def __init__(self, owner, duration=1500, parent=None):
        """初始化扫光循环。

        Args:
            owner: 接收重绘的 QWidget。
            duration: 一个周期的毫秒数。
            parent: Qt 父对象；省略时使用 owner。
        """
        super().__init__(owner, duration, QEasingCurve.Type.InOutCubic, parent)

    progress = Property(float, LoopDriver._get_phase, LoopDriver._set_phase)

    def progress_value(self):
        """返回当前扫光进度。"""
        return self.value()
