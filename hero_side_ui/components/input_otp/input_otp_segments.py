"""InputOtp 段行：自绘全部段，承接键盘/点击/粘贴；状态对照官方 segment.tsx。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...animation import stop_tween, tween_property

if TYPE_CHECKING:
    from .input_otp import InputOtp

from PySide6.QtCore import (
    Property,
    QPointF,
    QRect,
    QRectF,
    QSize,
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

    def __init__(self, host: InputOtp):
        """创建段行控件，绑定光标闪烁与下划线展开动画。

        Args:
            host: 所属的 InputOtp 宿主实例（提供状态与配置）。
        """
        super().__init__(host)
        self._host = host
        self._blink = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        # underlined 活动段下划线从中心展开（对齐项目 UnderlineBar 动画）
        self._expand = 0.0
        self._expand_anim = None
        # 光标换段时新活动段重新展开下划线
        self.caret_moved.connect(self._on_caret_moved)

    # expand_progress ∈ [0,1]：活动段下划线从中心展开的进度
    def _get_expand(self) -> float:
        """Property getter：下划线展开进度。

        Returns:
            float: 0.0~1.0 的展开进度。
        """
        return self._expand

    def _set_expand(self, value: float):
        """Property setter：写入下划线展开进度并重绘。

        Args:
            value: 新进度（每帧由补间调用）。
        """
        self._expand = value
        self.update()

    expand_progress = Property(float, _get_expand, _set_expand)

    def _run_underline_anim(self, active: bool):
        """动画驱动 underlined 活动段下划线展开 / 收起。

        Args:
            active: True 展开到 1.0，False 收起到 0.0。
        """
        tween_property(
            self,
            "_expand_anim",
            b"expand_progress",
            1.0 if active else 0.0,
            duration=200,
            animated=not self._host._disable_animation,
        )

    def _on_caret_moved(self):
        """光标移动回调：重置并重跑下划线展开动画。"""
        if self.hasFocus() and not self._host._is_read_only:
            stop_tween(self, "_expand_anim")
            if not self._host._disable_animation:
                self._set_expand(0.0)
            self._run_underline_anim(True)

    # ---- 段几何 ----

    def _seg_size(self) -> int:
        """单段边长（像素）。

        Returns:
            int: 当前尺寸档的 segment 值。
        """
        return self._host._size_token()["segment"]

    def _seg_gap(self) -> int:
        """段间距（像素）。

        Returns:
            int: 当前尺寸档的 gap 值。
        """
        return self._host._size_token()["gap"]

    def seg_rect(self, idx: int) -> QRect:
        """第 idx 段在行内的矩形；活动段随展开进度外扩（近似官方 scale-110）。

        Args:
            idx: 段索引。

        Returns:
            QRect: 该段的外框矩形。
        """
        side = self._seg_size()
        x = _PAD + idx * (side + self._seg_gap())
        if idx == self._host._cursor and self._host._is_active_segment():
            offset = round(2 * max(0.0, min(1.0, self._expand)))
            return QRect(x - offset, _PAD - offset, side + 2 * offset, side + 2 * offset)
        return QRect(x, _PAD, side, side)

    def row_size_hint(self) -> QSize:
        """计算段行整体建议尺寸（含四周预留）。

        Returns:
            QSize: 段行固定尺寸。
        """
        n = max(1, self._host._length)
        return QSize(
            2 * _PAD + n * self._seg_size() + (n - 1) * self._seg_gap(),
            2 * _PAD + self._seg_size(),
        )

    # ---- 焦点与光标闪烁 ----

    def _toggle_blink(self):
        """光标闪烁定时器回调：翻转可见性并重绘。"""
        self._blink = not self._blink
        self.update()

    def set_focused(self, focused: bool):
        """进入 / 退出聚焦：开关光标闪烁并触发下划线动画。

        Args:
            focused: True 表示获得焦点。
        """
        if focused:
            self._blink = True
            self._blink_timer.start(self._host._caret_period() // 2)
        else:
            self._blink_timer.stop()
        self._run_underline_anim(focused and self._host._is_active_segment())
        self.update()

    # ---- 交互 ----

    def focusInEvent(self, event):
        """获得焦点：启动闪烁、展开下划线并通知宿主。

        Args:
            event: Qt 焦点进入事件。
        """
        super().focusInEvent(event)
        self.set_focused(True)
        self._host._sync_focus()

    def focusOutEvent(self, event):
        """失去焦点：停止闪烁、收起下划线并通知宿主。

        Args:
            event: Qt 焦点离开事件。
        """
        super().focusOutEvent(event)
        self.set_focused(False)
        self._host._sync_focus()

    def keyPressEvent(self, event):
        """键盘处理：方向键 / Home / End / 退格 / 删除 / 输入字符转发给宿主。

        Args:
            event: Qt 按键事件。
        """
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
        """粘贴：过滤出合法字符后从光标处插入（官方 pasteTransformer 语义）。

        Args:
            source: 剪贴板 MIME 数据。
        """
        if self._host._insert_text(source.text()):
            return
        super().insertFromMimeData(source)

    def mousePressEvent(self, event):
        """点击聚焦并把光标钉到值末尾（精确移动靠键盘）。

        Args:
            event: Qt 鼠标事件。
        """
        super().mousePressEvent(event)
        # 官方 input-otp：透明输入层文本挤在左端，点击任意处光标都钉在值末尾
        # （第一个空段）；精确移动只靠键盘方向键
        self.setFocus()
        self._host._set_cursor(min(len(self._host._value), self._host._length))

    # ---- 绘制 ----

    def paintEvent(self, event):
        """自绘全部段、边框 / 下划线、光标与文字（两遍：先非活动段后活动段）。

        Args:
            event: Qt 绘制事件。
        """
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
            border = (
                styles["active_border"]
                if (active and styles["active_border"])
                else styles["border"]
            )
            if border and border != "none":
                pen = QPen(QColor(border), float(styles["border_w"]))
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                inset = styles["border_w"] / 2.0
                border_rect = draw.adjusted(inset, inset, -inset, -inset)
                if underlined:
                    # 官方 underlined !rounded-none + border-b-medium：只画底边
                    p.drawLine(
                        QPointF(border_rect.left(), draw.bottom() - inset),
                        QPointF(border_rect.right(), draw.bottom() - inset),
                    )
                else:
                    p.drawRoundedRect(border_rect, radius, radius)
            if underlined:
                # 官方 after 下划线：静止为段内 2px 短线，活动段随进度
                # 从中心展开到全宽（after:transition-width）
                line_color = styles["underline_active"] if active else styles["underline_base"]
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(line_color))
                bottom = draw.bottom() - 2
                if active:
                    line_w = draw.width() * max(0.0, min(1.0, self._expand))
                    p.drawRect(QRectF(draw.center().x() - line_w / 2, bottom, line_w, 2))
                else:
                    p.drawRect(QRectF(draw.center().x() - 1, bottom, 2, 2))

            self._draw_content(p, rect, char, active, styles)

    def _draw_content(self, p: QPainter, rect: QRect, char: str, active: bool, styles: dict):
        """在单个段内绘制：密码圆点 / 光标 / 文字。

        Args:
            p: 当前 QPainter。
            rect: 该段矩形。
            char: 该段字符（空串表示未填）。
            active: 是否为活动段（决定光标是否绘制）。
            styles: 段配色 token 字典。
        """
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
                p.drawRect(QRectF(c.x() - 0.5, c.y() - rect.height() / 4, 1, rect.height() / 2))
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
