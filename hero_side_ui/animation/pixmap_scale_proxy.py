"""使用截图代理缩放顶层窗口的内容。"""

from collections.abc import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class PixmapScaleProxy:
    """在过渡期间隐藏真实子控件并绘制缩放截图。

    父控件的 QPainter 变换不作用于子控件，因此整体缩放需要临时截图代理。
    """

    def __init__(
        self,
        owner: QWidget,
        content_widget_getter: Callable[[], QWidget | None],
        scale_getter: Callable[[], float],
        enable_predicate: Callable[[], bool] | None = None,
    ):
        """初始化截图代理。

        Args:
            owner: 负责截图和代理绘制的宿主。
            content_widget_getter: 返回需要临时隐藏的内容控件。
            scale_getter: 返回当前缩放比例。
            enable_predicate: 可选的启用条件。
        """
        self._owner = owner
        self._get_content = content_widget_getter
        self._get_scale = scale_getter
        self._enable_predicate = enable_predicate
        self._pixmap: QPixmap | None = None


    def is_active(self) -> bool:
        """返回当前是否持有代理截图。"""
        return self._pixmap is not None

    def pixmap(self) -> QPixmap | None:
        """获取当前代理截图。

        Returns:
            当前 QPixmap；未启用代理时为 None。
        """
        return self._pixmap


    def begin(self):
        """条件满足且宿主尺寸有效时截图并隐藏真实内容。"""
        if self._enable_predicate is not None and not self._enable_predicate():
            return

        w, h = self._owner.width(), self._owner.height()
        if w <= 0 or h <= 0:
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        # render 前确保 _pixmap=None，让 owner.paintEvent 走常规绘制
        self._pixmap = None
        effect = self._owner.graphicsEffect()
        effect_was_enabled = effect is not None and effect.isEnabled()
        if effect_was_enabled:
            effect.setEnabled(False)
        self._owner.render(pm)
        if effect_was_enabled:
            effect.setEnabled(True)

        self._pixmap = pm
        content = self._get_content()
        if content is not None:
            content.hide()
        self._owner.update()

    def end(self):
        """丢弃截图并恢复真实内容。"""
        self._pixmap = None
        content = self._get_content()
        if content is not None:
            content.show()
        self._owner.update()


    def draw(self, painter: QPainter, owner_rect: QRect, anchor: tuple[float, float]):
        """按当前缩放比例和锚点绘制代理。

        Args:
            painter: 宿主已开始绘制的 QPainter。
            owner_rect: 保留的宿主区域参数，当前绘制不使用。
            anchor: 缩放中心在宿主坐标中的横纵坐标。
        """
        if self._pixmap is None:
            return
        s = self._get_scale()
        cx, cy = anchor
        painter.save()
        painter.translate(cx, cy)
        painter.scale(s, s)
        painter.translate(-cx, -cy)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.restore()
