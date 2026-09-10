"""Drawer 遮罩层（私有）— 复用 Popover 的 _Backdrop，补一个跳终态入口。

绘制 / 模糊 / 淡入淡出全部走 popover._backdrop._Backdrop：

    transparent — 不建遮罩（Drawer 自身仍接收点击，点面板外照样关）
    opaque      — 黑色 50%
    blur        — host 客户区静态快照 + 高斯模糊，再叠黑色 30%

与 Drawer 同为 host 的子 widget，由 Drawer 用 `stackUnder` 压在自己下面，
于是层级是：host 内容 < 遮罩 < Drawer < 面板。
"""

from ..popover._backdrop import _Backdrop


class _DrawerBackdrop(_Backdrop):
    """Drawer 专用遮罩 —— 只比 _Backdrop 多一个 settle()。"""

    def settle(self, value: float):
        """把淡入淡出进度直接推到 value（0.0 / 1.0），跳过动画。

        disable_animation 时用：_Backdrop 的淡入淡出时长在构造时写死，
        外部改不了，只能直接写 BackdropFade 的 progress 属性。
        """
        self._fade.setProperty("progress", float(value))
        self.update()
