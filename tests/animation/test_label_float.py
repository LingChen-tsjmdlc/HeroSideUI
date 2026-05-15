"""hero_side_ui.animation.label_float 单元测试

LabelFloatAnimation: 0↔1 进度，on_progress 回调插值，float_up / fall_down 切换。
"""

from __future__ import annotations

import pytest

from hero_side_ui.animation import LabelFloatAnimation


class TestFloatUpDown:
    def test_initial_state_resting(self, qtbot):
        captured = []
        anim = LabelFloatAnimation(captured.append, duration=80)
        assert anim.is_floated is False
        assert anim.is_animating is False

    def test_float_up_reaches_one(self, qtbot):
        captured: list[float] = []
        anim = LabelFloatAnimation(captured.append, duration=80)
        anim.float_up()
        assert anim.is_floated is True
        # 等动画
        with qtbot.waitSignal(anim.finished, timeout=500) as blocker:
            pass
        assert blocker.args == [True]
        assert captured[-1] == pytest.approx(1.0, abs=0.01)

    def test_fall_down_reaches_zero(self, qtbot):
        captured: list[float] = []
        anim = LabelFloatAnimation(captured.append, duration=80)
        # 先浮起
        anim.float_up()
        with qtbot.waitSignal(anim.finished, timeout=500):
            pass
        # 再回落
        anim.fall_down()
        with qtbot.waitSignal(anim.finished, timeout=500) as blocker:
            pass
        assert blocker.args == [False]
        assert captured[-1] == pytest.approx(0.0, abs=0.01)


class TestSetState:
    def test_set_state_animated(self, qtbot):
        captured: list[float] = []
        anim = LabelFloatAnimation(captured.append, duration=60)
        anim.set_state(True, animate=True)
        assert anim.is_animating
        qtbot.wait(120)
        assert anim.is_floated is True

    def test_set_state_instant(self, qtbot):
        captured: list[float] = []
        anim = LabelFloatAnimation(captured.append, duration=200)
        anim.set_state(True, animate=False)
        # 不应进入动画
        assert anim.is_animating is False
        assert anim.is_floated is True
        # on_progress 应被立即调用为 1.0
        assert captured[-1] == 1.0

        anim.set_state(False, animate=False)
        assert captured[-1] == 0.0


class TestIdempotent:
    def test_float_up_when_already_floated(self, qtbot):
        anim = LabelFloatAnimation(lambda v: None, duration=50)
        anim.set_state(True, animate=False)
        # 已浮起且不在动画中
        anim.float_up()
        assert anim.is_animating is False
