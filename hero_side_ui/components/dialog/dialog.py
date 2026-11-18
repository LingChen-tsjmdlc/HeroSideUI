"""Dialog 对话框：带结果码的模态子 Window。

桌面端专属组件（HeroUI v2 无对应项），API 见 docs/dialog.md。
外壳（标题栏、圆角、阴影、风格）全部来自 Window；Dialog 只加结果码、
默认模态与固定宽度、自动高度、九宫格定位、按钮区和对父窗口的遮罩。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractButton, QVBoxLayout, QWidget

from ...themes import (
    DIALOG_SPEC,
    VALID_DIALOG_BACKDROPS,
    VALID_DIALOG_BUTTON_ORDERS,
    VALID_DIALOG_COLORS,
    VALID_DIALOG_FOOTER_ALIGNS,
    VALID_DIALOG_MODALITIES,
    VALID_DIALOG_PLACEMENTS,
    VALID_DIALOG_STAY_ON_TOP,
)
from ...utils import safe_delete
from ..scroll_shadow import ScrollShadow
from ..window import Window
from ..window._config import check_bool, check_int
from ._body import _Body, default_icon_color
from ._footer import ACCEPTED, REJECTED, _Footer
from ._geometry import _GeometryMixin
from ._quick import _QuickMixin
from ._result import _ResultMixin
from ._shade import _Shade

_MODALITY = {
    "window": Qt.WindowModality.WindowModal,
    "application": Qt.WindowModality.ApplicationModal,
    "none": Qt.WindowModality.NonModal,
}
_VALID_THEMES = ("auto", "light", "dark")


def _choice(name: str, value, valid: tuple):
    """取值必须在 valid 里（不允许 None）。"""
    if value not in valid:
        raise ValueError(f"{name} must be one of {valid}, got {value!r}")


def _flag(name: str, value):
    """必须是 bool。"""
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool, got {value!r}")


def _offset(value) -> tuple[int, int]:
    """placement_offset 必须是两个整数（bool 不算）。"""
    ok = (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    )
    if not ok:
        raise ValueError(f"placement_offset must be (int, int), got {value!r}")
    return int(value[0]), int(value[1])


class Dialog(_QuickMixin, _ResultMixin, _GeometryMixin, Window):
    """模态对话框。API/示例见 ``docs/dialog.md``。

    Attributes:
        finished: 每次关闭都发，参数是结果码。
        accepted: 结果码为 1 时发。
        rejected: 结果码为 0 时发。
    """

    Rejected = REJECTED
    Accepted = ACCEPTED

    finished = Signal(int)
    accepted = Signal()
    rejected = Signal()

    def __init__(
        self,
        *,
        title: str = "",
        heading: str | None = None,
        message: str | None = None,
        icon: str | QWidget | None = "info",
        color: str | None = None,
        icon_size: int = DIALOG_SPEC["icon_size"],
        message_selectable: bool = True,
        width: int = DIALOG_SPEC["default_width"],
        height: int | None = None,
        min_width: int | None = None,
        min_height: int | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
        resizable: bool = False,
        placement: str = "center",
        placement_offset: tuple[int, int] = (0, 0),
        modality: str = "window",
        backdrop: str = "none",
        stay_on_top: str = "system",
        footer_align: str = "end",
        button_order: str = "auto",
        dismiss_on_escape: bool = False,
        show_minimize: bool = False,
        show_maximize: bool = False,
        show_close: bool = True,
        system: str | None = None,
        radius: str | float | None = "system",
        title_bar_height: int | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建对话框（创建后不显示，用 exec() 或 open() 打开）。

        Args:
            title: 标题栏文字。
            heading: body 里的小标题（次要色）。
            message: body 里的正文；heading 与 message 都没有则 body 为空，自己 set_body。
            icon: info / success / warning / danger / question、内置图标名、自己的 QWidget，
                None 不显示。
            color: 图标与主按钮的语义色；None 跟随图标。
            icon_size: 图标边长 px。
            message_selectable: 正文能否选中复制。
            width: 固定宽度。
            height: None 按内容自动算高；数字则固定为该高度。
            min_width: 最小宽度，规则同 Window。
            min_height: 最小高度，规则同 Window。
            max_width: 最大宽度。
            max_height: 最大高度；自动高度的上限，没传取屏幕可用高度的 80%。
            resizable: 能否拖边缘缩放。
            placement: 九宫格位置，相对父窗口，无父窗口相对屏幕。
            placement_offset: 九宫格位置上再偏移的 (dx, dy) px。
            modality: window 只挡父窗口 / application 挡整个程序 / none 不挡。
            backdrop: 对父窗口的处理：none / dim 压暗 / blur 模糊。
            stay_on_top: none / parent / system 系统级置顶。
            footer_align: start / center / end / stretch。
            button_order: auto 跟随风格 / ok_first / cancel_first。
            dismiss_on_escape: 按 Esc 是否等于取消。
            show_minimize: 显示最小化按钮。
            show_maximize: 显示最大化按钮。
            show_close: 显示关闭按钮，关闭视为取消。
            system: 同 Window。
            radius: 同 Window。
            title_bar_height: 同 Window。
            theme: auto / light / dark。
            parent: 父窗口；传了才有遮罩、相对父窗口定位和模态。

        Raises:
            ValueError: 任一参数取值非法。
        """
        if color is not None:
            _choice("color", color, VALID_DIALOG_COLORS)
        check_int("icon_size", icon_size)
        check_int("height", height)
        _flag("message_selectable", message_selectable)
        _flag("dismiss_on_escape", dismiss_on_escape)
        _choice("placement", placement, VALID_DIALOG_PLACEMENTS)
        _choice("modality", modality, VALID_DIALOG_MODALITIES)
        _choice("backdrop", backdrop, VALID_DIALOG_BACKDROPS)
        _choice("stay_on_top", stay_on_top, VALID_DIALOG_STAY_ON_TOP)
        _choice("footer_align", footer_align, VALID_DIALOG_FOOTER_ALIGNS)
        _choice("button_order", button_order, VALID_DIALOG_BUTTON_ORDERS)
        _choice("theme", theme, _VALID_THEMES)
        for name, v in (
            ("resizable", resizable),
            ("show_minimize", show_minimize),
            ("show_maximize", show_maximize),
            ("show_close", show_close),
        ):
            check_bool(name, v)

        self._active = False
        self._reshowing = False
        self._result = REJECTED
        self._result_data = None
        self._data_provider = None
        self._fixed_height = None if height is None else int(height)
        self._placement = placement
        self._placement_offset = _offset(placement_offset)
        self._modality = modality
        self._backdrop_kind = backdrop
        self._stay_on_top = stay_on_top
        self._dismiss_on_escape = dismiss_on_escape
        self._icon = icon
        self._color = color
        self._default_button: QAbstractButton | None = None
        self._custom_body: QWidget | None = None
        self._shade = _Shade()

        super().__init__(
            system=system,
            radius=radius,
            title_bar_height=title_bar_height,
            show_minimize=show_minimize,
            show_maximize=show_maximize,
            show_close=show_close,
            resizable=resizable,
            width=width,
            height=self._fixed_height or 240,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height,
            theme=theme,
            parent=parent,
        )
        self.setWindowTitle(title)
        self._build(theme, heading, message, message_selectable, icon_size)
        self._footer.configure(
            align=footer_align,
            order=button_order,
            color=self._accent(),
            theme=theme,
        )
        shade = self._shade
        self.destroyed.connect(lambda *_: shade.clear())
        self._apply_height()

    def _build(self, theme: str, heading, message, selectable: bool, icon_size: int):
        """搭内容：可滚动的 body（内置内容或自定义控件）+ 底部按钮区。"""
        self._body = _Body(theme=theme, selectable=selectable, icon_size=icon_size)
        self._body.set_heading(heading)
        self._body.set_message(message)
        self._body.set_icon(self._icon, self._accent())

        self._scroll = ScrollShadow(theme=theme)
        self._scroll.layout().setContentsMargins(
            DIALOG_SPEC["padding_x"],
            DIALOG_SPEC["padding_top"],
            DIALOG_SPEC["padding_x"],
            DIALOG_SPEC["padding_bottom"],
        )
        self._scroll.add_widget(self._body)
        # 必须先挂到父级再改显隐：无父控件上的 setHidden(False) 会把它显示成顶层窗口
        self._body.setHidden(self._body.is_empty())
        self._scroll.add_stretch(1)

        self._footer = _Footer()
        self._footer.activated.connect(self._on_footer_activated)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._scroll, 1)
        lay.addWidget(self._footer)
        self.set_content(root)

    def current_bg_color(self) -> QColor:
        """窗口底色；ScrollShadow 的边缘渐隐靠它与窗口底色衔接。"""
        return self._colors.background

    # ============================================================
    # 内容
    # ============================================================
    def _accent(self) -> str:
        """图标与主按钮的语义色：显式指定的，否则跟随图标。"""
        return self._color or default_icon_color(self._icon)

    def _body_target(self) -> QWidget | None:
        """当前参与高度计算的 body；内置内容为空时返回 None。"""
        if self._custom_body is not None:
            return self._custom_body
        return None if self._body.is_empty() else self._body

    def _sync_content(self):
        """内容变化后：同步内置内容的显隐并重算高度。"""
        self._body.setHidden(self._custom_body is not None or self._body.is_empty())
        self._apply_height()

    def set_title(self, title: str):
        """设置标题栏文字，等同 setWindowTitle。"""
        self.setWindowTitle(title)

    def set_heading(self, text: str | None):
        """设置小标题；None 或空字符串隐藏。"""
        self._body.set_heading(text)
        self._sync_content()

    def set_message(self, text: str | None):
        """设置正文；None 或空字符串隐藏。"""
        self._body.set_message(text)
        self._sync_content()

    def set_icon(self, icon: str | QWidget | None):
        """设置图标，写法同构造参数；颜色没显式指定时跟随新图标。"""
        self._icon = icon
        self._refresh_accent()

    def icon(self) -> str | QWidget | None:
        """当前图标设置。"""
        return self._icon

    def set_color(self, color: str | None):
        """设置图标与主按钮的语义色；None 跟随图标。

        Raises:
            ValueError: 不是合法语义色。
        """
        if color is not None:
            _choice("color", color, VALID_DIALOG_COLORS)
        self._color = color
        self._refresh_accent()

    def color(self) -> str | None:
        """显式指定的语义色，None 表示跟随图标。"""
        return self._color

    def _refresh_accent(self):
        """图标或语义色变化后，刷新图标与主按钮。"""
        self._body.set_icon(self._icon, self._accent())
        self._footer.configure(color=self._accent())
        self._sync_content()

    def set_icon_size(self, size: int):
        """图标边长 px。"""
        check_int("icon_size", size)
        self._body.set_icon_size(int(size))
        self._sync_content()

    def set_message_selectable(self, value: bool):
        """正文能否选中复制。"""
        _flag("message_selectable", value)
        self._body.set_selectable(value)

    def set_body(self, widget: QWidget | None):
        """用自己的控件替换内置内容，旧控件由对话框销毁。

        Args:
            widget: 新内容；None 恢复内置的图标 + 小标题 + 正文。
        """
        old = self._custom_body
        if old is not None and old is not widget:
            safe_delete(old)
        self._custom_body = widget
        if widget is not None:
            self._scroll.insert_widget(0, widget)
            widget.show()
        self._sync_content()

    def body_widget(self) -> QWidget:
        """当前内容：自定义控件，没有则是内置内容。"""
        return self._custom_body if self._custom_body is not None else self._body

    # ============================================================
    # 按钮区
    # ============================================================
    def set_footer(self, buttons: list):
        """替换整个按钮区，旧按钮由对话框销毁。

        Args:
            buttons: 按钮规格列表：Button / (文字或 Button, 角色) / (文字或 Button, 角色, 数据)；
                角色为 accept / reject / none / 任意整数。

        Raises:
            ValueError: 写法或角色非法。
        """
        self._footer.set_items(buttons)
        self._sync_content()

    def add_button(self, button: str | QAbstractButton, role="none", data=None) -> QAbstractButton:
        """追加一个按钮。

        Args:
            button: 文字（对话框创建按钮）或自己的按钮。
            role: accept / reject / none / 任意整数。
            data: 点击时附带的结果数据。

        Returns:
            加入的按钮。
        """
        btn = self._footer.add_item(button, role, data)
        self._sync_content()
        return btn

    def buttons(self) -> list[QAbstractButton]:
        """按钮区的全部按钮（创建顺序）。"""
        return self._footer.buttons()

    def set_default_button(self, button: QAbstractButton | None):
        """指定 Enter 触发的按钮；None 恢复默认（第一个 reject 角色的按钮）。"""
        self._default_button = button

    def set_footer_align(self, align: str):
        """按钮对齐：start / center / end / stretch。"""
        _choice("footer_align", align, VALID_DIALOG_FOOTER_ALIGNS)
        self._footer.configure(align=align)

    def set_button_order(self, order: str):
        """按钮顺序：auto / ok_first / cancel_first。"""
        _choice("button_order", order, VALID_DIALOG_BUTTON_ORDERS)
        self._footer.configure(order=order)

    def _on_footer_activated(self, code: int, data):
        """带结果码的按钮被点击：以它的结果码关闭。"""
        self.done(code, data)

    # ============================================================
    # 位置、模态、遮罩、置顶
    # ============================================================
    def set_placement(self, placement: str):
        """九宫格位置；已显示时立即重新定位。"""
        _choice("placement", placement, VALID_DIALOG_PLACEMENTS)
        self._placement = placement
        if self.isVisible():
            self._reposition()

    def placement(self) -> str:
        """当前九宫格位置。"""
        return self._placement

    def set_placement_offset(self, offset: tuple[int, int]):
        """九宫格位置上再偏移的 (dx, dy)；已显示时立即重新定位。"""
        self._placement_offset = _offset(offset)
        if self.isVisible():
            self._reposition()

    def set_modality(self, modality: str):
        """window / application / none；已显示时会重新显示一次让它生效。"""
        _choice("modality", modality, VALID_DIALOG_MODALITIES)
        self._modality = modality
        self._reshow()

    def modality(self) -> str:
        """当前模态方式。"""
        return self._modality

    def set_backdrop(self, backdrop: str):
        """对父窗口的处理：none / dim / blur；已显示时立即切换。"""
        _choice("backdrop", backdrop, VALID_DIALOG_BACKDROPS)
        self._backdrop_kind = backdrop
        if self._active:
            self._sync_shade()

    def backdrop(self) -> str:
        """当前遮罩方式。"""
        return self._backdrop_kind

    def set_stay_on_top(self, value: str):
        """none / parent / system；已显示时会重新显示一次让它生效。"""
        _choice("stay_on_top", value, VALID_DIALOG_STAY_ON_TOP)
        self._stay_on_top = value
        self._reshow()

    def stay_on_top(self) -> str:
        """当前置顶方式。"""
        return self._stay_on_top

    def set_dismiss_on_escape(self, value: bool):
        """按 Esc 是否等于取消。"""
        _flag("dismiss_on_escape", value)
        self._dismiss_on_escape = value

    def dismiss_on_escape(self) -> bool:
        """按 Esc 是否等于取消。"""
        return self._dismiss_on_escape

    def _apply_modality(self):
        """把模态方式交给 Qt；必须在显示之前设置才生效。"""
        self.setWindowModality(_MODALITY[self._modality])

    def _apply_stay_on_top(self):
        """system 时打开 Qt 的置顶标志；none / parent 靠父窗口从属关系，不额外置顶。"""
        want = self._stay_on_top == "system"
        hint = Qt.WindowType.WindowStaysOnTopHint
        if bool(self.windowFlags() & hint) != want:
            self.setWindowFlag(hint, want)

    def _sync_shade(self):
        """按当前遮罩设置重建父窗口上的遮罩；没有父窗口或不模态时清掉。"""
        host = self._host()
        usable = host is not None and host.isVisible() and not host.isMinimized()
        if usable and self._modality != "none":
            self._shade.show(host, self._backdrop_kind)
        else:
            self._shade.clear()

    def _reshow(self):
        """已显示时隐藏再显示，让模态与置顶的改动生效，位置保持不变。"""
        if not self.isVisible():
            return
        pos = self.pos()
        self._reshowing = True
        try:
            self._apply_modality()
            self._apply_stay_on_top()
            self.hide()
            self.move(pos)
            self.show()
        finally:
            self._reshowing = False
        self.activateWindow()

    # ============================================================
    # 打开与关闭
    # ============================================================
    def _begin(self):
        """显示之前：重置结果、套用模态与置顶、算高度与位置、建遮罩。"""
        self._active = True
        self._result = REJECTED
        self._result_data = None
        self._apply_modality()
        self._apply_stay_on_top()
        self._apply_height()
        self._reposition()
        self._sync_shade()

    def _on_done(self):
        """关闭时：遮罩淡出并隐藏窗口。"""
        self._shade.fade_out()
        self.hide()

    def setVisible(self, visible: bool):
        """显示时先 _begin（show / open / exec 都走这里，结果状态一致）。"""
        if visible and not self._active and not self._reshowing and not self.isVisible():
            self._begin()
        super().setVisible(visible)
        if visible and self._active and not self._reshowing:
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        """标题栏关闭按钮、close() 都视为取消。"""
        if self._active:
            self.done(REJECTED)
        super().closeEvent(event)

    def hideEvent(self, event):
        """被代码 hide() 也视为取消；系统最小化等自发隐藏不算。"""
        super().hideEvent(event)
        if self._active and not self._reshowing and not event.spontaneous():
            self.reject()

    def keyPressEvent(self, event):
        """Esc 取消（dismiss_on_escape 时）；Enter 触发默认按钮。"""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self._dismiss_on_escape:
                self.reject()
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            btn = self._footer.default_button(self._default_button)
            if btn is not None and btn.isEnabled():
                btn.click()
                event.accept()
                return
        super().keyPressEvent(event)

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        """设置主题，并同步内部的文字、按钮与滚动区。

        Args:
            theme: auto 跟随全局，或固定 light / dark。

        Raises:
            ValueError: 取值非法。
        """
        super().set_theme(theme)
        self._body.set_theme(theme)
        self._footer.configure(theme=theme)
        self._scroll.set_theme(theme)


__all__ = ["Dialog"]
