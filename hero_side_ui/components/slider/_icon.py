"""Slider 内部 icon widget — `start_content` / `end_content` 传 str 时使用。

为什么要这一层：
    Slider 的 start_content / end_content 既支持任意 QWidget（自定义控件），
    也支持简洁的"传一个图标名"用法（HeroUI 官网典型范例：音量滑块两侧
    speaker icon）。后者按"高层意图 API（铁律 3）"应该零样板：
        Slider(start_content="heroicons--speaker-x-mark-solid", ...)
    而不是让用户自己包一层 Button 或 QLabel + setPixmap。

为什么不直接用 Button(icon_only=True)：
    Button 内部有 hover/press/focus/loading 状态机 + ripple 动画 + 信号槽 —
    渲染一个静态图标用 Button 是杀鸡用牛刀，且 light variant 在不 hover 时
    完全透明，跟 HeroUI 原网站紧贴 track 两端的实心图标视觉不一致。

为什么 QLabel 子类是合规的（铁律 9 例外）：
    铁律 9 禁止"用 QLabel 显示文字"，但允许"非文字用途的 QLabel"。这个类
    setPixmap 渲染 SVG，**永远不 setText**，属于例外清单第一条。同时它是
    slider 包内部实现细节（`_icon.py` 下划线前缀），用户不会裸用。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from ...utils.icon_utils import load_svg_icon


class _SliderIconLabel(QLabel):
    """Slider 内部 icon widget。

    构造时记录 icon name（不立即着色），由 Slider 在主题切换 / 显式调用
    `_render(theme)` 时按当前主题重新加载 SVG，从而做到亮暗自动跟随。

    Args:
        icon_name: 内置图标名（不含 .svg），或完整 SVG 文件路径。
        size: 渲染尺寸（正方形像素）。Slider 默认 16，与 HeroUI 原版尺寸一致。
        parent: Qt 父对象。
    """

    def __init__(
        self,
        icon_name: str,
        size: int = 16,
        parent: Optional[QWidget] = None,
    ):
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
        return self._icon_name

    def set_icon(self, icon_name: str):
        """运行时换 icon（极少用到，但 _api 层 set_start_content(str) 走这里）。"""
        if icon_name == self._icon_name:
            return
        self._icon_name = icon_name
        self._render()

    def _render(self):
        """按当前主题加载并渲染 SVG。

        load_svg_icon 在 color=None 时会读 ThemeProvider 当前主题选对比色，
        所以这里不用关心是亮是暗。Slider 主题切换时调本方法重渲染即可。
        """
        pm: QPixmap = load_svg_icon(self._icon_name, size=self._icon_size, color=None)
        self.setPixmap(pm)

    # 由 Slider 在 ThemeProvider 广播时调用
    def apply_theme(self):
        self._render()
