"""实现页码光标的位置与缩放两阶段过渡。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QSequentialAnimationGroup,
    QVariantAnimation,
)

from ._runner import alive, connect_owned, current, revision, start_runner
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
    on_finished: Callable[[], None] | None = None,
) -> QSequentialAnimationGroup | None:
    """先移动并放大光标，再恢复缩放。

    Args:
        owner: 动画组的 QObject 宿主。
        runner_attr: 保存当前动画组的字段名。
        start_x: 起始横坐标。
        end_x: 目标横坐标。
        on_step: 接收横坐标与缩放比例的回调。
        transition_ms: 每个阶段的毫秒数。
        max_scale: 第一阶段结束时的缩放比例。
        easing: 两个阶段使用的缓动曲线。
        on_finished: 全部阶段完成后执行的回调。

    Returns:
        运行期间有效的动画组；无需过渡或宿主失效时返回 None。
    """
    stop_tween(owner, runner_attr)
    if not alive(owner) or (start_x == end_x and max_scale == 1.0):
        return None

    group = QSequentialAnimationGroup(owner)

    phase_one = QVariantAnimation(group)
    phase_one.setStartValue(0.0)
    phase_one.setEndValue(1.0)
    phase_one.setDuration(int(transition_ms))
    phase_one.setEasingCurve(easing)

    def _phase_one_step(t):
        f = float(t)
        x = start_x + (end_x - start_x) * f
        s = 1.0 + (max_scale - 1.0) * f
        if current(owner, runner_attr, group):
            on_step(x, s)

    connect_owned(phase_one, phase_one.valueChanged, _phase_one_step)
    group.addAnimation(phase_one)

    phase_two = QVariantAnimation(group)
    phase_two.setStartValue(0.0)
    phase_two.setEndValue(1.0)
    phase_two.setDuration(int(transition_ms))
    phase_two.setEasingCurve(easing)

    def _phase_two_step(t):
        f = float(t)
        s = max_scale - (max_scale - 1.0) * f
        if current(owner, runner_attr, group):
            on_step(float(end_x), s)

    connect_owned(phase_two, phase_two.valueChanged, _phase_two_step)
    group.addAnimation(phase_two)

    def _on_done():
        before = revision(owner, runner_attr)
        on_step(float(end_x), 1.0)
        if alive(owner) and revision(owner, runner_attr) == before and on_finished is not None:
            on_finished()

    return start_runner(owner, runner_attr, group, _on_done)
