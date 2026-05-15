"""_InputWrapper — Input/Textarea 的背景画布（私有，自绘 bg + border + radius）。"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QWidget
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame

from ...themes import HEROUI_COLORS, RADIUS
from ...utils import hex_to_rgba




# ============================================================
# inputWrapper：带背景/边框/圆角的画布
# ============================================================
class _InputWrapper(QFrame):
    """输入框背景容器 — 用 QPainter 手绘背景 + 边框 + 圆角

    维护 bg_color / border_color / bottom_line_color 三个 Qt Property，
    通过 QPropertyAnimation 插值实现 150ms 颜色过渡（对齐 HeroUI 的
    `transition-background !duration-150` 与 `transition-colors`）。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroInputWrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        # 自绘，不需要 Qt 默认背景
        self.setAutoFillBackground(False)

        self._bg_color = QColor(0, 0, 0, 0)
        self._border_color = QColor(0, 0, 0, 0)
        self._bottom_line_color = QColor(0, 0, 0, 0)  # underlined 变体底部静态线
        self._border_width = 0  # 0 = 不画边框
        self._radius_px = 8
        self._show_bottom_line = False  # underlined 模式下为 True

        # 动画
        self._bg_anim = QPropertyAnimation(self, b"bg_color")
        self._bg_anim.setDuration(150)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._border_anim = QPropertyAnimation(self, b"border_color")
        self._border_anim.setDuration(150)
        self._border_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._bottom_anim = QPropertyAnimation(self, b"bottom_line_color")
        self._bottom_anim.setDuration(150)
        self._bottom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- Qt Properties (动画插值目标) ----
    from PySide6.QtCore import Property as _QtProperty  # 避免和 typing Property 冲突

    def _get_bg(self) -> QColor:
        return self._bg_color

    def _set_bg(self, c: QColor):
        self._bg_color = c
        self.update()

    bg_color = _QtProperty(QColor, _get_bg, _set_bg)

    def _get_border(self) -> QColor:
        return self._border_color

    def _set_border(self, c: QColor):
        self._border_color = c
        self.update()

    border_color = _QtProperty(QColor, _get_border, _set_border)

    def _get_bottom(self) -> QColor:
        return self._bottom_line_color

    def _set_bottom(self, c: QColor):
        self._bottom_line_color = c
        self.update()

    bottom_line_color = _QtProperty(QColor, _get_bottom, _set_bottom)

    # ---- 配置接口 ----
    def set_static(self, *, border_width: int, radius_px: int, show_bottom_line: bool):
        """设置非动画属性"""
        self._border_width = border_width
        self._radius_px = radius_px
        self._show_bottom_line = show_bottom_line
        self.update()

    def set_bg_color(self, c: QColor, animate: bool = True):
        if animate:
            self._bg_anim.stop()
            self._bg_anim.setStartValue(QColor(self._bg_color))
            self._bg_anim.setEndValue(QColor(c))
            self._bg_anim.start()
        else:
            self._bg_color = QColor(c)
            self.update()

    def set_border_color(self, c: QColor, animate: bool = True):
        if animate:
            self._border_anim.stop()
            self._border_anim.setStartValue(QColor(self._border_color))
            self._border_anim.setEndValue(QColor(c))
            self._border_anim.start()
        else:
            self._border_color = QColor(c)
            self.update()

    def set_bottom_line_color(self, c: QColor, animate: bool = True):
        if animate:
            self._bottom_anim.stop()
            self._bottom_anim.setStartValue(QColor(self._bottom_line_color))
            self._bottom_anim.setEndValue(QColor(c))
            self._bottom_anim.start()
        else:
            self._bottom_line_color = QColor(c)
            self.update()

    # ---- 手绘背景 + 边框 ----
    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        bw = self._border_width
        r = self._radius_px

        if self._show_bottom_line:
            # underlined 变体：只画底部 2px 静态线（聚焦时的彩色展开线由 UnderlineBar 覆盖）
            if self._bottom_line_color.alpha() > 0:
                painter.fillRect(0, h - 2, w, 2, self._bottom_line_color)
            painter.end()
            return

        # 圆角矩形背景
        if bw > 0:
            # 有边框：先画边框底，再画内部背景
            inner_offset = bw / 2.0
            # 画边框（stroke）
            if self._border_color.alpha() > 0:
                painter.setPen(QPen(self._border_color, bw))
                painter.setBrush(self._bg_color if self._bg_color.alpha() > 0 else Qt.BrushStyle.NoBrush)
                rect = QRectF(inner_offset, inner_offset, w - bw, h - bw)
                painter.drawRoundedRect(rect, max(0, r - inner_offset), max(0, r - inner_offset))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self._bg_color)
                painter.drawRoundedRect(0, 0, w, h, r, r)
        else:
            # 无边框：只画背景
            painter.setPen(Qt.PenStyle.NoPen)
            if self._bg_color.alpha() > 0:
                painter.setBrush(self._bg_color)
                painter.drawRoundedRect(0, 0, w, h, r, r)
        painter.end()
