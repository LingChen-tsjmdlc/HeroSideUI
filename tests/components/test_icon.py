"""Icon's real consumers and theme contract; rendering belongs to iconify."""

import pytest
from PySide6.QtGui import QPalette
from pyside_iconify import IconWidget, get_icon_data
from pyside_iconify.core.registry import registry
from pyside_iconify.network import client as network
from pyside_iconify.network.disk_cache import DiskCache
from pyside_iconify.network.downloader import DownloadResult

from hero_side_ui import Button, Icon, ThemeProvider, ThemeSwitcher
from hero_side_ui.core import resolve_text_color
from hero_side_ui.icons import resolve_icon


@pytest.mark.parametrize(
    "size,expected", [("sm", 16), ("md", 24), ("lg", 32), (20, 20), ("1em", None)]
)
def test_native_widget_and_size_tokens(qtbot, size, expected):
    icon = Icon("heroicons--eye-solid", size=size, theme="light")
    qtbot.addWidget(icon)
    assert isinstance(icon, IconWidget)
    if expected:
        assert icon.sizeHint().width() == expected
    icon.set_size("lg")
    assert icon.sizeHint().width() == 32
    icon.setSize("sm")
    assert icon.sizeHint().width() == 16


def test_theme_auto_and_local_override(qtbot):
    provider = ThemeProvider.instance()
    provider.set_mode("light")
    automatic = Icon("heroicons--eye-solid")
    fixed = Icon("heroicons--eye-solid", theme="light")
    qtbot.addWidget(automatic)
    qtbot.addWidget(fixed)
    provider.set_mode("dark")
    assert automatic.palette().color(QPalette.ColorRole.WindowText) == resolve_text_color(
        None, "dark"
    )
    assert fixed.palette().color(QPalette.ColorRole.WindowText) == resolve_text_color(None, "light")
    provider.set_mode("light")
    assert automatic.palette().color(QPalette.ColorRole.WindowText) == resolve_text_color(
        None, "light"
    )
    provider.set_mode("dark")
    assert automatic.palette().color(QPalette.ColorRole.WindowText) == resolve_text_color(
        None, "dark"
    )
    fixed.set_theme("auto")
    assert provider.is_registered(fixed)
    fixed.set_theme("light")
    assert not provider.is_registered(fixed)


def test_explicit_theme_selects_native_theme_colors(qtbot):
    icon = Icon(
        "heroicons--check-solid", color_light_theme="red", color_dark_theme="blue", theme="dark"
    )
    qtbot.addWidget(icon)
    icon.show()
    image = icon.grab().toImage()
    pixels = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
    assert any(c.blue() > 200 and c.red() < 50 and c.alpha() > 200 for c in pixels)


def test_native_options_and_strict_keywords(qtbot):
    icon = Icon(
        "heroicons--eye-solid", color="primary", hover_color="danger", spin=True, is_disabled=True
    )
    qtbot.addWidget(icon)
    assert not icon.isEnabled()
    icon.set_color("success")
    icon.set_icon("heroicons--check-solid")
    assert icon.iconName() == resolve_icon("heroicons--check-solid")
    icon.setAnimation(None)
    with pytest.raises(TypeError):
        Icon("heroicons--eye-solid", wrong_color="red")
    with pytest.raises(ValueError):
        Icon("heroicons--eye-solid", theme="wrong")


def test_bundled_widget_survives_registry_eviction_without_network(qtbot, monkeypatch):
    icon = Icon("heroicons--eye-solid", theme="light")
    qtbot.addWidget(icon)
    registry.clear()  # Test-only simulation of the shared data cache being evicted.
    monkeypatch.setattr(
        network, "default_client", lambda: pytest.fail("local icon attempted network")
    )
    icon.show()
    icon.grab()
    assert get_icon_data(icon.iconName()).body


def test_bundled_widgets_with_fallback_survive_single_entry_cache(qtbot, monkeypatch):
    monkeypatch.setattr(registry, "_limit", 1)
    monkeypatch.setattr(
        network, "default_client", lambda: pytest.fail("local icon attempted network")
    )
    first = Icon("heroicons--check-solid", fallback="heroicons--eye-solid", theme="light")
    second = Icon("heroicons--clock", theme="light")
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.show()
    second.show()
    for widget in (first, second, first):
        assert not widget.grab().isNull()
        assert get_icon_data(widget.iconName()).body


def test_explicit_local_fallback_with_offline_missing_remote(qtbot, monkeypatch, tmp_path):
    client = network.IconifyClient(offline=True, cache=DiskCache(directory=tmp_path))
    monkeypatch.setattr(network, "default_client", lambda: client)
    icon = Icon(
        "hsui-missing:unknown", fallback="heroicons--check-solid", color="red", theme="light"
    )
    qtbot.addWidget(icon)
    icon.show()
    image = icon.grab().toImage()
    assert any(
        image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 50
        for x in range(image.width())
        for y in range(image.height())
    )


def test_local_and_online_icons_coexist_with_native_api(qtbot, monkeypatch, tmp_path):
    client = network.default_client()
    assert not client.is_offline()
    monkeypatch.setattr(client, "_cache", DiskCache(directory=tmp_path))
    calls = []

    def respond(prefix, names):
        calls.append((prefix, frozenset(names)))
        client._downloader.resultReady.emit(
            DownloadResult(
                prefix=prefix,
                names=frozenset(names),
                width=24,
                height=24,
                icons={
                    name: {"body": '<path fill="currentColor" d="M0 0h24v24H0z"/>'}
                    for name in names
                },
            )
        )

    monkeypatch.setattr(client._downloader, "fetch", respond)
    local = Icon("heroicons--eye-solid")
    qtbot.addWidget(local)
    local.show()
    qtbot.wait(20)
    assert calls == []
    # Unique names also keep this test independent of the in-memory registry.
    prefix = "hsui-" + tmp_path.name.lower().replace("_", "-")
    online = Icon(prefix + ":online-wrapper")
    native = IconWidget(prefix + ":online-native")
    qtbot.addWidget(online)
    qtbot.addWidget(native)
    online.show()
    native.show()
    qtbot.waitUntil(
        lambda: (
            {name for _, names in calls for name in names} == {"online-wrapper", "online-native"}
        ),
        timeout=2000,
    )
    assert {name for _, names in calls for name in names} == {"online-wrapper", "online-native"}
    assert get_icon_data(prefix + ":online-wrapper").body
    assert not client.is_offline()


def test_existing_button_and_switcher_use_the_same_offline_data(qtbot, monkeypatch):
    monkeypatch.setattr(
        network, "default_client", lambda: pytest.fail("built-in consumer attempted network")
    )
    button = Button("Save", icon="heroicons--check-solid", theme="light")
    switcher = ThemeSwitcher()
    qtbot.addWidget(button)
    qtbot.addWidget(switcher)
    assert not button.icon().isNull()
    assert not switcher.icon().isNull()
    button.set_theme("dark")
    button.set_color("danger")
    assert not button.icon().isNull()
