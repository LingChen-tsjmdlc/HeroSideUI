"""Calendar 头部：上一月按钮 + N 个月份标题 + 下一月按钮（单行）。

对齐 HeroUI headerWrapper：prev 只在最左、next 只在最右，中间每个可见月
一个居中标题。固定高度，避免真实字体环境下被标题撑高导致按钮溢出。
show_pickers 时（仅单月）标题变可点胶囊，带 chevron-down，展开时 chevron 翻转。
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ...utils import load_svg_icon
from ..button import Button
from ..text import Text

_BTN_SIDE = 30


class _TitleButton(QWidget):
    """标题按钮：底层是 Button 组件（variant=light, radius=full），右侧叠一个
    chevron-down 图标（展开时平滑旋转 180°，收起再转回）。点击发 clicked。"""

    clicked = Signal()

    def __init__(self, theme: str, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QLabel
        self._theme = theme
        self._expanded = False
        self._angle = 0.0
        self._base_pixmap = None

        # 底层用真正的 Button 组件承载文字 + 交互 + full 圆角
        self._btn = Button("", variant="light", radius="full", size="sm",
                           color="default", theme=theme, parent=self)
        self._btn.clicked.connect(self.clicked.emit)

        # 右侧 chevron（叠加，鼠标穿透，随点击落到底层 Button）
        self._chevron = QLabel(self._btn)
        self._chevron.setFixedSize(16, 16)
        self._chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._load_base_pixmap()

        # chevron 旋转动画（0°→180°）
        self._rot_anim = QVariantAnimation(self)
        self._rot_anim.setDuration(200)
        self._rot_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._rot_anim.valueChanged.connect(self._on_rot_tick)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._btn)

    def _load_base_pixmap(self) -> None:
        self._base_pixmap = load_svg_icon("heroicons--chevron-down", size=16, color=None)
        self._apply_rotation()

    def _apply_rotation(self) -> None:
        if self._base_pixmap is None:
            return
        transform = QTransform().rotate(self._angle)
        rotated = self._base_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self._chevron.setPixmap(rotated)

    def _on_rot_tick(self, v) -> None:
        self._angle = float(v)
        self._apply_rotation()

    def _position_chevron(self) -> None:
        # chevron 贴 Button 右内侧，垂直居中
        x = self._btn.width() - self._chevron.width() - 8
        y = (self._btn.height() - self._chevron.height()) // 2
        self._chevron.move(max(0, x), max(0, y))

    def resizeEvent(self, ev) -> None:
        self._position_chevron()
        super().resizeEvent(ev)

    def setText(self, text: str) -> None:
        # 文字后留出 chevron 位置（尾部加空格给图标让位）
        self._btn.setText(f"{text}   ")
        self._btn.adjustSize()
        self._position_chevron()

    def set_expanded(self, expanded: bool) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self._rot_anim.stop()
        self._rot_anim.setStartValue(self._angle)
        self._rot_anim.setEndValue(180.0 if expanded else 0.0)
        self._rot_anim.start()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._btn.set_theme(theme)
        self._load_base_pixmap()
        self._position_chevron()


class _CalendarHeader(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()
    title_clicked = Signal()

    def __init__(self, sizes: dict, *, visible_months: int, month_width: int,
                 theme: str, show_pickers: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("HeroCalendarHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._sizes = sizes
        self._visible_months = visible_months
        self._month_width = month_width
        self._theme = theme
        self._show_pickers = show_pickers and visible_months == 1
        self._titles: List = []
        self._title_btn: Optional[_TitleButton] = None

        header_h = _BTN_SIDE + sizes["header_pad_y"] * 2
        self.setFixedHeight(header_h)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._build_ui()

    def _build_ui(self) -> None:
        hb = QHBoxLayout(self)
        hb.setContentsMargins(self._sizes["header_pad_x"], 0,
                              self._sizes["header_pad_x"], 0)
        hb.setSpacing(0)
        vcenter = Qt.AlignmentFlag.AlignVCenter

        self._prev_btn = Button(icon_only=True, icon="heroicons--chevron-left",
                                variant="light", color="default", size="sm",
                                theme=self._theme, parent=self)
        self._next_btn = Button(icon_only=True, icon="heroicons--chevron-right",
                                variant="light", color="default", size="sm",
                                theme=self._theme, parent=self)
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
                title = Text("", size="sm", weight="medium", color="default-500",
                             theme=self._theme, parent=self)
                title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._titles.append(title)
                hb.addWidget(title, 0, vcenter)
                hb.addStretch(1)

        hb.addWidget(self._next_btn, 0, vcenter)

    # ---- API ----------------------------------------------------------

    def set_titles(self, titles: List[str]) -> None:
        for lbl, text in zip(self._titles, titles):
            lbl.setText(text)

    def set_page_enabled(self, prev_enabled: bool, next_enabled: bool) -> None:
        self._prev_btn.setEnabled(prev_enabled)
        self._next_btn.setEnabled(next_enabled)

    def set_page_visible(self, visible: bool) -> None:
        """展开 picker 时隐藏翻页按钮（对齐 calendar.ts 展开态 opacity-0）。"""
        self._prev_btn.setVisible(visible)
        self._next_btn.setVisible(visible)

    def set_expanded(self, expanded: bool) -> None:
        if self._title_btn is not None:
            self._title_btn.set_expanded(expanded)

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._prev_btn.set_theme(theme)
        self._next_btn.set_theme(theme)
        for lbl in self._titles:
            lbl.set_theme(theme)
