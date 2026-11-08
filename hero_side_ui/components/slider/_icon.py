"""_SliderIconLabel：start/end_content 传 str 时的轻量图标 QLabel（永不 setText，
铁律 9 例外）。不用 Button——静态图标不需要状态机。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from ...utils.icon_utils import load_svg_icon


class _SliderIconLabel(QLabel):
    """Slider 内部静态图标 QLabel，按当前主题着色 SVG。

    Note:
        构造时只记录 icon name，由 Slider 在主题切换时重新渲染 SVG，
        以做到亮暗自动跟随。
    """

    def __init__(
        self,
        icon_name: str,
        size: int = 16,
        parent: QWidget | None = None,
    ):
        """记录图标名与尺寸并做首次渲染。

        Args:
            icon_name: 内置图标名（不含 .svg），或完整 SVG 文件路径。
            size: 渲染尺寸（正方形像素），Slider 默认 16。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = size
        # icon 是装饰，不应抢鼠标事件（用户点击应当落到 track 上）
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 首次渲染：color=None 让 load_svg_icon 自动跟主题
        self._render()

    @property
    def icon_name(self) -> str:
        """返回当前图标名。"""
        return self._icon_name

    def set_icon(self, icon_name: str):
        """运行时换 icon（极少用到，但 _api 层 set_start_content(str) 走这里）。"""
        if icon_name == self._icon_name:
            return
        self._icon_name = icon_name
        self._render()

    def _render(self):
        """按当前主题渲染 SVG；color=None 时由 load_svg_icon 自动选对比色。"""
        pm: QPixmap = load_svg_icon(self._icon_name, size=self._icon_size, color=None)
        self.setPixmap(pm)

    # 由 Slider 在 ThemeProvider 广播时调用
    def apply_theme(self):
        """主题广播时重新渲染图标以跟随新主题。"""
        self._render()
