"""ARCH-05：登记簿、应用级设施的撤销，以及调用方传入控件的所有权。"""

import os
import subprocess
import sys
import textwrap
import warnings

import pytest
from PySide6.QtWidgets import QLabel, QWidget
from shiboken6 import delete, isValid

from hero_side_ui import Alert, Input, Slider, Textarea, ThemeProvider
from hero_side_ui.core._registry import WidgetRegistry


class Listener(QWidget):
    def __init__(self, fail=None):
        super().__init__()
        self.fail = fail
        self.calls = 0

    def notify(self):
        self.isVisible()  # 访问 C++ 部分，对象已删除时抛 RuntimeError
        self.calls += 1
        if self.fail:
            raise self.fail


# ============================================================
# 登记簿
# ============================================================
class TestWidgetRegistry:
    def test_broadcast_reaches_every_registered_widget(self, qtbot):
        registry = WidgetRegistry("Test")
        a, b = Listener(), Listener()
        for w in (a, b):
            qtbot.addWidget(w)
            registry.add(w)
        registry.broadcast(lambda w: w.notify())
        assert (a.calls, b.calls) == (1, 1)

    def test_destroyed_widget_is_unregistered_silently(self, qtbot):
        registry = WidgetRegistry("Test")
        dead, alive = Listener(), Listener()
        qtbot.addWidget(alive)
        registry.add(dead)
        registry.add(alive)
        delete(dead)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            registry.broadcast(lambda w: w.notify())
        assert alive.calls == 1
        assert len(registry) == 1

    def test_real_errors_warn_once_and_do_not_stop_the_broadcast(self, qtbot):
        registry = WidgetRegistry("Test")
        broken, healthy = Listener(fail=ValueError("boom")), Listener()
        for w in (broken, healthy):
            qtbot.addWidget(w)
            registry.add(w)
        with pytest.warns(RuntimeWarning, match="Listener.*ValueError: boom"):
            registry.broadcast(lambda w: w.notify())
        assert healthy.calls == 1
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            registry.broadcast(lambda w: w.notify())

    def test_membership_and_count(self, qtbot):
        registry = WidgetRegistry("Test")
        w = Listener()
        qtbot.addWidget(w)
        registry.add(w)
        assert w in registry
        assert len(registry) == 1
        registry.discard(w)
        assert w not in registry


def test_theme_provider_keeps_its_registration_contract(qtbot):
    provider = ThemeProvider.instance()
    before = provider.registered_count
    inp = Input()
    qtbot.addWidget(inp)
    assert provider.is_registered(inp)
    assert provider.registered_count > before
    provider.unregister(inp)
    assert not provider.is_registered(inp)


# ============================================================
# 撤销应用级设施
# ============================================================
def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=True,
    )
    return result.stdout.strip()


def test_teardown_restores_the_application_palette():
    out = _run(
        """
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        before = (app.palette().color(QPalette.ColorRole.Window).name(),
                  app.palette().color(QPalette.ColorRole.WindowText).name())
        from hero_side_ui import HeroSideUIProvider, ThemeProvider
        HeroSideUIProvider.setup(app, theme="dark", filter_libpng_warnings=False)
        changed = app.palette().color(QPalette.ColorRole.Window).name()
        HeroSideUIProvider.teardown()
        after = (app.palette().color(QPalette.ColorRole.Window).name(),
                 app.palette().color(QPalette.ColorRole.WindowText).name())
        ThemeProvider.instance().set_mode("light")
        later = app.palette().color(QPalette.ColorRole.Window).name()
        print(before == after, changed != before[0], later == after[0])
        """
    )
    assert out == "True True True"


def test_teardown_removes_the_scrollbar_style_and_can_be_repeated():
    out = _run(
        """
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from hero_side_ui import HeroSideUIProvider
        HeroSideUIProvider.setup(app, filter_libpng_warnings=False)
        installed = "HEROSIDEUI_SCROLLSTYLE_BEGIN" in app.styleSheet()
        HeroSideUIProvider.teardown()
        removed = "HEROSIDEUI_SCROLLSTYLE_BEGIN" not in app.styleSheet()
        HeroSideUIProvider.teardown()
        HeroSideUIProvider.setup(app, filter_libpng_warnings=False)
        again = "HEROSIDEUI_SCROLLSTYLE_BEGIN" in app.styleSheet()
        print(installed, removed, again)
        """
    )
    assert out == "True True True"


