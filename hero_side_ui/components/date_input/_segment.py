"""_DateSegment — 单个可聚焦的日期段（私有）。

一个段就是一个可获得焦点的 Text：接收数字键逐位输入、上下键增减、
Backspace/Delete 清空、滚轮增减，并把变化上报给宿主 DateInput。

段的焦点底色一律走 QSS（配合 WA_StyledBackground=True），不用 paintEvent
自绘——QLabel 的 super().paintEvent 会把 QPalette.Window 画上去，Fusion 下透黑底。
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from ..text import Text

# 段类型 → 是否接受数字键输入
_NUMERIC_TYPES = frozenset({"year", "month", "day", "hour", "minute", "second"})


class _DateSegment(Text):
    """可编辑的日期段。

    :param seg_type: 段类型（year/month/day/hour/...）
    :param min_digits: pattern 中该字段的位数，决定占位符宽度
    :param on_edit: 段值被键盘改动后的回调，用于宿主重算文本与发信号
    :param on_focus_move: 请求把焦点移到相邻段的回调，参数为 +1 / -1
    :param on_focus_change: 段获得/失去焦点的回调
    """

    def __init__(
        self,
        seg_type: str,
        *,
        min_digits: int = 1,
        on_edit: Optional[Callable[[str, str, object], None]] = None,
        on_focus_move: Optional[Callable[[int], None]] = None,
        on_focus_change: Optional[Callable[[str, bool], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        # theme 非 "auto" 才不会注册进 ThemeProvider。段的颜色由宿主 DateInput
        # 按 variant/color/焦点态统一决策，若让 Text 保留主题自治，主题广播时
        # Text._apply_color() 会 setStyleSheet 整体覆盖，把宿主设的字色冲成
        # 默认前景色（暗色下即白字），并连带丢掉 padding / border-radius。
        super().__init__("", selectable=False, theme="light", parent=parent)

        self._seg_type = seg_type
        self._min_digits = min_digits
        self._on_edit = on_edit
        self._on_focus_move = on_focus_move
        self._on_focus_change = on_focus_change
        self._editable = True
        self._readonly = False

        # QSS 背景生效的前提：QLabel 默认 WA_StyledBackground=False，
        # 不开这个属性 setStyleSheet 的 background-color 不会被绘制。
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    # ============================================================
    # 结构信息
    # ============================================================
    @property
    def seg_type(self) -> str:
        return self._seg_type

    @property
    def min_digits(self) -> int:
        return self._min_digits

    def set_editable(self, editable: bool) -> None:
        """字面量段不可聚焦，走这里关掉焦点与光标。"""
        self._editable = editable
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus if editable else Qt.FocusPolicy.NoFocus
        )
        self.setCursor(
            Qt.CursorShape.IBeamCursor if editable else Qt.CursorShape.ArrowCursor
        )

    def set_readonly(self, readonly: bool) -> None:
        self._readonly = readonly

    # ============================================================
    # 视觉
    # ============================================================
    def apply_visual(
        self,
        *,
        text_color: QColor,
        focus_bg: Optional[QColor],
        radius_px: int,
        padding_x: int,
        focused: bool,
    ) -> None:
        """套用段的字色与焦点底色。

        颜色一律用 QColor 直接构造再取 rgba 分量拼 QSS —— 不把
        hex_to_rgba() 的 "rgba(...)" 字符串喂给 QColor（Qt 不解析，会得黑色）。
        """
        parts = [
            f"color: rgba({text_color.red()}, {text_color.green()}, "
            f"{text_color.blue()}, {text_color.alphaF():.4f})",
            f"padding-left: {padding_x}px",
            f"padding-right: {padding_x}px",
            f"border-radius: {radius_px}px",
        ]
        if focused and focus_bg is not None and focus_bg.alpha() > 0:
            parts.append(
                f"background-color: rgba({focus_bg.red()}, {focus_bg.green()}, "
                f"{focus_bg.blue()}, {focus_bg.alphaF():.4f})"
            )
        else:
            parts.append("background-color: transparent")
        self.setStyleSheet("QLabel {" + "; ".join(parts) + ";}")

    # ============================================================
    # 焦点
    # ============================================================
    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self._on_focus_change:
            self._on_focus_change(self._seg_type, True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._on_focus_change:
            self._on_focus_change(self._seg_type, False)

    def mousePressEvent(self, event):
        if self._editable:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        event.accept()

    # ============================================================
    # 键盘 / 滚轮
    # ============================================================
    def keyPressEvent(self, event):
        if not self._editable or self._readonly:
            super().keyPressEvent(event)
            return

        key = event.key()

        if key == Qt.Key.Key_Up:
            self._emit_edit("increment", 1)
            event.accept()
            return
        if key == Qt.Key.Key_Down:
            self._emit_edit("increment", -1)
            event.accept()
            return
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._emit_edit("clear", None)
            event.accept()
            return
        if key == Qt.Key.Key_Left:
            self._move_focus(-1)
            event.accept()
            return
        if key == Qt.Key.Key_Right:
            self._move_focus(1)
            event.accept()
            return

        text = event.text()

        # 数字键：逐位输入
        if text.isdigit() and self._seg_type in _NUMERIC_TYPES:
            self._emit_edit("digit", int(text))
            event.accept()
            return

        # a/p 快捷切 AM/PM（对齐 react-aria）
        if self._seg_type == "dayPeriod" and text.lower() in ("a", "p"):
            self._emit_edit("day_period", 0 if text.lower() == "a" else 1)
            event.accept()
            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if not self._editable or self._readonly or not self.hasFocus():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta:
            self._emit_edit("increment", 1 if delta > 0 else -1)
        event.accept()

    # ============================================================
    # 上报
    # ============================================================
    def _emit_edit(self, action: str, payload) -> None:
        if self._on_edit:
            self._on_edit(self._seg_type, action, payload)

    def _move_focus(self, direction: int) -> None:
        if self._on_focus_move:
            self._on_focus_move(direction)


class _SegmentLiteral(Text):
    """段之间的字面量分隔符（"/"、":"、", "）。不可聚焦、不响应鼠标。"""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        # 同 _DateSegment：退出 Text 的主题自治，颜色由宿主统一决策。
        super().__init__(text, selectable=False, theme="light", parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def apply_visual(self, *, text_color: QColor) -> None:
        self.setStyleSheet(
            "QLabel { background-color: transparent; padding: 0; color: rgba("
            f"{text_color.red()}, {text_color.green()}, {text_color.blue()}, "
            f"{text_color.alphaF():.4f}); }}"
        )


__all__ = ["_DateSegment", "_SegmentLiteral"]
