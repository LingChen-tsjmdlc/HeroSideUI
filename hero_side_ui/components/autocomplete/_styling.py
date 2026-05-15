"""Autocomplete 内部"视觉同步" mixin（私有）。

负责：
- 末尾按钮（clear / arrow）尺寸根据 size 刷新
- 末尾按钮 icon 颜色根据 theme 刷新
- clear 按钮显隐根据 hover/value 状态计算
- enter/leave 事件下的 hover 状态切换
"""

from ...themes import AUTOCOMPLETE_SIZES

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS, INPUT_SIZES
from ...utils import load_svg_icon


class _AutocompleteStylingMixin:
    """Autocomplete 视觉同步 mixin。"""

    # ============================================================
    # 内部：图标/尺寸刷新
    # ============================================================
    def _refresh_end_btn_sizes(self):
        cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
        size = cfg["end_btn_size"]
        # clear_btn 是 Button 组件:用 set_icon_only_side(持久化 override),
        # 不能直接 setFixedSize —— Button._apply_styles 在主题切换时会被 ThemeProvider
        # 触发,把 setFixedSize 重新设回 BUTTON_SIZES 算的 30/... px。
        self._end.clear_btn.set_icon_only_side(size)
        self._end.selector_btn.setFixedSize(size, size)
        self._end._h.setSpacing(cfg["end_gap"])

    def _refresh_end_icons(self):
        cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])

        # Clear 按钮:用 Button 组件的高层 API —— 只传 icon name + size,
        # 颜色完全交给 Button 内部(light variant + default color 会渲染成柔和灰,
        # hover 时也会自动出 light hover bg)。铁律 3「高层意图 API」落地。
        self._end.clear_btn.set_icon(self._clear_icon)
        self._end.clear_btn.set_icon_size(cfg["clear_icon_size"])

        # Selector chevron 颜色策略(对齐用户要求点 4):
        # - color == "default" → 用 default-500(灰)
        # - color != "default" → 用对应 palette 的 500 色,与组件主色呼应
        if self._color != "default":
            sel_color = QColor(HEROUI_COLORS[self._color][500])
        else:
            sel_color = QColor(HEROUI_COLORS["default"][500])

        sel_pix = load_svg_icon(
            self._selector_icon,
            size=cfg["selector_icon_size"],
            color=sel_color,
            stroke_width=2.5,
        )
        self._end.selector_btn.set_pixmap(sel_pix)

    def _refresh_clear_visibility(self):
        has_value = bool(self._input_value) or self._selected_key is not None
        # 显示规则(对齐 HeroUI):
        #   1. is_clearable 开
        #   2. 有值
        #   3. 非 disabled / 非 readonly
        #   4. 容器被 hover **或** 当前已聚焦(focus 时也保留 clear,方便键盘流操作)
        # focus 时保留:用户可能用 Tab 切到这个 input,没移鼠标,不该突然失去 clear
        is_focused = self._input.line_edit.hasFocus() or self._is_open
        show = (
            self._is_clearable
            and has_value
            and not self._is_disabled
            and not self._input._is_readonly
            and (self._is_hovered or is_focused)
        )
        self._end.clear_btn.setVisible(show)

    # ============================================================
    # Hover 跟踪 —— 决定 clear 按钮显隐
    # ============================================================
    def enterEvent(self, event):
        self._is_hovered = True
        self._refresh_clear_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._refresh_clear_visibility()
        super().leaveEvent(event)

