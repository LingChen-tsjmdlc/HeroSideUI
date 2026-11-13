"""输入类组件的外框画布，自绘背景、边框与圆角。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QWidget

from ...animation import tween_property


# ============================================================
# inputWrapper：带背景/边框/圆角的画布
# ============================================================
class InputWrapper(QFrame):
    """输入框背景容器：QPainter 自绘背景/边框/圆角，三颜色 Property 走
    QPropertyAnimation 做 150ms 过渡。
    """

    def __init__(self, parent: QWidget | None = None):
        """创建自绘背景画布。

        Args:
            parent: Qt 父对象。

        Note:
            关闭 WA_StyledBackground 与 AutoFillBackground，
            背景完全由 paintEvent 负责；三个颜色 Property 走 150ms 补间。
        """
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
        self._bg_anim = None

        self._border_anim = None

        self._bottom_anim = None

    # ---- Qt Properties (动画插值目标) ----
    from PySide6.QtCore import Property as _QtProperty  # 避免和 typing Property 冲突

    def _get_bg(self) -> QColor:
        """Property getter：当前背景色。

        Returns:
            背景 QColor（可含 alpha）。
        """
        return self._bg_color

    def _set_bg(self, c: QColor):
        """Property setter：写入背景色并重绘。

        Args:
            c: 新颜色，由补间每帧调用。
        """
        self._bg_color = c
        self.update()

    bg_color = _QtProperty(QColor, _get_bg, _set_bg)

    def _get_border(self) -> QColor:
        """Property getter：当前边框色。

        Returns:
            边框 QColor。
        """
        return self._border_color

    def _set_border(self, c: QColor):
        """Property setter：写入边框色并重绘。

        Args:
            c: 新颜色，由补间每帧调用。
        """
        self._border_color = c
        self.update()

    border_color = _QtProperty(QColor, _get_border, _set_border)

    def _get_bottom(self) -> QColor:
        """Property getter：underlined 底部静态线颜色。

        Returns:
            底线的 QColor。
        """
        return self._bottom_line_color

    def _set_bottom(self, c: QColor):
        """Property setter：写入底线颜色并重绘。

        Args:
            c: 新颜色，由补间每帧调用。
        """
        self._bottom_line_color = c
        self.update()

    bottom_line_color = _QtProperty(QColor, _get_bottom, _set_bottom)

    # ---- 配置接口 ----
    def set_static(self, *, border_width: int, radius_px: int, show_bottom_line: bool):
        """设置非动画属性。

        Args:
            border_width: 边框宽度；0 表示不画边框。
            radius_px: 圆角半径（像素）。
            show_bottom_line: underlined 变体是否画底部静态线。
        """
        self._border_width = border_width
        self._radius_px = radius_px
        self._show_bottom_line = show_bottom_line
        self.update()

    def set_bg_color(self, c: QColor, animate: bool = True):
        """设置背景色，按需走 150ms 补间。

        Args:
            c: 目标颜色。
            animate: False 时直达终态。
        """
        tween_property(self, "_bg_anim", b"bg_color", QColor(c), duration=150, animated=animate)

    def set_border_color(self, c: QColor, animate: bool = True):
        """设置边框色，按需走 150ms 补间。

        Args:
            c: 目标颜色。
            animate: False 时直达终态。
        """
        tween_property(
            self, "_border_anim", b"border_color", QColor(c), duration=150, animated=animate
        )

    def set_bottom_line_color(self, c: QColor, animate: bool = True):
        """设置 underlined 底部静态线颜色，按需走 150ms 补间。

        Args:
            c: 目标颜色。
            animate: False 时直达终态。
        """
        tween_property(
            self, "_bottom_anim", b"bottom_line_color", QColor(c), duration=150, animated=animate
        )

    # ---- 手绘背景 + 边框 ----
    def paintEvent(self, event):
        """自绘圆角背景与边框。

        Args:
            event: Qt 绘制事件。

        Note:
            underlined 变体只画底部 2px 静态线并提前返回；
            有边框时把矩形内缩半笔宽避免线条被裁，且背景只在
            alpha > 0 时填充。
        """
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
                painter.setBrush(
                    self._bg_color if self._bg_color.alpha() > 0 else Qt.BrushStyle.NoBrush
                )
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
