"""SmoothScroll 平滑滚动测试"""

import pytest
from PySide6.QtCore import QEasingCurve
from PySide6.QtWidgets import QPlainTextEdit, QScrollArea

from hero_side_ui import SmoothScroll


class TestSmoothScrollAttach:
    def test_attach_returns_filter(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        filt = SmoothScroll.attach(edit)
        assert filt is not None

    def test_attach_idempotent(self, qtbot):
        """同一 area 重复 attach 应返回同一 filter"""
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        f1 = SmoothScroll.attach(edit)
        f2 = SmoothScroll.attach(edit)
        assert f1 is f2

    def test_attach_with_params(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        filt = SmoothScroll.attach(edit, lines_per_step=5, duration=400)
        assert filt is not None
        assert filt._lines_per_step == 5
        assert filt._duration == 400

    def test_attach_non_scrollarea_returns_none(self, qtbot):
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton()
        qtbot.addWidget(btn)
        filt = SmoothScroll.attach(btn)
        assert filt is None


class TestSmoothScrollDetach:
    def test_detach_clears_filter(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        SmoothScroll.attach(edit)
        SmoothScroll.detach(edit)
        # detach 后再 attach 应能重新创建
        f2 = SmoothScroll.attach(edit)
        assert f2 is not None

    def test_detach_unattached_safe(self, qtbot):
        """没 attach 过 detach 不报错"""
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        SmoothScroll.detach(edit)  # 不报错


class TestSmoothScrollGlobalDefault:
    def test_set_global_default_lines_per_step(self, qtbot):
        SmoothScroll.set_global_default(lines_per_step=5)
        assert SmoothScroll._default_lines_per_step == 5
        SmoothScroll.set_global_default(lines_per_step=3)  # 恢复

    def test_set_global_default_duration(self, qtbot):
        SmoothScroll.set_global_default(duration=400)
        assert SmoothScroll._default_duration == 400
        SmoothScroll.set_global_default(duration=300)  # 恢复

    def test_set_global_default_easing(self, qtbot):
        SmoothScroll.set_global_default(easing=QEasingCurve.Type.OutQuad)
        assert SmoothScroll._default_easing == QEasingCurve.Type.OutQuad
        SmoothScroll.set_global_default(easing=QEasingCurve.Type.OutCubic)  # 恢复

    def test_set_global_default_enabled_false(self, qtbot):
        """enabled=False 时 attach 返回 None"""
        SmoothScroll.set_global_default(enabled=False)
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        filt = SmoothScroll.attach(edit)
        assert filt is None
        SmoothScroll.set_global_default(enabled=True)  # 恢复

    def test_attach_uses_global_default(self, qtbot):
        SmoothScroll.set_global_default(lines_per_step=7, duration=250)
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        filt = SmoothScroll.attach(edit)
        assert filt._lines_per_step == 7
        assert filt._duration == 250
        SmoothScroll.set_global_default(lines_per_step=3, duration=300)  # 恢复


class TestSmoothScrollOnScrollArea:
    """ScrollArea 是 QAbstractScrollArea 子类，也能正常 attach"""

    def test_attach_qscrollarea(self, qtbot):
        sa = QScrollArea()
        qtbot.addWidget(sa)
        filt = SmoothScroll.attach(sa)
        assert filt is not None
