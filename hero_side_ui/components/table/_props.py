"""Table 动态属性 setter + top/bottom content 装配（mixin）。

把运行期可调的属性 setter（颜色/尺寸/圆角/阴影/斑马/紧凑/隐藏表头等）与
顶部 / 底部内容区装配从主体抽出，保持 table.py 在舒适行数内。

宿主 Table 需提供：_color/_size/_radius/_shadow/_is_striped/_is_compact/
_hide_header/_disallow_empty_selection/_card/_row_checkboxes/_select_all_cb/
_top_content/_bottom_content/_top_placement/_bottom_placement/_outer/_inside_v
以及 _propagate_style / _apply_row_states / _rebuild / _card_radius 等方法。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ...utils import safe_delete
from ._constants import (
    VALID_COLORS,
    VALID_RADII,
    VALID_SHADOWS,
    VALID_SIZES,
)


class _PropsMixin:
    # ------------------------------------------------------------
    # 动态属性 setter
    # ------------------------------------------------------------
    def set_color(self, c: str):
        if c not in VALID_COLORS:
            return
        self._color = c
        for cb in list(self._row_checkboxes.values()):
            cb.set_color(c)
        if self._select_all_cb:
            self._select_all_cb.set_color(c)
        self._propagate_style()
        self._apply_row_states(animated=False)

    def set_size(self, s: str):
        if s not in VALID_SIZES:
            return
        self._size = s
        self._rebuild()

    def set_radius(self, r: str):
        if r not in VALID_RADII:
            return
        self._radius = r
        if self._card is not None:
            self._card.set_radius(self._card_radius())
        self._propagate_style()
        self.update()

    def set_shadow(self, s: str):
        if s not in VALID_SHADOWS:
            return
        self._shadow = s
        if self._card is not None:
            self._card.set_shadow(s)
        self.update()

    def set_is_striped(self, v: bool):
        self._is_striped = bool(v)
        self._propagate_style()
        self._apply_row_states(animated=False)

    def set_is_compact(self, v: bool):
        self._is_compact = bool(v)
        self._propagate_style()

    def set_hide_header(self, v: bool):
        self._hide_header = bool(v)
        self._propagate_style()

    def set_disallow_empty_selection(self, v: bool):
        self._disallow_empty_selection = bool(v)

    # ------------------------------------------------------------
    # top / bottom content
    # ------------------------------------------------------------
    def set_top_content(self, w: Optional[QWidget]):
        if self._top_content is not None:
            safe_delete(self._top_content)
            self._top_content = None
        if w is not None:
            self._top_content = w
            if self._top_placement == "outside":
                self._outer.insertWidget(0, w)
            else:
                self._inside_v.insertWidget(0, w)

    def set_bottom_content(self, w: Optional[QWidget]):
        if self._bottom_content is not None:
            safe_delete(self._bottom_content)
            self._bottom_content = None
        if w is not None:
            self._bottom_content = w
            if self._bottom_placement == "outside":
                self._outer.addWidget(w)
            else:
                self._inside_v.addWidget(w)
