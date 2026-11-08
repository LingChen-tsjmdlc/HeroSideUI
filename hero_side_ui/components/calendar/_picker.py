"""Calendar 月/年滚动选择器：中心吸附 + 距离渐隐 + 平滑滚动。
前后垫空项使首尾也能居中。
"""

from __future__ import annotations

from PySide6.QtCore import (
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...animation import tween_value
from ..text import Text
from . import _palette as pal

_ITEM_H = 32
_EMPTY_OFFSET = 3
_SETTLE_MS = 90  # 滚动停止判定
_SNAP_ANIM_MS = 250  # 吸附 / 点击滚动动画时长
_FADE_SIZE = 90  # 顶/底渐隐高度


class _PickerColumn(QScrollArea):
    """单列 snap 滚动。项为 (value, label)。滚动停下后吸附居中并 emit value_committed。"""

    value_committed = Signal(object)

    def __init__(self, items: list[tuple], *, theme: str, align_left: bool, parent=None) -> None:
        """创建单列 snap 滚动列。

        Args:
            items: (value, label) 列表。
            theme: 主题名。
            align_left: True 左对齐（年列），False 居中（月列）。
            parent: Qt 父对象。

        Note:
            前后各垫 _EMPTY_OFFSET 个空项，让首尾项也能滚到居中位。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._theme = theme
        self._align_left = align_left
        self._items = items
        self._rows: list[_PickerItem] = []
        self._value_to_index: dict = {}
        self._snapping = False

        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget > QWidget "
            "{ background: transparent; border: none; }"
        )
        self.viewport().setAutoFillBackground(False)

        # 平滑滚动动画
        self._anim = None

        # 停止判定
        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(_SETTLE_MS)
        self._settle.timeout.connect(self._snap_to_nearest)

        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self._build()

    def _build(self) -> None:
        """构建列体：空垫项 + 数据项 + 空垫项的纵向布局。"""
        body = QWidget(self)
        body.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        col = QVBoxLayout(body)
        # 左对齐列（年）加左内边距，让文字落在中央高亮框内、不贴左边缘；
        # 右对齐/居中列不需要。
        col.setContentsMargins(
            12 if self._align_left else 0, 0, 12 if not self._align_left else 0, 0
        )
        col.setSpacing(0)
        align = Qt.AlignmentFlag.AlignLeft if self._align_left else Qt.AlignmentFlag.AlignHCenter

        for _ in range(_EMPTY_OFFSET):
            col.addWidget(self._make_row("", None))
        for idx, (value, label) in enumerate(self._items):
            self._value_to_index[value] = idx
            row = self._make_row(label, value)
            self._rows.append(row)
            col.addWidget(row, 0, align)
        for _ in range(_EMPTY_OFFSET):
            col.addWidget(self._make_row("", None))

        self.setWidget(body)

    def _make_row(self, label: str, value) -> _PickerItem:
        """构造单个 picker 项并接好点击。

        Args:
            label: 显示文本。
            value: 项的值；None 表示空垫项。

        Returns:
            已连接 clicked 的 _PickerItem。
        """
        row = _PickerItem(label, value, theme=self._theme)
        row.clicked.connect(self._on_item_clicked)
        return row

    # ---- 滚动 / 吸附 --------------------------------------------------

    def _center_y(self) -> float:
        """视口中心的绝对 y 坐标。

        Returns:
            滚动值 + 视口高度一半。
        """
        return self.verticalScrollBar().value() + self.viewport().height() / 2

    def _row_center(self, row) -> float:
        """某行中心的绝对 y 坐标。

        Args:
            row: 目标行 widget。

        Returns:
            行 pos.y + 行高一半。
        """
        return row.pos().y() + row.height() / 2

    def _nearest_index(self) -> int:
        """找离视口中心最近的数据项下标。

        Returns:
            距离最小项的 index；无行时为 0。
        """
        center = self._center_y()
        best_i, best_d = 0, None
        for i, row in enumerate(self._rows):
            d = abs(self._row_center(row) - center)
            if best_d is None or d < best_d:
                best_d, best_i = d, i
        return best_i

    def _on_scroll(self, _v: int) -> None:
        """滚动回调：刷新颜色梯度并重启停止判定计时。

        Args:
            _v: 滚动条当前值（未使用）。
        """
        self._update_item_colors()
        if not self._snapping:
            self._settle.start()

    def _snap_to_nearest(self) -> None:
        """滚动停止后吸附到最近项并提交其值。"""
        if not self._rows:
            return
        idx = self._nearest_index()
        self._animate_center(idx, emit=True)

    def _on_item_clicked(self, value) -> None:
        """处理项点击：滚动该项到中心并提交。

        Args:
            value: 被点击项的值。
        """
        idx = self._value_to_index.get(value)
        if idx is not None:
            self._animate_center(idx, emit=True)

    def _target_for(self, idx: int) -> int:
        """计算把第 idx 项滚到中心所需的滚动值。

        Args:
            idx: 目标项下标。

        Returns:
            钳制在滚动条范围内的目标滚动值。
        """
        row = self._rows[idx]
        target = int(self._row_center(row) - self.viewport().height() / 2)
        bar = self.verticalScrollBar()
        return max(bar.minimum(), min(bar.maximum(), target))

    def _animate_center(self, idx: int, *, emit: bool) -> None:
        """用补间把第 idx 项滚到中心。

        Args:
            idx: 目标项下标。
            emit: 结束后是否 emit value_committed。

        Note:
            _snapping 标记抑制吸附期间 _on_scroll 重启 settle 计时，
            防止吸附动画被判定为新的用户滚动。
        """
        target = self._target_for(idx)
        bar = self.verticalScrollBar()
        self._snapping = True

        def done():
            self._snapping = False
            self._update_item_colors()
            if emit:
                self.value_committed.emit(self._items[idx][0])

        tween_value(
            self,
            "_anim",
            bar.value(),
            target,
            lambda v: bar.setValue(int(v)),
            duration=_SNAP_ANIM_MS,
            on_finished=done,
            animated=target != bar.value(),
        )

    def scroll_to_value(self, value, *, animated: bool) -> None:
        """滚动到指定值（不提交）。

        Args:
            value: 目标值；不存在时忽略。
            animated: True 播放滚动动画，False 直接跳转。
        """
        idx = self._value_to_index.get(value)
        if idx is None:
            return
        if animated:
            self._animate_center(idx, emit=False)
        else:
            self.verticalScrollBar().setValue(self._target_for(idx))
            self._update_item_colors()

    def _update_item_colors(self) -> None:
        """按距中心距离设每项深浅（对齐官方：中心深、越远越淡）。"""
        center = self._center_y()
        for row in self._rows:
            dist = abs(self._row_center(row) - center) / _ITEM_H
            row.set_distance(dist)

    def set_theme(self, theme: str) -> None:
        """切换主题并联动全部项与颜色梯度。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        for row in self._rows:
            row.set_theme(theme)
        self._update_item_colors()


class _PickerItem(Text):
    """picker 单项，可点击。空项（value=None）不可点。按距中心距离渐隐。"""

    clicked = Signal(object)

    def __init__(self, label: str, value, *, theme: str, parent=None) -> None:
        """创建 picker 单项。

        Args:
            label: 显示文本。
            value: 项的值；None 为空垫项（不可点、不渐隐）。
            theme: 主题名。
            parent: Qt 父对象。
        """
        super().__init__(
            label,
            size=18,
            weight="normal",
            color="default-300",
            theme=theme,
            selectable=False,
            parent=parent,
        )
        self._value = value
        self.setFixedHeight(_ITEM_H)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if value is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, ev) -> None:
        """鼠标释放：仍在项内且非空垫项时发 clicked。

        Args:
            ev: Qt 鼠标释放事件。
        """
        if self._value is not None and self.rect().contains(ev.pos()):
            self.clicked.emit(self._value)
        super().mouseReleaseEvent(ev)

    def set_distance(self, dist: float) -> None:
        """按距中心距离设置文字深浅与字重。

        Args:
            dist: 距离（0 中心最深，越大越淡）。
        """
        if self._value is None:
            return
        if dist < 0.5:
            self.set_color("foreground")
            self.set_weight("medium")
        elif dist < 1.5:
            self.set_color("default-500")
            self.set_weight("normal")
        elif dist < 2.5:
            self.set_color("default-400")
            self.set_weight("normal")
        else:
            self.set_color("default-300")
            self.set_weight("normal")


