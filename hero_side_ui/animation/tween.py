"""
Tween 动画工具
============

封装两类常用动画样板，避免在组件代码里反复写 "新建动画 → 停旧的 → connect step → 持有 runner 防 GC → finished 时清空 runner" 这一套。

API
---

- ``tween_value(owner, runner_attr, start, end, on_step, *, duration, easing, on_finished=None)``
  通用值过渡（``QVariantAnimation``）。``owner`` 上的 ``runner_attr``
  字段持有当前动画实例；自动停旧 → 起新 → finished 时把 attr 清回 ``None``。
  返回新 anim。``end == start`` 时不启动并返回 ``None``。

- ``stop_tween(owner, runner_attr)``
  显式停掉某条 tween（断点切换样式时清场用）。

- ``tween_geometry(widget, runner_attr, end_rect, *, duration, easing, on_finished=None)``
  ``QPropertyAnimation(widget, b"geometry")`` 版本，行为一致；返回新 anim。

约束
----
- 内部不做相等性比较以外的状态判断；调用方负责语义（如 ``disable_animation``
  下应直接跳到目标值，而非调用本工具）。
- ``on_step`` 接受 ``QVariantAnimation.valueChanged`` 派发的值，类型由
  ``start``/``end`` 推断（QColor / float / int / QRect 等）。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QVariantAnimation

__all__ = ["tween_value", "stop_tween", "tween_geometry"]


def stop_tween(owner: Any, runner_attr: str) -> None:
    """显式停掉 owner.<runner_attr> 上挂的动画。"""
    runner = getattr(owner, runner_attr, None)
    if runner is None:
        return
    try:
        runner.stop()
    except RuntimeError:
        # C++ 端已销毁
        pass
    setattr(owner, runner_attr, None)


def tween_value(
    owner: Any,
    runner_attr: str,
    start: Any,
    end: Any,
    on_step: Callable[[Any], None],
    *,
    duration: int,
    easing: QEasingCurve.Type = QEasingCurve.OutCubic,
    on_finished: Optional[Callable[[], None]] = None,
) -> Optional[QVariantAnimation]:
    """启动一段值过渡（QColor / float / int / 任何 QVariantAnimation 支持的类型）。

    使用模式::

        tween_value(self, "_color_anim_runner",
                    self._current_text_color, target,
                    self._on_color_step,
                    duration=150)

    返回新 anim；若 ``start == end`` 不启动并返回 ``None``。
    """
    if start == end:
        return None

    stop_tween(owner, runner_attr)

    anim = QVariantAnimation(owner)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(on_step)

    def _on_done():
        # 仅当当前 runner 仍是本 anim 时清空（避免被新 tween 覆盖后误清）
        if getattr(owner, runner_attr, None) is anim:
            setattr(owner, runner_attr, None)
        if on_finished is not None:
            on_finished()

    anim.finished.connect(_on_done)
    setattr(owner, runner_attr, anim)
    anim.start()
    return anim


def tween_geometry(
    widget,
    runner_attr: str,
    end_rect,
    *,
    duration: int,
    easing: QEasingCurve.Type = QEasingCurve.OutCubic,
    on_finished: Optional[Callable[[], None]] = None,
) -> Optional[QPropertyAnimation]:
    """启动一段 ``geometry`` 过渡。

    runner_attr 挂在 widget 自身上 —— widget 同时是动画对象和持有者。
    """
    start_rect = widget.geometry()
    if start_rect == end_rect:
        return None

    stop_tween(widget, runner_attr)

    anim = QPropertyAnimation(widget, b"geometry")
    anim.setDuration(duration)
    anim.setStartValue(start_rect)
    anim.setEndValue(end_rect)
    anim.setEasingCurve(easing)

    def _on_done():
        if getattr(widget, runner_attr, None) is anim:
            setattr(widget, runner_attr, None)
        if on_finished is not None:
            on_finished()

    anim.finished.connect(_on_done)
    setattr(widget, runner_attr, anim)
    anim.start()
    return anim
