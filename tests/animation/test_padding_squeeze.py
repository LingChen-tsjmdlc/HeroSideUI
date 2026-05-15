"""hero_side_ui.animation.padding_squeeze 单元测试

PaddingSqueezeAnimation: 通过 QLayout.contentsMargins 实现"内容挤压扩张"动画。
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget, QHBoxLayout

from hero_side_ui.animation import PaddingSqueezeAnimation


@pytest.fixture
def layout(qtbot):
    """返回 layout 并把 host widget 也注册给 qtbot 防止 GC。"""
    host = QWidget()
    qtbot.addWidget(host)
    lay = QHBoxLayout(host)
    # 把 host 也挂到 layout 上当弱引用，避免 fixture 返回后 host 被 GC
    lay._test_host = host  # type: ignore[attr-defined]
    return lay


class TestInit:
    def test_default_progress_is_one(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(8, 8, 8, 8), delta=10)
        assert anim.progress() == 1.0

    def test_invalid_origin_raises(self, qtbot, layout):
        with pytest.raises(ValueError):
            PaddingSqueezeAnimation(layout, origin="diagonal")


class TestExpandCollapse:
    def test_expand_drives_progress_to_one(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(8, 8, 8, 8),
                                       delta=10, duration=80)
        anim.set_immediate(False)  # 起点 progress=0
        assert anim.progress() == 0.0
        with qtbot.waitSignal(anim.finished, timeout=500) as blocker:
            anim.expand()
        assert blocker.args == [True]
        assert anim.progress() == pytest.approx(1.0, abs=0.01)

    def test_collapse_drives_progress_to_zero(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(8, 8, 8, 8),
                                       delta=10, duration=80)
        # 起点是 1.0
        with qtbot.waitSignal(anim.finished, timeout=500) as blocker:
            anim.collapse()
        assert blocker.args == [False]
        assert anim.progress() == pytest.approx(0.0, abs=0.01)


class TestSetImmediate:
    def test_set_immediate_no_animation(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(8, 8, 8, 8), delta=10)
        anim.set_immediate(False)
        assert anim.progress() == 0.0
        # margins 应被立即应用：collapse 时四边各加 5（center origin）
        m = layout.contentsMargins()
        # base 8 + extra 5 = 13
        assert m.left() == 13 and m.top() == 13 and m.right() == 13 and m.bottom() == 13


class TestSqueezeExtraGeometry:
    """squeeze_extra() 应该与 _apply_progress 中加到 margins 的逻辑保持一致。"""

    def test_center_origin_uniform(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(0, 0, 0, 0),
                                       delta=10, origin="center")
        anim.set_immediate(False)
        # extra=10, half=5，四边各加 5
        assert anim.squeeze_extra() == (5, 5, 5, 5)

    def test_top_origin_keeps_top_zero(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(0, 0, 0, 0),
                                       delta=10, origin="top")
        anim.set_immediate(False)
        l, t, r, b = anim.squeeze_extra()
        assert t == 0  # top 锚定
        assert l == r == b == 5

    def test_bottom_origin_keeps_bottom_zero(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(0, 0, 0, 0),
                                       delta=10, origin="bottom")
        anim.set_immediate(False)
        l, t, r, b = anim.squeeze_extra()
        assert b == 0  # bottom 锚定
        assert l == t == r == 5

    def test_fully_expanded_zero_extra(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(0, 0, 0, 0),
                                       delta=10, origin="center")
        anim.set_immediate(True)
        assert anim.squeeze_extra() == (0, 0, 0, 0)


class TestProgressChangedSignal:
    def test_progress_changed_emitted_during_animation(self, qtbot, layout):
        anim = PaddingSqueezeAnimation(layout, base_margins=(8, 8, 8, 8),
                                       delta=10, duration=80)
        received: list[float] = []
        anim.progress_changed.connect(received.append)
        anim.set_immediate(False)
        anim.expand()
        qtbot.wait(150)
        assert len(received) > 1
        assert received[-1] == pytest.approx(1.0, abs=0.01)
