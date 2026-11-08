"""Drawer 遮罩：复用 Popover _Backdrop，仅补 settle() 跳终态入口。"""

from ..popover._backdrop import _Backdrop


class _DrawerBackdrop(_Backdrop):
    """Drawer 专用遮罩 —— 只比 _Backdrop 多一个 settle()。"""

    def settle(self, value: float):
        """把淡入淡出进度直接推到 0 / 1 跳过动画。

        Args:
            value: 目标进度；0 为全透明、1 为完全遮罩。

        Note:
            淡入时长在构造时写死无法修改，故用直接写 property 的方式跳终态。
        """
        self._fade.setProperty("progress", float(value))
        self.update()
