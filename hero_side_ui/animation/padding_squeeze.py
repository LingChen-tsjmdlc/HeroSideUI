"""通过边距变化实现内容展开与收拢。"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation, Signal
from PySide6.QtWidgets import QLayout

from .tween import stop_tween, tween_value

_ORIGIN_CENTER = "center"
_ORIGIN_TOP = "top"
_ORIGIN_BOTTOM = "bottom"
_VALID_ORIGINS = (_ORIGIN_CENTER, _ORIGIN_TOP, _ORIGIN_BOTTOM)


class PaddingSqueezeAnimation(QObject):
    """将公共过渡进度换算为锚点相关的额外边距。

    Attributes:
        finished: 完成时发出展开或收起方向的信号。
        progress_changed: 当前进度变化信号。
    """

    finished = Signal(bool)

    progress_changed = Signal(float)

    def __init__(
        self,
        layout: QLayout,
        base_margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        delta: int = 8,
        duration: int = 180,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        easing_out: QEasingCurve.Type | None = None,
        origin: str = _ORIGIN_CENTER,
        parent: QObject | None = None,
    ):
        """初始化边距效果。

        Args:
            layout: 接受边距变化的布局。
            base_margins: 稳定状态下的左、上、右、下边距。
            delta: 收起时增加的边距像素量。
            duration: 过渡毫秒数。
            easing: 展开曲线。
            easing_out: 收起曲线；省略时沿用展开曲线。
            origin: 锚点，可为 center、top 或 bottom。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        if origin not in _VALID_ORIGINS:
            raise ValueError(f"origin must be one of {_VALID_ORIGINS}, got {origin!r}")

        self._layout = layout
        self._base = tuple(base_margins)
        self._delta = max(0, int(delta))
        self._duration = max(0, int(duration))
        self._easing_in = easing
        self._easing_out = easing_out if easing_out is not None else easing
        self._origin = origin

        self._progress: float = 1.0

        self._anim: QVariantAnimation | None = None
        self._forward: bool = True

    def expand(self, *, animated: bool = True) -> None:
        """从当前进度展开内容。

        Args:
            animated: 是否播放过渡。
        """
        self._play(target=1.0, forward=True, animated=animated)

    def collapse(self, *, animated: bool = True) -> None:
        """从当前进度收拢内容。

        Args:
            animated: 是否播放过渡。
        """
        self._play(target=0.0, forward=False, animated=animated)

    def set_immediate(self, expanded: bool) -> None:
        """取消旧动画并直接应用终态。

        Args:
            expanded: 是否设置为展开状态。
        """
        self._stop_anim()
        self._progress = 1.0 if expanded else 0.0
        self._apply_progress()

    def progress(self) -> float:
        """返回当前展开进度。"""
        return self._progress

    def stop(self) -> None:
        """停止过渡，保留当前边距。"""
        self._stop_anim()

    def _play(self, target: float, forward: bool, animated: bool) -> None:
        """启动边距过渡，按方向选择缓动曲线。"""
        self._forward = forward
        tween_value(
            self,
            "_anim",
            float(self._progress),
            float(target),
            self._on_step,
            duration=self._duration,
            animated=animated,
            easing=self._easing_in if forward else self._easing_out,
            on_finished=lambda: self.finished.emit(forward),
        )

    def _on_step(self, v) -> None:
        """接收过渡帧并应用边距。"""
        try:
            self._progress = float(v)
        except (TypeError, ValueError):
            return
        self._apply_progress()

    def _stop_anim(self) -> None:
        """取消当前边距过渡。"""
        stop_tween(self, "_anim")

    def _apply_progress(self) -> None:
        """按锚点分配额外边距，保持锚点一侧稳定。"""
        if self._layout is None:
            return

        extra = (1.0 - self._progress) * self._delta
        half = extra / 2.0

        l, t, r, b = self._base
        if self._origin == _ORIGIN_CENTER:
            l_, t_, r_, b_ = l + half, t + half, r + half, b + half
        elif self._origin == _ORIGIN_TOP:
            l_, t_, r_, b_ = l + half, t, r + half, b + half
        else:
            l_, t_, r_, b_ = l + half, t + half, r + half, b

        try:
            self._layout.setContentsMargins(int(l_), int(t_), int(r_), int(b_))
        except RuntimeError:
            pass

        self.progress_changed.emit(float(self._progress))

    def squeeze_extra(self) -> tuple[int, int, int, int]:
        """计算当前进度对应的额外边距。

        Returns:
            依次包含左、上、右、下额外像素量的四元组。
        """
        extra = (1.0 - self._progress) * self._delta
        half = extra / 2.0
        if self._origin == _ORIGIN_CENTER:
            return (int(half), int(half), int(half), int(half))
        if self._origin == _ORIGIN_TOP:
            return (int(half), 0, int(half), int(half))

        return (int(half), int(half), int(half), 0)
