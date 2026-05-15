"""hero_side_ui.animation.fade_scale 单元测试

测试 FadeScaleAnimation：
    - play_in 把 progress 推到 1.0
    - play_out 把 progress 推到 0.0
    - scale_value() = scale_min + (1 - scale_min) * progress
    - finished_in / finished_out 信号
    - instant=True 跳过动画
    - apply_opacity_via='effect' 模式创建 GraphicsOpacityEffect
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from hero_side_ui.animation import FadeScaleAnimation


@pytest.fixture
def widget(qtbot):
    w = QWidget()
    qtbot.addWidget(w)
    w.resize(200, 100)
    w.show()
    return w


class TestInitialState:
    def test_initial_progress_zero(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="effect")
        assert fade.progress_value() == 0.0
        # scale_value = 0.95 + (1 - 0.95) * 0 = 0.95
        assert fade.scale_value() == pytest.approx(0.95, abs=0.001)

    def test_effect_mode_creates_opacity_effect(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="effect")
        assert fade._effect is not None
        assert fade._effect.opacity() == pytest.approx(0.0, abs=0.01)


class TestPlayIn:
    def test_play_in_reaches_one(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="effect",
                                  duration_in=80)
        with qtbot.waitSignal(fade.finished_in, timeout=1000):
            fade.play_in()
        assert fade.progress_value() == pytest.approx(1.0, abs=0.001)
        assert fade.scale_value() == pytest.approx(1.0, abs=0.001)
        assert fade._effect.opacity() == pytest.approx(1.0, abs=0.001)

    def test_play_in_instant(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="effect")
        with qtbot.waitSignal(fade.finished_in, timeout=500):
            fade.play_in(instant=True)
        assert fade.progress_value() == 1.0


class TestPlayOut:
    def test_play_out_from_open(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="effect",
                                  duration_in=50, duration_out=50)
        # 先打开
        with qtbot.waitSignal(fade.finished_in, timeout=500):
            fade.play_in()
        # 再关闭
        with qtbot.waitSignal(fade.finished_out, timeout=500):
            fade.play_out()
        assert fade.progress_value() == pytest.approx(0.0, abs=0.001)
        assert fade.scale_value() == pytest.approx(0.95, abs=0.001)


class TestScaleValueRange:
    """scale_value 与 progress 严格线性。"""

    def test_scale_at_half_progress(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="manual",
                                  scale_min=0.5)
        fade._progress = 0.5
        # scale = 0.5 + (1 - 0.5) * 0.5 = 0.75
        assert fade.scale_value() == pytest.approx(0.75, abs=0.001)


class TestWindowMode:
    """apply_opacity_via='window' 改 windowOpacity（不挂 GraphicsOpacityEffect）。"""

    def test_window_mode_no_effect(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="window")
        # 不应创建 GraphicsOpacityEffect
        assert fade._effect is None


class TestManualMode:
    """apply_opacity_via='manual' 也不创建 effect。"""

    def test_manual_mode_no_effect(self, qtbot, widget):
        fade = FadeScaleAnimation(widget, apply_opacity_via="manual")
        assert fade._effect is None
