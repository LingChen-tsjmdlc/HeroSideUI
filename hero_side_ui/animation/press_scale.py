"""
HeroUI 风格按压缩放动画 (Press Scale)

仿照 HeroUI 的 data-[pressed=true]:scale-[0.97] 效果:
  - 鼠标按下: 缩小到 97%，80ms，OutCubic
  - 鼠标松开: 恢复到 100%，150ms，OutCubic

实现方式:
  自定义 QGraphicsEffect，在 draw() 中对 source pixmap 做居中缩放绘制。
  通过 QPropertyAnimation 平滑驱动缩放值。

用法:
    scaler = PressScaleEffect(target_widget)
    scaler.press()    # mousePressEvent 中调用
    scaler.release()  # mouseReleaseEvent 中调用
"""

from PySide6.QtWidgets import QWidget, QGraphicsEffect
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, QRectF, QPointF,
    Property,
)
from PySide6.QtGui import QPainter
from typing import Optional


class _ScaleEffect(QGraphicsEffect):
    """自定义 QGraphicsEffect: 居中缩放绘制

    通过 setScale() 驱动缩放值，在 draw() 中:
    1. 获取控件截图 (sourcePixmap)
    2. 计算缩放后的居中矩形
    3. 用 SmoothPixmapTransform 绘制缩放后的截图
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._scale = 1.0

    def scale(self) -> float:
        return self._scale

    def setScale(self, value: float):
        self._scale = value
        self.update()  # 触发重绘

    def draw(self, painter: QPainter):
        if self._scale >= 0.999:
            # 无缩放时直接绘制，零开销
            self.drawSource(painter)
            return

        # 获取源控件的截图
        pixmap = self.sourcePixmap()
        if pixmap.isNull():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = pixmap.width()
        h = pixmap.height()
        s = self._scale

        # 缩放后的尺寸和居中偏移
        sw = w * s
        sh = h * s
        dx = (w - sw) / 2.0
        dy = (h - sh) / 2.0

        painter.drawPixmap(QRectF(dx, dy, sw, sh), pixmap, QRectF(0, 0, w, h))
        painter.restore()


class PressScaleEffect(QObject):
    """按压缩放效果管理器

    将 _ScaleEffect 安装到目标控件上，通过 QPropertyAnimation 驱动缩放动画。

    参数:
        target: 目标控件
        scale_factor: 按下时的缩放比例，默认 0.97 (与 HeroUI 一致)
        press_duration: 按下动画时长(ms)，默认 80
        release_duration: 松开动画时长(ms)，默认 150
    """

    def __init__(self, target: QWidget,
                 scale_factor: float = 0.97,
                 press_duration: int = 80,
                 release_duration: int = 150,
                 parent: Optional[QObject] = None):
        super().__init__(parent or target)
        self._target = target
        self._scale_factor = scale_factor
        self._press_duration = press_duration
        self._release_duration = release_duration

        # 安装自定义图形效果
        self._effect = _ScaleEffect(target)
        target.setGraphicsEffect(self._effect)

        # 动画: 驱动 _effect 的 scale 值
        self._anim = QPropertyAnimation(self, b"scale_value")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- Qt Property: scale_value ----
    def _get_scale(self) -> float:
        return self._effect.scale()

    def _set_scale(self, value: float):
        self._effect.setScale(value)

    scale_value = Property(float, _get_scale, _set_scale)

    # ---- 公开接口 ----

    def press(self):
        """鼠标按下 — 缩小到 scale_factor"""
        self._anim.stop()
        self._anim.setStartValue(self._effect.scale())
        self._anim.setEndValue(self._scale_factor)
        self._anim.setDuration(self._press_duration)
        self._anim.start()

    def release(self):
        """鼠标松开 — 恢复到 1.0"""
        self._anim.stop()
        self._anim.setStartValue(self._effect.scale())
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self._release_duration)
        self._anim.start()
