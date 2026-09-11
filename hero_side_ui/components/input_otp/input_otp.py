"""HeroSideUI InputOtp — 验证码输入框 (HeroUI v2)。完整 API/示例见 docs/input_otp.md。

用法::

    otp = InputOtp(length=4, color="primary")
    otp.completed.connect(lambda v: print(v))
"""

from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import (
    INPUT_OTP_CARET_PERIOD_MS,
    INPUT_OTP_SIZES,
    VALID_INPUT_OTP_RADII,
    VALID_INPUT_OTP_SIZES,
    VALID_INPUT_OTP_TEXT_ALIGNS,
    VALID_INPUT_OTP_VARIANTS,
)
from ..text import Text
from ._styling import build_input_otp_styles
from .input_otp_segments import _SegmentRow


class InputOtp(QWidget):
    """HeroUI 风格验证码输入框：length 个等宽段 + helper 行。"""

    value_changed = Signal(str)  # 值变化（对齐官方 onValueChange）
    completed = Signal(str)      # 值填满 length 位时触发（对齐官方 onComplete）
    text_changed = Signal(str)   # 值变化（对齐官方 onChange 的可用子集）

    def __init__(
        self,
        length: int = 4,
        *,
        allowed_keys: str = "^[0-9]*$",
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str = "md",
        value: str = "",
        description: str = "",
        error_message: str = "",
        full_width: bool = False,
        is_required: bool = False,
        is_read_only: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        disable_animation: bool = False,
        auto_focus: bool = False,
        text_align: str = "center",
        type: str = "text",
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroInputOtp")

        self._length = max(1, int(length))
        self._allowed_keys = allowed_keys
        self._variant = variant if variant in VALID_INPUT_OTP_VARIANTS else "flat"
        self._color = color
        self._size = size if size in INPUT_OTP_SIZES else "md"
        self._radius = radius if radius in VALID_INPUT_OTP_RADII else "md"
        self._value = str(value)
        self._cursor = len(self._value)
        self._description = str(description)
        self._error_message = str(error_message)
        self._full_width = bool(full_width)
        self._is_required = bool(is_required)
        self._is_read_only = bool(is_read_only)
        self._is_disabled = bool(is_disabled)
        self._is_invalid = bool(is_invalid)
        self._disable_animation = bool(disable_animation)
        self._auto_focus = bool(auto_focus)
        self._text_align = text_align if text_align in VALID_INPUT_OTP_TEXT_ALIGNS else "center"
        self._type = type
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme
        self._completed_fired = False

        self._font = QFont()
        self._build_ui()
        self._apply_styles()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ---- build ----

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._row = _SegmentRow(self)
        self._row.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._row.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_row_size()
        lay.addWidget(self._row)

        helper_lay = QHBoxLayout()
        helper_lay.setContentsMargins(0, 0, 0, 0)
        helper_lay.setSpacing(0)
        self._helper_label = Text("", size=12, weight="light", theme=self._theme)
        self._helper_label.setVisible(False)
        helper_lay.addWidget(self._helper_label)
        helper_lay.addStretch()
        lay.addLayout(helper_lay)

        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _update_row_size(self):
        hint = self._row.row_size_hint()
        self._row.setFixedSize(hint)

    # ---- derived state ----

    def _size_token(self) -> dict:
        return INPUT_OTP_SIZES[self._size]

    def _caret_period(self) -> int:
        return INPUT_OTP_CARET_PERIOD_MS

    def _is_active_segment(self) -> bool:
        """活动段是否呈现 active 视觉：聚焦且非禁用（readonly 不缩放）。"""
        return (self._row.hasFocus() and not self._is_disabled
                and not self._is_read_only)

    def _segment_styles(self) -> dict:
        return build_input_otp_styles(
            self._variant, self._color, self._theme,
            self._is_invalid, self._is_read_only,
        )

    # ---- 值编辑 ----

    def _char_allowed(self, ch: str) -> bool:
        return bool(ch) and re.fullmatch(self._allowed_keys, ch) is not None

    def _insert_text(self, text: str) -> bool:
        """从光标处插入文本中所有合法字符（截断到 length），返回是否有变化。"""
        if self._is_disabled or self._is_read_only:
            return False
        allowed = "".join(ch for ch in text if self._char_allowed(ch))
        if not allowed:
            return False
        room = self._length - len(self._value)
        allowed = allowed[:room]
        if not allowed:
            return False
        pos = min(self._cursor, len(self._value))
        new_value = self._value[:pos] + allowed + self._value[pos:self._length]
        self._set_value(new_value)
        self._set_cursor(pos + len(allowed))
        return True

    def _backspace(self):
        if self._is_disabled or self._is_read_only or not self._value:
            if not self._value:
                self._move_cursor(-1)
            return
        pos = min(self._cursor, len(self._value))
        if pos == 0:
            return
        new_value = self._value[:pos - 1] + self._value[pos:]
        self._set_value(new_value)
        self._set_cursor(pos - 1)

    def _delete_at_cursor(self):
        if self._is_disabled or self._is_read_only:
            return
        pos = min(self._cursor, len(self._value))
        if pos >= len(self._value):
            return
        new_value = self._value[:pos] + self._value[pos + 1:]
        self._set_value(new_value)

    def _move_cursor(self, delta: int):
        self._set_cursor(self._cursor + delta)

    def _set_cursor(self, pos: int):
        self._cursor = max(0, min(pos, self._length))
        self._row.update()
        self._row.caret_moved.emit()

    def _set_value(self, value: str):
        value = value[:self._length]
        if value == self._value:
            return
        self._value = value
        self._update_row_size()
        self._sync_helper()
        self._row.update()
        self.value_changed.emit(self._value)
        self.text_changed.emit(self._value)
        if len(self._value) == self._length:
            if not self._completed_fired:
                self._completed_fired = True
            self.completed.emit(self._value)
        else:
            self._completed_fired = False

    # ---- helper 行 ----

    def _sync_helper(self):
        show_error = self._is_invalid and bool(self._error_message)
        if show_error:
            self._helper_label.setText(self._error_message)
            self._helper_label.set_color("#f31260")
            self._helper_label.setVisible(True)
        elif self._description:
            self._helper_label.setText(self._description)
            # 官方 description text-foreground-400
            self._helper_label.set_color("#a1a1aa" if self._theme == "dark" else "#71717a")
            self._helper_label.setVisible(True)
        else:
            self._helper_label.setVisible(False)

    def _sync_focus(self):
        self._row.update()

    # ---- 公共 API ----

    def value(self) -> str:
        return self._value

    def set_value(self, value: str):
        """外部设值：仅保留合法字符，截断到 length，光标移到末尾。"""
        allowed = "".join(ch for ch in str(value) if self._char_allowed(ch))
        self._value = ""
        self._set_value(allowed[:self._length])
        self._set_cursor(len(self._value))

    def set_length(self, length: int):
        """改变段数：值与光标截断到新长度。"""
        self._length = max(1, int(length))
        self._value = self._value[:self._length]
        self._set_cursor(min(self._cursor, self._length))
        self._update_row_size()
        self._sync_helper()
        self._row.update()

    def set_allowed_keys(self, pattern: str):
        self._allowed_keys = pattern

    def set_variant(self, variant: str):
        self._variant = variant if variant in VALID_INPUT_OTP_VARIANTS else "flat"
        self._row.update()

    def set_color(self, color: str):
        self._color = color
        self._row.update()
        self._sync_helper()

    def set_size(self, size: str):
        if size not in INPUT_OTP_SIZES:
            return
        self._size = size
        self._font = self._make_font()
        self._update_row_size()
        self._row.update()

    def set_radius(self, radius: str):
        self._radius = radius if radius in VALID_INPUT_OTP_RADII else "md"
        self._row.update()

    def set_description(self, description: str):
        self._description = str(description)
        self._sync_helper()

    def set_error_message(self, error_message: str):
        self._error_message = str(error_message)
        self._sync_helper()

    def set_text_align(self, align: str):
        self._text_align = align if align in VALID_INPUT_OTP_TEXT_ALIGNS else "center"
        self._row.update()

    def set_type(self, type: str):
        self._type = type
        self._row.update()

    def set_read_only(self, read_only: bool):
        self._is_read_only = bool(read_only)
        self._row.update()

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self._row.setEnabled(not self._is_disabled)
        self._row.update()

    def set_invalid(self, invalid: bool):
        self._is_invalid = bool(invalid)
        self._sync_helper()
        self._row.update()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = bool(disable)
        self._row.update()

    def focus_input(self):
        """编程式聚焦（对齐官方 autoFocus 行为）。"""
        self._row.setFocus()

    # ---- theme ----

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._helper_label.set_theme(self._theme)
        self._sync_helper()
        self._row.update()

    def _apply_provider_theme(self, theme: str):
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._helper_label.set_theme(self._theme)
        self._sync_helper()
        self._row.update()

    def _apply_styles(self):
        self._font = self._make_font()
        self._sync_helper()
        self._row.update()

    def _make_font(self) -> QFont:
        """段文字字体：官方 font-semibold(600)，字重表无 semibold 用 medium(500)。"""
        from ...core.text_style import make_text_qfont

        return make_text_qfont(
            size=self._size_token()["font"], weight="medium", style_name=False
        )

    def showEvent(self, event):
        super().showEvent(event)
        if self._auto_focus:
            self._row.setFocus()
