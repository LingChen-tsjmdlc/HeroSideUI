"""
HeroUI 风格 Label 浮动动画 (Floating Label Animation)

对应 HeroUI 原版 Input 的 label 过渡：
    transition-[transform,color,left,opacity,translate,scale]
    duration-200
    ease-out

两种状态:
    resting (未聚焦 + 空值): label 位于输入框中央，字号较大
    floating (聚焦 或 有值): label 上移至顶部，字号缩至 85%，颜色变深

关键设计:
    - QSS 无法同时动画化 translate/scale/color，所以用 QPropertyAnimation
      驱动一个浮点参数 `progress` (0.0→1.0)，在回调里手动插值计算
      label 的 geometry / fontSize / color
    - 让 label 用 QLabel + 自适应位置，不占布局空间（通过 setGeometry 手动摆放）
"""

from PySide6.QtCore import (
    QObject,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    Signal,
)
from typing import Optional, Callable


class LabelFloatAnimation(QObject):
    """Label 浮动过渡控制器

    参数:
        on_progress: 每次 progress 更新时的回调，接收 float ∈ [0,1]
                     调用方根据 progress 计算并应用 label 的位置/字号/颜色
        duration: 动画时长（ms），默认 200 对齐 HeroUI
    """

    finished = Signal(bool)  # True=浮起完成, False=回落完成

    def __init__(
        self,
        on_progress: Callable[[float], None],
        duration: int = 250,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._on_progress = on_progress
        self._progress = 0.0
        self._floated = False

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(lambda: self.finished.emit(self._floated))

    # Qt Property (供 QPropertyAnimation 驱动)
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float):
        self._progress = value
        self._on_progress(value)

    progress = Property(float, _get_progress, _set_progress)

    @property
    def is_floated(self) -> bool:
        return self._floated

    @property
    def is_animating(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running

    def float_up(self):
        """浮起 (resting → floating)"""
        if self._floated and not self.is_animating:
            return
        self._floated = True
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def fall_down(self):
        """回落 (floating → resting)"""
        if not self._floated and not self.is_animating:
            return
        self._floated = False
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_state(self, floated: bool, animate: bool = True):
        """直接设置状态

        Args:
            floated: 目标状态
            animate: True=带动画过渡，False=瞬间跳到目标
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
