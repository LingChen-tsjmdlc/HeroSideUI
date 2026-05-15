"""_Backdrop — Popover 弹出时的全屏遮罩层（私有，可选启用）。"""

from PySide6.QtCore import Signal
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from ...animation import BackdropFade




# ============================================================
# Backdrop
# ============================================================
class _Backdrop(QWidget):
    """遮罩层 — 作为 **host window 的子 widget**，只覆盖 host 的客户区；
    不会遮到其他应用、其他屏幕。

    kind:
        transparent — 透明遮罩（只用于拦截/不拦截点击）
        opaque      — 黑色 50% 遮罩
        blur        — 对 host 客户区做静态截屏 + 高斯模糊作为背景，再叠 30% 黑

    淡入淡出由 `BackdropFade` 驱动（paintEvent 里 `setOpacity(progress)`）。

    **static snapshot 说明**：`blur` 模式是在 `show()` 之前截图的，
    之后 host 内容变化不会反映到 backdrop 上。对 Popover 这种打开-关闭短期场景够用。
    """

    clicked = Signal()

    def __init__(self, kind: str = "transparent", host: Optional[QWidget] = None):
        # 关键：parent = host，不是独立顶层窗口
        super().__init__(host)
        self._kind = kind
        self._host = host
        self._blur_pixmap: Optional["QPixmap"] = None

        # 作为 host 的子 widget，不需要 window flags
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # transparent 模式不拦截点击（事件穿透）
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, kind == "transparent"
        )

        # 淡入淡出 —— 复用通用 BackdropFade 动画
        self._fade = BackdropFade(owner=self, duration_in=260, duration_out=200)

    def play_in(self):
        self._fade.play_in()

    def play_out(self):
        self._fade.play_out()

    def prepare_blur_snapshot(self):
        """在 show() 之前调用：抓取 host 客户区做高斯模糊快照。"""
        if self._host is None:
            return
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QGraphicsScene,
            QGraphicsPixmapItem,
            QGraphicsBlurEffect,
        )

        pm = self._host.grab()
        if pm.isNull():
            return

        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pm)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(16)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)

        blurred = QPixmap(pm.size())
        blurred.fill(Qt.GlobalColor.transparent)
        painter = QPainter(blurred)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        scene.render(painter)
        painter.end()

        self._blur_pixmap = blurred

    def paintEvent(self, event):
        if self._kind == "transparent":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # 整体透明度随 BackdropFade.progress 渐变
        painter.setOpacity(self._fade.progress_value())

        if self._kind == "blur" and self._blur_pixmap is not None:
            painter.drawPixmap(self.rect(), self._blur_pixmap)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))  # 30%
        elif self._kind == "opaque":
            painter.fillRect(self.rect(), QColor(0, 0, 0, 128))  # 50%
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 76))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
