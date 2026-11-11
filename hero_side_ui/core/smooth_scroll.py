"""SmoothScroll：给 QAbstractScrollArea 提供滚轮平滑滚动。

拦截 wheelEvent 用 QPropertyAnimation 在 scrollbar value 上过渡；连续滚动
时目标值累加、动画从当前值重启。步进用 singleStep 倍率以适配各 widget 单位。
"""

from __future__ import annotations

import weakref

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QScrollBar

__all__ = ["SmoothScroll"]


# attach 状态放在 Python 侧：Qt 动态属性的 QVariant 只持有裸 QObject*，
# 对象销毁后 PySide 从 property() 读回并包装会触发 dynamic_cast 悬空；
# setProperty 还会发 QDynamicPropertyChangeEvent，制造嵌套事件过滤。
_ATTACHED: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
# 永久退出标记：opt_out() 写 True 后，auto-attach 与显式 attach 都不再挂
_OPTED_OUT: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


class _SmoothScrollFilter(QObject):
    """每个 QAbstractScrollArea 一份的 wheel 拦截器 + 动画驱动器"""

    def __init__(
        self,
        area: QAbstractScrollArea,
        *,
        lines_per_step: int = 3,
        duration: int = 300,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    ):
        """初始化过滤器并把事件过滤器装到 viewport 与 area。

        Args:
            area: 目标 QAbstractScrollArea。
            lines_per_step: 每格滚轮滚动的 singleStep 倍数。
            duration: 动画时长（ms）。
            easing: 缓动曲线。
        """
        super().__init__(area)
        self._area = area
        self._lines_per_step = lines_per_step
        self._duration = duration
        self._easing = easing

        self._v_anim: QPropertyAnimation | None = None
        self._h_anim: QPropertyAnimation | None = None
        self._v_target: int | None = None
        self._h_target: int | None = None

        # 装到 viewport 上（QAbstractScrollArea 的 wheel 走 viewport）
        # 同时也装到 area 自己，覆盖一些直接给 area 发 wheel 的情况
        area.viewport().installEventFilter(self)
        area.installEventFilter(self)

    def set_lines_per_step(self, n: int):
        """设置每格滚轮的步进倍数，至少 1。"""
        self._lines_per_step = max(1, int(n))

    def set_duration(self, ms: int):
        """设置动画时长（ms），下限 0。"""
        self._duration = max(0, int(ms))

    def set_easing(self, curve: QEasingCurve.Type):
        """设置动画缓动曲线。"""
        self._easing = curve

    # ============================================================
    # eventFilter
    # ============================================================
    def eventFilter(self, obj, event):
        """拦截 Wheel 事件并交给滚轮处理器。"""
        if event.type() == QEvent.Type.Wheel:
            try:
                handled = self._handle_wheel(event)
            except RuntimeError:
                return False
            if handled:
                return True  # 吞掉 Qt 默认 wheel
        return super().eventFilter(obj, event)

    def _handle_wheel(self, event) -> bool:
        """把滚轮增量换算为水平与垂直方向的滚动步进。"""
        ad = event.angleDelta()
        dx = ad.x()
        dy = ad.y()

        v_bar = self._area.verticalScrollBar()
        h_bar = self._area.horizontalScrollBar()

        consumed = False

        # 用 bar.singleStep() × lines_per_step 计算步进，自适应 widget 单位
        # （QPlainTextEdit 的 step=1 行；QScrollArea 的 step=20px）
        if dy != 0 and v_bar is not None and v_bar.maximum() > 0:
            step = max(1, v_bar.singleStep()) * self._lines_per_step
            # dy > 0 滚轮向上 → 内容向下移 → bar.value 减小
            delta = -int(dy / 120 * step)
            self._scroll_to(v_bar, axis="v", delta=delta)
            consumed = True

        if dx != 0 and h_bar is not None and h_bar.maximum() > 0:
            step = max(1, h_bar.singleStep()) * self._lines_per_step
            delta = -int(dx / 120 * step)
            self._scroll_to(h_bar, axis="h", delta=delta)
            consumed = True

        return consumed

    # ============================================================
    # 滚动驱动
    # ============================================================
    def _scroll_to(self, bar: QScrollBar, *, axis: str, delta: int):
        """按目标增量启动或续接单轴滚动动画。"""
        if delta == 0:
            return

        target_attr = "_v_target" if axis == "v" else "_h_target"
        anim_attr = "_v_anim" if axis == "v" else "_h_anim"

        cur_target = getattr(self, target_attr)
        cur_anim: QPropertyAnimation | None = getattr(self, anim_attr)

        # 动画进行中，新 target 在它的目标值上累加（连续滚动顺畅）
        if (
            cur_anim is not None
            and cur_anim.state() == QPropertyAnimation.State.Running
            and cur_target is not None
        ):
            base = cur_target
        else:
            base = bar.value()

        new_target = base + delta
        new_target = max(bar.minimum(), min(bar.maximum(), new_target))

        if new_target == bar.value() and (
            cur_anim is None or cur_anim.state() != QPropertyAnimation.State.Running
        ):
            return

        if self._duration <= 0:
            bar.setValue(new_target)
            setattr(self, target_attr, new_target)
            return

        if cur_anim is not None:
            try:
                cur_anim.stop()
            except RuntimeError:
                pass

        anim = QPropertyAnimation(bar, b"value")
        anim.setStartValue(bar.value())
        anim.setEndValue(new_target)
        anim.setDuration(self._duration)
        anim.setEasingCurve(self._easing)

        def _on_finished(a=anim, t=target_attr, ah=anim_attr):
            """动画结束时清空对应的动画句柄。"""
            if getattr(self, ah, None) is a:
                setattr(self, ah, None)

        anim.finished.connect(_on_finished)

        setattr(self, anim_attr, anim)
        setattr(self, target_attr, new_target)
        anim.start()


