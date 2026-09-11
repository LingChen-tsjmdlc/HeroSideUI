"""InputOtp 段行：自绘全部段并承接键盘/点击/粘贴交互。

段状态对照官方 input-otp-segment.tsx：char（已填字符）、isActive（当前
光标段）、passwordChar（密码圆点）、caret（活动空段的闪烁竖线）。
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QPropertyAnimation,
    QEasingCurve,
    QSize,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QWidget

_RADIUS_PX = {"none": 0, "sm": 4, "md": 8, "lg": 12, "full": 9999}

# 段行四周预留：活动段外扩 2px 的绘制空间（超出会被父 widget 裁剪）
_PAD = 2


class _SegmentRow(QWidget):
    value_edited = Signal(str)  # 用户输入导致 value 变化（含删除）
    caret_moved = Signal()

    def __init__(self, host: "InputOtp"):
        super().__init__(host)
        self._host = host
        self._blink = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        # underlined 活动段下划线从中心展开（对齐项目 UnderlineBar 动画）
        self._expand = 0.0
        self._expand_anim = QPropertyAnimation(self, b"expand_progress", self)
        self._expand_anim.setDuration(200)
        self._expand_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        # 光标换段时新活动段重新展开下划线
        self.caret_moved.connect(self._on_caret_moved)

    # expand_progress ∈ [0,1]：活动段下划线从中心展开的进度
    def _get_expand(self) -> float:
        return self._expand

    def _set_expand(self, value: float):
        self._expand = value
        self.update()

    expand_progress = Property(float, _get_expand, _set_expand)

    def _run_underline_anim(self, active: bool):
        """活动段出现时播放展开动画（外扩+下划线共用进度），离开时收回。"""
        if self._host._disable_animation:
            self._set_expand(1.0 if active else 0.0)
            return
        self._expand_anim.stop()
        self._expand_anim.setStartValue(self._expand)
        self._expand_anim.setEndValue(1.0 if active else 0.0)
        self._expand_anim.start()

    def _on_caret_moved(self):
        if self.hasFocus() and not self._host._is_read_only:
            self._expand_anim.stop()
            self._expand_anim.setStartValue(0.0)
            self._expand_anim.setEndValue(1.0)
            self._expand_anim.start()

    # ---- 段几何 ----

    def _seg_size(self) -> int:
        return self._host._size_token()["segment"]

    def _seg_gap(self) -> int:
        return self._host._size_token()["gap"]

    def seg_rect(self, idx: int) -> QRect:
        """第 idx 段在行内的矩形；活动段随展开进度外扩（近似官方 scale-110）。"""
        side = self._seg_size()
        x = _PAD + idx * (side + self._seg_gap())
        if idx == self._host._cursor and self._host._is_active_segment():
            offset = round(2 * max(0.0, min(1.0, self._expand)))
            return QRect(x - offset, _PAD - offset, side + 2 * offset, side + 2 * offset)
        return QRect(x, _PAD, side, side)

    def row_size_hint(self) -> QSize:
        n = max(1, self._host._length)
        return QSize(
            2 * _PAD + n * self._seg_size() + (n - 1) * self._seg_gap(),
            2 * _PAD + self._seg_size(),
        )

    # ---- 焦点与光标闪烁 ----

    def _toggle_blink(self):
        self._blink = not self._blink
        self.update()

    def set_focused(self, focused: bool):
        if focused:
            self._blink = True
            self._blink_timer.start(self._host._caret_period() // 2)
        else:
            self._blink_timer.stop()
        self._run_underline_anim(focused and self._host._is_active_segment())
        self.update()

    # ---- 交互 ----

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.set_focused(True)
        self._host._sync_focus()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.set_focused(False)
        self._host._sync_focus()

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        host = self._host
        if key == Qt.Key.Key_Left:
            host._move_cursor(-1)
        elif key == Qt.Key.Key_Right:
            host._move_cursor(1)
        elif key == Qt.Key.Key_Home:
            host._set_cursor(0)
        elif key == Qt.Key.Key_End:
            host._set_cursor(len(host._value))
        elif key == Qt.Key.Key_Backspace:
            host._backspace()
        elif key == Qt.Key.Key_Delete:
            host._delete_at_cursor()
        elif text and host._insert_text(text):
            return
        else:
            super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        # 粘贴：过滤出合法字符后从光标处插入（官方 pasteTransformer 语义）
        if self._host._insert_text(source.text()):
            return
        super().insertFromMimeData(source)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # 官方 input-otp：透明输入层文本挤在左端，点击任意处光标都钉在值末尾
        # （第一个空段）；精确移动只靠键盘方向键
        self.setFocus()
        self._host._set_cursor(min(len(self._host._value), self._host._length))

    # ---- 绘制 ----

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # 官方 isDisabled opacity-disabled：整组半透明
        p.setOpacity(0.5 if self._host._is_disabled else 1.0)
        host = self._host
        styles = host._segment_styles()
        side = self._seg_size()
        radius = min(_RADIUS_PX[host._radius], side / 2)
        underlined = host._variant == "underlined"
        cursor = host._cursor

        # 两遍绘制：非活动段先画，活动段最后画（外扩部分不被邻段覆盖）
        order = [i for i in range(host._length) if i != cursor] + (
            [cursor] if host._length > 0 else []
        )
        for idx in order:
            rect = self.seg_rect(idx)
            active = idx == cursor and host._is_active_segment()
            char = host._value[idx] if idx < len(host._value) else ""
            draw = QRectF(rect)
            if underlined:
                # 官方 underlined 只保留底边，高度扣掉边框
                draw = draw.adjusted(0, 0, 0, -styles["border_w"])
            bg = styles["active_bg"] if (active and styles["active_bg"]) else styles["bg"]
            if bg and bg != "none":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(bg))
                p.drawRoundedRect(draw, radius, radius)
            border = (styles["active_border"]
                      if (active and styles["active_border"]) else styles["border"])
            if border and border != "none":
                pen = QPen(QColor(border), float(styles["border_w"]))
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                inset = styles["border_w"] / 2.0
                border_rect = draw.adjusted(inset, inset, -inset, -inset)
                if underlined:
                    # 官方 underlined !rounded-none + border-b-medium：只画底边
                    p.drawLine(QPointF(border_rect.left(), draw.bottom() - inset),
                               QPointF(border_rect.right(), draw.bottom() - inset))
                else:
                    p.drawRoundedRect(border_rect, radius, radius)
            if underlined:
                # 官方 after 下划线：静止为段内 2px 短线，活动段随进度
                # 从中心展开到全宽（after:transition-width）
                line_color = (styles["underline_active"] if active
                              else styles["underline_base"])
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(line_color))
                bottom = draw.bottom() - 2
                if active:
                    line_w = draw.width() * max(0.0, min(1.0, self._expand))
                    p.drawRect(QRectF(draw.center().x() - line_w / 2, bottom,
                                      line_w, 2))
                else:
                    p.drawRect(QRectF(draw.center().x() - 1, bottom, 2, 2))

            self._draw_content(p, rect, char, active, styles)

    def _draw_content(self, p: QPainter, rect: QRect, char: str, active: bool,
                      styles: dict):
        host = self._host
        has_value = bool(char)
        p.setFont(host._font)
        fm = QFontMetricsF(host._font)
        if has_value and host._type == "password":
            # 密码圆点：官方 w-1(4px) 偏小，桌面放大到 6px 并精确居中
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(styles["dot_color"]))
            c = rect.center()
            p.drawEllipse(c, 3, 3)
            return
        if active and not has_value:
            # 官方 caret w-px h-[50%]，readonly 时光标透明
            if self._blink and not host._is_read_only:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(styles["caret_color"]))
                c = rect.center()
                p.drawRect(QRectF(c.x() - 0.5, c.y() - rect.height() / 4, 1,
                                  rect.height() / 2))
            return
        if has_value:
            fg = QColor(styles["text_filled"] if has_value else styles["text"])
            p.setPen(QPen(fg, 0))
            advance = fm.horizontalAdvance(char)
            align = host._text_align
            x = rect.center().x() - advance / 2
            if align == "left":
                x = rect.left() + self._seg_gap()
            elif align == "right":
                x = rect.right() - self._seg_gap() - advance
            baseline = rect.center().y() + (fm.ascent() - fm.descent()) / 2
            p.drawText(QPointF(x, baseline), char)
