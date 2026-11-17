"""Window 的尺寸层：记录用户设的最小 / 最大尺寸，并叠加默认下限。"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ._config import QWIDGETSIZE_MAX
from ._style import min_size_floor


def _size_args(args: tuple) -> tuple[int, int]:
    """把 (QSize,) 或 (w, h) 统一成 (w, h)。"""
    if len(args) == 1:
        return args[0].width(), args[0].height()
    return int(args[0]), int(args[1])


class _SizeMixin:
    """setMinimumSize 等的覆盖：用户值 + 默认下限 / 按钮保底；固定尺寸会隐藏最大化。

    宿主类需提供 _user_min / _user_max / _config_changed() / _visible_buttons() 等。
    """

    def _apply_min_size(self):
        """最小尺寸 = max(用户值, 默认下限与按钮保底)。"""
        count = sum(self._visible_buttons().values())
        fw, fh = min_size_floor(self.resolved_system(), self.resolved_title_bar_height(), count)
        QWidget.setMinimumSize(self, max(self._user_min[0], fw), max(self._user_min[1], fh))

    def native_size_limits(self) -> tuple[int, int, int, int]:
        """（原生层回调）最小 / 最大尺寸，换算成设备像素。"""
        dpr = self.devicePixelRatioF()
        return (
            round(self.minimumWidth() * dpr),
            round(self.minimumHeight() * dpr),
            round(self.maximumWidth() * dpr),
            round(self.maximumHeight() * dpr),
        )

    def setMinimumSize(self, *args):
        """记录用户的最小尺寸；实际最小尺寸再叠加默认下限。"""
        w, h = _size_args(args)
        self._user_min = (max(0, w), max(0, h))
        self._apply_min_size()
        self._config_changed()

    def setMinimumWidth(self, w: int):
        """同 setMinimumSize，只改宽。"""
        self.setMinimumSize(w, self._user_min[1])

    def setMinimumHeight(self, h: int):
        """同 setMinimumSize，只改高。"""
        self.setMinimumSize(self._user_min[0], h)

    def setMaximumSize(self, *args):
        """记录用户的最大尺寸；最大化时按它钳制窗口（见 _maximize_target）。"""
        w, h = _size_args(args)
        self._user_max = (min(w, QWIDGETSIZE_MAX), min(h, QWIDGETSIZE_MAX))
        QWidget.setMaximumSize(self, *self._user_max)
        self._config_changed()

    def setMaximumWidth(self, w: int):
        """同 setMaximumSize，只改宽。"""
        self.setMaximumSize(w, self._user_max[1])

    def setMaximumHeight(self, h: int):
        """同 setMaximumSize，只改高。"""
        self.setMaximumSize(self._user_max[0], h)

    def setFixedSize(self, *args):
        """固定尺寸：等价于最小 = 最大，同样会隐藏最大化。"""
        w, h = _size_args(args)
        self.setMaximumSize(w, h)
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def setFixedWidth(self, w: int):
        """固定宽度。"""
        self.setMaximumSize(w, self._user_max[1])
        self.setMinimumSize(w, self._user_min[1])

    def setFixedHeight(self, h: int):
        """固定高度。"""
        self.setMaximumSize(self._user_max[0], h)
        self.setMinimumSize(self._user_min[0], h)


__all__ = ["_SizeMixin"]
