"""Calendar 头部：prev/next 按钮 + 居中月份标题；show_pickers 时标题可点。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ...animation import tween_value
from ...utils import load_svg_icon
from ..button import Button
from ..text import Text

_BTN_SIDE = 30


class _TitleButton(QWidget):
    """标题按钮：底层是 Button 组件（variant=light, radius=full），右侧叠一个
    chevron-down 图标（展开时平滑旋转 180°，收起再转回）。点击发 clicked。"""

    clicked = Signal()

    def __init__(self, theme: str, parent=None) -> None:
        """创建标题按钮：Button 底座 + 叠加 chevron。

        Args:
            theme: 主题名。
            parent: Qt 父对象。

        Note:
            chevron 鼠标穿透，点击事件落到底层 Button 统一处理。
        """
        super().__init__(parent)
        from PySide6.QtWidgets import QLabel

        self._theme = theme
        self._expanded = False
        self._angle = 0.0
        self._base_pixmap = None

        # 底层用真正的 Button 组件承载文字 + 交互 + full 圆角
        self._btn = Button(
            "", variant="light", radius="full", size="sm", color="default", theme=theme, parent=self
        )
        self._btn.clicked.connect(self.clicked.emit)

        # 右侧 chevron（叠加，鼠标穿透，随点击落到底层 Button）
        self._chevron = QLabel(self._btn)
        self._chevron.setFixedSize(16, 16)
        self._chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._load_base_pixmap()

        # chevron 旋转动画（0°→180°）
        self._rot_anim = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._btn)

    def _load_base_pixmap(self) -> None:
        """加载未旋转的 chevron 底图并按当前角度应用。"""
        self._base_pixmap = load_svg_icon("heroicons--chevron-down", size=16, color=None)
        self._apply_rotation()

    def _apply_rotation(self) -> None:
        """按 _angle 旋转底图并写回 chevron。"""
        if self._base_pixmap is None:
            return
        transform = QTransform().rotate(self._angle)
        rotated = self._base_pixmap.transformed(
            transform, Qt.TransformationMode.SmoothTransformation
        )
        self._chevron.setPixmap(rotated)

    def _on_rot_tick(self, v) -> None:
        """旋转补间回调：写入角度并重应用。

        Args:
            v: 当前角度值（0 ~ 180）。
        """
        self._angle = float(v)
        self._apply_rotation()

    def _position_chevron(self) -> None:
        """把 chevron 贴到 Button 右内侧并垂直居中。"""
        # chevron 贴 Button 右内侧，垂直居中
        x = self._btn.width() - self._chevron.width() - 8
        y = (self._btn.height() - self._chevron.height()) // 2
        self._chevron.move(max(0, x), max(0, y))

    def resizeEvent(self, ev) -> None:
        """尺寸变化后重新定位 chevron。

        Args:
            ev: Qt 尺寸变化事件。
        """
        self._position_chevron()
        super().resizeEvent(ev)

    def setText(self, text: str) -> None:
        """设置标题文本。

        Args:
            text: 标题文字；尾部加空格给 chevron 让位。
        """
        # 文字后留出 chevron 位置（尾部加空格给图标让位）
        self._btn.setText(f"{text}   ")
        self._btn.adjustSize()
        self._position_chevron()

    def set_expanded(self, expanded: bool) -> None:
        """切换展开态并播放 chevron 旋转动画。

        Args:
            expanded: True 旋到 180°，False 转回 0°。

        Note:
            状态未变直接返回。
        """
        if expanded == self._expanded:
            return
        self._expanded = expanded
        tween_value(
            self,
            "_rot_anim",
            self._angle,
            180.0 if expanded else 0.0,
            self._on_rot_tick,
            duration=200,
        )

    def set_theme(self, theme: str) -> None:
        """切换主题并联动底座按钮与 chevron 底图。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        self._btn.set_theme(theme)
        self._load_base_pixmap()
        self._position_chevron()


