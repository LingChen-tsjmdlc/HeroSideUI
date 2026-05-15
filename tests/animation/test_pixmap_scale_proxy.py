"""hero_side_ui.animation.pixmap_scale_proxy 单元测试

PixmapScaleProxy: 顶层窗口"整窗 pixmap 缩放"代理。

测试关注点：
    - begin() 抓快照 + 隐藏 content
    - end() 清快照 + 恢复 content
    - is_active() 状态切换
    - enable_predicate 为 False 时 begin 空操作
    - owner 尺寸非法时 begin 空操作
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from hero_side_ui.animation import PixmapScaleProxy


@pytest.fixture
def owner_with_content(qtbot):
    owner = QWidget()
    qtbot.addWidget(owner)
    owner.resize(120, 80)
    lay = QVBoxLayout(owner)
    lay.setContentsMargins(0, 0, 0, 0)
    content = QLabel("Hi")
    content.setFixedSize(120, 80)
    lay.addWidget(content)
    owner.show()
    qtbot.wait(20)
    return owner, content


class TestLifecycle:
    def test_initial_inactive(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: 1.0,
        )
        assert proxy.is_active() is False
        assert proxy.pixmap() is None

    def test_begin_activates_and_hides_content(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: 0.9,
        )
        assert content.isVisible()
        proxy.begin()
        assert proxy.is_active()
        assert proxy.pixmap() is not None
        # content 被隐藏，让 pixmap 取代它
        assert not content.isVisible()

    def test_end_restores_content(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: 0.9,
        )
        proxy.begin()
        proxy.end()
        assert proxy.is_active() is False
        assert proxy.pixmap() is None
        assert content.isVisible()


class TestEnablePredicate:
    def test_predicate_false_makes_begin_noop(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: 0.9,
            enable_predicate=lambda: False,
        )
        proxy.begin()
        assert proxy.is_active() is False
        assert content.isVisible()

    def test_predicate_true_works_normally(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: 0.9,
            enable_predicate=lambda: True,
        )
        proxy.begin()
        assert proxy.is_active()


class TestInvalidSize:
    def test_zero_sized_owner_noop(self, qtbot):
        owner = QWidget()
        qtbot.addWidget(owner)
        owner.resize(0, 0)  # 显式 0 尺寸
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: None,
            scale_getter=lambda: 1.0,
        )
        proxy.begin()
        # 应空操作
        assert proxy.is_active() is False


class TestDraw:
    def test_draw_blits_pixmap_with_scale(self, qtbot, owner_with_content):
        owner, content = owner_with_content
        scale = [0.5]
        proxy = PixmapScaleProxy(
            owner,
            content_widget_getter=lambda: content,
            scale_getter=lambda: scale[0],
        )
        proxy.begin()
        assert proxy.pixmap() is not None

        # 在外部 canvas 上调 draw，验证不抛
        canvas = QImage(120, 80, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(QColor("white"))
        p = QPainter(canvas)
        proxy.draw(p, QRect(0, 0, 120, 80), anchor=(60, 40))
        p.end()
        # 不抛就算 pass（视觉验证靠 examples）
