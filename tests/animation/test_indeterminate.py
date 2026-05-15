"""hero_side_ui.animation.indeterminate 单元测试

测 IndeterminateBarAnimation 和 SpinAnimation：
    - start 后 is_running True，stop 后 False
    - position / angle 在动画期间会推进
    - 循环动画 setLoopCount(-1)
    - bar_ratio / period 公开 getter
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from hero_side_ui.animation import IndeterminateBarAnimation, SpinAnimation


@pytest.fixture
def owner(qtbot):
    w = QWidget()
    qtbot.addWidget(w)
    w.show()
    return w


# ============================================================
# IndeterminateBarAnimation
# ============================================================


class TestBarBasic:
    def test_initial_position(self, qtbot, owner):
        anim = IndeterminateBarAnimation(owner, bar_ratio=0.4)
        assert anim.position == pytest.approx(-0.4, abs=0.001)
        assert anim.is_running() is False
        assert anim.bar_ratio() == pytest.approx(0.4, abs=0.001)

    def test_start_makes_it_running(self, qtbot, owner):
        anim = IndeterminateBarAnimation(owner, duration=300)
        anim.start()
        assert anim.is_running() is True
        # position 推进
        qtbot.wait(80)
        assert anim.position > -0.4
        anim.stop()
        assert anim.is_running() is False

    def test_stop_freezes_position(self, qtbot, owner):
        anim = IndeterminateBarAnimation(owner, duration=300)
        anim.start()
        qtbot.wait(60)
        anim.stop()
        frozen = anim.position
        qtbot.wait(100)
        # stop 之后 position 不再变化
        assert anim.position == pytest.approx(frozen, abs=0.001)


class TestBarLoop:
    def test_loop_count_infinite(self, qtbot, owner):
        anim = IndeterminateBarAnimation(owner, duration=200)
        assert anim._anim.loopCount() == -1


# ============================================================
# SpinAnimation
# ============================================================


class TestSpinBasic:
    def test_initial_angle_zero(self, qtbot, owner):
        anim = SpinAnimation(owner)
        assert anim.angle == 0.0
        assert anim.is_running() is False

    def test_start_advances_angle(self, qtbot, owner):
        anim = SpinAnimation(owner, duration=300)
        anim.start()
        qtbot.wait(80)
        assert anim.angle > 0
        anim.stop()

    def test_angle_value_getter(self, qtbot, owner):
        anim = SpinAnimation(owner, duration=200)
        anim.start()
        qtbot.wait(50)
        assert anim.angle_value() == anim.angle
        anim.stop()


class TestSpinLoop:
    def test_infinite_loop(self, qtbot, owner):
        anim = SpinAnimation(owner)
        assert anim._anim.loopCount() == -1
