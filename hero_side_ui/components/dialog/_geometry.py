"""Dialog 的几何层：自动高度与相对父窗口的定位。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from ...themes import DIALOG_SPEC
from ..window._config import QWIDGETSIZE_MAX, check_int
from ._placement import clamp_point, place, split_placement


def measure_height(widget: QWidget, width: int) -> int:
    """控件在给定宽度下需要的高度。

    优先用控件自带的 height_for_width；其次是 Qt 的「宽度决定高度」；都没有则取 sizeHint，
    sizeHint 无效（无布局的普通 QWidget）时取 minimumSizeHint，最后按控件的最小 / 最大高度钳制。
    """
    own = getattr(widget, "height_for_width", None)
    if callable(own):
        return own(width)
    h = widget.heightForWidth(width) if widget.hasHeightForWidth() else -1
    if h < 0:
        h = max(widget.sizeHint().height(), widget.minimumSizeHint().height(), 0)
    return max(widget.minimumHeight(), min(h, widget.maximumHeight()))


class _GeometryMixin:
    """高度默认跟内容走，位置按九宫格贴父窗口。

    宿主类需提供 _scroll / _footer / _title_bar / _root_layout / _user_max /
    _fixed_height / _placement / _placement_offset / _body_target()。
    """

    # ---- 参照区域 ----
    def _host(self) -> QWidget | None:
        """被对话框挡住的顶层窗口；没有父窗口时为 None。"""
        parent = self.parentWidget()
        return parent.window() if parent is not None else None

    def _ref_and_avail(self) -> tuple[QRect, QRect]:
        """(定位参照区域, 所在屏幕可用区域)。

        父窗口可见且未最小化时，参照父窗口客户区；否则参照屏幕可用区域。
        """
        host = self._host()
        if host is not None and host.isVisible() and not host.isMinimized():
            ref = QRect(host.mapToGlobal(QPoint(0, 0)), host.size())
            screen = QGuiApplication.screenAt(ref.center()) or host.screen()
        else:
            screen = self.screen() or QGuiApplication.primaryScreen()
            ref = screen.availableGeometry()
        return ref, screen.availableGeometry()

    # ---- 自动高度 ----
    def _auto_height(self, width: int, avail: QRect) -> int:
        """标题栏 + 内容 + 按钮区的高度，封顶：max_height，没传则取屏幕可用高度的 80%。"""
        m = self._scroll.layout().contentsMargins()
        body = self._body_target()
        body_h = 0
        if body is not None:
            inner = max(1, width - m.left() - m.right())
            body_h = measure_height(body, inner) + m.top() + m.bottom()
        foot_h = 0 if self._footer.isHidden() else self._footer.sizeHint().height()
        frame = self._root_layout.contentsMargins()
        total = self._title_bar.title_bar_height() + body_h + foot_h + frame.top() + frame.bottom()
        cap = self._user_max[1]
        if cap >= QWIDGETSIZE_MAX:
            cap = int(avail.height() * DIALOG_SPEC["max_height_ratio"])
        return min(total, cap)

    def _apply_height(self):
        """按当前内容重算高度（固定高度则用固定值）。

        Note:
            已显示时以 placement 的锚点为基准变高：top 系顶边不动，bottom 系底边不动，
            其余保持垂直居中，最后钳回屏幕内。
        """
        _, avail = self._ref_and_avail()
        h = self._fixed_height
        if h is None:
            h = self._auto_height(self.width(), avail)
        h = max(self.minimumHeight(), min(h, avail.height(), self.maximumHeight()))
        if h == self.height():
            return
        if not self.isVisible():
            self.resize(self.width(), h)
            return
        g = self.geometry()
        dy = g.height() - h
        row = split_placement(self._placement)[1]
        y = g.y() if row == "top" else g.y() + dy if row == "bottom" else g.y() + dy // 2
        pos = clamp_point(QPoint(g.x(), y), QSize(g.width(), h), avail)
        self.setGeometry(QRect(pos, QSize(g.width(), h)))

    def set_height(self, height: int | None):
        """固定高度，或恢复自动高度。

        Args:
            height: px；None 恢复自动。

        Raises:
            ValueError: 不是正数。
        """
        check_int("height", height)
        self._fixed_height = None if height is None else int(height)
        self._apply_height()

    # ---- 定位 ----
    def _reposition(self):
        """按 placement 与偏移算位置并移动；每次打开时重算。"""
        ref, avail = self._ref_and_avail()
        self.move(place(ref, self.size(), self._placement, self._placement_offset, avail))


__all__ = ["_GeometryMixin", "measure_height"]
