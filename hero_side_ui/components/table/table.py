"""HeroSideUI Table 主组件。

复刻 HeroUI v2 Table。结构::

    Table (QWidget)
        ├── top_content (outside, 可选)
        ├── _card_host (Card 外壳，自带 content1 背景 + 阴影 + 圆角)
        │     ├── top_content (inside, 可选)
        │     ├── _grid_host (_GridHost + QGridLayout)  —— max_height 时套进 ScrollShadow
        │     │     ├── row 0: 列头（_TableColumnHeader ...）
        │     │     ├── row 1..n: 数据单元格（_TableCell ...）
        │     │     └── 多选时 col 0 为 select-all / checkbox 列
        │     ├── _empty_widget  (无数据时)
        │     └── bottom_content (inside, 可选)
        └── bottom_content (outside, 可选)

设计要点：
    - 用 QGridLayout 让同列单元格自动等宽，天然解决列对齐。
    - 每个单元格是独立自绘 QWidget（_TableCell），行状态由 Table 集中管理后推入。
    - 行 hover / 选中 / 斑马纹由 cell 自己绘制 before 行条，圆角按首尾列/行拼接。
    - 外壳复用现成 Card；max_height 时表体套进 ScrollShadow 支持滚动 + sticky 表头。

子模块: _cell.py / _header_cell.py / _hosts.py / _engine.py / _virtual.py /
        _data.py / _props.py / _selection.py / _sorting.py / _palette.py / _constants.py
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import TABLE_SIZES
from ..card import Card, CardBody
from ..checkbox import Checkbox
from ..text import Text
from . import _palette as pal
from ._cell import _TableCell
from ._constants import (
    VALID_COLORS,
    VALID_LAYOUTS,
    VALID_RADII,
    VALID_SELECTION_MODES,
    VALID_SHADOWS,
    VALID_SIZES,
)
from ._header_cell import _TableColumnHeader
from ._hosts import _CheckboxCell, _GridHost
from ._data import _DataMixin
from ._engine import _RowRenderer
from ._props import _PropsMixin
from ._selection import _SelectionMixin
from ._sorting import _SortingMixin
from ._virtual import _VirtualMixin


class Table(
    _SelectionMixin, _SortingMixin, _VirtualMixin, _PropsMixin, _DataMixin, QWidget
):
    """HeroUI 风格表格。

    用法::

        t = Table(color="primary", selection_mode="multiple", is_striped=True)
        t.set_columns([
            {"key": "name", "label": "NAME"},
            {"key": "role", "label": "ROLE"},
            {"key": "status", "label": "STATUS", "align": "center"},
        ])
        t.add_row("1", {"name": "Tony", "role": "CEO", "status": "Active"})
        t.selection_changed.connect(print)
    """

    selection_changed = Signal(set)
    row_action = Signal(str)
    sort_changed = Signal(object, object)  # (column_key, direction|None)

    def __init__(
        self,
        *,
        color: str = "default",
        size: str = "md",
        radius: str = "lg",
        shadow: str = "sm",
        layout: str = "auto",
        selection_mode: str = "none",
        selected_keys: Optional[Iterable[str]] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        disallow_empty_selection: bool = False,
        is_striped: bool = False,
        is_compact: bool = False,
        hide_header: bool = False,
        full_width: bool = True,
        remove_wrapper: bool = False,
        empty_content: Optional[str] = None,
        top_content: Optional[QWidget] = None,
        bottom_content: Optional[QWidget] = None,
        top_content_placement: str = "inside",
        bottom_content_placement: str = "inside",
        max_height: Optional[int] = None,
        is_header_sticky: bool = False,
        is_virtualized: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent=None,
    ):
        super().__init__(parent)

        if color not in VALID_COLORS:
            color = "default"
        if size not in VALID_SIZES:
            size = "md"
        if radius not in VALID_RADII:
            radius = "lg"
        if shadow not in VALID_SHADOWS:
            shadow = "sm"
        if layout not in VALID_LAYOUTS:
            layout = "auto"
        if selection_mode not in VALID_SELECTION_MODES:
            selection_mode = "none"

        self._color = color
        self._size = size
        self._radius = radius
        self._shadow = shadow
        self._layout_mode = layout
        self._selection_mode = selection_mode
        self._disallow_empty_selection = bool(disallow_empty_selection)
        self._is_striped = is_striped
        self._is_compact = is_compact
        self._hide_header = hide_header
        self._full_width = full_width
        self._remove_wrapper = remove_wrapper
        self._empty_content_text = empty_content
        self._top_placement = top_content_placement if top_content_placement in ("inside", "outside") else "inside"
        self._bottom_placement = bottom_content_placement if bottom_content_placement in ("inside", "outside") else "inside"
        self._max_height = max_height
        self._is_header_sticky = bool(is_header_sticky)
        # 虚拟化需要滚动容器；未给 max_height 时自动给一个兜底高度
        self._is_virtualized = bool(is_virtualized)
        if self._is_virtualized and self._max_height is None:
            self._max_height = 420
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 行渲染引擎（行复用 + 虚拟化）
        self._renderer = _RowRenderer(self)
        self._virtual_pending = False

        # 数据状态
        self._columns: list[dict] = []
        self._row_order: list[str] = []
        self._row_data: dict[str, dict] = {}
        self._row_disabled_flags: dict[str, bool] = {}
        self._render_cell: Optional[Callable] = None

        # 选中 / hover
        self._selected_keys: set[str] = set(selected_keys or [])
        # 禁用集合分两个来源，避免互相污染：
        #   _user_disabled_keys —— 用户通过构造 disabled_keys= / set_disabled_keys() 显式设置
        #   _row_disabled_flags —— 行内联 is_disabled / _disabled
        # _disabled_keys 是二者的并集，每次数据变动后由 _recompute_disabled() 重算。
        self._user_disabled_keys: set[str] = set(str(k) for k in (disabled_keys or []))
        self._disabled_keys: set[str] = set(self._user_disabled_keys)
        self._hover_key: Optional[str] = None

        # 排序（None = 无排序）
        self._sort_column: Optional[str] = None
        self._sort_direction: Optional[str] = None

        # widget 引用
        self._headers: dict[str, _TableColumnHeader] = {}
        self._cells: dict[str, dict[str, _TableCell]] = {}  # row_key -> col_key -> cell
        self._row_checkboxes: dict[str, Checkbox] = {}
        self._select_all_cb: Optional[Checkbox] = None

        self._build_ui()

        if top_content is not None:
            self.set_top_content(top_content)
        if bottom_content is not None:
            self.set_bottom_content(bottom_content)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ------------------------------------------------------------
    # UI 骨架
    # ------------------------------------------------------------
    def _build_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        self._outer.setSpacing(cfg["wrapper_gap"])

        self._top_content: Optional[QWidget] = None
        self._bottom_content: Optional[QWidget] = None

        # 外壳：复用现成 Card（自带阴影系统 + content1 背景 + 圆角 + 主题）
        self._card: Optional[Card] = None
        if self._remove_wrapper:
            self._card_host = QWidget(self)
            self._inside_v = QVBoxLayout(self._card_host)
            self._inside_v.setContentsMargins(0, 0, 0, 0)
            self._inside_v.setSpacing(cfg["wrapper_gap"])
        else:
            self._card = Card(
                shadow=self._shadow,
                radius=self._card_radius(),
                full_width=self._full_width,
                theme="auto" if self._theme_mode == "auto" else self._theme_mode,
            )
            self._card_host = self._card
            body = CardBody()
            body.set_padding(cfg["wrapper_padding"])
            body._layout.setSpacing(cfg["wrapper_gap"])
            self._card.add_body(body)
            self._inside_v = body._layout

        # grid host：表头行 0 + 数据行 1..n（单网格，列宽天然对齐）。
        # 套滚动区时必须有实心底色（_GridHost 自绘），否则黑底+重影。
        self._scroll: Optional[QScrollArea] = None  # paintEvent 会读，先占位
        self._grid_host = _GridHost(self)
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(0)
        self._grid.setVerticalSpacing(0)

        # max_height：grid_host 套进 ScrollShadow（滚动 + 边缘渐隐）
        if self._max_height is not None:
            from ..scroll_shadow import ScrollShadow

            self._scroll = ScrollShadow(
                theme="auto" if self._theme_mode == "auto" else self._theme_mode,
                fade_color=pal.wrapper_bg(self._theme).name(),
                is_enabled=False,  # 表格默认不要卷轴边缘阴影
            )
            self._scroll.setWidgetResizable(True)
            self._scroll.setMaximumHeight(int(self._max_height))
            self._scroll.setWidget(self._grid_host)
            if self._is_header_sticky:
                self._scroll.verticalScrollBar().valueChanged.connect(
                    self._on_scroll_sticky
                )
            if self._is_virtualized:
                self._scroll.verticalScrollBar().valueChanged.connect(
                    self._on_virtual_scroll
                )
            self._inside_v.addWidget(self._scroll)
        else:
            self._inside_v.addWidget(self._grid_host)

        # empty 占位（带 parent 防构造期无父闪窗，addWidget 后归 inside 容器）
        self._empty_widget = QWidget(self)
        ev = QHBoxLayout(self._empty_widget)
        ev.setContentsMargins(0, 24, 0, 24)
        ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label = Text(self._empty_content_text or "No rows to display.", theme="auto")
        ev.addWidget(self._empty_label)
        self._inside_v.addWidget(self._empty_widget)
        self._empty_widget.hide()

        # 组装 outer：[outside-top] card [outside-bottom]
        self._outer.addWidget(self._card_host)

        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def _on_scroll_sticky(self, value: int):
        """sticky 表头：滚动时把表头行 widget 上移 value，钉在视口顶部。"""
        col_offset = 1 if self._selection_mode == "multiple" else 0
        widgets = []
        if self._select_all_cb is not None:
            holder = self._grid.itemAtPosition(0, 0)
            if holder and holder.widget():
                widgets.append(holder.widget())
        for ci in range(len(self._columns)):
            it = self._grid.itemAtPosition(0, ci + col_offset)
            if it and it.widget():
                widgets.append(it.widget())
        for w in widgets:
            w.move(w.x(), value)
            w.raise_()

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------
    def _card_radius(self) -> str:
        """外壳 Card 的圆角：full 仅作用于表头/行条（药丸），Card 不跟随 full，
        退回 lg 保持外框正常圆角。"""
        return "lg" if self._radius == "full" else self._radius

    def _resolve_theme(self, mode: str) -> str:
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        if self._theme_mode != "auto":
            return
        self._theme = theme
        # Card 在 auto 模式自行跟随 ThemeProvider，无需手动转发
        self._propagate_style()
        self._refresh_empty_color()
        self._grid_host.update()
        self.update()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            ThemeProvider.instance().register(self)
            self._theme = ThemeProvider.instance().current_theme
        elif theme in ("light", "dark"):
            self._theme_mode = theme
            self._theme = theme
        else:
            return
        if self._card is not None:
            self._card.set_theme(theme)
        self._propagate_style()
        self._refresh_empty_color()
        self._grid_host.update()
        self.update()

    def _refresh_empty_color(self):
        from ...core.state_palette import StatePalette

        self._empty_label.set_color(StatePalette.text_description(self._theme).name())

    # ------------------------------------------------------------
    # 重建网格
    # ------------------------------------------------------------
    def _clear_header(self):
        """只清表头行（row 0）的列头与全选框；数据行由 _renderer 管理，不在此处理。"""
        for header in list(self._headers.values()):
            self._grid.removeWidget(header)
            header.hide()
            header.deleteLater()
        self._headers.clear()
        if self._select_all_cb is not None:
            holder = self._select_all_cb.parentWidget()
            self._grid.removeWidget(self._select_all_cb)
            if holder is not None:
                self._grid.removeWidget(holder)
                holder.hide()
                holder.deleteLater()
            self._select_all_cb = None

    def _rebuild(self):
        # 重建期间关掉刷新，避免中间态逐控件重绘导致的闪烁/卡顿
        self._grid_host.setUpdatesEnabled(False)
        try:
            self._rebuild_inner()
        finally:
            self._grid_host.setUpdatesEnabled(True)

    def _rebuild_inner(self):
        self._clear_header()

        has_checkbox_col = self._selection_mode == "multiple"
        col_offset = 1 if has_checkbox_col else 0

        # --- 表头行（row 0） ---
        if has_checkbox_col:
            # 带 parent 防止无父 widget 瞬间变顶层窗口（Windows 闪原生空窗）
            self._select_all_cb = Checkbox(
                color=self._color, size=self._size, theme="auto",
                parent=self._grid_host,
            )
            self._select_all_cb.clicked.connect(lambda *_: self._on_select_all_clicked())
            holder = self._checkbox_holder(self._select_all_cb, self._on_select_all_clicked)
            self._grid.addWidget(holder, 0, 0)

        for ci, col in enumerate(self._columns):
            header = _TableColumnHeader(
                col["key"], col["label"], align=col["align"],
                allows_sorting=col["allows_sorting"], parent=self._grid_host,
            )
            header.sort_clicked.connect(self._on_header_sort_clicked)
            self._grid.addWidget(header, 0, ci + col_offset)
            self._headers[col["key"]] = header
            if col["width"]:
                self._grid.setColumnMinimumWidth(ci + col_offset, int(col["width"]))

        # --- 数据行：交给行渲染引擎（复用 / 虚拟化） ---
        if self._is_virtualized and self._scroll is not None:
            self._render_virtual(force=True)
        else:
            self._renderer.render()

        # 列伸缩：full_width 时让数据列平分剩余空间
        if self._full_width and self._columns:
            for ci in range(len(self._columns)):
                stretch = 0 if (self._columns[ci]["width"]) else 1
                self._grid.setColumnStretch(ci + col_offset, stretch)

        self._propagate_style()
        self._apply_row_states(animated=False)
        self._sync_header_sort_state()
        self._refresh_empty()
        # 重建后若处于 sticky 且已滚动，重新把表头钉到当前位置
        if self._is_header_sticky and self._scroll is not None:
            self._on_scroll_sticky(self._scroll.verticalScrollBar().value())

    def _checkbox_holder(self, cb: Checkbox, on_click) -> QWidget:
        # 整格可点（_CheckboxCell），消除复选框周围 padding/空白的点击死区。
        holder = _CheckboxCell(on_click, self._grid_host)
        h = QHBoxLayout(holder)
        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        h.setContentsMargins(cfg["cell_padding_x"], 0, cfg["cell_padding_x"], 0)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(cb)
        holder.setFixedWidth(cfg["checkbox_col_width"])
        return holder

    # ------------------------------------------------------------
    # 样式下发
    # ------------------------------------------------------------
    def _propagate_style(self):
        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        self._inside_v.setSpacing(cfg["wrapper_gap"])

        n_cols = len(self._columns)
        for ci, col in enumerate(self._columns):
            header = self._headers.get(col["key"])
            if header:
                header.apply_style(
                    color=self._color, size=self._size, theme=self._theme,
                    radius=self._radius, is_first_col=(ci == 0),
                    is_last_col=(ci == n_cols - 1), hide_header=self._hide_header,
                )

        n_rows = len(self._row_order)
        is_multi = self._selection_mode == "multiple"
        col_index = {col["key"]: ci for ci, col in enumerate(self._columns)}
        index_of = {k: i for i, k in enumerate(self._row_order)}
        # 只遍历当前已渲染的行（虚拟化下 _cells 仅含可视行），开销与可视行数成正比
        for row_key, row_cells in self._cells.items():
            ri = index_of.get(row_key, 0)
            for col_key, cell in row_cells.items():
                ci = col_index.get(col_key)
                if ci is None:
                    continue
                cell.apply_style(
                    color=self._color, size=self._size, theme=self._theme,
                    radius=self._radius, is_striped=self._is_striped,
                    is_compact=self._is_compact, is_multi=is_multi,
                    align=self._columns[ci]["align"],
                    disable_animation=self._disable_animation,
                )
                cell.set_position(
                    is_first_row=(ri == 0), is_last_row=(ri == n_rows - 1),
                    is_first_col=(ci == 0), is_last_col=(ci == n_cols - 1),
                )

    def _apply_row_states(self, *, animated: bool = True, only_rows=None):
        """重绘行的 hover / selected / striped 视觉。

        only_rows 为 None 时刷当前已渲染的行；传入 row_key 集合时只刷这些行
        —— hover 仅影响"离开的旧行 + 进入的新行"两行，避免每次移动重刷整表掉帧。
        虚拟化下 _cells 只含可视行，故按 _cells 而非全量 _row_order 遍历，
        保证开销与可视行数成正比、与总行数无关。
        """
        # 行下标用于斑马纹奇偶；虚拟化时按全量数据下标算，保证滚动时条纹连续
        index_of = {k: i for i, k in enumerate(self._row_order)}
        target_keys = self._cells.keys() if only_rows is None else only_rows
        for row_key in list(target_keys):
            cells = self._cells.get(row_key)
            if not cells:
                continue
            selected = row_key in self._selected_keys
            hover = row_key == self._hover_key
            disabled = row_key in self._disabled_keys
            odd = (index_of.get(row_key, 0) % 2) == 1
            for cell in cells.values():
                cell.set_row_state(
                    hover=hover, selected=selected, odd=odd,
                    disabled=disabled, animated=animated,
                )
            cb = self._row_checkboxes.get(row_key)
            if cb is not None and cb.is_selected() != selected:
                # 不能 blockSignals —— 那会掐断 stateChanged，使勾选视觉动画不触发。
                # 编程式 setChecked 只发 stateChanged/toggled，不发 clicked，无回环风险。
                cb.set_is_selected(selected)
        self._sync_select_all()

    # ------------------------------------------------------------
    # 交互回调
    # ------------------------------------------------------------
    def _on_cell_hover(self, row_key: str, entered: bool):
        # 仅可选模式响应行 hover 高亮（对齐 HeroUI isSelectable hover 语义）
        if self._selection_mode == "none":
            return
        # 禁用行不参与 hover 高亮
        if entered and row_key in self._disabled_keys:
            return
        prev = self._hover_key
        if entered:
            self._hover_key = row_key
        elif self._hover_key == row_key:
            self._hover_key = None
        if prev == self._hover_key:
            return
        # 只刷受影响的两行（旧 hover 行 + 新 hover 行），不动整表
        dirty = {k for k in (prev, self._hover_key) if k is not None}
        self._apply_row_states(only_rows=dirty)

    def _on_checkbox_clicked(self, row_key: str):
        self._on_row_clicked(row_key)

    def _on_select_all_clicked(self):
        self._toggle_select_all()
        self._sync_select_all()

    def _sync_select_all(self):
        if self._select_all_cb is None:
            return
        state = self._select_all_state()
        # 同上：不 blockSignals，让勾选/取消的视觉动画正常触发。
        if state == "all":
            self._select_all_cb.set_is_indeterminate(False)
            self._select_all_cb.set_is_selected(True)
        elif state == "partial":
            self._select_all_cb.set_is_selected(False)
            self._select_all_cb.set_is_indeterminate(True)
        else:
            self._select_all_cb.set_is_indeterminate(False)
            self._select_all_cb.set_is_selected(False)

    # ------------------------------------------------------------
    # 选中 / 禁用 API
    # ------------------------------------------------------------
    def selected_keys(self) -> set:
        return set(self._selected_keys)

    def set_selected_keys(self, keys: Iterable[str]):
        keys = set(str(k) for k in keys)
        if self._selection_mode == "none":
            return
        # 过滤掉不存在的行与禁用行，保证选中集合始终合法
        if self._row_order:
            valid = set(self._row_order) - self._disabled_keys
            keys &= valid
        if self._selection_mode == "single" and len(keys) > 1:
            keys = {next(iter(keys))}
        old = set(self._selected_keys)
        self._selected_keys = keys
        self._apply_row_states()
        if old != keys:
            self.selection_changed.emit(set(self._selected_keys))

    def selection_mode(self) -> str:
        return self._selection_mode

    def set_selection_mode(self, mode: str):
        if mode not in VALID_SELECTION_MODES or mode == self._selection_mode:
            return
        self._selection_mode = mode
        cleared = False
        if mode == "none" and self._selected_keys:
            self._selected_keys.clear()
            cleared = True
        elif mode == "single" and len(self._selected_keys) > 1:
            self._selected_keys = {next(iter(self._selected_keys))}
            cleared = True
        self._rebuild()
        if cleared:
            self.selection_changed.emit(set(self._selected_keys))

    def disabled_keys(self) -> set:
        return set(self._disabled_keys)

    def set_disabled_keys(self, keys: Iterable[str]):
        self._user_disabled_keys = set(str(k) for k in keys)
        self._recompute_disabled()
        self._rebuild()

    # ------------------------------------------------------------
    # 空状态
    # ------------------------------------------------------------
    def _refresh_empty(self):
        is_empty = len(self._row_order) == 0
        grid_visible = not is_empty or len(self._columns) > 0
        host = self._scroll if self._scroll is not None else self._grid_host
        host.setVisible(grid_visible)
        self._empty_widget.setVisible(is_empty)
        if is_empty:
            self._refresh_empty_color()


__all__ = ["Table"]
