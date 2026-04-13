"""
HeroUI 风格折叠/展开动画 (Collapse Animation)

仿照 HeroUI 的 framer-motion 实现:
  展开: height 0→target 同时 opacity 0→1
  收起: height current→0 同时 opacity 1→0

关键设计:
  - 所有动画独立启停，支持随时中断并从当前状态衔接
  - wrapper 的 maximumHeight 做裁剪
  - 动画前锁定内容区宽度，防止文字重排抖动
  - 展开前预计算目标高度并缓存

用法:
    anim = CollapseAnimation(target_widget, clip_wrapper)
    anim.expand()    # 展开
    anim.collapse()  # 收起
"""

from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve,
    Signal,
)
from typing import Optional


class CollapseAnimation(QObject):
    """折叠/展开动画管理器

    参数:
        content: 实际内容控件（opacity effect 作用于此）
        wrapper: 外层裁剪容器（maximumHeight 动画作用于此）
        expanded: 初始是否展开
    """

    finished = Signal(bool)  # True=展开完成, False=收起完成

    def __init__(
        self,
        content: QWidget,
        wrapper: QWidget,
        expanded: bool = False,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._content = content
        self._wrapper = wrapper
        self._expanded = expanded
        self._cached_height = 0  # 缓存内容高度

        # 透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(content)
        content.setGraphicsEffect(self._opacity_effect)

        # 高度动画
        self._height_anim = QPropertyAnimation(wrapper, b"maximumHeight")
        self._height_anim.finished.connect(self._on_height_finished)

        # 透明度动画
        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")

        # 初始状态
        if expanded:
            self._opacity_effect.setOpacity(1.0)
            wrapper.setMaximumHeight(16777215)
        else:
            self._opacity_effect.setOpacity(0.0)
            wrapper.setMaximumHeight(0)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def is_animating(self) -> bool:
        return (
            self._height_anim.state() == QPropertyAnimation.State.Running
            or self._opacity_anim.state() == QPropertyAnimation.State.Running
        )

    def expand(self):
        """展开"""
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

        # 高度动画
        self._height_anim.setStartValue(old_max)
        self._height_anim.setEndValue(target_height)
        self._height_anim.setDuration(450)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_anim.start()

        # 透明度动画
        self._opacity_anim.setStartValue(self._opacity_effect.opacity())
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setDuration(350)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._opacity_anim.start()

    def collapse(self):
        """收起"""
        if not self._expanded and not self.is_animating:
            return

        self._height_anim.stop()
        self._opacity_anim.stop()
        self._expanded = False

        # 锁定内容区宽度
        self._content.setFixedWidth(self._wrapper.width())

        # 高度动画
        current_height = min(self._wrapper.height(), self._wrapper.maximumHeight())
        self._height_anim.setStartValue(current_height)
        self._height_anim.setEndValue(0)
        self._height_anim.setDuration(400)
        self._height_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._height_anim.start()

        # 透明度动画
        self._opacity_anim.setStartValue(self._opacity_effect.opacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setDuration(250)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._opacity_anim.start()

    def toggle(self):
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def _on_height_finished(self):
        """高度动画完成后做最终清理"""
        # 解锁宽度，让内容区恢复自适应
        self._content.setMinimumWidth(0)
        self._content.setMaximumWidth(16777215)

        if self._expanded:
            self._wrapper.setMaximumHeight(16777215)
            self._opacity_effect.setOpacity(1.0)
        else:
            self._wrapper.setMaximumHeight(0)
            self._opacity_effect.setOpacity(0.0)
        self.finished.emit(self._expanded)
