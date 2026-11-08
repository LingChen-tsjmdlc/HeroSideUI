"""Accordion 组件的展开/收起箭头 — 私有子组件。"""

from PySide6.QtCore import Property
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from ...utils import load_svg_icon


class _IndicatorWidget(QWidget):
    """展开/收起箭头指示器 — 使用 SVG 图标渲染

    默认显示向右的 chevron，展开时顺时针旋转 90° 变成向下。
    """

    def __init__(self, icon_name: str = "heroicons--chevron-right-solid", parent=None):
        """初始化指示器并按默认色渲染图标。

        Args:
            icon_name: SVG 图标名，默认向右的 chevron。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._rotation = 0.0
        self._color = QColor("#a1a1aa")
        self._icon_name = icon_name
        self._pixmap = None
        self._update_pixmap()

    # Qt Property: rotation（供 QPropertyAnimation 驱动）
    def _get_rotation(self) -> float:
        """Property getter：返回当前旋转角度。

        Returns:
            rotation 的度数，0 为原始方向。
        """
        return self._rotation

    def _set_rotation(self, value: float):
        """Property setter：写入旋转角度并触发重绘。

        Args:
            value: 新角度（度），由 QPropertyAnimation 每帧调用。
        """
        self._rotation = value
        self.update()

    def set_rotation(self, value: float):
        """公共接口：直接设置旋转角度。

        Args:
            value: 角度（度）；展开态由调用方传 90。
        """
        self._rotation = value
        self.update()

    rotation = Property(float, _get_rotation, _set_rotation)

    def set_color(self, color: QColor):
        """设置图标颜色并按新色重渲染。

        Args:
            color: 新的 QColor，随主题切换时由宿主调用。
        """
        self._color = color
        self._update_pixmap()
        self.update()

    def set_icon(self, icon_name: str):
        """替换 SVG 图标并重渲染。

        Args:
            icon_name: 新图标名。
        """
        self._icon_name = icon_name
        self._update_pixmap()
        self.update()

    def _update_pixmap(self):
        """按当前图标名与颜色重新渲染 SVG 像素图。

        Note:
            尺寸取 max(宽, 高, 18)：构造期宽高还是默认垃圾值，
            18 保证首帧也有可用的图标尺寸。
        """
        size = max(self.width(), self.height(), 18)
        self._pixmap = load_svg_icon(self._icon_name, size=size, color=self._color)

    def resizeEvent(self, event):
        """尺寸变化后按新尺寸重渲染图标。

        Args:
            event: Qt 尺寸变化事件。
        """
        super().resizeEvent(event)
        self._update_pixmap()

    def paintEvent(self, event):
        """以中心为轴旋转绘制图标。

        Args:
            event: Qt 绘制事件。

        Note:
            translate → rotate → translate 回原点，保证围绕几何中心旋转；
            像素图未就绪时直接返回不绘制。
        """
        if self._pixmap is None or self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # 居中旋转
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.translate(-cx, -cy)

        # 居中绘制 pixmap
        px = (w - self._pixmap.width()) / 2.0
        py = (h - self._pixmap.height()) / 2.0
        painter.drawPixmap(int(px), int(py), self._pixmap)

        painter.end()
