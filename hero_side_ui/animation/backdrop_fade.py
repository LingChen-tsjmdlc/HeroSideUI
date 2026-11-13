"""提供遮罩淡入淡出的进度控制。"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QWidget


class BackdropFade(QObject):
    """驱动遮罩透明度进度并请求宿主重绘。

    Attributes:
        progress: 0 到 1 的当前透明度进度。
    """

    def __init__(
        self,
        owner: QWidget,
        duration_in: int = 260,
        duration_out: int = 200,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        auto_hide_on_out: bool = True,
        parent: QObject | None = None,
    ):
        """初始化遮罩控制器。

        Args:
            owner: 负责绘制遮罩的 QWidget。
            duration_in: 淡入毫秒数。
            duration_out: 淡出毫秒数。
            easing: 进出场共用的缓动曲线。
            auto_hide_on_out: 淡出完成后是否隐藏宿主。
            parent: Qt 父对象；省略时使用 owner。
        """
        super().__init__(parent or owner)
        self._owner = owner
        self._duration_in = duration_in
        self._duration_out = duration_out
        self._easing = easing
        self._auto_hide = auto_hide_on_out

        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setEasingCurve(self._easing)
        self._anim.finished.connect(self._on_finished)

    def _get_progress(self) -> float:
        """返回当前遮罩进度。"""
        return self._progress

    def _set_progress(self, v: float):
        """设置遮罩进度并请求宿主重绘。"""
        self._progress = v
        self._owner.update()

    progress = Property(float, _get_progress, _set_progress)

    def progress_value(self) -> float:
        """返回当前遮罩进度。"""
        return self._progress

    def settle(self, value: float):
        """停止过渡并直接定位到终态。

        Args:
            value: 目标进度，0 为全透明，1 为完全显示。
        """
        self._anim.stop()
        self._progress = float(value)
        self._owner.update()

    def play_in(self):
        """从当前进度淡入。"""
        self._anim.stop()
        self._anim.setDuration(self._duration_in)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def play_out(self):
        """从当前进度淡出。"""
        self._anim.stop()
        self._anim.setDuration(self._duration_out)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_finished(self):
        """按配置在淡出完成后隐藏遮罩。"""
        if self._auto_hide and self._progress <= 0.01:
            self._owner.hide()
