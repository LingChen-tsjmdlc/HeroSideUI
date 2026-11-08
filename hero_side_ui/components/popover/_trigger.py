"""Popover 触发器 mixin：attach 绑定、eventFilter 拦截与游离延迟关闭。"""

from PySide6.QtCore import QEvent, QPoint
from PySide6.QtWidgets import QWidget


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

        Args:
            trigger: 目标控件。
            event: click 切换 / hover 进出开合（150ms 防闪）/ manual 仅记录。
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
        """拦截 trigger 与 popover 自身的事件，驱动点击/悬停开合。

        Args:
            obj: 事件目标对象（trigger 或 popover 自己）。
            event: Qt 事件对象。

        Returns:
            bool: 始终返回 super().eventFilter 结果，不主动吞事件。

        Note:
            click 模式下刚关闭不久（<250ms）的 trigger 点击会被忽略，
            避免外部点击关闭逻辑与 click 玩家互相打架造成"点两次才开"。
        """
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

    def _cursor_global_pos(self) -> QPoint | None:
        """获取当前鼠标全局坐标。

        Returns:
            QPoint | None: 鼠标全局坐标；获取失败返回 None。

        Note:
            用 try/except 包裹 QCursor 导入与调用，避免 GUI 上下文缺失时报错。
        """
        try:
            from PySide6.QtGui import QCursor

            return QCursor.pos()
        except Exception:
            return None

    def _point_inside_trigger_or_popover(self, gp: QPoint) -> bool:
        """判断全局坐标点是否落在 trigger 或 popover 之内。

        Args:
            gp: 待判断的全局坐标点。

        Returns:
            bool: 命中 trigger 或 popover 返回 True，否则 False。

        Note:
            用于 hover 模式延迟关闭时确认鼠标是否回到可交互区域。
        """
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
        """开合时给 trigger 视觉反馈。

        Note:
            不用 setGraphicsEffect——会覆盖 trigger 自身 effect 导致 C++
            对象析构崩溃；改用动态属性 + QSS 刷新。
        """
        if self._trigger is None:
            return
        self._trigger.setProperty("popoverOpen", opened)
        # 触发 style 刷新（很多控件的 QSS 会读 property）
        style = self._trigger.style()
        if style is not None:
            style.unpolish(self._trigger)
            style.polish(self._trigger)
