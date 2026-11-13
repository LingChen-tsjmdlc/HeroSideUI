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

    def test_live_widget_raising_runtime_error_stays_registered(self, qtbot):
        registry = WidgetRegistry("Test")
        broken, healthy = Listener(fail=RuntimeError("business failure")), Listener()
        for w in (broken, healthy):
            qtbot.addWidget(w)
            registry.add(w)
        with pytest.warns(RuntimeWarning, match="Listener.*RuntimeError: business failure"):
            registry.broadcast(lambda w: w.notify())
        assert broken in registry and isValid(broken)
        assert healthy.calls == 1

    def test_destroyed_widget_raising_runtime_error_is_unregistered(self, qtbot):
        registry = WidgetRegistry("Test")
        dead = Listener()
        registry.add(dead)
        delete(dead)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            registry.broadcast(lambda w: w.notify())
        assert len(registry) == 0

    def test_plain_python_listener_with_runtime_error_is_kept_and_reported(self):
        class Plain:
            def notify(self):
                raise RuntimeError("oops")

        registry = WidgetRegistry("Test")
        plain = Plain()
        registry.add(plain)
        with pytest.warns(RuntimeWarning, match="Plain.*RuntimeError: oops"):
            registry.broadcast(lambda w: w.notify())
        assert plain in registry

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
    """在独立进程中运行代码，隔离全局状态（调色板、样式表、fd）。"""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
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
        import os
        from hero_side_ui.core import _libpng_filter as f
        original = os.fstat(2)
        f.install()
        installed = f._active is not None
        f.uninstall()
        f.uninstall()
        restored = (os.fstat(2).st_ino, os.fstat(2).st_dev) == (original.st_ino, original.st_dev)
        print(installed, f._active is None, restored)
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


# ============================================================
# 调色板的完整往返
# ============================================================
_PALETTE_PRELUDE = """
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
G, R = QPalette.ColorGroup, QPalette.ColorRole
app = QApplication([])

def snapshot():
    pal = app.palette()
    return {
        (g.name, r.name): pal.color(g, r).name()
        for g in (G.Active, G.Inactive, G.Disabled)
        for r in (R.Window, R.WindowText, R.Highlight, R.Button)
    }

def window():
    return app.palette().color(R.Window).name()
"""


def test_teardown_restores_every_color_group_and_keeps_other_roles():
    out = _run(
        _PALETTE_PRELUDE
        + """
host = app.palette()
host.setColor(G.Inactive, R.Window, QColor("#00ff00"))
host.setColor(G.Disabled, R.WindowText, QColor("#ff0000"))
app.setPalette(host)
before = snapshot()

from hero_side_ui import HeroSideUIProvider
HeroSideUIProvider.setup(app, theme="dark", filter_libpng_warnings=False)
# 宿主在 setup 之后改了一个与 HeroSideUI 无关的角色
changed = app.palette()
changed.setColor(R.Highlight, QColor("#123456"))
app.setPalette(changed)
HeroSideUIProvider.teardown()

after = snapshot()
host_role_kept = after[("Active", "Highlight")] == "#123456"
others_untouched = all(
    after[k] == before[k] for k in before if k[1] in ("Window", "WindowText", "Button")
)
print(others_untouched, host_role_kept)
"""
    )
    assert out == "True True"


@pytest.mark.parametrize("second_theme", ["dark", "light"])
def test_setup_after_teardown_resumes_palette_sync(second_theme):
    out = _run(
        _PALETTE_PRELUDE
        + f"""
from hero_side_ui import HeroSideUIProvider, ThemeProvider
HeroSideUIProvider.setup(app, theme="dark", filter_libpng_warnings=False)
HeroSideUIProvider.teardown()
host_window = window()
HeroSideUIProvider.setup(app, theme="{second_theme}", filter_libpng_warnings=False)
applied = window()
ThemeProvider.instance().toggle()
toggled = window()
print(applied != host_window, toggled != applied)
"""
    )
    assert out == "True True"


def test_setup_without_theme_after_teardown_syncs_the_current_mode():
    out = _run(
        _PALETTE_PRELUDE
        + """
from hero_side_ui import HeroSideUIProvider, ThemeProvider
HeroSideUIProvider.setup(app, theme="dark", filter_libpng_warnings=False)
HeroSideUIProvider.teardown()
HeroSideUIProvider.setup(app, filter_libpng_warnings=False)
dark = window()
ThemeProvider.instance().set_mode("light")
print(dark == "#0b0d12", window() == "#fafbfd")
"""
    )
    assert out == "True True"


def test_repeated_setup_and_teardown_cycles_stay_consistent():
    out = _run(
        _PALETTE_PRELUDE
        + """
from hero_side_ui import HeroSideUIProvider
original = snapshot()
results = []
for theme in ("dark", "light", "dark"):
    HeroSideUIProvider.setup(app, theme=theme, filter_libpng_warnings=False)
    results.append(window() == ("#0b0d12" if theme == "dark" else "#fafbfd"))
    HeroSideUIProvider.teardown()
    results.append(snapshot() == original)
print(all(results))
"""
    )
    assert out == "True"


def test_setup_keeps_a_manually_disabled_palette_sync():
    out = _run(
        _PALETTE_PRELUDE
        + """
from hero_side_ui import HeroSideUIProvider, ThemeProvider
HeroSideUIProvider.setup(app, theme="dark", filter_libpng_warnings=False)
ThemeProvider.instance().set_auto_app_palette(False)
HeroSideUIProvider.teardown()
host_window = window()
HeroSideUIProvider.setup(app, theme="light", filter_libpng_warnings=False)
print(window() == host_window)
"""
    )
    assert out == "True"


# ============================================================
# libpng 过滤器的资源所有权
# ============================================================
def test_libpng_filter_does_not_leak_descriptors_across_cycles():
    out = _run(
        """
        import os
        from hero_side_ui.core import _libpng_filter as f
        baseline = os.dup(2); os.close(baseline)
        for _ in range(30):
            f.install()
            f.uninstall()
        probe = os.dup(2); os.close(probe)
        print(probe == baseline)
        """
    )
    assert out == "True"


def test_libpng_filter_drops_only_the_known_warning_and_flushes_the_tail():
    script = textwrap.dedent(
        """
        import os
        from hero_side_ui.core import _libpng_filter as f
        f.install()
        os.write(2, b"libpng warning: iCCP: known incorrect sRGB profile\\n")
        os.write(2, b"keep this line\\n")
        os.write(2, b"tail without newline")
        f.uninstall()
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b"keep this line\ntail without newline"


def test_libpng_filter_install_is_idempotent_and_uninstall_waits_for_the_thread():
    out = _run(
        """
        import threading
        from hero_side_ui.core import _libpng_filter as f
        f.install(); f.install()
        worker = f._active.thread
        f.uninstall()
        print(f._active is None, not worker.is_alive(),
              not any(t.name == "hero_side_ui-libpng-filter" for t in threading.enumerate()))
        """
    )
    assert out == "True True True"


def test_libpng_filter_releases_descriptors_when_installation_fails():
    out = _run(
        """
        import os
        from hero_side_ui.core import _libpng_filter as f
        baseline = os.dup(2); os.close(baseline)
        real_pipe, real_dup2 = os.pipe, os.dup2
        def broken_dup2(*args):
            raise OSError("dup2 failed")
        os.dup2 = broken_dup2
        try:
            for _ in range(10):
                f.install()
        finally:
            os.dup2 = real_dup2
        probe = os.dup(2); os.close(probe)
        print(f._active is None, probe == baseline)
        """
    )
    assert out == "True True"