def test_teardown_without_setup_does_not_install_anything():
    out = _run(
        """
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from hero_side_ui import HeroSideUIProvider
        HeroSideUIProvider.teardown()
        print(app.styleSheet() == "")
        """
    )
    assert out == "True"


def test_libpng_filter_restores_stderr():
    out = _run(
        """
        import os, sys
        from hero_side_ui.core import _libpng_filter as f
        original = os.fstat(2)
        f.install()
        installed = os.fstat(2) != original or f._installed
        f.uninstall()
        f.uninstall()
        restored = (os.fstat(2).st_ino, os.fstat(2).st_dev) == (original.st_ino, original.st_dev)
        print(installed, f._installed is False, restored)
        """
    )
    assert out == "True True True"


# ============================================================
# 调用方传入的控件
# ============================================================
class TestAlertContent:
    def test_set_replaces_and_destroys_the_old_widget(self, qtbot):
        alert = Alert(title="t")
        qtbot.addWidget(alert)
        first, second = QLabel("a"), QLabel("b")
        alert.set_start_content(first)
        count = alert._layout.count()
        alert.set_start_content(second)
        qtbot.waitUntil(lambda: not isValid(first))
        assert alert._layout.count() == count
        assert alert._layout.indexOf(second) == 0

    def test_end_content_sits_before_the_close_button(self, qtbot):
        alert = Alert(title="t")
        qtbot.addWidget(alert)
        first, second = QLabel("a"), QLabel("b")
        alert.set_end_content(first)
        alert.set_end_content(second)
        qtbot.waitUntil(lambda: not isValid(first))
        assert alert._layout.indexOf(second) == alert._layout.count() - 2

    def test_none_clears_and_constructor_arguments_share_the_setter(self, qtbot):
        start = QLabel("s")
        alert = Alert(title="t", start_content=start)
        qtbot.addWidget(alert)
        assert alert._layout.indexOf(start) == 0
        alert.set_start_content(None)
        qtbot.waitUntil(lambda: not isValid(start))

    def test_setting_the_same_widget_again_keeps_it(self, qtbot):
        alert = Alert(title="t")
        qtbot.addWidget(alert)
        label = QLabel("a")
        alert.set_start_content(label)
        alert.set_start_content(label)
        assert isValid(label)
        assert alert._layout.count(), "layout still holds items"


class TestSliderContent:
    def test_caller_widget_is_handed_back_alive(self, qtbot):
        slider = Slider()
        qtbot.addWidget(slider)
        mine = QLabel("mine")
        slider.set_start_content(mine)
        slider.set_start_content(QLabel("other"))
        assert isValid(mine)
        assert mine.parent() is None

    def test_icon_made_from_a_string_is_destroyed(self, qtbot):
        slider = Slider()
        qtbot.addWidget(slider)
        slider.set_end_content("heroicons--plus-solid")
        icon = slider._end_content_widget
        slider.set_end_content(None)
        qtbot.waitUntil(lambda: not isValid(icon))

    @pytest.mark.parametrize("setter", ["set_top_end_content", "set_bottom_start_content"])
    def test_label_row_slots_hand_the_old_widget_back(self, qtbot, setter):
        slider = Slider(label="x")
        qtbot.addWidget(slider)
        mine = QLabel("mine")
        getattr(slider, setter)(mine)
        getattr(slider, setter)(None)
        assert isValid(mine)


class TestInputSlotsKeepGivingBack:
    def test_input_returns_the_callers_widget(self, qtbot):
        field = Input()
        qtbot.addWidget(field)
        mine = QLabel("mine")
        field.set_start_content(mine)
        field.set_start_content(QLabel("other"))
        assert isValid(mine)

    def test_textarea_returns_the_callers_widget(self, qtbot):
        area = Textarea()
        qtbot.addWidget(area)
        mine = QLabel("mine")
        area.set_top_right_content(mine)
        area.set_top_right_content(QLabel("other"))
        assert isValid(mine)

    def test_textarea_keeps_a_widget_that_is_already_in_its_slot(self, qtbot):
        area = Textarea()
        qtbot.addWidget(area)
        mine = QLabel("mine")
        area.set_top_right_content(mine)
        parent = mine.parent()
        area._apply_styles()
        assert mine.parent() is parent
        assert isValid(mine)
