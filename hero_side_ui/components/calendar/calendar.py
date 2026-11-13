"""Calendar 单选日历：持 CalendarState 只读渲染，翻页带滑动动画。
支持月/年选择器与自定义 top/bottom content。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..._shared.dates import (
    CalendarDate,
    month_name,
    month_title,
    weekday_names,
    year_range,
)
from ...core import FontProvider, ThemeProvider
from ...themes import CALENDAR_SIZES, RADIUS
from ..text import Text
from . import _palette as pal
from ._header import _CalendarHeader
from ._month import _MonthGrid
from ._picker import _CalendarPicker
from ._state import CalendarState
from ._transition import _SlideTransition
from ._weekday_bar import _WeekdayBar

VALID_COLORS = ("foreground", "primary", "secondary", "success", "warning", "danger")
VALID_SURFACES = ("default", "popover")


class Calendar(QWidget):
    change = Signal(object)  # 发射 CalendarDate（选中值）
    focus_change = Signal(object)  # 发射 CalendarDate（焦点移动）
    header_expanded_change = Signal(bool)  # 月/年选择器展开/收起

    def __init__(
        self,
        *,
        value: CalendarDate | None = None,
        min_value: CalendarDate | None = None,
        max_value: CalendarDate | None = None,
        color: str = "primary",
        visible_months: int = 1,
        first_day_of_week: str | None = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = False,
        is_header_default_expanded: bool = False,
        is_disabled: bool = False,
        is_readonly: bool = False,
        is_invalid: bool = False,
        error_message: str | None = None,
        is_date_unavailable: Callable[[CalendarDate], bool] | None = None,
        disable_animation: bool = False,
        top_content: QWidget | None = None,
        bottom_content: QWidget | None = None,
        identifier: str = "gregorian",
        surface: str = "default",
        theme: str = "auto",
        parent=None,
    ) -> None:
        """创建单选日历：状态机 + 头部 + 星期名条 + 网格 viewport。

        Args:
            value: 初始选中日期。
            min_value: 可选下界。
            max_value: 可选上界。
            color: 语义色或 foreground。
            visible_months: 并排可见月数（1~3）。
            first_day_of_week: 周起点（sun/mon/...）。
            weekday_style: 星期名宽度 narrow / short / long。
            page_behavior: visible / single 翻页步长策略。
            show_month_and_year_pickers: 是否启用月/年选择器（仅单月）。
            is_header_default_expanded: 初始是否展开选择器。
            is_disabled: 整体禁用。
            is_readonly: 只读。
            is_invalid: 错误态（红框）。
            error_message: 错误提示文本。
            is_date_unavailable: 自定义不可用日期判定。
            disable_animation: 关闭翻页滑动。
            top_content: 头部上方自定义内容。
            bottom_content: 网格下方自定义内容。
            identifier: ICU 历法标识。
            surface: 日期区底色；popover 与 Popover 实心底一致，用于嵌入浮层。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。

        Raises:
            ValueError: surface 不在 VALID_SURFACES 内。

        Note:
            RangeCalendar 通过覆写 _create_state 复用本骨架。
        """
        if surface not in VALID_SURFACES:
            raise ValueError(f"surface must be one of {VALID_SURFACES}, got {surface!r}")
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
        self._surface = surface

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

        self._months: list[_MonthGrid] = []
        self._picker = None
        self._build_ui()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)
        FontProvider.instance().register(self)

        self._render_all()
        self._apply_styles()

    def _apply_font(self) -> None:
        """日期格文字绘制时取当前字体，字体变化后重绘全部子件。"""
        for child in self.findChildren(QWidget):
            child.update()
        self.update()

    # ---- 状态工厂（RangeCalendar 覆盖）--------------------------------

    def _create_state(self, **kwargs) -> CalendarState:
        """构造状态机（供 RangeCalendar 覆写换范围实现）。

        Args:
            **kwargs: 透传给 CalendarState 的构造参数。

        Returns:
            CalendarState 实例。
        """
        return CalendarState(**kwargs)

    # ---- 构建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        """构建完整布局：header → 星期名条 → 网格 viewport → 自定义内容。

        Note:
            top/bottom content 包进固定宽度的横向滚动容器，既不撑宽
            日历也不裁切内容（对齐 HeroUI bottomContent 的 overflow-scroll）。
            错误消息总是创建，以支持运行时 set_invalid 动态显隐。
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 统一列宽 = max(cell, 最长星期名宽 + 留白)，星期名条与日期网格共用
        self._col_width = self._compute_col_width()

        # top_content 需插在最前，但要等日历宽度算出后才能约束/包滚动，
        # 故此处仅占位，实际插入在 viewport 尺寸确定后（见下）。

        month_w = self._sizes["calendar_width"]
        self._header = _CalendarHeader(
            self._sizes,
            visible_months=self._visible_months,
            month_width=month_w,
            theme=self._theme,
            show_pickers=self._show_pickers,
            parent=self,
        )
        self._header.prev_clicked.connect(self._on_prev)
        self._header.next_clicked.connect(self._on_next)
        self._header.title_clicked.connect(self._toggle_expanded)
        root.addWidget(self._header)

        # 固定星期名条（属顶部亮区，翻月不动、不参与滑动）
        self._weekday_bar = _WeekdayBar(
            self._sizes,
            visible_months=self._visible_months,
            col_width=self._col_width,
            theme=self._theme,
            parent=self,
        )
        root.addWidget(self._weekday_bar)

        # 网格 viewport（固定尺寸，滑动裁剪窗口）+ content（横排 N 个月）
        self._viewport = QWidget(self)
        self._viewport.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._content = QWidget(self._viewport)
        cl = QHBoxLayout(self._content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        for _ in range(self._visible_months):
            mg = _MonthGrid(
                self._state,
                self._sizes,
                color=self._color,
                theme=self._theme,
                col_width=self._col_width,
                parent=self._content,
            )
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
        self._error_label = Text(
            self._error_message or "", size="xs", color="danger-500", theme=self._theme, parent=self
        )
        self._error_label.setContentsMargins(
            self._sizes["grid_pad_x"], 2, self._sizes["grid_pad_x"], 6
        )
        self._error_label.setVisible(bool(self._is_invalid and self._error_message))
        root.addWidget(self._error_label)

        if self._show_pickers:
            self._build_picker()
            if self._is_expanded:
                self._apply_expanded(True, animate=False)

    def _compute_col_width(self) -> int:
        """计算星期名条与日期网格共用的列宽。

        Returns:
            max(cell_size, 该周起点下最长星期名文字宽 + 10px 留白)。
        """
        from PySide6.QtGui import QFontMetrics

        from ...core import make_text_qfont

        cell = self._sizes["cell_size"]
        names = weekday_names(
            self._state.first_day_of_week,
            self._weekday_style,
            self._state.identifier if hasattr(self._state, "identifier") else "gregorian",
        )
        fm = QFontMetrics(make_text_qfont("xs", "normal"))
        longest = max((fm.horizontalAdvance(n) for n in names), default=0)
        return max(cell, longest + 10)

    def _wrap_scrollable(self, content: QWidget, width: int) -> QWidget:
        """把自定义内容包进固定宽度横向滚动容器。

        Args:
            content: 用户自定义 widget。
            width: 容器固定宽度（= 日历宽）。

        Returns:
            透明底、横向按需滚动的 QScrollArea。

        Note:
            不 resizable：content 保持自然宽度，超出时滚动不被压缩。
        """
        from PySide6.QtWidgets import QScrollArea

        area = QScrollArea(self)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget > QWidget "
            "{ background: transparent; border: none; }"
        )
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
        """构建月 / 年选择器并接入变更信号。

        Note:
            不用 QGraphicsOpacityEffect——picker 含可交互滚动列，
            加 effect 会走离屏渲染导致子控件错位；
            展开/收起用 show/hide + 日期网格隐藏体现。
        """
        ident = self._state.identifier
        month_items = [(m, month_name(m, ident)) for m in range(1, 13)]
        year_items = [(y, str(y)) for y in year_range(self._state.min_value, self._state.max_value)]
        self._picker = _CalendarPicker(
            self._sizes,
            month_items=month_items,
            year_items=year_items,
            theme=self._theme,
            parent=self._viewport,
        )
        self._picker.setGeometry(0, 0, self._viewport.width(), self._viewport.height())
        self._picker.month_changed.connect(self._on_picker_month)
        self._picker.year_changed.connect(self._on_picker_year)
        # 不用 QGraphicsOpacityEffect：picker 含可交互滚动列，给它加 effect 会走离屏
        # 渲染导致子控件错位。展开/收起用 show/hide + 日期网格隐藏体现。
        self._picker.hide()

    def _toggle_expanded(self) -> None:
        """点击标题：切换选择器展开态。"""
        self.set_header_expanded(not self._is_expanded)

    def _apply_expanded(self, expanded: bool, *, animate: bool) -> None:
        """应用选择器的展开 / 收起。

        Args:
            expanded: True 展开。
            animate: 是否播放动画（当前实现用 show/hide，参数保留兼容）。

        Note:
            展开时先把 picker 滚到焦点所在的月/年，并隐藏底层日期网格。
        """
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
        """显隐底层日期网格内容。

        Args:
            visible: False 时给 picker 让位。
        """
        self._content.setVisible(visible)

    def _on_picker_month(self, month: int) -> None:
        """月选择器提交：更新焦点月份。

        Args:
            month: 1~12 的月份。
        """
        self._set_focused_month_year(month=month)

    def _on_picker_year(self, year: int) -> None:
        """年选择器提交：更新焦点年份。

        Args:
            year: 目标年份。
        """
        self._set_focused_month_year(year=year)

    def _set_focused_month_year(self, *, month: int | None = None, year: int | None = None) -> None:
        """按选择器结果改写焦点月 / 年并重绘。

        Args:
            month: 新月份；None 保持。
            year: 新年份；None 保持。

        Note:
            picker 展开时焦点变了，需同步底层月网格（收起后可见）。
        """
        f = self._state.focused_date
        new = f.with_fields(
            month=month if month is not None else f.month, year=year if year is not None else f.year
        )
        self._state.set_focused_date(new)
        # picker 展开时焦点变了，同步底层月网格（收起后可见）
        self._render_months()
        self._render_titles()

    # ---- 键盘：Esc 收起 ----------------------------------------------

    def keyPressEvent(self, ev) -> None:
        """键盘处理：选择器展开时 Esc 收起。

        Args:
            ev: Qt 键盘事件。
        """
        if self._is_expanded and ev.key() == Qt.Key.Key_Escape:
            self.set_header_expanded(False)
            ev.accept()
            return
        super().keyPressEvent(ev)

    # ---- 渲染 ---------------------------------------------------------

    def _month_starts(self) -> list[CalendarDate]:
        """当前可见各月的 1 号。

        Returns:
            月首日列表。
        """
        return self._state.visible_month_starts()

    def _render_months(self) -> None:
        """把可见月份逐个渲染到对应的 _MonthGrid。"""
        starts = self._month_starts()
        for mg, start in zip(self._months, starts, strict=False):
            mg.render_month(start)

    def _render_titles(self) -> None:
        """按当前历法本地化刷新头部月份标题。"""
        titles = [month_title(s.year, s.month, s.identifier) for s in self._month_starts()]
        self._header.set_titles(titles)

    def _render_weekdays(self) -> None:
        """按周起点与宽度样式刷新星期名条。"""
        names = weekday_names(
            self._state.first_day_of_week, self._weekday_style, self._month_starts()[0].identifier
        )
        self._weekday_bar.set_names(names)

    def _render_all(self) -> None:
        """整体刷新：网格、标题、星期名、翻页按钮启用态。"""
        self._render_months()
        self._render_titles()
        self._render_weekdays()
        self._header.set_page_enabled(self._state.can_page_previous(), self._state.can_page_next())

    def _apply_styles(self) -> None:
        """应用容器 QSS：日期区底 / header content1 / 边框。

        Note:
            禁用 QGraphicsDropShadowEffect——给含交互子按钮的容器加
            effect 会走离屏渲染，Windows 下子按钮被合成到错误偏移；
            这里改用边框模拟卡片浮起，invalid 态换 danger 红边框。
        """
        radius = int(RADIUS["lg"].rstrip("px"))
        # 分层：日期区底 = 窗口背景色；header/星期名行 = content1（亮，_MonthGrid 自绘）。
        if self._surface == "popover":
            base_bg = pal.surface_popover(self._theme)
        else:
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

    def _on_state_change(self, value: CalendarDate | None) -> None:
        """状态机选中值变化回调。

        Args:
            value: 新的选中日期。
        """
        self._render_all()
        self.change.emit(value)

    def _on_state_focus_change(self, focused: CalendarDate) -> None:
        """状态机焦点变化回调。

        Args:
            focused: 新的焦点日期。
        """
        self.focus_change.emit(focused)

    # ---- 交互 ---------------------------------------------------------

    def _on_date_clicked(self, date: CalendarDate) -> None:
        """处理日期格点击：交给状态机选中。

        Args:
            date: 被点击的日期。
        """
        self._state.select_date(date)

    def _on_date_hovered(self, date) -> None:
        """基类无操作；RangeCalendar 覆盖用于范围 hover 预览。

        Args:
            date: 当前 hover 的日期（基类忽略）。
        """
        pass

    def _on_prev(self) -> None:
        """上一页按钮：向前翻页并播放滑动。"""
        self._page(-1, self._state.focus_previous_page)

    def _on_next(self) -> None:
        """下一页按钮：向后翻页并播放滑动。"""
        self._page(1, self._state.focus_next_page)

    def _page(self, direction: int, step_fn) -> None:
        """执行翻页，必要时走滑动过渡。

        Args:
            direction: -1 向前、+1 向后。
            step_fn: 状态机的翻页函数。

        Note:
            禁用动画、无过渡对象或过渡进行中时直接翻页重绘。
        """
        if self._disable_animation or not self._transition or self._transition.is_active():
            step_fn()
            self._render_all()
            return

        def render_new():
            step_fn()
            self._render_all()

        self._transition.run(direction, render_new)

    # ---- 公共 API -----------------------------------------------------

    def value(self) -> CalendarDate | None:
        """返回当前选中日期。

        Returns:
            选中日期；未选中时为 None。
        """
        return self._state.value

    def set_value(self, date: CalendarDate | None) -> None:
        """程序化设置选中日期。

        Args:
            date: 目标日期；None 不做操作。
        """
        if date is not None:
            self._state.select_date(date)

    def set_color(self, color: str) -> None:
        """切换语义色并联动全部月网格。

        Args:
            color: 语义色名或 foreground；非法值忽略。
        """
        if color in VALID_COLORS:
            self._color = color
            for mg in self._months:
                mg.set_color(color)

    def is_invalid(self) -> bool:
        """返回当前错误态。

        Returns:
            True 表示红框 + 错误提示生效。
        """
        return self._is_invalid

    def set_invalid(self, is_invalid: bool, error_message: str | None = None) -> None:
        """运行时切换无效态：红框 + 底部错误提示。

        Args:
            is_invalid: 是否错误态。
            error_message: 新错误文本；None 时保留原文本。
        """
        self._is_invalid = bool(is_invalid)
        if error_message is not None:
            self._error_message = error_message
            self._error_label.setText(error_message)
        self._error_label.setVisible(bool(self._is_invalid and self._error_message))
        self._apply_styles()

    def set_surface(self, surface: str) -> None:
        """切换日期区底色。

        Args:
            surface: default 为日历自身底色，popover 与 Popover 实心底一致。

        Raises:
            ValueError: surface 不在 VALID_SURFACES 内。
        """
        if surface not in VALID_SURFACES:
            raise ValueError(f"surface must be one of {VALID_SURFACES}, got {surface!r}")
        self._surface = surface
        self._apply_styles()

    def is_header_expanded(self) -> bool:
        """选择器是否展开。

        Returns:
            True 表示月/年选择器当前可见。
        """
        return self._is_expanded

    def set_header_expanded(self, expanded: bool) -> None:
        """切换选择器展开态并发出信号。

        Args:
            expanded: 目标状态；未启用 picker 时强制回落 False。

        Note:
            状态未变直接返回，不重复发 header_expanded_change。
        """
        expanded = bool(expanded) and self._show_pickers
        if expanded == self._is_expanded:
            return
        self._apply_expanded(expanded, animate=True)
        self.header_expanded_change.emit(expanded)

    # ---- 主题 ---------------------------------------------------------

    def set_theme(self, theme: str) -> None:
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
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
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._propagate_theme()

    def _propagate_theme(self) -> None:
        """把主题下发到头部、星期名条、月网格、picker 与错误提示。"""
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