class _FadeOverlay(QWidget):
    """顶/底渐隐遮罩（content1 色 → 透明），透明鼠标事件，覆盖在滚动列之上。"""

    def __init__(self, theme: str, parent=None) -> None:
        """创建透明鼠标事件的渐隐遮罩。

        Args:
            theme: 主题名。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_theme(self, theme: str) -> None:
        """切换主题色并重绘。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        self.update()

    def paintEvent(self, ev) -> None:
        """绘制顶 / 底两条 content1 → 透明的线性渐变。

        Args:
            ev: Qt 绘制事件。
        """
        p = QPainter(self)
        base = pal.surface_content1(self._theme)
        w, h = self.width(), self.height()
        # 顶部渐隐
        top = QLinearGradient(0, 0, 0, _FADE_SIZE)
        c0 = QColor(base)
        c0.setAlpha(255)
        c1 = QColor(base)
        c1.setAlpha(0)
        top.setColorAt(0.0, c0)
        top.setColorAt(1.0, c1)
        p.fillRect(QRectF(0, 0, w, _FADE_SIZE), top)
        # 底部渐隐
        bot = QLinearGradient(0, h - _FADE_SIZE, 0, h)
        bot.setColorAt(0.0, c1)
        bot.setColorAt(1.0, c0)
        p.fillRect(QRectF(0, h - _FADE_SIZE, w, _FADE_SIZE), bot)
        p.end()


