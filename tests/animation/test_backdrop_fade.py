"""hero_side_ui.animation.backdrop_fade 单元测试

BackdropFade: progress 0↔1，play_out 默认 auto_hide。
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from hero_side_ui.animation import BackdropFade


@pytest.fixture
def owner(qtbot):
    w = QWidget()
    qtbot.addWidget(w)
    w.resize(100, 100)
    w.show()
    return w


class TestPlay:
    def test_play_in_reaches_one(self, qtbot, owner):
        fade = BackdropFade(owner, duration_in=80, duration_out=80)
        fade.play_in()
        qtbot.wait(150)
        assert fade.progress_value() == pytest.approx(1.0, abs=0.01)

    def test_play_out_reaches_zero(self, qtbot, owner):
        fade = BackdropFade(owner, duration_in=50, duration_out=50)
        fade.play_in()
        qtbot.wait(100)
        fade.play_out()
        qtbot.wait(100)
        assert fade.progress_value() == pytest.approx(0.0, abs=0.01)


class TestAutoHide:
    def test_play_out_auto_hides_owner(self, qtbot, owner):
        fade = BackdropFade(owner, duration_in=40, duration_out=40, auto_hide_on_out=True)
        fade.play_in()
        qtbot.wait(80)
        assert owner.isVisible()
        fade.play_out()
        qtbot.wait(120)
        assert not owner.isVisible()

    def test_auto_hide_disabled(self, qtbot, owner):
        fade = BackdropFade(owner, duration_in=40, duration_out=40, auto_hide_on_out=False)
        fade.play_in()
        qtbot.wait(80)
        fade.play_out()
        qtbot.wait(120)
        # owner 仍然可见
        assert owner.isVisible()


class TestInterrupt:
    def test_play_in_interrupts_out(self, qtbot, owner):
        """play_out 进行中再调 play_in 应衔接当前 progress 向 1.0 推进。"""
        fade = BackdropFade(owner, duration_in=80, duration_out=200)
        fade.play_in()
        qtbot.wait(120)
        assert fade.progress_value() == pytest.approx(1.0, abs=0.01)
        fade.play_out()
        qtbot.wait(60)  # 关闭进行中
        mid = fade.progress_value()
        assert 0 < mid < 1
        fade.play_in()
        qtbot.wait(150)
        assert fade.progress_value() == pytest.approx(1.0, abs=0.01)
