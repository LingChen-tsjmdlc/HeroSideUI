"""提供按通道抢占、支持立即终态的单次过渡。"""

import weakref
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QVariantAnimation

from ._runner import alive, connect_owned, current, settle, start_runner, stop_runner

__all__ = ["stop_tween", "tween_geometry", "tween_property", "tween_value"]


def stop_tween(owner: Any, runner_attr: str) -> None:
    """取消通道并释放旧动画，不通知完成。

    Args:
        owner: 通道持有者；Qt 对象已销毁时也可清理。
        runner_attr: 保存动画的字段名。
    """
    stop_runner(owner, runner_attr)


def tween_value(
    owner: Any,
    runner_attr: str,
    start: Any,
    end: Any,
    on_step: Callable[[Any], None],
    *,
    duration: int,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    on_finished: Callable[[], None] | None = None,
    animated: bool = True,
) -> QVariantAnimation | None:
    """从当前值过渡到目标值，先取消通道中的旧请求。

    Args:
        owner: 作为 Qt 父对象和通道持有者的 QObject。
        runner_attr: 保存当前动画的字段名。
        start: 起始值。
        end: 目标值。
        on_step: 每帧接收插值结果的回调。
        duration: 时长，单位为毫秒；非正数时立即完成。
        easing: 插值缓动曲线。
        on_finished: 自然完成或立即完成后执行的回调；取消时不调用。
        animated: 是否播放过渡；False 时先应用目标值。

    Returns:
        运行期间有效的 Qt 动画句柄；无需动画时返回 None。

    Note:
        同值请求不派发帧更新，但会取消旧请求并通知完成；回调中发出的新请求优先。
    """
    stop_tween(owner, runner_attr)
    if not alive(owner):
        return None
    if not animated or duration <= 0:
        settle(owner, runner_attr, lambda: on_step(end), on_finished)
        return None
    if start == end:
        settle(owner, runner_attr, on_finished=on_finished)
        return None
    anim = QVariantAnimation(owner)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(easing)

    owner_ref = weakref.ref(owner)

    def step(value):
        holder = owner_ref()
        if holder is not None and current(holder, runner_attr, anim):
            on_step(value)

    connect_owned(anim, anim.valueChanged, step)
    return start_runner(owner, runner_attr, anim, on_finished)


def tween_property(
    target,
    runner_attr: str,
    property_name: bytes,
    end,
    *,
    duration: int,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    owner=None,
    on_finished: Callable[[], None] | None = None,
    animated: bool = True,
) -> QPropertyAnimation | None:
    """从 Qt 属性当前值过渡到目标值。

    Args:
        target: 持有目标属性的 QObject。
        runner_attr: 通道字段名。
        property_name: Qt 属性名的 ASCII 字节串。
        end: 目标属性值。
        duration: 时长，单位为毫秒；非正数时立即完成。
        easing: 插值缓动曲线。
        owner: 通道持有者；省略时使用 target，普通持有者须支持弱引用。
        on_finished: 完成回调；取消或目标销毁时不调用。
        animated: 是否播放过渡。

    Returns:
        运行期间有效的 Qt 动画句柄；无需动画时返回 None。

    Note:
        QObject 持有者同时作为 Qt 父对象；普通持有者的动画以 target 为父对象。
    """
    owner = target if owner is None else owner
    stop_tween(owner, runner_attr)
    if not alive(owner) or not alive(target):
        return None
    name = property_name.decode("ascii")
    if not animated or duration <= 0:
        settle(owner, runner_attr, lambda: target.setProperty(name, end), on_finished)
        return None
    start = target.property(name)
    if start == end:
        settle(owner, runner_attr, on_finished=on_finished)
        return None
    parent = owner if isinstance(owner, QObject) else target
    anim = QPropertyAnimation(target, property_name, parent)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(easing)
    owner_ref = weakref.ref(owner)

    def target_destroyed():
        holder = owner_ref()
        if holder is not None and current(holder, runner_attr, anim):
            stop_runner(holder, runner_attr)

    connect_owned(anim, target.destroyed, target_destroyed)
    return start_runner(owner, runner_attr, anim, on_finished)


def tween_geometry(
    widget,
    runner_attr: str,
    end_rect,
    *,
    duration: int,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    on_finished: Callable[[], None] | None = None,
    animated: bool = True,
) -> QPropertyAnimation | None:
    """通过公共属性过渡更新控件几何。

    Args:
        widget: 目标控件及通道持有者。
        runner_attr: 保存当前动画的字段名。
        end_rect: 目标 QRect。
        duration: 时长，单位为毫秒。
        easing: 插值缓动曲线。
        on_finished: 完成回调。
        animated: 是否播放过渡。

    Returns:
        运行期间有效的 Qt 动画句柄；无需动画时返回 None。
    """
    return tween_property(
        widget,
        runner_attr,
        b"geometry",
        end_rect,
        duration=duration,
        easing=easing,
        on_finished=on_finished,
        animated=animated,
    )
