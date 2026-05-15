"""Popover 测试 — 注意：popover 是顶层窗口，测试时不调用 .open() 避免抢焦点"""

import pytest
from PySide6.QtWidgets import QPushButton, QLabel

from hero_side_ui import Button, Popover, PopoverContent, ThemeProvider


class TestPopoverInit:
    def test_default(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        assert p._color == "default"
        assert p._size == "md"
        assert p._radius == "md"
        assert p._shadow == "md"
        assert p._placement == "top"
        assert p._backdrop_kind == "transparent"
        assert p.is_open() is False

    def test_invalid_placement_falls_back(self, qtbot):
        p = Popover(placement="weird-place")
        qtbot.addWidget(p)
        assert p._placement == "top"

    @pytest.mark.parametrize("place", [
        "top", "top-start", "top-end",
        "bottom", "bottom-start", "bottom-end",
        "left", "left-start", "left-end",
        "right", "right-start", "right-end",
    ])
    def test_all_placements(self, qtbot, place):
        p = Popover(placement=place)
        qtbot.addWidget(p)
        assert p._placement == place

    @pytest.mark.parametrize("color", [
        "default", "primary", "secondary",
        "success", "warning", "danger",
    ])
    def test_all_colors(self, qtbot, color):
        p = Popover(color=color)
        qtbot.addWidget(p)
        assert p._color == color

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_all_radius(self, qtbot, radius):
        p = Popover(radius=radius)
        qtbot.addWidget(p)
        assert p._radius == radius

    @pytest.mark.parametrize("shadow", ["none", "sm", "md", "lg"])
    def test_all_shadow(self, qtbot, shadow):
        p = Popover(shadow=shadow)
        qtbot.addWidget(p)
        assert p._shadow == shadow

    @pytest.mark.parametrize("backdrop", ["transparent", "opaque", "blur"])
    def test_backdrops(self, qtbot, backdrop):
        p = Popover(backdrop=backdrop)
        qtbot.addWidget(p)
        assert p._backdrop_kind == backdrop


class TestPopoverContent:
    def test_set_content(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        c = PopoverContent()
        c.layout().addWidget(QLabel("hello"))
        p.set_content(c)
        assert p.content() is c

    def test_set_content_replaces_old(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        c1 = PopoverContent()
        p.set_content(c1)
        c2 = PopoverContent()
        p.set_content(c2)
        assert p.content() is c2


class TestPopoverAttach:
    def test_attach_records_trigger(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        btn = QPushButton("trigger")
        qtbot.addWidget(btn)
        p.attach(btn)
        assert p._trigger is btn

    def test_attach_manual_does_not_install_filter(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        btn = QPushButton("trigger")
        qtbot.addWidget(btn)
        p.attach(btn, event="manual")
        assert p._trigger is btn

    def test_attach_does_not_lock_auto_trigger_theme(self, qtbot):
        """Popover 同步 trigger color/variant 时不能把 Button 从 auto 主题注销。"""
        ThemeProvider._reset_for_test()
        provider = ThemeProvider.instance()
        provider.set_mode("light")

        p = Popover(color="primary")
        qtbot.addWidget(p)
        btn = Button("trigger", color="primary", variant="flat")
        qtbot.addWidget(btn)
        assert btn._theme_mode == "auto"
        assert provider.is_registered(btn)

        p.attach(btn)
        assert btn._theme_mode == "auto"
        assert provider.is_registered(btn)

        provider.set_mode("dark")
        assert btn._theme == "dark"
        assert "color: #99c7fb" in btn.styleSheet().lower()
        ThemeProvider._reset_for_test()


class TestPopoverDynamicAPI:
    def test_set_color(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_color("primary")
        assert p._color == "primary"

    def test_set_size(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_size("lg")
        assert p._size == "lg"

    def test_set_radius(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_radius("none")
        assert p._radius == "none"

    def test_set_shadow(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_shadow("lg")
        assert p._shadow == "lg"

    def test_set_placement(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_placement("top-start")
        assert p._placement == "top-start"

    def test_set_placement_invalid_ignored(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_placement("garbage")
        assert p._placement == "top"

    def test_set_backdrop(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_backdrop("blur")
        assert p._backdrop_kind == "blur"

    def test_set_theme(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_theme("dark")
        assert p._theme == "dark"

    def test_set_disabled(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_is_disabled(True)
        assert p._is_disabled is True


class TestFlipPlacement:
    @pytest.mark.parametrize("place,flipped", [
        ("top", "bottom"),
        ("top-start", "bottom-start"),
        ("top-end", "bottom-end"),
        ("bottom", "top"),
        ("bottom-start", "top-start"),
        ("bottom-end", "top-end"),
        ("left", "right"),
        ("left-start", "right-start"),
        ("left-end", "right-end"),
        ("right", "left"),
        ("right-start", "left-start"),
        ("right-end", "left-end"),
    ])
    def test_flip(self, place, flipped):
        assert Popover._flip_placement(place) == flipped
