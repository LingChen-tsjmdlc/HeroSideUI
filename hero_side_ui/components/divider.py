"""
HeroSideUI Divider Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/divider.ts

结构:
    Divider (QFrame)
        一条纯色分割线，支持水平/垂直方向。
        当 orientation="horizontal" 且传入 text 时，会在分割线中间显示文字，
        左右各一段短线 —— 用 paintEvent 自绘。

特性对齐 HeroUI:
    - 2 种方向: horizontal (默认) / vertical
    - 亮暗双主题 (light / dark)
    - 可自定义颜色 (默认跟随主题的 divider 色)
    - shrink-0: 不被 flex 压缩
    - border-none: 无边框（由背景色决定视觉）
    - 可选中间文字（只水平方向生效，如 "OR"、"或"）
"""

from PySide6.QtWidgets import QFrame, QSizePolicy
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from typing import Optional

from ..themes import HEROUI_COLORS, FONT_FAMILY
from ..themes.sizes import DIVIDER_SIZES


class Divider(QFrame):
    """HeroUI 风格的分割线组件

    特性：
    - 保持 PySide 原生 API (继承 QFrame)
    - 支持方向 (horizontal, vertical)
    - 支持主题 (light, dark)
    - 可选自定义颜色 (十六进制或 rgba 字符串)
    - 可选中间文字 text（仅 horizontal 生效），text_size 控制字号

    用法:
        # 水平分割线
        divider = Divider(orientation="horizontal", theme="light")

        # 垂直分割线
        divider = Divider(orientation="vertical", theme="dark")

        # 自定义颜色
        divider = Divider(color="#ff0000")

        # 带中间文字的水平分割线（常用于 "OR continue with ..."）
        divider = Divider(text="OR", text_size=12)
    """

    def __init__(
        self,
        orientation: str = "horizontal",
        theme: str = "light",
        color: Optional[str] = None,
        text: Optional[str] = None,
        text_size: int = 12,
        parent=None,
    ):
        super().__init__(parent)
        self._orientation = orientation
        self._theme = theme
        self._custom_color = color
        self._text = text or ""
        self._text_size = int(text_size)

        self.setObjectName("heroDivider")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)

        self._apply_styles()

    # ============================================================
    # 内部：解析颜色
    # ============================================================

    def _line_color(self) -> str:
        """分割线颜色: 自定义 > 主题默认"""
        if self._custom_color:
            return self._custom_color
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        # 亮色: default-200, 暗色: default-700（对齐 HeroUI bg-divider token）
        return dc[700] if is_dark else dc[200]

    def _text_color(self) -> str:
        """文字颜色: 跟随主题（亮色偏灰 500，暗色偏灰 400）"""
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        return dc[400] if is_dark else dc[500]

    def _has_text_mode(self) -> bool:
        """是否启用"带文字"模式：只在水平方向且 text 非空时生效"""
        return bool(self._text) and self._orientation != "vertical"

    # ============================================================
    # 样式系统
    # ============================================================

    def _apply_styles(self):
        """根据方向 + 是否带文字，选择 QSS 背景色模式 或 paintEvent 自绘模式"""
        if self._orientation == "vertical":
            # 垂直分割线：固定宽度，垂直 Expanding，QSS 背景
            thickness = DIVIDER_SIZES["vertical"]["thickness"]
            self.setFixedWidth(thickness)
            self.setMaximumHeight(16777215)  # 清理可能的 setFixedHeight 残留
            self.setMinimumHeight(0)
            self.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
            self.setStyleSheet(
                f"#heroDivider {{ background-color: {self._line_color()}; border: none; }}"
            )
        elif self._has_text_mode():
            # 水平 + 带文字：paintEvent 自绘；高度 = 文字行高 + 上下留白
            # QSS 必须清空，否则 setStyleSheet 的实心背景会盖在 paintEvent 上面
            fm_height = QFontMetrics(self._build_font()).height()
            h = max(fm_height + 8, 18)
            self.setFixedHeight(h)
            self.setMaximumWidth(16777215)
            self.setMinimumWidth(0)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self.setStyleSheet("")  # 清空 QSS，交给 paintEvent
            self.update()
        else:
            # 水平 + 无文字：1px 实线，QSS 背景
            thickness = DIVIDER_SIZES["horizontal"]["thickness"]
            self.setFixedHeight(thickness)
            self.setMaximumWidth(16777215)
            self.setMinimumWidth(0)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self.setStyleSheet(
                f"#heroDivider {{ background-color: {self._line_color()}; border: none; }}"
            )

    def _build_font(self) -> QFont:
        f = QFont(FONT_FAMILY)
        f.setPixelSize(self._text_size)
        return f

    # ============================================================
    # 自绘 (仅水平 + 带文字时)
    # ============================================================

    def paintEvent(self, event):
        if not self._has_text_mode():
            # 非文字模式交给 QFrame 默认绘制（QSS 背景走 styled background）
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        line_color = QColor(self._line_color())
        text_color = QColor(self._text_color())
        font = self._build_font()
        painter.setFont(font)

        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._text)
        text_h = fm.height()
        gap = 8  # 文字与左右线条之间的间距
        baseline_y = h / 2  # 线条和文字中心

        # 文字矩形（水平/垂直居中）
        text_x = (w - text_w) / 2
        text_rect = QRectF(text_x, 0, text_w, h)

        # 左侧线条: 从 0 到 (text_x - gap)
        # 右侧线条: 从 (text_x + text_w + gap) 到 w
        pen = QPen(line_color)
        pen.setWidthF(1.0)
        painter.setPen(pen)

        left_end = text_x - gap
        right_start = text_x + text_w + gap
        if left_end > 0:
            painter.drawLine(0, int(baseline_y), int(left_end), int(baseline_y))
        if right_start < w:
            painter.drawLine(int(right_start), int(baseline_y), w, int(baseline_y))

        # 文字
        painter.setPen(QPen(text_color))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._text)

        painter.end()

    # ============================================================
    # 公共 API
    # ============================================================

    def set_orientation(self, orientation: str):
        """设置方向 ("horizontal" / "vertical")"""
        self._orientation = orientation
        self._apply_styles()

    def set_theme(self, theme: str):
        """设置主题 ("light" / "dark")"""
        self._theme = theme
        self._apply_styles()

    def set_color(self, color: Optional[str]):
        """设置自定义颜色 (十六进制字符串或 None 恢复默认)"""
        self._custom_color = color
        self._apply_styles()

    def set_text(self, text: Optional[str]):
        """设置中间文字（仅水平方向生效；传 None 或 "" 恢复纯线）"""
        self._text = text or ""
        self._apply_styles()

    def set_text_size(self, size: int):
        """设置文字字号（像素）"""
        self._text_size = int(size)
        self._apply_styles()

    def text(self) -> str:
        return self._text

    def text_size(self) -> int:
        return self._text_size