class _CalendarHeader(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()
    title_clicked = Signal()

    def __init__(
        self,
        sizes: dict,
        *,
        visible_months: int,
        month_width: int,
        theme: str,
        show_pickers: bool = False,
        parent=None,
    ) -> None:
        """创建日历头部：翻页按钮 + 标题（可点或纯文本）。

        Args:
            sizes: 尺寸 token（header_pad_x / header_pad_y 等）。
            visible_months: 可见月份数；仅单月时支持可点标题。
            month_width: 单月区宽度（多月标题分布参考）。
            theme: 主题名。
            show_pickers: 是否启用可点标题（展开月/年选择器）。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("HeroCalendarHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sizes = sizes
        self._visible_months = visible_months
        self._month_width = month_width
        self._theme = theme
        self._show_pickers = show_pickers and visible_months == 1
        self._titles: list = []
        self._title_btn: _TitleButton | None = None

        header_h = _BTN_SIDE + sizes["header_pad_y"] * 2
        self.setFixedHeight(header_h)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._build_ui()

    def _build_ui(self) -> None:
        """构建头部布局：prev → 标题区 → next。

        Note:
            单月且 show_pickers 时标题是 _TitleButton（可点开选择器）；
            多月时每个可见月一个居中 Text 标题。
        """
        hb = QHBoxLayout(self)
        hb.setContentsMargins(self._sizes["header_pad_x"], 0, self._sizes["header_pad_x"], 0)
        hb.setSpacing(0)
        vcenter = Qt.AlignmentFlag.AlignVCenter

        self._prev_btn = Button(
            icon_only=True,
            icon="heroicons--chevron-left",
            variant="light",
            color="default",
            size="sm",
            theme=self._theme,
            parent=self,
        )
        self._next_btn = Button(
            icon_only=True,
            icon="heroicons--chevron-right",
            variant="light",
            color="default",
            size="sm",
            theme=self._theme,
            parent=self,
        )
        self._prev_btn.setFixedSize(_BTN_SIDE, _BTN_SIDE)
        self._next_btn.setFixedSize(_BTN_SIDE, _BTN_SIDE)
        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._next_btn.clicked.connect(self.next_clicked.emit)

        hb.addWidget(self._prev_btn, 0, vcenter)

        if self._show_pickers:
            # 单月可点标题
            hb.addStretch(1)
            self._title_btn = _TitleButton(self._theme, parent=self)
            self._title_btn.clicked.connect(self.title_clicked.emit)
            self._titles.append(self._title_btn)
            hb.addWidget(self._title_btn, 0, vcenter)
            hb.addStretch(1)
        else:
            for _i in range(self._visible_months):
                hb.addStretch(1)
                title = Text(
                    "",
                    size="sm",
                    weight="medium",
                    color="default-500",
                    theme=self._theme,
                    parent=self,
                )
                title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._titles.append(title)
                hb.addWidget(title, 0, vcenter)
                hb.addStretch(1)

        hb.addWidget(self._next_btn, 0, vcenter)

    # ---- API ----------------------------------------------------------

    def set_titles(self, titles: list[str]) -> None:
        """填充各可见月的标题文本。

        Args:
            titles: 标题列表，与 _titles 逐位对应。
        """
        for lbl, text in zip(self._titles, titles, strict=False):
            lbl.setText(text)

    def set_page_enabled(self, prev_enabled: bool, next_enabled: bool) -> None:
        """设置前后翻页按钮的启用态。

        Args:
            prev_enabled: 上一页是否可用。
            next_enabled: 下一页是否可用。
        """
        self._prev_btn.setEnabled(prev_enabled)
        self._next_btn.setEnabled(next_enabled)

    def set_page_visible(self, visible: bool) -> None:
        """展开 picker 时隐藏翻页按钮（对齐 calendar.ts 展开态 opacity-0）。

        Args:
            visible: False 表示随 picker 展开隐藏。
        """
        self._prev_btn.setVisible(visible)
        self._next_btn.setVisible(visible)

    def set_expanded(self, expanded: bool) -> None:
        """转发展开态给标题按钮的 chevron。

        Args:
            expanded: True 展开（chevron 旋到 180°）。
        """
        if self._title_btn is not None:
            self._title_btn.set_expanded(expanded)

    def set_theme(self, theme: str) -> None:
        """切换主题并联动按钮与标题。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        self._prev_btn.set_theme(theme)
        self._next_btn.set_theme(theme)
        for lbl in self._titles:
            lbl.set_theme(theme)
