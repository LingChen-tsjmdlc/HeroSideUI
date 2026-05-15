"""hero_side_ui.animation.collapse 单元测试

测试 CollapseAnimation：
    - 初始 expanded / collapsed 状态对应正确的 maximumHeight / opacity
    - expand() 后 wrapper.maximumHeight 应达到 content.sizeHint().height()
    - collapse() 后 wrapper.maximumHeight == 0
    - finished(bool) 信号正确发射
    - toggle() 切换
    - is_animating / is_expanded 属性
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from hero_side_ui.animation import CollapseAnimation


@pytest.fixture
def wrapper_and_content(qtbot):
    """构造 wrapper(裁剪容器) + content(里面塞 200px 内容)。"""
    wrapper = QWidget()
    qtbot.addWidget(wrapper)
    wrapper.resize(300, 200)

    content = QWidget(wrapper)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel("L" * 10)
    label.setFixedHeight(200)
    layout.addWidget(label)
    content.adjustSize()

    wrapper.show()
    return wrapper, content


class TestInitialState:
    def test_default_collapsed(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=False)
        assert anim.is_expanded is False
        assert wrapper.maximumHeight() == 0
        assert anim._opacity_effect.opacity() == pytest.approx(0.0, abs=0.01)

    def test_initial_expanded(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=True)
        assert anim.is_expanded is True
        assert wrapper.maximumHeight() == 16777215
        assert anim._opacity_effect.opacity() == pytest.approx(1.0, abs=0.01)


class TestExpandCollapse:
    def test_expand_animates_height_up(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=False)
        anim.expand()
        assert anim.is_expanded is True
        assert anim.is_animating
        # 等动画跑完
        with qtbot.waitSignal(anim.finished, timeout=2000) as blocker:
            pass
        assert blocker.args == [True]
        assert anim.is_animating is False
        assert wrapper.maximumHeight() == 16777215

    def test_collapse_animates_height_down(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=True)
        anim.collapse()
        with qtbot.waitSignal(anim.finished, timeout=2000) as blocker:
            pass
        assert blocker.args == [False]
        assert wrapper.maximumHeight() == 0
        assert anim.is_expanded is False

    def test_toggle_flips_state(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=False)

        anim.toggle()
        assert anim.is_expanded is True
        with qtbot.waitSignal(anim.finished, timeout=2000):
            pass

        anim.toggle()
        assert anim.is_expanded is False
        with qtbot.waitSignal(anim.finished, timeout=2000):
            pass
        assert wrapper.maximumHeight() == 0


class TestIdempotent:
    def test_expand_when_already_expanded_no_op(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=True)
        # 已展开且不在动画中 → expand 应直接返回
        anim.expand()
        assert anim.is_animating is False

    def test_collapse_when_already_collapsed_no_op(self, qtbot, wrapper_and_content):
        wrapper, content = wrapper_and_content
        anim = CollapseAnimation(content, wrapper, expanded=False)
        anim.collapse()
        assert anim.is_animating is False
