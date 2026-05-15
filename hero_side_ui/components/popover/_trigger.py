"""Popover 触发器附着与悬停/点击行为 mixin（私有）。

负责：
- attach(): 把 popover 绑到一个 trigger widget，并设置 trigger 类型（hover/click/manual）
- eventFilter(): 拦截 trigger 上的 hover/click/focus 事件
- 鼠标"游离"时的延迟关闭逻辑（避免移到 popover 内部就消失）
- 触发器视觉响应（_apply_trigger_open_state）：popover 打开时给 trigger 加视觉反馈
"""

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget


class _PopoverTriggerMixin:
    """Popover trigger 附着 mixin。"""

    # ============================================================
    # 触发器
    # ============================================================
    def attach(
        self,
        trigger: QWidget,
        event: str = "click",
    ):
        """把任意 widget 设为触发器。

        - event="click"：触发器点击切换 open/close
        - event="hover"：进入时打开，离开时关闭（150ms 延迟防闪烁）
        - event="manual"：仅记录 trigger，使用方手动调用 open/close
        """
        if self._trigger is not None and self._trigger is not trigger:
            self._trigger.removeEventFilter(self)
        self._trigger = trigger

        if event == "manual":
            return

        trigger.installEventFilter(self)
        self._trigger_event_kind = event
        # 绑定时把颜色同步到 trigger（如果 trigger 支持 set_color）
        self._sync_trigger_color()

    def eventFilter(self, obj, event):
        # ---- trigger 的事件 ----
        if obj is self._trigger:
            kind = getattr(self, "_trigger_event_kind", "click")
            if kind == "click" and event.type() == QEvent.Type.MouseButtonRelease:
                if self._is_disabled:
                    return False
                # 如果刚关掉不久（<250ms），说明用户点到 trigger 的这一下同时
                # 被外部点击逻辑关闭了 popover，这里应忽略，避免立刻又开一遍
                if self._just_closed.isValid() and self._just_closed.elapsed() < 250:
                    return False
                self.toggle()
                return False

            if kind == "hover":
                if event.type() == QEvent.Type.Enter:
                    self._hover_close_timer.stop()
                    if not self._is_disabled:
                        self.open()
                    return False
                if event.type() == QEvent.Type.Leave:
                    # 延迟关闭：鼠标可能正在移向 popover
                    self._hover_close_timer.start()
                    return False

        # ---- popover 自己的 Enter/Leave（hover 模式下要能停掉关闭计时器）----
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self._hover_close_timer.stop()
            elif event.type() == QEvent.Type.Leave:
                if getattr(self, "_trigger_event_kind", "click") == "hover":
                    self._hover_close_timer.start()

        return super().eventFilter(obj, event)

    def _hover_maybe_close(self):
        """hover 模式下延迟关闭：如果鼠标已进入 popover 或 trigger 就取消。"""
        if not self._is_open:
            return
        gpos = self._cursor_global_pos()
        if gpos is None:
            self.close()
            return
        if self._point_inside_trigger_or_popover(gpos):
            return
        self.close()

    def _cursor_global_pos(self) -> Optional[QPoint]:
        try:
            from PySide6.QtGui import QCursor

            return QCursor.pos()
        except Exception:
            return None

    def _point_inside_trigger_or_popover(self, gp: QPoint) -> bool:
        # trigger
        if self._trigger is not None:
            tr_top_left = self._trigger.mapToGlobal(QPoint(0, 0))
            tr_rect = (
                tr_top_left.x(),
                tr_top_left.y(),
                self._trigger.width(),
                self._trigger.height(),
            )
            if (
                tr_rect[0] <= gp.x() <= tr_rect[0] + tr_rect[2]
                and tr_rect[1] <= gp.y() <= tr_rect[1] + tr_rect[3]
            ):
                return True
        # popover 自己（以 widget 几何为准）
        my_rect = self.geometry()
        if my_rect.contains(gp):
            return True
        return False

    # ============================================================
    # 触发器视觉响应
    # ============================================================
    def _apply_trigger_open_state(self, opened: bool):
        """打开/关闭时给 trigger 的视觉反馈。

        注意：不能用 setGraphicsEffect，会覆盖 trigger 自身的 effect
        （例如 Button 的 PressScaleEffect），一旦旧 effect 被替换 Qt
        C++ 端会立即析构 _ScaleEffect，后续 PressScaleEffect 动画回调
        再访问就会抛 "Internal C++ object already deleted"。

        改为通过动态属性 + Qt 的 styleSheet 刷新实现。如果触发器没有
        QSS 响应这个属性，则视觉上没变化，但不会崩。
        """
        if self._trigger is None:
            return
        self._trigger.setProperty("popoverOpen", opened)
        # 触发 style 刷新（很多控件的 QSS 会读 property）
        style = self._trigger.style()
        if style is not None:
            style.unpolish(self._trigger)
            style.polish(self._trigger)

