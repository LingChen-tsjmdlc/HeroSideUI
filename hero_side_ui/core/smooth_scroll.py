"""
HeroSideUI 平滑滚动 (SmoothScroll)

PySide/Qt 默认的 QAbstractScrollArea（QPlainTextEdit / QTextEdit / QScrollArea / QListView 等）
滚动行为是"整行跳跃"——滚轮转一格 = scrollbar.singleStep（默认是一行字高），
没有动画过渡，所以体感生硬。

SmoothScroll 通过：
    1. 拦截 wheelEvent，自己接管滚动（不让 Qt 默认行为生效）
    2. 用 QPropertyAnimation 在 verticalScrollBar.value 上做 0→target 的丝滑过渡
    3. 若动画进行中又来一次 wheel，target 在**当前 target 基础上累加**，动画
       从"当前实际值"重启到新 target—— 这样连续滚动是顺畅的，不会跳回起点

⚠️ 单位说明（重要踩坑点）：
    QScrollBar.value 的单位**不是像素**，由 widget 自己定义：
      - QPlainTextEdit / QTextEdit / QListView: value 是"行/项目编号"，singleStep = 1
      - QScrollArea / QGraphicsView: value 是像素，singleStep ≈ 20
    所以不能用固定像素数做步进；要用 `bar.singleStep() × lines_per_step` 倍率，
    天然适配各种 widget。

用法：
    from hero_side_ui import SmoothScroll
    SmoothScroll.apply_global()         # 推荐：全局所有 QAbstractScrollArea 自动接管（含运行时新建）
    SmoothScroll.attach(my_scroll_area) # 单 area 手动挂（仅特殊场景）

    # 自定义参数
    SmoothScroll.attach(area, lines_per_step=5, duration=250)

参数：
    lines_per_step: 滚轮一格滚多少个 singleStep（QPlainTextEdit 一行 = 1 step；默认 3）
    duration: 动画时长 ms（默认 200ms）
    easing: 缓动曲线（默认 OutCubic）
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    QObject,
    QEvent,
    QPropertyAnimation,
    QEasingCurve,
    Qt,
)
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QScrollBar

__all__ = ["SmoothScroll"]


# 标记 widget 是否已挂过 SmoothScroll，避免重复
_ATTACHED_FLAG = "_hs_smooth_scroll_attached"


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
        super().__init__(area)
        self._area = area
        self._lines_per_step = lines_per_step
        self._duration = duration
        self._easing = easing

        self._v_anim: Optional[QPropertyAnimation] = None
        self._h_anim: Optional[QPropertyAnimation] = None
        self._v_target: Optional[int] = None
        self._h_target: Optional[int] = None

        # 装到 viewport 上（QAbstractScrollArea 的 wheel 走 viewport）
        # 同时也装到 area 自己，覆盖一些直接给 area 发 wheel 的情况
        area.viewport().installEventFilter(self)
        area.installEventFilter(self)

    def set_lines_per_step(self, n: int):
        self._lines_per_step = max(1, int(n))

    def set_duration(self, ms: int):
        self._duration = max(0, int(ms))

    def set_easing(self, curve: QEasingCurve.Type):
        self._easing = curve

    # ============================================================
    # eventFilter
    # ============================================================
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            try:
                handled = self._handle_wheel(event)
            except RuntimeError:
                return False
            if handled:
                return True  # 吞掉 Qt 默认 wheel
        return super().eventFilter(obj, event)

    def _handle_wheel(self, event) -> bool:
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
        if delta == 0:
            return

        target_attr = "_v_target" if axis == "v" else "_h_target"
        anim_attr = "_v_anim" if axis == "v" else "_h_anim"

        cur_target = getattr(self, target_attr)
        cur_anim: Optional[QPropertyAnimation] = getattr(self, anim_attr)

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
            if getattr(self, ah, None) is a:
                setattr(self, ah, None)

        anim.finished.connect(_on_finished)

        setattr(self, anim_attr, anim)
        setattr(self, target_attr, new_target)
        anim.start()


class _GlobalAutoAttachFilter(QObject):
    """装在 QApplication 上的事件过滤器：自动给每个新出现的 QAbstractScrollArea 挂 SmoothScroll

    为什么用 Show 而不是 ChildAdded：ChildAdded 时 widget 往往还没构造完，
    viewport 可能还是 None；Show 事件保证 widget 已就绪。attach() 内部有 _ATTACHED_FLAG
    防重复，所以多次 Show 也安全。
    """

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and isinstance(obj, QAbstractScrollArea):
            if obj.property(_ATTACHED_FLAG) is None:
                SmoothScroll.attach(obj)
        return super().eventFilter(obj, event)


class SmoothScroll:
    """命名空间：给 QAbstractScrollArea 挂载平滑滚动能力的工具

    两种使用方式：
      - SmoothScroll.apply_global()：QApplication 级自动接管（推荐，零样板）
      - SmoothScroll.attach(area)：手动挂单个 area（特殊场景退路）

    SmoothScroll 不是单例 —— 每个 area 自己挂一个 _SmoothScrollFilter 实例。
    """

    # 全局默认参数
    _default_lines_per_step: int = 3
    _default_duration: int = 300
    _default_easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    _default_enabled: bool = True

    # 全局自动挂载相关
    _global_filter: Optional[_GlobalAutoAttachFilter] = None

    @classmethod
    def attach(
        cls,
        area: QAbstractScrollArea,
        *,
        lines_per_step: Optional[int] = None,
        duration: Optional[int] = None,
        easing: Optional[QEasingCurve.Type] = None,
    ) -> Optional[_SmoothScrollFilter]:
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

        existing = area.property(_ATTACHED_FLAG)
        if existing is not None:
            return existing

        filt = _SmoothScrollFilter(
            area,
            lines_per_step=(
                lines_per_step
                if lines_per_step is not None
                else cls._default_lines_per_step
            ),
            duration=duration if duration is not None else cls._default_duration,
            easing=easing if easing is not None else cls._default_easing,
        )
        area.setProperty(_ATTACHED_FLAG, filt)
        return filt

    @classmethod
    def detach(cls, area: QAbstractScrollArea):
        """从 area 上卸载平滑滚动"""
        existing = area.property(_ATTACHED_FLAG)
        if existing is None:
            return
        try:
            area.viewport().removeEventFilter(existing)
            area.removeEventFilter(existing)
        except RuntimeError:
            pass
        existing.deleteLater()
        area.setProperty(_ATTACHED_FLAG, None)

    @classmethod
    def ensure_applied(cls) -> bool:
        """幂等激活：已装则跳、QApplication 不在则跳（等 app 起来再试）。

        设计参考 FontProvider.ensure_loaded。ThemeProvider 初始化时会调一次，
        使得用户只要用了 hero_side_ui 任何一个组件（组件会注册到 ThemeProvider），
        平滑滚动就自动生效。高级用户仍可调 disable_global() 关掉。
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
        lines_per_step: Optional[int] = None,
        duration: Optional[int] = None,
        easing: Optional[QEasingCurve.Type] = None,
    ):
        """全局自动给所有 QAbstractScrollArea 挂上平滑滚动（含运行时新建的）

        与 ScrollStyle.apply_global() 对称的零样板入口。调一次后：
          1) 立即扫描 QApplication.allWidgets() 已存在的 area 全部 attach
          2) 装 QApplication eventFilter，后续新建 area Show 时自动 attach

        如果某个 area 不想要平滑滚动，调 SmoothScroll.detach(area) 单独退出。
        """
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
            if (
                isinstance(w, QAbstractScrollArea)
                and w.property(_ATTACHED_FLAG) is None
            ):
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
        lines_per_step: Optional[int] = None,
        duration: Optional[int] = None,
        easing: Optional[QEasingCurve.Type] = None,
        enabled: Optional[bool] = None,
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
