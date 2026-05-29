"""HeroUI 招牌 cursor 滑动 + 弹簧动画 (两阶段)。

对齐 use-pagination.ts 的 scrollTo 实现:
  - 阶段一 (0~300ms): translateX(start_x → end_x) + scale 1.0 → 1.1
  - 阶段二 (300~600ms): scale 1.1 → 1.0 (位置已锁定 end_x)

API:
  start_cursor_slide(owner, runner_attr, start_x, end_x, on_step, *,
                     transition_ms=300, max_scale=1.1, easing=OutCubic,
                     on_finished=None) -> Optional[QSequentialAnimationGroup]

  on_step(x, scale) 每帧回调,调用方在自绘时直接使用。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QSequentialAnimationGroup,
    QVariantAnimation,
)

from .tween import stop_tween

__all__ = ["start_cursor_slide"]


def start_cursor_slide(
    owner: Any,
    runner_attr: str,
    start_x: float,
    end_x: float,
    on_step: Callable[[float, float], None],
    *,
    transition_ms: int = 300,
    max_scale: float = 1.1,
    easing: QEasingCurve.Type = QEasingCurve.OutCubic,
    on_finished: Optional[Callable[[], None]] = None,
) -> Optional[QSequentialAnimationGroup]:
    """启动两阶段 cursor 动画。"""
    if start_x == end_x and max_scale == 1.0:
        return None

    stop_tween(owner, runner_attr)

    group = QSequentialAnimationGroup(owner)

    # 阶段一: 单条 0~1 进度同时驱动 x + scale 1.0 → max_scale
    phase_one = QVariantAnimation(group)
    phase_one.setStartValue(0.0)
    phase_one.setEndValue(1.0)
    phase_one.setDuration(int(transition_ms))
    phase_one.setEasingCurve(easing)

    def _phase_one_step(t):
        f = float(t)
        x = start_x + (end_x - start_x) * f
        s = 1.0 + (max_scale - 1.0) * f
        on_step(x, s)

    phase_one.valueChanged.connect(_phase_one_step)
    group.addAnimation(phase_one)

    # 阶段二: scale max_scale → 1.0,x 锁定 end_x
    phase_two = QVariantAnimation(group)
    phase_two.setStartValue(0.0)
    phase_two.setEndValue(1.0)
    phase_two.setDuration(int(transition_ms))
    phase_two.setEasingCurve(easing)

    def _phase_two_step(t):
        f = float(t)
        s = max_scale - (max_scale - 1.0) * f
        on_step(float(end_x), s)

    phase_two.valueChanged.connect(_phase_two_step)
    group.addAnimation(phase_two)

    def _on_done():
        if getattr(owner, runner_attr, None) is group:
            setattr(owner, runner_attr, None)
        try:
            on_step(float(end_x), 1.0)
        except Exception:
            pass
        if on_finished is not None:
            on_finished()

    group.finished.connect(_on_done)
    setattr(owner, runner_attr, group)
    group.start()
    return group
