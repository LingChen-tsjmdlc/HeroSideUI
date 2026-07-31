"""Calendar 单选日历（对外组件）。

对齐 HeroUI Calendar：base 容器（圆角 + 边框浮起 + bg）内含头部（N 个月份
标题 + 上/下月翻页）与网格区（1~3 个月并排）。持 CalendarState 逻辑机，
只读它渲染、把点击转成 state 调用，对外发 change / focus_change 信号。翻页带
横向滑动动画（可用 disable_animation 关闭）。支持月/年选择器（仅单月）、
自定义 top/bottom content、无效态提示。
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import CALENDAR_SIZES, RADIUS
from ._date import (
    CalendarDate,
    month_name,
    month_title,
    weekday_names,
    year_range,
)
from ._header import _CalendarHeader
from ._month import _MonthGrid
from ._picker import _CalendarPicker
from ._state import CalendarState
from ._transition import _SlideTransition
from ._weekday_bar import _WeekdayBar
from ..text import Text
from . import _palette as pal

VALID_COLORS = ("foreground", "primary", "secondary", "success", "warning", "danger")


class Calendar(QWidget):
    change = Signal(object)                  # 发射 CalendarDate（选中值）
    focus_change = Signal(object)            # 发射 CalendarDate（焦点移动）
    header_expanded_change = Signal(bool)    # 月/年选择器展开/收起

    def __init__(
        self,
        *,
        value: Optional[CalendarDate] = None,
        min_value: Optional[CalendarDate] = None,
        max_value: Optional[CalendarDate] = None,
        color: str = "primary",
        visible_months: int = 1,
        first_day_of_week: Optional[str] = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = False,
        is_header_default_expanded: bool = False,
        is_disabled: bool = False,
        is_readonly: bool = False,
        is_invalid: bool = False,
        error_message: Optional[str] = None,
        is_date_unavailable: Optional[Callable[[CalendarDate], bool]] = None,
        disable_animation: bool = False,
        top_content: Optional[QWidget] = None,
        bottom_content: Optional[QWidget] = None,
        identifier: str = "gregorian",
        theme: str = "auto",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HeroCalendar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._color = color if color in VALID_COLORS else "primary"
        self._weekday_style = weekday_style
        self._disable_animation = disable_animation
        self._top_content = top_content
        self._bottom_content = bottom_content
        self._is_invalid = is_invalid
        self._error_message = error_message
        self._sizes = CALENDAR_SIZES

        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme

        self._state = self._create_state(
            value=value,
            min_value=min_value,
            max_value=max_value,
            visible_months=visible_months,
            page_behavior=page_behavior,
            first_day_of_week=first_day_of_week,
            is_disabled=is_disabled,
            is_readonly=is_readonly,
            is_unavailable_fn=is_date_unavailable,
            identifier=identifier,
        )
        self._visible_months = self._state.visible_months
        # 月/年选择器仅单月生效（对齐 HeroUI）
        self._show_pickers = show_month_and_year_pickers and self._visible_months == 1
        self._is_expanded = bool(is_header_default_expanded) and self._show_pickers
        self._state.on_change = self._on_state_change
        self._state.on_focus_change = self._on_state_focus_change

        self._months: List[_MonthGrid] = []
        self._picker = None
        self._build_ui()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._render_all()
        self._apply_styles()

    # ---- 状态工厂（RangeCalendar 覆盖）--------------------------------

    def _create_state(self, **kwargs) -> CalendarState:
        return CalendarState(**kwargs)

    # ---- 构建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 统一列宽 = max(cell, 最长星期名宽 + 留白)，星期名条与日期网格共用
        self._col_width = self._compute_col_width()

        # top_content 需插在最前，但要等日历宽度算出后才能约束/包滚动，
        # 故此处仅占位，实际插入在 viewport 尺寸确定后（见下）。

        month_w = self._sizes["calendar_width"]
        self._header = _CalendarHeader(self._sizes, visible_months=self._visible_months,
                                       month_width=month_w, theme=self._theme,
                                       show_pickers=self._show_pickers, parent=self)
        self._header.prev_clicked.connect(self._on_prev)
        self._header.next_clicked.connect(self._on_next)
        self._header.title_clicked.connect(self._toggle_expanded)
        root.addWidget(self._header)

        # 固定星期名条（属顶部亮区，翻月不动、不参与滑动）
        self._weekday_bar = _WeekdayBar(self._sizes, visible_months=self._visible_months,
                                        col_width=self._col_width, theme=self._theme,
                                        parent=self)
        root.addWidget(self._weekday_bar)

        # 网格 viewport（固定尺寸，滑动裁剪窗口）+ content（横排 N 个月）
        self._viewport = QWidget(self)
        self._viewport.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._content = QWidget(self._viewport)
        cl = QHBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        for _ in range(self._visible_months):
            mg = _MonthGrid(self._state, self._sizes, color=self._color,
                            theme=self._theme, col_width=self._col_width,
                            parent=self._content)
            mg.date_clicked.connect(self._on_date_clicked)
            mg.date_hovered.connect(self._on_date_hovered)
            cl.addWidget(mg)
            self._months.append(mg)
        self._content.adjustSize()
        size = self._content.sizeHint()
        self._content.setFixedSize(size)
        self._content.move(0, 0)
        self._viewport.setFixedSize(size)
        root.addWidget(self._viewport)

        # top/bottom content 包进固定宽度(=日历宽)的横向滚动容器：内容窄时铺满、
        # 内容宽（多按钮/多选项）时横向滚动，既不撑宽日历也不裁切内容（对齐
        # HeroUI bottomContent 的 overflow-scroll）。
        cal_w = size.width()
        if self._top_content is not None:
            self._top_wrap = self._wrap_scrollable(self._top_content, cal_w)
            root.insertWidget(0, self._top_wrap)  # top 置于最前
        if self._bottom_content is not None:
            self._bottom_wrap = self._wrap_scrollable(self._bottom_content, cal_w)
            root.addWidget(self._bottom_wrap)

        self._transition = _SlideTransition(self._viewport, self._content)

        # 错误消息（is_invalid + 有文本时显示，danger 色）。总是创建以支持
        # 运行时 set_invalid 动态显隐。
        self._error_label = Text(self._error_message or "", size="xs",
                                 color="danger-500", theme=self._theme, parent=self)
        self._error_label.setContentsMargins(self._sizes["grid_pad_x"], 2,
                                              self._sizes["grid_pad_x"], 6)
        self._error_label.setVisible(bool(self._is_invalid and self._error_message))
        root.addWidget(self._error_label)

        if self._show_pickers:
            self._build_picker()
            if self._is_expanded:
                self._apply_expanded(True, animate=False)

    def _compute_col_width(self) -> int:
        """列宽 = max(cell_size, 该周起点下最长星期名的文字宽 + 左右留白)。"""
        from PySide6.QtGui import QFontMetrics
        from ...core import make_text_qfont

        cell = self._sizes["cell_size"]
        names = weekday_names(self._state.first_day_of_week, self._weekday_style,
                              self._state.identifier if hasattr(self._state, "identifier")
                              else "gregorian")
        fm = QFontMetrics(make_text_qfont("xs", "normal"))
        longest = max((fm.horizontalAdvance(n) for n in names), default=0)
        return max(cell, longest + 10)

    def _wrap_scrollable(self, content: QWidget, width: int) -> QWidget:
        """把自定义内容包进固定宽度的横向滚动容器。

        内容窄→铺满该宽度不出滚动条；内容宽（多按钮/多选项）→横向滚动，
        既不撑宽日历也不裁切。透明底以融入日历配色。
        """
        from PySide6.QtWidgets import QScrollArea

        area = QScrollArea(self)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget "
                           "{ background: transparent; border: none; }")
        area.viewport().setAutoFillBackground(False)
        content.setParent(area)
        content.adjustSize()
        area.setWidget(content)
        # 不 resizable：content 保持自然宽度，超过容器宽度时横向滚动（不被压缩）；
        # 窄内容由 content 自身布局的 stretch 决定是否铺满。
        area.setWidgetResizable(content.sizeHint().width() <= width)
        area.setFixedWidth(width)
        area.setFixedHeight(content.sizeHint().height() + 14)  # 留横向滚动条高
        area.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return area

    # ---- 月/年选择器 --------------------------------------------------

    def _build_picker(self) -> None:
        ident = self._state.identifier
        month_items = [(m, month_name(m, ident)) for m in range(1, 13)]
        year_items = [(y, str(y)) for y in
                      year_range(self._state.min_value, self._state.max_value)]
        self._picker = _CalendarPicker(self._sizes, month_items=month_items,
                                       year_items=year_items, theme=self._theme,
                                       parent=self._viewport)
        self._picker.setGeometry(0, 0, self._viewport.width(), self._viewport.height())
        self._picker.month_changed.connect(self._on_picker_month)
        self._picker.year_changed.connect(self._on_picker_year)
        # 不用 QGraphicsOpacityEffect：picker 含可交互滚动列，给它加 effect 会走离屏
        # 渲染导致子控件错位。展开/收起用 show/hide + 日期网格隐藏体现。
        self._picker.hide()

    def _toggle_expanded(self) -> None:
        self.set_header_expanded(not self._is_expanded)

    def _apply_expanded(self, expanded: bool, *, animate: bool) -> None:
        self._is_expanded = expanded
        self._header.set_expanded(expanded)
        self._header.set_page_visible(not expanded)
        if self._picker is None:
            return
        if expanded:
            focused = self._state.focused_date
            self._picker.set_current(focused.month, focused.year)
            self._picker.show()
            self._picker.raise_()
            self._viewport_content_visible(False)
        else:
            self._picker.hide()
            self._viewport_content_visible(True)

    def _viewport_content_visible(self, visible: bool) -> None:
        self._content.setVisible(visible)

    def _on_picker_month(self, month: int) -> None:
        self._set_focused_month_year(month=month)

    def _on_picker_year(self, year: int) -> None:
        self._set_focused_month_year(year=year)

    def _set_focused_month_year(self, *, month: int = None, year: int = None) -> None:
        f = self._state.focused_date
        new = f.with_fields(month=month if month is not None else f.month,
                            year=year if year is not None else f.year)
        self._state.set_focused_date(new)
        # picker 展开时焦点变了，同步底层月网格（收起后可见）
        self._render_months()
        self._render_titles()

    # ---- 键盘：Esc 收起 ----------------------------------------------

    def keyPressEvent(self, ev) -> None:
        if self._is_expanded and ev.key() == Qt.Key.Key_Escape:
            self.set_header_expanded(False)
            ev.accept()
            return
        super().keyPressEvent(ev)

    # ---- 渲染 ---------------------------------------------------------

    def _month_starts(self) -> List[CalendarDate]:
        return self._state.visible_month_starts()

    def _render_months(self) -> None:
        starts = self._month_starts()
        for mg, start in zip(self._months, starts):
            mg.render_month(start)

    def _render_titles(self) -> None:
        titles = [month_title(s.year, s.month, s.identifier) for s in self._month_starts()]
        self._header.set_titles(titles)

    def _render_weekdays(self) -> None:
        names = weekday_names(self._state.first_day_of_week, self._weekday_style,
                              self._month_starts()[0].identifier)
        self._weekday_bar.set_names(names)

    def _render_all(self) -> None:
        self._render_months()
        self._render_titles()
        self._render_weekdays()
        self._header.set_page_enabled(self._state.can_page_previous(),
                                      self._state.can_page_next())

    def _apply_styles(self) -> None:
        radius = int(RADIUS["lg"].rstrip("px"))
        # 分层：日期区底 = 窗口背景色；header/星期名行 = content1（亮，_MonthGrid 自绘）。
        base_bg = pal.surface_base(self._theme)
        header_bg = pal.surface_content1(self._theme).name()
        if self._is_invalid:
            border = pal._shade("danger", 500).name()  # invalid 红边框
        elif self._theme == "dark":
            border = "rgba(255, 255, 255, 0.08)"
        else:
            border = "rgba(0, 0, 0, 0.08)"
        # 边框模拟卡片浮起。禁用 QGraphicsDropShadowEffect：给含交互子按钮的容器加
        # effect 会走离屏渲染，Windows 下子按钮被合成到错误偏移。
        self.setStyleSheet(
            f"#HeroCalendar {{ background: {base_bg}; border-radius: {radius}px;"
            f" border: 1px solid {border}; }}"
            f"#HeroCalendarHeader {{ background: {header_bg};"
            f" border-top-left-radius: {radius}px; border-top-right-radius: {radius}px; }}"
        )

    # ---- state 回调 ---------------------------------------------------

    def _on_state_change(self, value: Optional[CalendarDate]) -> None:
        self._render_all()
        self.change.emit(value)

    def _on_state_focus_change(self, focused: CalendarDate) -> None:
        self.focus_change.emit(focused)

    # ---- 交互 ---------------------------------------------------------

    def _on_date_clicked(self, date: CalendarDate) -> None:
        self._state.select_date(date)

    def _on_date_hovered(self, date) -> None:
        """基类无操作；RangeCalendar 覆盖用于范围 hover 预览。"""
        pass

    def _on_prev(self) -> None:
        self._page(-1, self._state.focus_previous_page)

    def _on_next(self) -> None:
        self._page(1, self._state.focus_next_page)

    def _page(self, direction: int, step_fn) -> None:
        if self._disable_animation or not self._transition or self._transition.is_active():
            step_fn()
            self._render_all()
            return

        def render_new():
            step_fn()
            self._render_all()

        self._transition.run(direction, render_new)

    # ---- 公共 API -----------------------------------------------------

    def value(self) -> Optional[CalendarDate]:
        return self._state.value

    def set_value(self, date: Optional[CalendarDate]) -> None:
        if date is not None:
            self._state.select_date(date)

    def set_color(self, color: str) -> None:
        if color in VALID_COLORS:
            self._color = color
            for mg in self._months:
                mg.set_color(color)

    def is_invalid(self) -> bool:
        return self._is_invalid

    def set_invalid(self, is_invalid: bool, error_message: Optional[str] = None) -> None:
        """运行时切换无效态：红框 + 底部错误提示。error_message 为 None 时保留原文本。"""
        self._is_invalid = bool(is_invalid)
        if error_message is not None:
            self._error_message = error_message
            self._error_label.setText(error_message)
        self._error_label.setVisible(bool(self._is_invalid and self._error_message))
        self._apply_styles()

    def is_header_expanded(self) -> bool:
        return self._is_expanded

    def set_header_expanded(self, expanded: bool) -> None:
        expanded = bool(expanded) and self._show_pickers
        if expanded == self._is_expanded:
            return
        self._apply_expanded(expanded, animate=True)
        self.header_expanded_change.emit(expanded)

    # ---- 主题 ---------------------------------------------------------

    def set_theme(self, theme: str) -> None:
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._propagate_theme()

    def _apply_provider_theme(self, theme: str) -> None:
        self._theme = theme
        self._propagate_theme()

    def _propagate_theme(self) -> None:
        self._header.set_theme(self._theme)
        self._weekday_bar.set_theme(self._theme)
        for mg in self._months:
            mg.set_theme(self._theme)
        if self._picker is not None:
            self._picker.set_theme(self._theme)
        if self._error_label is not None:
            self._error_label.set_theme(self._theme)
        self._apply_styles()
        self._render_all()
