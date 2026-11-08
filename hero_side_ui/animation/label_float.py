"""提供输入标签的浮起与回落进度。"""

from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    Signal,
)


class LabelFloatAnimation(QObject):
    """驱动标签状态过渡，由回调负责实际布局与绘制。"""

    finished = Signal(bool)

    def __init__(
        self,
        on_progress: Callable[[float], None],
        duration: int = 250,
        parent: QObject | None = None,
    ):
        """初始化浮动标签控制器。

        Args:
            on_progress: 进度变化时执行的布局或绘制回调。
            duration: 过渡毫秒数。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._on_progress = on_progress
        self._progress = 0.0
        self._floated = False

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(lambda: self.finished.emit(self._floated))

    def _get_progress(self) -> float:
        """返回当前过渡进度。"""
        return self._progress

    def _set_progress(self, value: float):
        """设置过渡进度并通知回调。"""
        self._progress = value
        self._on_progress(value)

    progress = Property(float, _get_progress, _set_progress)

    @property
    def is_floated(self) -> bool:
        """返回当前目标是否为浮起状态。"""
        return self._floated

    @property
    def is_animating(self) -> bool:
        """返回标签过渡是否正在运行。"""
        return self._anim.state() == QPropertyAnimation.State.Running

    def float_up(self):
        """将标签过渡到浮起状态。"""
        if self._floated and not self.is_animating:
            return
        self._floated = True
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def fall_down(self):
        """将标签过渡到回落状态。"""
        if not self._floated and not self.is_animating:
            return
        self._floated = False
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_state(self, floated: bool, animate: bool = True):
        """设置标签的目标状态。

        Args:
            floated: 是否浮起。
            animate: 是否播放过渡。
        """
        if animate:
            if floated:
                self.float_up()
            else:
                self.fall_down()
        else:
            self._anim.stop()
            self._floated = floated
            self._progress = 1.0 if floated else 0.0
            self._on_progress(self._progress)
