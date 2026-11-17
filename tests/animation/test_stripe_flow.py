"""hero_side_ui.animation.stripe_flow 单元测试

StripeFlowAnimation: 0 → period 的循环 offset。
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from hero_side_ui.animation import StripeFlowAnimation
from tests._waits import flush, until


@pytest.fixture
def owner(qtbot):
    w = QWidget()
    qtbot.addWidget(w)
    w.show()
    return w


class TestStripeFlow:
    def test_initial_state(self, qtbot, owner):
        anim = StripeFlowAnimation(owner, period=32.0, duration=400)
        assert anim.offset == 0.0
        assert anim.period() == pytest.approx(32.0, abs=0.001)
        assert anim.is_running() is False

    def test_start_advances_offset(self, qtbot, owner):
        anim = StripeFlowAnimation(owner, period=64.0, duration=400)
        anim.start()
        assert anim.is_running()
        qtbot.waitUntil(lambda: anim.offset > 0, timeout=5000)
        assert anim.offset > 0
        anim.stop()
        assert anim.is_running() is False

    def test_offset_value_getter_matches_offset(self, qtbot, owner):
        anim = StripeFlowAnimation(owner, period=32.0, duration=300)
        anim.start()
        until(qtbot, lambda: anim.offset > 0)
        assert anim.offset_value() == anim.offset
        anim.stop()

    def test_loop_infinite(self, qtbot, owner):
        anim = StripeFlowAnimation(owner)
        assert anim._anim.loopCount() == -1

    def test_stop_freezes_offset(self, qtbot, owner):
        anim = StripeFlowAnimation(owner, period=32.0, duration=300)
        anim.start()
        until(qtbot, lambda: anim.offset > 0)
        anim.stop()
        frozen = anim.offset
        flush(qtbot)
        assert anim.offset == pytest.approx(frozen, abs=0.001)
