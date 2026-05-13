"""ScrollStyle 全局滚动条样式测试"""

import pytest
from PySide6.QtCore import QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QScrollBar

from hero_side_ui import ScrollStyle, ThemeProvider


class TestScrollStyleSingleton:
    def test_instance_returns_same_object(self, qtbot):
        a = ScrollStyle.instance()
        b = ScrollStyle.instance()
        assert a is b


class TestScrollStyleDefaults:
    def test_default_values(self, qtbot):
        ss = ScrollStyle.instance()
        assert ss.thickness == 6
        assert ss.hover_thickness == 8  # 6 + 2
        # 默认色 neutral
        assert ss.color == "neutral"

    def test_hover_thickness_computed(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_thickness(10)
        ss.set_hover_thickness_delta(4)
        assert ss.hover_thickness == 14
        # 还原默认
        ss.set_thickness(6)
        ss.set_hover_thickness_delta(2)


class TestScrollStyleSetters:
    def test_set_thickness(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_thickness(8)
        assert ss.thickness == 8
        ss.set_thickness(6)  # 恢复

    def test_set_hover_thickness_delta(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_hover_thickness_delta(3)
        assert ss.hover_thickness == 9  # 6+3
        ss.set_hover_thickness_delta(2)  # 恢复

    def test_set_color_valid(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_color("primary")
        assert ss.color == "primary"
        ss.set_color("neutral")  # 恢复

    def test_set_color_invalid_raises(self, qtbot):
        ss = ScrollStyle.instance()
        with pytest.raises(ValueError):
            ss.set_color("not_a_color")

    def test_set_min_handle_length_clamp(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_min_handle_length(4)  # 最小 8
        assert ss._min_handle_length == 8
        ss.set_min_handle_length(24)  # 恢复

    def test_set_track_padding(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_track_padding(6)
        assert ss._track_padding == 6
        ss.set_track_padding(4)  # 恢复

    def test_set_duration(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_duration(200)
        assert ss._duration == 200
        ss.set_duration(150)  # 恢复

    def test_set_easing(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_easing(QEasingCurve.Type.OutQuad)
        assert ss._easing == QEasingCurve.Type.OutQuad
        ss.set_easing(QEasingCurve.Type.OutCubic)  # 恢复

    def test_set_shadow_alpha(self, qtbot):
        ss = ScrollStyle.instance()
        ss.set_shadow_alpha(light=40, dark=120)
        assert ss._shadow_alpha_light == 40
        assert ss._shadow_alpha_dark == 120
        ss.set_shadow_alpha(light=15, dark=50)  # 恢复


class TestScrollStyleColorRamp:
    """颜色规则：亮 300→400, 暗 700→600"""

    def test_neutral_light(self, qtbot):
        ss = ScrollStyle.instance()
        normal, hover = ss._resolve_handle_colors("neutral", is_dark=False)
        assert normal.name() == "#d4d4d4"  # neutral-300
        assert hover.name() == "#a3a3a3"  # neutral-400

    def test_neutral_dark(self, qtbot):
        ss = ScrollStyle.instance()
        normal, hover = ss._resolve_handle_colors("neutral", is_dark=True)
        assert normal.name() == "#404040"  # neutral-700
        assert hover.name() == "#525252"  # neutral-600

    def test_primary_light(self, qtbot):
        ss = ScrollStyle.instance()
        normal, hover = ss._resolve_handle_colors("primary", is_dark=False)
        assert normal.name() == "#66aaf9"  # primary-300
        assert hover.name() == "#338ef7"  # primary-400


class TestScrollStyleQss:
    """build_qss 生成"""

    def test_build_qss_returns_string(self, qtbot):
        qss = ScrollStyle.instance().build_qss()
        assert isinstance(qss, str)
        assert "QScrollBar" in qss
        assert "::handle" in qss

    def test_build_qss_with_color(self, qtbot):
        qss = ScrollStyle.instance().build_qss(color="primary")
        assert isinstance(qss, str)
        assert "QScrollBar" in qss

    def test_build_qss_no_border_for_custom_color(self, qtbot):
        """自定义色 build_qss 不带 border 阴影"""
        # primary 不是全局色，应无 border
        qss = ScrollStyle.instance().build_qss(color="primary")
        # primary 状态下 handle 段应是 border: none 或没 1px solid
        # 简单检查：无 1px solid rgba 段
        assert "1px solid rgba" not in qss

    def test_build_qss_neutral_has_border(self, qtbot):
        """全局 neutral 色 build_qss 带 border 阴影"""
        ss = ScrollStyle.instance()
        # 确保全局是 neutral
        assert ss.color == "neutral"
        qss = ss.build_qss()  # 默认色 = neutral
        # 应有 1px solid rgba
        assert "1px solid rgba" in qss


class TestScrollStyleApply:
    """apply_global / remove_global"""

    def test_apply_global_injects_qss(self, qtbot):
        app = QApplication.instance()
        ss = ScrollStyle.instance()
        ss.apply_global()
        sheet = app.styleSheet() or ""
        assert "HEROSIDEUI_SCROLLSTYLE_BEGIN" in sheet
        assert "HEROSIDEUI_SCROLLSTYLE_END" in sheet
        assert ss._applied
        # cleanup
        ss.remove_global()

    def test_apply_global_idempotent(self, qtbot):
        """多次 apply_global 不应累加 QSS"""
        app = QApplication.instance()
        ss = ScrollStyle.instance()
        ss.apply_global()
        ss.apply_global()
        ss.apply_global()
        sheet = app.styleSheet() or ""
        assert sheet.count("HEROSIDEUI_SCROLLSTYLE_BEGIN") == 1
        ss.remove_global()

    def test_remove_global_clears_qss(self, qtbot):
        app = QApplication.instance()
        ss = ScrollStyle.instance()
        ss.apply_global()
        ss.remove_global()
        sheet = app.styleSheet() or ""
        assert "HEROSIDEUI_SCROLLSTYLE" not in sheet
        assert not ss._applied


class TestScrollStyleBarColor:
    """set_bar_color: 单条 bar 颜色覆盖"""

    def test_set_bar_color_stores_property(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        ScrollStyle.instance().set_bar_color(bar, "primary")
        assert bar.property("_hs_scroll_color") == "primary"

    def test_set_bar_color_none_clears(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        ScrollStyle.instance().set_bar_color(bar, "primary")
        ScrollStyle.instance().set_bar_color(bar, None)
        assert bar.property("_hs_scroll_color") is None

    def test_set_bar_color_invalid_raises(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        with pytest.raises(ValueError):
            ScrollStyle.instance().set_bar_color(bar, "not_a_color")

    def test_resolve_bar_color_uses_global_when_none(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        ss = ScrollStyle.instance()
        # 没设过 → 走全局
        assert ss._resolve_bar_color(bar) == ss.color

    def test_resolve_bar_color_uses_custom(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        ss = ScrollStyle.instance()
        ss.set_bar_color(bar, "success")
        assert ss._resolve_bar_color(bar) == "success"

    def test_bar_uses_custom_color(self, qtbot):
        edit = QPlainTextEdit()
        qtbot.addWidget(edit)
        bar = edit.verticalScrollBar()
        ss = ScrollStyle.instance()
        # 没设
        assert not ss._bar_uses_custom_color(bar)
        # 设和全局色一样
        ss.set_bar_color(bar, ss.color)
        assert not ss._bar_uses_custom_color(bar)
        # 设不同色
        ss.set_bar_color(bar, "primary")
        assert ss._bar_uses_custom_color(bar)
