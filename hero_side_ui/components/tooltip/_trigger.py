"""Tooltip 触发器附着 / hover 调度 / 触发器视觉响应 mixin。

为什么独立：tooltip.py 太大；attach + eventFilter + schedule_open/close +
apply_trigger_open_state 这些"trigger 交互"逻辑高聚合，迁出后主类专注状态机/装配。

宿主类需要提供：
    self._trigger, self._is_open, self._closing, self._is_disabled,
    self._open_delay, self._close_delay, self._open_timer, self._close_timer,
    self._embedded, self._anchor_ancestor, self._refresh_geometry()
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget

__all__ = ["_TooltipTriggerMixin"]


class _TooltipTriggerMixin:
    """Tooltip trigger 附着 + hover 事件调度。"""

    def attach(self, trigger: QWidget):
        """把任意 widget 设为触发器（hover 自动触发）。

        embedded 模式下：同时把 tooltip reparent 到 trigger 顶层 ancestor。
        这样 trigger 随父滚动/移动时 tooltip 自动跟随（Qt 原生能力，零代码）。
        """
        if self._trigger is not None and self._trigger is not trigger:  # type: ignore[attr-defined]
            self._trigger.removeEventFilter(self)  # type: ignore[attr-defined]
        self._trigger = trigger  # type: ignore[attr-defined]
        trigger.installEventFilter(self)  # type: ignore[arg-type]
        self.installEventFilter(self)  # type: ignore[arg-type]
        if self._embedded:  # type: ignore[attr-defined]
            top = trigger.window()
            if top is not None and top is not self.parent():  # type: ignore[attr-defined]
                self.setParent(top)  # type: ignore[attr-defined]
                self.hide()  # type: ignore[attr-defined]
            self._anchor_ancestor = top  # type: ignore[attr-defined]

    def eventFilter(self, obj, event):
        # ---- trigger 的事件 ----
        if obj is self._trigger:  # type: ignore[attr-defined]
            if event.type() == QEvent.Type.Enter:
                if not self._is_disabled:  # type: ignore[attr-defined]
                    self._close_timer.stop()  # type: ignore[attr-defined]
                    self._schedule_open()
                return False
            if event.type() == QEvent.Type.Leave:
                self._open_timer.stop()  # type: ignore[attr-defined]
                self._schedule_close()
                return False
            # trigger 几何变化（移动/缩放）→ 已 open 的 tooltip 跟随重定位
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize) and self._is_open:  # type: ignore[attr-defined]
                self._refresh_geometry()  # type: ignore[attr-defined]
                return False

        # ---- tooltip 自己的 Enter/Leave ----
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self._close_timer.stop()  # type: ignore[attr-defined]
                self._open_timer.stop()  # type: ignore[attr-defined]
            elif event.type() == QEvent.Type.Leave:
                self._schedule_close()

        return super().eventFilter(obj, event)  # type: ignore[misc]

    def _schedule_open(self):
        """根据 open_delay 决定立即/延迟打开。

        bail 条件区分"已稳定 open"与"fade-out 中"：
        fade-out 中 _is_open 仍 True，这时用户再 hover 必须进 _do_open 走 reopening 分支。
        """
        if self._is_open and not self._closing:  # type: ignore[attr-defined]
            return
        if self._open_delay <= 0:  # type: ignore[attr-defined]
            self._do_open()  # type: ignore[attr-defined]
        else:
            self._open_timer.setInterval(self._open_delay)  # type: ignore[attr-defined]
            self._open_timer.start()  # type: ignore[attr-defined]

    def _schedule_close(self):
        """根据 close_delay 决定立即/延迟关闭。"""
        if not self._is_open:  # type: ignore[attr-defined]
            self._open_timer.stop()  # type: ignore[attr-defined]
            return
        # 已在 fade-out，不重复启动 close 计时器
        if self._closing:  # type: ignore[attr-defined]
            return
        if self._close_delay <= 0:  # type: ignore[attr-defined]
            self._do_close()  # type: ignore[attr-defined]
        else:
            self._close_timer.setInterval(self._close_delay)  # type: ignore[attr-defined]
            self._close_timer.start()  # type: ignore[attr-defined]

    def _apply_trigger_open_state(self, opened: bool):
        """trigger 视觉反馈（设动态属性 + 重新 polish style）。"""
        if self._trigger is None:  # type: ignore[attr-defined]
            return
        self._trigger.setProperty("tooltipOpen", opened)  # type: ignore[attr-defined]
        style = self._trigger.style()  # type: ignore[attr-defined]
        if style is not None:
            style.unpolish(self._trigger)  # type: ignore[attr-defined]
            style.polish(self._trigger)  # type: ignore[attr-defined]
