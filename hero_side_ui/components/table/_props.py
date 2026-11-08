"""Table 动态 setter + top/bottom content 装配 mixin。"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ...utils import safe_delete
from ._constants import (
    VALID_COLORS,
    VALID_RADII,
    VALID_SHADOWS,
    VALID_SIZES,
)


class _PropsMixin:
    """表格动态属性与 top/bottom content 装配 mixin。"""

    # ------------------------------------------------------------
    # 动态属性 setter
    # ------------------------------------------------------------
    def set_color(self, c: str):
        """设置语义色并刷新行与勾选框样式。

        Args:
            c: 目标语义色。

        Note:
            c 不在 VALID_COLORS 时直接返回，未做报错。
        """
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
        """设置尺寸档位并触发表格重建。

        Args:
            s: 目标尺寸档位。

        Note:
            s 不在 VALID_SIZES 时直接返回，未做报错。
        """
        if s not in VALID_SIZES:
            return
        self._size = s
        self._rebuild()

    def set_radius(self, r: str):
        """设置圆角档位并同步 Card 与行样式。

        Args:
            r: 目标圆角档位。

        Note:
            r 不在 VALID_RADII 时直接返回，未做报错。
        """
        if r not in VALID_RADII:
            return
        self._radius = r
        if self._card is not None:
            self._card.set_radius(self._card_radius())
        self._propagate_style()
        self.update()

    def set_shadow(self, s: str):
        """设置阴影档位并同步 Card。

        Args:
            s: 目标阴影档位。

        Note:
            s 不在 VALID_SHADOWS 时直接返回，未做报错。
        """
        if s not in VALID_SHADOWS:
            return
        self._shadow = s
        if self._card is not None:
            self._card.set_shadow(s)
        self.update()

    def set_is_striped(self, v: bool):
        """设置斑马纹开关并刷新行状态。

        Args:
            v: 是否启用斑马纹。
        """
        self._is_striped = bool(v)
        self._propagate_style()
        self._apply_row_states(animated=False)

    def set_is_compact(self, v: bool):
        """设置紧凑模式开关并刷新样式。

        Args:
            v: 是否启用紧凑模式。
        """
        self._is_compact = bool(v)
        self._propagate_style()

    def set_hide_header(self, v: bool):
        """设置表头隐藏开关并刷新样式。

        Args:
            v: 是否隐藏表头。
        """
        self._hide_header = bool(v)
        self._propagate_style()

    def set_disallow_empty_selection(self, v: bool):
        """设置是否禁止空选。

        Args:
            v: 是否禁止空选。
        """
        self._disallow_empty_selection = bool(v)

    # ------------------------------------------------------------
    # top / bottom content
    # ------------------------------------------------------------
    def set_top_content(self, w: QWidget | None):
        """替换顶部内容 widget。

        Args:
            w: 新的顶部内容，None 表示清空。

        Note:
            旧内容经 safe_delete 删除；按 _top_placement 插到外层或内层布局。
        """
        if self._top_content is not None:
            safe_delete(self._top_content)
            self._top_content = None
        if w is not None:
            self._top_content = w
            if self._top_placement == "outside":
                self._outer.insertWidget(0, w)
            else:
                self._inside_v.insertWidget(0, w)

    def set_bottom_content(self, w: QWidget | None):
        """替换底部内容 widget。

        Args:
            w: 新的底部内容，None 表示清空。

        Note:
            旧内容经 safe_delete 删除；按 _bottom_placement 插到外层或内层布局。
        """
        if self._bottom_content is not None:
            safe_delete(self._bottom_content)
            self._bottom_content = None
        if w is not None:
            self._bottom_content = w
            if self._bottom_placement == "outside":
                self._outer.addWidget(w)
            else:
                self._inside_v.addWidget(w)
