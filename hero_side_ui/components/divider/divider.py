"""Divider 分割线组件：水平/垂直纯色线，水平方向可选中间文字。"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QFrame, QSizePolicy

from ...core import FontProvider, ThemeProvider
from ...themes import DIVIDER_SIZES, HEROUI_COLORS


class Divider(QFrame):
    """HeroUI 风格分割线，继承 QFrame。

    Args:
        orientation: horizontal（默认）或 vertical。
        color: 自定义颜色；None 跟随主题。
        text: 中间文字，仅水平生效。
        text_size: 中间文字字号。
    """

    def __init__(
        self,
        orientation: str = "horizontal",
        theme: str = "auto",
        color: str | None = None,
        text: str | None = None,
        text_size: int = 12,
        parent=None,
    ):
        """创建分割线并按方向选择绘制方式。

        Args:
            orientation: horizontal 或 vertical。
            theme: 主题名；auto 时跟随 ThemeProvider。
            color: 自定义线色；None 表示跟随主题。
            text: 中间文字，仅水平方向生效。
            text_size: 中间文字字号，单位像素。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._orientation = orientation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._custom_color = color
        self._text = text or ""
        self._text_size = int(text_size)

        self.setObjectName("heroDivider")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)

        self._apply_styles()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)
        FontProvider.instance().register(self)

    # ============================================================
    # 内部：解析颜色
    # ============================================================

    def _line_color(self) -> str:
        """返回分割线颜色，自定义色优先于主题默认色。

        Returns:
            自定义颜色的十六进制字符串；未设置时亮色取 default-200、
            暗色取 default-700。
        """
        if self._custom_color:
            return self._custom_color
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        # 亮色: default-200, 暗色: default-700（对齐 HeroUI bg-divider token）
        return dc[700] if is_dark else dc[200]

    def _text_color(self) -> str:
        """返回中间文字颜色，只跟随主题。

        Returns:
            亮色取 default-500、暗色取 default-400 的十六进制字符串。
        """
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        return dc[400] if is_dark else dc[500]

    def _has_text_mode(self) -> bool:
        """是否启用「带文字」模式。

        Returns:
            text 非空且方向不是 vertical 时为 True；垂直分割线永远不带文字。
        """
        return bool(self._text) and self._orientation != "vertical"

    # ============================================================
    # 样式系统
    # ============================================================

    def _apply_styles(self):
        """按方向与是否带文字，在 QSS 背景与 paintEvent 自绘之间切换。

        垂直线固定宽度、垂直 Expanding；水平带文字时高度由字体行高决定；
        水平纯线固定 1px 高、水平 Expanding。

        Note:
            切到带文字模式必须把 QSS 清空，否则 setStyleSheet 的实心背景
            会盖在 paintEvent 的绘制结果上。
        """
        if self._orientation == "vertical":
            # 垂直分割线：固定宽度，垂直 Expanding，QSS 背景
            thickness = DIVIDER_SIZES["vertical"]["thickness"]
            self.setFixedWidth(thickness)
            self.setMaximumHeight(16777215)  # 清理可能的 setFixedHeight 残留
            self.setMinimumHeight(0)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
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
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setStyleSheet("")  # 清空 QSS，交给 paintEvent
            self.update()
        else:
            # 水平 + 无文字：1px 实线，QSS 背景
            thickness = DIVIDER_SIZES["horizontal"]["thickness"]
            self.setFixedHeight(thickness)
            self.setMaximumWidth(16777215)
            self.setMinimumWidth(0)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setStyleSheet(
                f"#heroDivider {{ background-color: {self._line_color()}; border: none; }}"
            )

    def _apply_font(self):
        """全局字体变化后重算带文字分割线的高度并重绘。"""
        self._apply_styles()

    def _build_font(self) -> QFont:
        """按 text_size 构建中间文字使用的字体。

        Returns:
            normal 字重的 QFont；供 paintEvent 与行高测量共用。
        """
        from ...core import make_text_qfont

        return make_text_qfont(self._text_size, "normal")

    # ============================================================
    # 自绘 (仅水平 + 带文字时)
    # ============================================================

    def paintEvent(self, event):
        """绘制水平带文字分割线：两侧线段 + 居中文字。

        Args:
            event: Qt 绘制事件。

        Note:
            非文字模式直接交给 QFrame 默认绘制（QSS 背景走 styled background），
            本方法只处理 _has_text_mode() 为 True 的分支。
        """
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
        fm.height()
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
        """切换分割线方向并重算样式。

        Args:
            orientation: horizontal 或 vertical；垂直方向不显示中间文字。
        """
        self._orientation = orientation
        self._apply_styles()

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 的注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切到固定主题时先 unregister，避免后续广播覆盖设定。
        """
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，只更新主题并重算样式。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark 或 auto 等其他值。

        Returns:
            light / dark 原样返回；其余返回 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_color(self, color: str | None):
        """设置自定义线色。

        Args:
            color: 十六进制颜色字符串；None 恢复跟随主题。
        """
        self._custom_color = color
        self._apply_styles()

    def set_text(self, text: str | None):
        """设置中间文字。

        Args:
            text: 文字内容；None 或空串恢复为纯线。

        Note:
            仅水平方向生效，垂直方向始终忽略该文字。
        """
        self._text = text or ""
        self._apply_styles()

    def set_text_size(self, size: int):
        """设置中间文字字号。

        Args:
            size: 字号，单位像素；内部转成 int 后会影响带文字模式的高度。
        """
        self._text_size = int(size)
        self._apply_styles()

    def text(self) -> str:
        """返回中间文字。

        Returns:
            当前文字；未设置时为空串。
        """
        return self._text

    def text_size(self) -> int:
        """返回中间文字字号。

        Returns:
            当前字号，单位像素。
        """
        return self._text_size
