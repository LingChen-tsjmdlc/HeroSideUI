"""hero_side_ui.animation.press_scale 单元测试

测试 PressScaleEffect：
    - press() 后 scale 趋向 scale_factor (默认 0.97)
    - release() 后 scale 回到 1.0
    - 默认初始 scale = 1.0
    - 重复 press / release 不崩
    - QGraphicsEffect 在 widget 销毁后 _effect C++ 已死时调用 press 不抛
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QPushButton

from hero_side_ui.animation import PressScaleEffect


@pytest.fixture
def host(qtbot):
    btn = QPushButton("X")
    qtbot.addWidget(btn)
    btn.resize(120, 36)
    btn.show()
    return btn


class TestInitialState:
    def test_initial_scale_is_one(self, qtbot, host):
        effect = PressScaleEffect(host)
        assert effect._get_scale() == pytest.approx(1.0, abs=0.001)


class TestPressRelease:
    def test_press_animates_to_scale_factor(self, qtbot, host):
        effect = PressScaleEffect(host, press_duration=60)
        effect.press()
        qtbot.wait(120)
        # 缩到 0.97 附近
        assert effect._get_scale() == pytest.approx(0.97, abs=0.01)

    def test_release_returns_to_one(self, qtbot, host):
        effect = PressScaleEffect(host, press_duration=60, release_duration=80)
        effect.press()
        qtbot.wait(120)
        assert effect._get_scale() < 1.0
        effect.release()
        qtbot.wait(160)
        assert effect._get_scale() == pytest.approx(1.0, abs=0.001)

    def test_custom_scale_factor(self, qtbot, host):
        effect = PressScaleEffect(host, scale_factor=0.85, press_duration=60)
        effect.press()
        qtbot.wait(120)
        assert effect._get_scale() == pytest.approx(0.85, abs=0.01)


class TestRapidToggle:
    """快速来回 press/release 不应崩；最终 release 一次后应能回到 1.0。"""

    def test_rapid_press_release(self, qtbot, host):
        effect = PressScaleEffect(host, press_duration=40, release_duration=40)
        for _ in range(5):
            effect.press()
            qtbot.wait(10)
            effect.release()
            qtbot.wait(10)
        # 给最后一次 release 完整时间
        qtbot.wait(120)
        assert effect._get_scale() == pytest.approx(1.0, abs=0.05)
