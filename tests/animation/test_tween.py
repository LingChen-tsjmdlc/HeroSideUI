"""hero_side_ui.animation.tween 单元测试

tween_value / tween_geometry / stop_tween 是组件层最常用的动画样板。
测试关注点：
    - 边界：start == end 时不启动，返回 None
    - 生命周期：动画结束后 owner.<runner_attr> 自动清回 None
    - 抢占：第二次调用应停掉第一次的动画
    - on_step 至少被调用一次，端值应被发射
    - on_finished 回调被触发
    - stop_tween 显式停掉
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from hero_side_ui.animation import tween_value, tween_geometry, stop_tween


class _Owner(QObject):
    """普通的 QObject 持有 runner_attr 即可。"""


# ============================================================
# tween_value
# ============================================================


class TestTweenValueBasic:
    def test_start_equals_end_returns_none(self, qtbot):
        owner = _Owner()
        captured: list = []
        anim = tween_value(owner, "_r", 1.0, 1.0, captured.append, duration=50)
        assert anim is None
        # runner_attr 不应被设置
        assert getattr(owner, "_r", None) is None
        assert captured == []

    def test_runner_set_during_animation(self, qtbot):
        owner = _Owner()
        anim = tween_value(owner, "_r", 0.0, 1.0, lambda v: None, duration=80)
        assert anim is not None
        assert owner._r is anim
        # 等动画跑完
        qtbot.wait(150)

    def test_runner_cleared_after_finish(self, qtbot):
        owner = _Owner()
        anim = tween_value(owner, "_r", 0.0, 1.0, lambda v: None, duration=50)
        qtbot.wait(120)
        # finished 后 runner_attr 应清回 None
        assert owner._r is None
        assert anim.state() == anim.State.Stopped

    def test_on_step_called_with_endpoints(self, qtbot):
        owner = _Owner()
        captured: list[float] = []
        tween_value(owner, "_r", 0.0, 1.0, captured.append, duration=50)
        qtbot.wait(120)
        assert len(captured) > 0
        # 终值应该接近 1.0
        assert captured[-1] == pytest.approx(1.0, abs=0.01)

    def test_on_finished_called(self, qtbot):
        owner = _Owner()
        done = []
        tween_value(
            owner, "_r", 0.0, 1.0, lambda v: None,
            duration=50, on_finished=lambda: done.append(True),
        )
        qtbot.wait(120)
        assert done == [True]


class TestTweenValuePreemption:
    """连续两次调用：第二次应停掉第一次。"""

    def test_second_call_stops_first(self, qtbot):
        owner = _Owner()
        a1 = tween_value(owner, "_r", 0.0, 1.0, lambda v: None, duration=500)
        a2 = tween_value(owner, "_r", 1.0, 0.0, lambda v: None, duration=500)
        assert a1 is not a2
        # owner 现在持有 a2
        assert owner._r is a2
        # 给 Qt 一点时间让 a1 真正停下
        qtbot.wait(30)
        assert a1.state() == a1.State.Stopped
        # 清场：让 a2 结束
        qtbot.wait(600)
        assert owner._r is None


class TestTweenValueQColor:
    """tween_value 同样支持 QColor。"""

    def test_qcolor_endpoints(self, qtbot):
        owner = _Owner()
        captured: list[QColor] = []
        tween_value(
            owner, "_r",
            QColor("#000000"), QColor("#FFFFFF"),
            captured.append, duration=50,
        )
        qtbot.wait(120)
        assert len(captured) > 0
        # 终值应为白色
        last = captured[-1]
        assert last.red() == 255 and last.green() == 255 and last.blue() == 255


# ============================================================
# stop_tween
# ============================================================


class TestStopTween:
    def test_stop_active_animation(self, qtbot):
        owner = _Owner()
        anim = tween_value(owner, "_r", 0.0, 1.0, lambda v: None, duration=1000)
        assert owner._r is anim
        stop_tween(owner, "_r")
        assert owner._r is None
        # 给 Qt 一点时间，确认动画真的停了
        qtbot.wait(30)
        assert anim.state() == anim.State.Stopped

    def test_stop_when_no_animation(self, qtbot):
        """attr 未设置或为 None 时也不能崩。"""
        owner = _Owner()
        # 不存在的 attr
        stop_tween(owner, "_never_set")
        # 已经是 None
        owner._r = None
        stop_tween(owner, "_r")
        # 不抛异常即可


# ============================================================
# tween_geometry
# ============================================================


class TestTweenGeometry:
    def test_geometry_animates_widget(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from PySide6.QtCore import QRect

        w = QWidget()
        qtbot.addWidget(w)
        w.setGeometry(0, 0, 100, 50)

        end_rect = QRect(50, 50, 200, 100)
        anim = tween_geometry(w, "_geo_anim", end_rect, duration=80)
        assert anim is not None
        assert w._geo_anim is anim

        qtbot.wait(150)
        # 终态应到达目标
        assert w.geometry() == end_rect
        # runner_attr 已清空
        assert w._geo_anim is None

    def test_same_geometry_returns_none(self, qtbot):
        from PySide6.QtWidgets import QWidget
        from PySide6.QtCore import QRect

        w = QWidget()
        qtbot.addWidget(w)
        w.setGeometry(0, 0, 100, 50)

        anim = tween_geometry(w, "_geo_anim", QRect(0, 0, 100, 50), duration=50)
        assert anim is None
