"""hero_side_ui.animation.ripple 单元测试

测试 RippleOverlay 的核心行为：
    - 添加水波纹后 _ripples 列表增长
    - 启用/禁用控制
    - 动画完成后自动清理（_ripples 移除）
    - 父控件 resize 时跟随
    - 禁用状态下 add_ripple 不创建实例
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QEvent
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton

from hero_side_ui.animation import RippleOverlay


@pytest.fixture
def host(qtbot):
    btn = QPushButton("X")
    qtbot.addWidget(btn)
    btn.resize(120, 36)
    btn.show()
    return btn


class TestAddRipple:
    def test_add_creates_single_ripple(self, qtbot, host):
        overlay = RippleOverlay(host)
        assert len(overlay._ripples) == 0
        overlay.add_ripple(QPoint(60, 18))
        assert len(overlay._ripples) == 1

    def test_multiple_ripples_coexist(self, qtbot, host):
        overlay = RippleOverlay(host)
        overlay.add_ripple(QPoint(10, 10))
        overlay.add_ripple(QPoint(80, 20))
        overlay.add_ripple(QPoint(110, 30))
        assert len(overlay._ripples) == 3

    def test_disabled_skips_ripple(self, qtbot, host):
        overlay = RippleOverlay(host, ripple_enabled=False)
        overlay.add_ripple(QPoint(50, 18))
        assert len(overlay._ripples) == 0

    def test_set_enabled_toggle(self, qtbot, host):
        overlay = RippleOverlay(host)
        overlay.set_enabled(False)
        overlay.add_ripple(QPoint(50, 18))
        assert len(overlay._ripples) == 0
        overlay.set_enabled(True)
        overlay.add_ripple(QPoint(50, 18))
        assert len(overlay._ripples) == 1


class TestRippleCleanup:
    """动画跑完后水波纹应从列表中移除。"""

    def test_ripple_removed_after_animation(self, qtbot, host):
        overlay = RippleOverlay(host)
        overlay.add_ripple(QPoint(60, 18))
        assert len(overlay._ripples) == 1
        # ripple duration clamp 在 500~900ms，等 1.2s 足够
        qtbot.wait(1200)
        assert len(overlay._ripples) == 0


class TestColorAndFollowResize:
    def test_set_color_updates_field(self, qtbot, host):
        overlay = RippleOverlay(host)
        red = QColor(255, 0, 0)
        overlay.set_color(red)
        assert overlay._color.red() == 255
        assert overlay._color.green() == 0
        assert overlay._color.blue() == 0

    def test_follows_parent_resize(self, qtbot, host):
        overlay = RippleOverlay(host)
        host.resize(300, 50)
        # eventFilter 处理 ResizeEvent → setGeometry
        qtbot.wait(20)
        assert overlay.width() == 300
        assert overlay.height() == 50


class TestSingleRippleProgress:
    """通过单个 ripple 的 progress 验证动画推进。"""

    def test_progress_advances(self, qtbot, host):
        overlay = RippleOverlay(host)
        overlay.add_ripple(QPoint(60, 18))
        ripple = overlay._ripples[0]
        assert ripple.progress == pytest.approx(0.0, abs=0.05)
        qtbot.wait(200)
        # 200ms 内 progress 应推进过一部分
        assert ripple.progress > 0.1
        qtbot.wait(1200)
        # 跑完后 ripple 已被移除
        assert len(overlay._ripples) == 0
