"""Popover 滚动跟随 / 关闭 / wheel 转发 mixin（私有）。"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QWidget

if TYPE_CHECKING:  # 仅类型提示，运行期不导入避免循环
    pass


class _PopoverScrollMixin:
    """Popover 滚动相关 mixin。

    Note:
        宿主需提供 _is_open/_closing/_close_on_scroll/_trigger/_backdrop 等属性
        与 close()/_calc_position() 方法。
    """

    # ============================================================
    # 滚动监听 connect / disconnect
    # ============================================================
    def _connect_scroll_watchers(self, trigger: QWidget):
        """沿 trigger 祖先链找所有 QAbstractScrollArea，监听其滚动条变化；
        同时监听 trigger.window() 的 Move/Resize，
        让整窗拖动 / 缩放 也能触发 popover 跟随。"""
        self._disconnect_scroll_watchers()
        w = trigger
        seen = set()
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                for bar in (w.verticalScrollBar(), w.horizontalScrollBar()):
                    if bar is not None and id(bar) not in seen:
                        seen.add(id(bar))
                        bar.valueChanged.connect(self._on_scroll_detected)
                        self._scroll_bars.append(bar)
            w = w.parentWidget()

        # 几何变化监听：只挂 host 窗口的 Move/Resize，复用节流路径重定位。
        # 不挂 trigger 自身：全面介入 trigger 事件路径容易平交导致 click 豌异。
        watcher = self._host_resize_watcher
        if watcher is not None:
            host = trigger.window() if hasattr(trigger, "window") else None
            if host is not None:
                host.installEventFilter(watcher)
                self._watched_host = host

    def _disconnect_scroll_watchers(self):
        """断开所有滚动条 valueChanged 监听与宿主几何 watcher 并清空状态。

        Note:
            在打开前清理、关闭后释放，避免悬挂引用导致悬空信号回调。
        """
        for bar in self._scroll_bars:
            try:
                bar.valueChanged.disconnect(self._on_scroll_detected)
            except (RuntimeError, TypeError):
                pass
        self._scroll_bars.clear()

        # 几何 watcher 同步释放，防悬挂引用
        watcher = self._host_resize_watcher
        host = getattr(self, "_watched_host", None)
        if host is not None and watcher is not None:
            try:
                host.removeEventFilter(watcher)
            except RuntimeError:
                pass
        self._watched_host = None

    # ============================================================
    # backdrop wheel → SmoothScroll 转发
    # ============================================================
    def _on_backdrop_wheel(self, angle_delta):
        """backdrop 拦到 wheel 时重建事件投递给祖先 ScrollArea 的 viewport。

        Args:
            angle_delta: QWheelEvent.angleDelta()。

        Note:
            必须走 postEvent 让 SmoothScroll 接管；直接 setValue 会绕过
            平滑动画导致一帧到位。
        """
        if not self._is_open or self._trigger is None:
            return
        if angle_delta is None:
            return

        # 沿 trigger 祖先链找第一个 QAbstractScrollArea（最近的可滚动容器）
        w = self._trigger
        scroll_area = None
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                scroll_area = w
                break
            w = w.parentWidget()
        if scroll_area is None:
            return
        viewport = scroll_area.viewport()
        if viewport is None:
            return

        # 投递点取 viewport 中心（任意点皆可，scroll wheel 不挑位置；中心最稳）
        local = QPointF(viewport.width() / 2.0, viewport.height() / 2.0)
        global_pos = QPointF(viewport.mapToGlobal(local.toPoint()))

        # PySide6 QWheelEvent 现代构造：
        #   (pos, globalPos, pixelDelta, angleDelta, buttons, modifiers, phase, inverted)
        # pixelDelta 给 QPoint(0,0) 表示"没有像素级精度"，由 angleDelta 决定步长——
        # 这是普通鼠标滚轮的标准状态（高精度触控板才会有 pixelDelta）。
        evt = QWheelEvent(
            local,
            global_pos,
            QPoint(0, 0),  # pixelDelta
            angle_delta,  # angleDelta
            Qt.MouseButton.NoButton,
            QApplication.keyboardModifiers(),
            Qt.ScrollPhase.NoScrollPhase,
            False,  # inverted
        )
        # postEvent 异步派发：避免在 backdrop wheelEvent 派发栈内同步重入。
        # SmoothScroll 的 eventFilter 装在 viewport 上，下一轮事件循环时拦到
        # → 启动 QPropertyAnimation → 平滑滚动。期间动画逐帧 setValue 也会
        # 触发 valueChanged → _on_scroll_detected 接管"关闭 / 跟随"逻辑。
        QApplication.postEvent(viewport, evt)

    # ============================================================
    # 滚动事件分派 + 节流跟随
    # ============================================================
    def _on_scroll_detected(self, _value: int):
        """祖先滚动响应：close_on_scroll=True 首滚淡出关闭（期间继续跟随），
        False 纯跟随重定位。
        """
        if not self._is_open:
            return

        # close_on_scroll=True 且首次检测到滚动（还没在 fade-out）→ 触发关闭
        if self._close_on_scroll and not self._closing:
            self.close()  # 走 fade-out 动画路径，会标 _closing=True
            # fall through 到 reposition 分支：让 popover 在淡出第一帧就跟到 trigger 新位置

        # 跟随 reposition：节流到下一帧重算一次（多条 scrollbar 同帧变动只 move 一次）。
        # fade-out 期间也持续跟随，避免 popover 脱离 trigger 视觉轨迹；
        # _finalize_close 时 disconnect 后续 valueChanged 自然不再触发。
        if self._scroll_reposition_pending:
            return
        self._scroll_reposition_pending = True
        QTimer.singleShot(0, self._do_scroll_reposition)

    def _do_scroll_reposition(self):
        """按 _scroll_anchor_offset 相对 trigger 纯平移 popover。

        Note:
            不走 _calc_position，避免 auto-flip 换边与 fade-out 期间
            sizeHint 退化造成的几何错位。
        """
        self._scroll_reposition_pending = False
        if not self._is_open or self._trigger is None:
            return
        try:
            anchor = self._near or self._trigger
            tr_global = anchor.mapToGlobal(QPoint(0, 0))
        except RuntimeError:
            # trigger C++ 对象已销毁
            return
        offset = getattr(self, "_scroll_anchor_offset", None)
        if offset is None:
            return
        self.move(tr_global + offset)
        # backdrop 是 host window 的子 widget，几何随 host 自动跟随，无需 move。
        # 但 blur 模式下 backdrop 显示的是 prepare_blur_snapshot 时的**静止**截图——
        # 滚动后 host 内容已位移，模糊像素还停在旧位置 → 透过 30% 黑半透明叠加，
        # 视觉上能明显感知"模糊画面 vs 真实背景"的错位 = 残影感。
        #
        # **两种场景都需要每帧刷新**：
        # - close_on_scroll=False（粘住跟随）：popover 长期可见，必须保持模糊
        #   与背景一致。
        # - close_on_scroll=True（滚动即关）：fade-out 仍持续 200~260ms，期间
        #   用户可能继续滚（甚至 SmoothScroll 动画自己还在跑 setValue），
        #   模糊静止 = 用户反馈的"残影感"。在 backdrop 完全淡出（progress→0）
        #   之前必须持续刷新。
        #
        # 自然停机制：_finalize_close 会 disconnect valueChanged → 此后再无 reposition
        # 触发，无需在这里手动加 progress > 0 守卫。SmoothScroll 动画结束后
        # 用户也不再滚 → valueChanged 也不再发 → 自动停止刷新。零额外开销。
        if self._backdrop is not None and self._backdrop_kind == "blur":
            self._backdrop.refresh_blur_fast()

    # ============================================================
    # 完整重算（host Resize 路径专用）
    # ============================================================
    def _request_full_reposition(self):
        """host Resize 时请求一次完整 _calc_position 重算（节流到下一帧合并）。"""
        if not self._is_open:
            return
        if self._full_reposition_pending:
            return
        self._full_reposition_pending = True
        QTimer.singleShot(0, self._do_full_reposition)

    def _do_full_reposition(self):
        """完整重算路径：走 _calc_position 按 placement 重新对齐 trigger。"""
        self._full_reposition_pending = False
        if not self._is_open or self._trigger is None:
            return
        try:
            anchor = self._near or self._trigger
            self.adjustSize()
            self.resize(self.sizeHint())
            pos = self._calc_position(anchor)
            self.move(pos)
            tr_global = anchor.mapToGlobal(QPoint(0, 0))
            self._scroll_anchor_offset = pos - tr_global
        except RuntimeError:
            return
        # backdrop 几何由它自己的 host eventFilter 同步；blur 快照也由 backdrop 重抓
