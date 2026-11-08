"""_DateSegment 可聚焦日期段：接收键盘/滚轮编辑并上报宿主。
焦点底色走 QSS + WA_StyledBackground，防 Fusion 画黑底。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget

from ..text import Text

# 段类型 → 是否接受数字键输入
_NUMERIC_TYPES = frozenset({"year", "month", "day", "hour", "minute", "second"})


class _DateSegment(Text):
    """可编辑的日期段。

    Args:
        seg_type: 段类型（year/month/day/hour/...）。
        min_digits: pattern 位数，决定占位宽度。
        on_edit: 值被改动后的回调。
        on_focus_move: 请求焦点移到相邻段（+1/-1）。
        on_focus_change: 段获得/失去焦点回调。
    """

    def __init__(
        self,
        seg_type: str,
        *,
        min_digits: int = 1,
        on_edit: Callable[[str, str, object], None] | None = None,
        on_focus_move: Callable[[int], None] | None = None,
        on_focus_change: Callable[[str, bool], None] | None = None,
        parent: QWidget | None = None,
    ):
        """创建可编辑日期段。

        Args:
            seg_type: 段类型（year/month/day/hour/...）。
            min_digits: pattern 位数，决定占位宽度。
            on_edit: 值被改动后的回调 fn(seg_type, action, payload)。
            on_focus_move: 请求焦点移到相邻段 fn(+1/-1)。
            on_focus_change: 段获得 / 失去焦点回调 fn(seg_type, focused)。
            parent: Qt 父对象。

        Note:
            theme 固定为 light（非 auto）才不会注册进 ThemeProvider——
            段的颜色由宿主按 variant/color/焦点态统一决策，若让 Text
            保留主题自治，广播时 _apply_color 会用 setStyleSheet 整体
            覆盖，冲掉宿主字色与 padding / border-radius。
        """
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
        """段类型。

        Returns:
            如 year / month / day / hour 等。
        """
        return self._seg_type

    @property
    def min_digits(self) -> int:
        """段的最少显示位数。

        Returns:
            pattern 解析出的位数。
        """
        return self._min_digits

    def set_editable(self, editable: bool) -> None:
        """设置该段是否可聚焦可编辑（字面量段传 False）。

        Args:
            editable: True 时 StrongFocus + IBeam 光标；False 时 NoFocus + 箭头。
        """
        self._editable = editable
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if editable else Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor if editable else Qt.CursorShape.ArrowCursor)

    def set_readonly(self, readonly: bool) -> None:
        """切换只读态（仍可聚焦但键盘编辑被拦截）。

        Args:
            readonly: True 表示只读。
        """
        self._readonly = readonly

    # ============================================================
    # 视觉
    # ============================================================
    def apply_visual(
        self,
        *,
        text_color: QColor,
        focus_bg: QColor | None,
        radius_px: int,
        padding_x: int,
        focused: bool,
    ) -> None:
        """套用段字色与焦点底色。

        Args:
            text_color: 当前状态字色。
            focus_bg: 焦点底色；None 或 alpha=0 时用透明。
            radius_px: 段高亮圆角。
            padding_x: 左右内边距。
            focused: 是否为焦点段。

        Note:
            用 QColor 分量拼 QSS，不直接喂 rgba 字符串。
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
        """获得焦点：上报宿主刷新视觉。

        Args:
            event: Qt 焦点事件。
        """
        super().focusInEvent(event)
        if self._on_focus_change:
            self._on_focus_change(self._seg_type, True)

    def focusOutEvent(self, event):
        """失去焦点：上报宿主刷新视觉。

        Args:
            event: Qt 焦点事件。
        """
        super().focusOutEvent(event)
        if self._on_focus_change:
            self._on_focus_change(self._seg_type, False)

    def mousePressEvent(self, event):
        """鼠标点击：可编辑段请求焦点。

        Args:
            event: Qt 鼠标按下事件。
        """
        if self._editable:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        event.accept()

    # ============================================================
    # 键盘 / 滚轮
    # ============================================================
    def keyPressEvent(self, event):
        """键盘编辑：上下增减、删除清空、左右跳段、数字逐位输入、a/p 切 AM/PM。

        Args:
            event: Qt 键盘事件。

        Note:
            不可编辑或只读时交回父类；dayPeriod 段只接受 a/p 快捷键。
        """
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
        """滚轮编辑：仅在持有焦点时按滚动方向增减段值。

        Args:
            event: Qt 滚轮事件。
        """
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
        """把编辑动作上报宿主。

        Args:
            action: increment / clear / digit / day_period。
            payload: 动作参数（步长、数字、AM/PM 值或 None）。
        """
        if self._on_edit:
            self._on_edit(self._seg_type, action, payload)

    def _move_focus(self, direction: int) -> None:
        """请求焦点移到相邻段。

        Args:
            direction: +1 下一段、-1 上一段。
        """
        if self._on_focus_move:
            self._on_focus_move(direction)


class _SegmentLiteral(Text):
    """段之间的字面量分隔符（"/"、":"、", "）。不可聚焦、不响应鼠标。"""

    def __init__(self, text: str, parent: QWidget | None = None):
        """创建字面量分隔符。

        Args:
            text: 分隔符文本。
            parent: Qt 父对象。

        Note:
            同 _DateSegment：退出 Text 的主题自治，颜色由宿主统一决策。
        """
        # 同 _DateSegment：退出 Text 的主题自治，颜色由宿主统一决策。
        super().__init__(text, selectable=False, theme="light", parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def apply_visual(self, *, text_color: QColor) -> None:
        """套用分隔符字色（背景恒透明、无内边距）。

        Args:
            text_color: 当前状态字色。
        """
        self.setStyleSheet(
            "QLabel { background-color: transparent; padding: 0; color: rgba("
            f"{text_color.red()}, {text_color.green()}, {text_color.blue()}, "
            f"{text_color.alphaF():.4f}); }}"
        )


__all__ = ["_DateSegment", "_SegmentLiteral"]