class _CalendarPicker(QWidget):
    """月 + 年 两列选择器 + 中央高亮条 + 顶底渐隐。展开时覆盖日期网格。"""

    month_changed = Signal(int)
    year_changed = Signal(int)

    def __init__(
        self,
        sizes: dict,
        *,
        month_items: list[tuple],
        year_items: list[tuple],
        theme: str,
        parent=None,
    ) -> None:
        """创建月 + 年两列选择器。

        Args:
            sizes: 尺寸 token（grid_pad_x 等）。
            month_items: (value, label) 月份项。
            year_items: (value, label) 年份项。
            theme: 主题名。
            parent: Qt 父对象。

        Note:
            中国习惯年在左、月在右；中央高亮条与顶底渐隐由本类自绘。
        """
        super().__init__(parent)
        self._sizes = sizes
        self._theme = theme

        lay = QHBoxLayout(self)
        lay.setContentsMargins(sizes["grid_pad_x"], 0, sizes["grid_pad_x"], 0)
        lay.setSpacing(8)

        # 中国习惯：年在左、月在右
        self._year_col = _PickerColumn(year_items, theme=theme, align_left=True, parent=self)
        self._month_col = _PickerColumn(month_items, theme=theme, align_left=False, parent=self)
        self._month_col.value_committed.connect(self.month_changed.emit)
        self._year_col.value_committed.connect(self.year_changed.emit)
        lay.addWidget(self._year_col, 1)
        lay.addWidget(self._month_col, 1)

        # 顶底渐隐遮罩（覆盖全区，鼠标穿透）
        self._fade = _FadeOverlay(theme, self)

    def resizeEvent(self, ev) -> None:
        """尺寸变化后让渐隐遮罩铺满并置顶。

        Args:
            ev: Qt 尺寸变化事件。
        """
        self._fade.setGeometry(0, 0, self.width(), self.height())
        self._fade.raise_()
        super().resizeEvent(ev)

    def paintEvent(self, ev) -> None:
        """绘制 content1 底色与中央高亮条。

        Args:
            ev: Qt 绘制事件。
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), pal.surface_content1(self._theme))
        pad = self._sizes["grid_pad_x"]
        y = (self.height() - _ITEM_H) / 2
        rect = QRectF(pad, y, self.width() - pad * 2, _ITEM_H)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.picker_highlight_bg(self._theme))
        p.drawRoundedRect(rect, 8, 8)
        p.end()

    def set_current(self, month: int, year: int) -> None:
        """把两列滚到当前月 / 年（不提交）。

        Args:
            month: 当前月（1~12）。
            year: 当前年。

        Note:
            延迟到布局 settle 后再定位——构造/展开瞬间 row.pos 尚未算出。
        """
        # 延迟到布局 settle 后再定位（构造/展开瞬间 row.pos 尚未算出）
        self._pending = (month, year)
        QTimer.singleShot(0, self, self._apply_current)

    def _apply_current(self) -> None:
        """执行 set_current 延迟的定位。"""
        month, year = self._pending
        self._month_col.scroll_to_value(month, animated=False)
        self._year_col.scroll_to_value(year, animated=False)
        self._month_col._update_item_colors()
        self._year_col._update_item_colors()

    def set_theme(self, theme: str) -> None:
        """切换主题并联动两列与遮罩。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        self._month_col.set_theme(theme)
        self._year_col.set_theme(theme)
        self._fade.set_theme(theme)
        self.update()
