"""Skeleton 组件测试"""

from __future__ import annotations

import pytest

from PySide6.QtWidgets import QWidget

from hero_side_ui import Skeleton

RADII = ("none", "sm", "md", "lg", "full")


class TestSkeletonInit:
    def test_default_no_args(self, qtbot):
        s = Skeleton()
        qtbot.addWidget(s)
        assert s.is_loaded() is False
        assert s._disable_animation is False
        assert s._radius == "lg"

    def test_with_parent(self, qtbot):
        parent = QWidget()
        s = Skeleton(parent=parent)
        qtbot.addWidget(parent)
        assert s.parent() is parent

    def test_is_loaded_true(self, qtbot):
        s = Skeleton(is_loaded=True)
        qtbot.addWidget(s)
        assert s.is_loaded() is True

    def test_disable_animation(self, qtbot):
        s = Skeleton(disable_animation=True)
        qtbot.addWidget(s)
        assert s._disable_animation is True

    def test_no_shimmer_when_loaded(self, qtbot):
        s = Skeleton(is_loaded=True)
        qtbot.addWidget(s)
        assert not s._shimmer.is_running()

    def test_no_shimmer_when_disable_animation(self, qtbot):
        s = Skeleton(disable_animation=True)
        qtbot.addWidget(s)
        assert not s._shimmer.is_running()


class TestSkeletonRadius:
    @pytest.mark.parametrize("radius", RADII)
    def test_all_radii(self, qtbot, radius):
        s = Skeleton(radius=radius)
        qtbot.addWidget(s)
        assert s._radius == radius


class TestSkeletonSetters:
    def test_set_loaded_true(self, qtbot):
        s = Skeleton()
        qtbot.addWidget(s)
        s.set_loaded(True)
        assert s.is_loaded() is True
        assert not s._shimmer.is_running()

    def test_set_loaded_false(self, qtbot):
        s = Skeleton(is_loaded=True)
        qtbot.addWidget(s)
        s.set_loaded(False)
        assert s.is_loaded() is False

    def test_set_loaded_idempotent(self, qtbot):
        s = Skeleton(is_loaded=True)
        qtbot.addWidget(s)
        s.set_loaded(True)  # same state
        assert s.is_loaded() is True

    def test_set_disable_animation(self, qtbot):
        s = Skeleton()
        qtbot.addWidget(s)
        s.set_disable_animation(True)
        assert s._disable_animation is True
        assert not s._shimmer.is_running()

    def test_set_radius(self, qtbot):
        s = Skeleton(radius="sm")
        qtbot.addWidget(s)
        s.set_radius("full")
        assert s._radius == "full"

    def test_set_child(self, qtbot):
        s = Skeleton()
        qtbot.addWidget(s)
        child = QWidget()
        s.set_child(child)
        assert child.parent() is not None


class TestSkeletonTheme:
    def test_auto_theme(self, qtbot):
        s = Skeleton(theme="auto")
        qtbot.addWidget(s)
        assert s._theme_mode == "auto"

    def test_fixed_light_theme(self, qtbot):
        s = Skeleton(theme="light")
        qtbot.addWidget(s)
        assert s._theme == "light"

    def test_fixed_dark_theme(self, qtbot):
        s = Skeleton(theme="dark")
        qtbot.addWidget(s)
        assert s._theme == "dark"

    def test_set_theme(self, qtbot):
        s = Skeleton(theme="light")
        qtbot.addWidget(s)
        s.set_theme("dark")
        assert s._theme == "dark"


class TestSkeletonCombo:
    _RADII = ("sm", "lg", "full")

    @pytest.mark.parametrize("radius", _RADII)
    def test_loaded_combo(self, qtbot, radius):
        s = Skeleton(radius=radius, is_loaded=True)
        qtbot.addWidget(s)
        assert s.is_loaded() is True

    @pytest.mark.parametrize("radius", _RADII)
    def test_unloaded_combo(self, qtbot, radius):
        s = Skeleton(radius=radius, is_loaded=False, disable_animation=True)
        qtbot.addWidget(s)
        assert s.is_loaded() is False
        assert s._disable_animation is True
