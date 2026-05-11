"""ThemeProvider 单元测试"""

from __future__ import annotations

import gc

import pytest
from PySide6.QtWidgets import QWidget

from hero_side_ui import ThemeProvider, Button, Divider, Card, Checkbox, Input
from hero_side_ui.core.theme_provider import VALID_MODES


@pytest.fixture(autouse=True)
def reset_provider():
    """每个测试前后重置 ThemeProvider 单例"""
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


class TestSingleton:
    """单例行为"""

    def test_instance_returns_same_object(self, qtbot):
        p1 = ThemeProvider.instance()
        p2 = ThemeProvider.instance()
        assert p1 is p2

    def test_default_mode_is_auto(self, qtbot):
        p = ThemeProvider.instance()
        assert p.mode == "auto"

    def test_current_theme_is_light_or_dark(self, qtbot):
        p = ThemeProvider.instance()
        assert p.current_theme in ("light", "dark")


class TestSetMode:
    """set_mode 功能"""

    def test_set_mode_light(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("light")
        assert p.mode == "light"
        assert p.current_theme == "light"

    def test_set_mode_dark(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("dark")
        assert p.mode == "dark"
        assert p.current_theme == "dark"

    def test_set_mode_auto(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("dark")
        p.set_mode("auto")
        assert p.mode == "auto"
        # auto 模式下 current_theme 取决于系统，但不会是空
        assert p.current_theme in ("light", "dark")

    def test_set_mode_invalid_raises(self, qtbot):
        p = ThemeProvider.instance()
        with pytest.raises(ValueError):
            p.set_mode("invalid")

    def test_set_mode_same_value_does_nothing(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("dark")
        # 信号不应再次发射
        signals = []
        p.theme_changed.connect(lambda t: signals.append(t))
        p.set_mode("dark")  # same
        assert len(signals) == 0


class TestToggle:
    """toggle 功能"""

    def test_toggle_from_light_to_dark(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("light")
        p.toggle()
        assert p.current_theme == "dark"
        assert p.mode == "dark"

    def test_toggle_from_dark_to_light(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("dark")
        p.toggle()
        assert p.current_theme == "light"
        assert p.mode == "light"

    def test_toggle_from_auto(self, qtbot):
        """auto 模式 toggle 后进入手动模式"""
        p = ThemeProvider.instance()
        # auto 模式下 current_theme 是系统值
        old_theme = p.current_theme
        p.toggle()
        # 应该翻转
        expected = "dark" if old_theme == "light" else "light"
        assert p.current_theme == expected
        # 模式变为手动
        assert p.mode in ("light", "dark")


class TestRegisterUnregister:
    """注册/取消注册机制"""

    def test_register_auto_button(self, qtbot):
        p = ThemeProvider.instance()
        btn = Button("Test")  # theme="auto" by default
        qtbot.addWidget(btn)
        assert p.is_registered(btn)

    def test_no_register_for_fixed_theme(self, qtbot):
        p = ThemeProvider.instance()
        btn = Button("Fixed", theme="light")
        qtbot.addWidget(btn)
        assert not p.is_registered(btn)

    def test_unregister(self, qtbot):
        p = ThemeProvider.instance()
        btn = Button("Test")
        qtbot.addWidget(btn)
        assert p.is_registered(btn)
        p.unregister(btn)
        assert not p.is_registered(btn)

    def test_register_requires_set_theme(self, qtbot):
        p = ThemeProvider.instance()
        w = QWidget()
        qtbot.addWidget(w)
        with pytest.raises(TypeError):
            p.register(w)

    def test_weakref_auto_cleanup(self, qtbot):
        """组件销毁后自动从注册表中移除"""
        p = ThemeProvider.instance()
        btn = Button("Temp")
        qtbot.addWidget(btn)
        assert p.registered_count >= 1
        count_before = p.registered_count
        btn.deleteLater()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().processEvents()
        gc.collect()
        # weakref 应已被清理
        assert p.registered_count <= count_before


class TestBroadcast:
    """广播主题变化"""

    def test_auto_buttons_follow_toggle(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("light")  # 先确保 light

        btn1 = Button("A")
        btn2 = Button("B")
        qtbot.addWidget(btn1)
        qtbot.addWidget(btn2)

        assert btn1._theme == "light"
        assert btn2._theme == "light"

        p.toggle()  # → dark
        assert btn1._theme == "dark"
        assert btn2._theme == "dark"

    def test_fixed_buttons_not_affected(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("light")

        btn_auto = Button("Auto")
        btn_fixed = Button("Fixed", theme="dark")
        qtbot.addWidget(btn_auto)
        qtbot.addWidget(btn_fixed)

        p.toggle()
        assert btn_auto._theme == "dark"
        assert btn_fixed._theme == "dark"  # 本来就是 dark，没被改

    def test_mixed_components_follow(self, qtbot):
        """不同类型组件都跟随切换"""
        p = ThemeProvider.instance()
        p.set_mode("light")

        btn = Button("A")
        div = Divider()
        card = Card()
        qtbot.addWidget(btn)
        qtbot.addWidget(div)
        qtbot.addWidget(card)

        p.toggle()
        assert btn._theme == "dark"
        assert div._theme == "dark"
        assert card._theme == "dark"


class TestSetThemeAPI:
    """组件 set_theme API 与 ThemeProvider 的联动"""

    def test_set_theme_auto_registers(self, qtbot):
        p = ThemeProvider.instance()
        btn = Button("X", theme="light")
        qtbot.addWidget(btn)
        assert not p.is_registered(btn)

        btn.set_theme("auto")
        assert p.is_registered(btn)

    def test_set_theme_fixed_unregisters(self, qtbot):
        p = ThemeProvider.instance()
        btn = Button("X")  # auto
        qtbot.addWidget(btn)
        assert p.is_registered(btn)

        btn.set_theme("dark")
        assert not p.is_registered(btn)
        assert btn._theme == "dark"


class TestSignals:
    """信号发射"""

    def test_theme_changed_signal(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("light")

        signals = []
        p.theme_changed.connect(lambda t: signals.append(t))

        p.toggle()
        assert signals == ["dark"]

    def test_mode_changed_signal(self, qtbot):
        p = ThemeProvider.instance()
        signals = []
        p.mode_changed.connect(lambda m: signals.append(m))

        p.set_mode("light")
        p.set_mode("dark")
        assert "light" in signals
        assert "dark" in signals
