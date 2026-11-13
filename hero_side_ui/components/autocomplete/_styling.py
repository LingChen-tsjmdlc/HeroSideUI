"""Autocomplete 视觉同步 mixin：末尾按钮尺寸/配色与 clear 显隐刷新。"""

from PySide6.QtGui import QColor

from ...themes import AUTOCOMPLETE_SIZES, HEROUI_COLORS
from ...utils import load_svg_icon


class _AutocompleteStylingMixin:
    """Autocomplete 视觉同步 mixin。"""

    # ============================================================
    # 内部：图标/尺寸刷新
    # ============================================================
    def _refresh_end_btn_sizes(self):
        """按当前尺寸档位同步末尾按钮尺寸与间距。

        Note:
            clear_btn 必须走 set_icon_only_side（持久化 override）而非
            setFixedSize —— 主题切换会触发 Button._apply_styles 把
            setFixedSize 重设回 BUTTON_SIZES 的默认值。
        """
        cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
        size = cfg["end_btn_size"]
        # clear_btn 是 Button 组件:用 set_icon_only_side(持久化 override),
        # 不能直接 setFixedSize —— Button._apply_styles 在主题切换时会被 ThemeProvider
        # 触发,把 setFixedSize 重新设回 BUTTON_SIZES 算的 30/... px。
        self._end.clear_btn.set_icon_only_side(size)
        self._end.selector_btn.setFixedSize(size, size)
        self._end._h.setSpacing(cfg["end_gap"])

    def _refresh_end_icons(self):
        """刷新 clear 图标与 selector chevron 的渲染。

        Note:
            clear 按钮只传 icon 名与尺寸，颜色由 Button 内部管理；
            selector 颜色策略：default 用 default-500 灰，其余用主色
            palette 的 500 色与组件呼应。
        """
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
        """按四条规则刷新 clear 按钮显隐。

        规则（对齐 HeroUI）：is_clearable 开、有值、非 disabled / readonly、
        且容器 hover 或持有焦点（键盘流 Tab 切入时 clear 不消失）。
        """
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
            and not self._input.is_readonly()
            and (self._is_hovered or is_focused)
        )
        self._end.clear_btn.setVisible(show)

    # ============================================================
    # Hover 跟踪 —— 决定 clear 按钮显隐
    # ============================================================
    def enterEvent(self, event):
        """鼠标进入：置 hover 位并刷新 clear 显隐。

        Args:
            event: Qt 进入事件。
        """
        self._is_hovered = True
        self._refresh_clear_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：清 hover 位并刷新 clear 显隐。

        Args:
            event: Qt 离开事件。
        """
        self._is_hovered = False
        self._refresh_clear_visibility()
        super().leaveEvent(event)