class _GlobalAutoAttachFilter(QObject):
    """QApplication 事件过滤器：给新出现的 QAbstractScrollArea 自动挂载。

    Note:
        监听 Show 而非 ChildAdded——Show 时 viewport 必已就绪；
        attach 内部有防重标记，多次触发安全。
    """

    def eventFilter(self, obj, event):
        """在新出现的滚动区显示时自动挂载平滑滚动。"""
        if event.type() == QEvent.Type.Show and isinstance(obj, QAbstractScrollArea):
            try:
                if not _OPTED_OUT.get(obj) and obj not in _ATTACHED:
                    SmoothScroll.attach(obj)
            except RuntimeError:
                # obj 的 C++ 端已释放，不再尝试包装或挂载
                return False
        return super().eventFilter(obj, event)


class SmoothScroll:
    """命名空间工具：给滚动区挂载平滑滚动。

    apply_global() 全局自动接管（推荐）；attach(area) 手动挂单个。
    非 单例，每个 area 独立持有过滤器实例。
    """

    # 全局默认参数
    _default_lines_per_step: int = 3
    _default_duration: int = 300
    _default_easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    _default_enabled: bool = True

    # 全局自动挂载相关
    _global_filter: _GlobalAutoAttachFilter | None = None

    @classmethod
    def attach(
        cls,
        area: QAbstractScrollArea,
        *,
        lines_per_step: int | None = None,
        duration: int | None = None,
        easing: QEasingCurve.Type | None = None,
    ) -> _SmoothScrollFilter | None:
        """给一个 QAbstractScrollArea 挂上平滑滚动

        Args:
            area: 目标 QAbstractScrollArea
            lines_per_step: 滚轮一格滚动多少个 singleStep（默认 3）
            duration: 动画时长 ms（默认 200）
            easing: 缓动曲线（默认 OutCubic）

        Returns:
            创建的 filter 实例（已挂到 area 上）；若已挂过则返回已有 filter
        """
        if not cls._default_enabled and lines_per_step is None:
            return None
        if not isinstance(area, QAbstractScrollArea):
            return None
        if _OPTED_OUT.get(area):
            return None  # 永久退出过，尊重之

        existing = _ATTACHED.get(area)
        if existing is not None:
            return existing

        filt = _SmoothScrollFilter(
            area,
            lines_per_step=(
                lines_per_step if lines_per_step is not None else cls._default_lines_per_step
            ),
            duration=duration if duration is not None else cls._default_duration,
            easing=easing if easing is not None else cls._default_easing,
        )
        _ATTACHED[area] = filt
        return filt

    @classmethod
    def detach(cls, area: QAbstractScrollArea):
        """从 area 上卸载平滑滚动"""
        existing = _ATTACHED.pop(area, None)
        if existing is None:
            return
        try:
            area.viewport().removeEventFilter(existing)
            area.removeEventFilter(existing)
        except RuntimeError:
            pass
        existing.deleteLater()

    @classmethod
    def opt_out(cls, area: QAbstractScrollArea):
        """永久退出平滑滚动（detach + 写禁用标记，auto-attach 与 attach 都不再挂）"""
        cls.detach(area)
        if isinstance(area, QAbstractScrollArea):
            _OPTED_OUT[area] = True

    @classmethod
    def ensure_applied(cls) -> bool:
        """幂等激活全局平滑滚动；QApplication 未就绪时静默等待下次。

        Returns:
            是否已安装。
        """
        if cls._global_filter is not None:
            return True
        if QApplication.instance() is None:
            return False  # 不记志完成，等下次重试
        cls.apply_global()
        return True

    @classmethod
    def apply_global(
        cls,
        *,
        lines_per_step: int | None = None,
        duration: int | None = None,
        easing: QEasingCurve.Type | None = None,
    ):
        """全局接管所有滚动区（含运行时新建），调一次即生效。"""
        # 设置默认参数（影响后续自动 attach 的 area）
        cls.set_global_default(
            lines_per_step=lines_per_step,
            duration=duration,
            easing=easing,
            enabled=True,
        )

        app = QApplication.instance()
        if app is None:
            return

        # 装一次全局事件过滤器
        if cls._global_filter is None:
            cls._global_filter = _GlobalAutoAttachFilter()
            app.installEventFilter(cls._global_filter)

        # 立即扫一遍现有的 area
        for w in app.allWidgets():
            if isinstance(w, QAbstractScrollArea) and w not in _ATTACHED:
                cls.attach(w)

    @classmethod
    def disable_global(cls):
        """卸载全局自动接管（已挂的 area 不会自动 detach，需要的话各自调 detach）"""
        app = QApplication.instance()
        if app is not None and cls._global_filter is not None:
            app.removeEventFilter(cls._global_filter)
        if cls._global_filter is not None:
            cls._global_filter.deleteLater()
            cls._global_filter = None

    @classmethod
    def set_global_default(
        cls,
        *,
        lines_per_step: int | None = None,
        duration: int | None = None,
        easing: QEasingCurve.Type | None = None,
        enabled: bool | None = None,
    ):
        """设置全局默认参数（影响后续 attach 调用，不影响已挂载 area）"""
        if lines_per_step is not None:
            cls._default_lines_per_step = max(1, int(lines_per_step))
        if duration is not None:
            cls._default_duration = max(0, int(duration))
        if easing is not None:
            cls._default_easing = easing
        if enabled is not None:
            cls._default_enabled = bool(enabled)
