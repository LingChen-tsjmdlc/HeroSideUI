"""提供内容高度与透明度联动的折叠效果。"""

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class CollapseAnimation(QObject):
    """协调内容高度与透明度的展开和收起。

    Attributes:
        finished: 过渡结束时发出目标展开状态的信号。
    """

    finished = Signal(bool)

    def __init__(
        self,
        content: QWidget,
        wrapper: QWidget,
        expanded: bool = False,
        parent: QObject | None = None,
    ):
        """初始化折叠效果。

        Args:
            content: 提供自然高度的内容控件。
            wrapper: 接受高度限制的裁剪容器。
            expanded: 初始是否展开。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._content = content
        self._wrapper = wrapper
        self._expanded = expanded
        self._cached_height = 0


        self._opacity_effect = QGraphicsOpacityEffect(content)
        content.setGraphicsEffect(self._opacity_effect)


        self._height_anim = QPropertyAnimation(wrapper, b"maximumHeight")
        self._height_anim.finished.connect(self._on_height_finished)


        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")


        if expanded:
            self._opacity_effect.setOpacity(1.0)
            wrapper.setMaximumHeight(16777215)
        else:
            self._opacity_effect.setOpacity(0.0)
            wrapper.setMaximumHeight(0)

    @property
    def is_expanded(self) -> bool:
        """返回当前目标是否为展开状态。"""
        return self._expanded

    @property
    def is_animating(self) -> bool:
        """返回高度或透明度过渡是否仍在运行。"""
        return (
            self._height_anim.state() == QPropertyAnimation.State.Running
            or self._opacity_anim.state() == QPropertyAnimation.State.Running
        )

    def expand(self):
        """从当前状态展开内容。"""
        if self._expanded and not self.is_animating:
            return

        self._height_anim.stop()
        self._opacity_anim.stop()
        self._expanded = True

        # 锁定内容区宽度，防止动画期间文字重排抖动
        self._content.setFixedWidth(self._wrapper.width())

        # 临时取消高度限制来测量真实高度
        old_max = self._wrapper.maximumHeight()
        self._wrapper.setMaximumHeight(16777215)
        self._content.adjustSize()
        target_height = self._content.sizeHint().height()
        if target_height <= 0:
            target_height = 100
        self._cached_height = target_height
        self._wrapper.setMaximumHeight(old_max)


        self._height_anim.setStartValue(old_max)
        self._height_anim.setEndValue(target_height)
        self._height_anim.setDuration(450)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_anim.start()


        self._opacity_anim.setStartValue(self._opacity_effect.opacity())
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setDuration(350)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._opacity_anim.start()

    def collapse(self):
        """从当前状态收起内容。"""
        if not self._expanded and not self.is_animating:
            return

        self._height_anim.stop()
        self._opacity_anim.stop()
        self._expanded = False


        self._content.setFixedWidth(self._wrapper.width())


        current_height = min(self._wrapper.height(), self._wrapper.maximumHeight())
        self._height_anim.setStartValue(current_height)
        self._height_anim.setEndValue(0)
        self._height_anim.setDuration(400)
        self._height_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._height_anim.start()


        self._opacity_anim.setStartValue(self._opacity_effect.opacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setDuration(250)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._opacity_anim.start()

    def toggle(self):
        """切换目标展开状态。"""
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def _on_height_finished(self):
        """恢复自适应尺寸并通知完成。"""

        self._content.setMinimumWidth(0)
        self._content.setMaximumWidth(16777215)

        if self._expanded:
            self._wrapper.setMaximumHeight(16777215)
            self._opacity_effect.setOpacity(1.0)
        else:
            self._wrapper.setMaximumHeight(0)
            self._opacity_effect.setOpacity(0.0)
        self.finished.emit(self._expanded)
