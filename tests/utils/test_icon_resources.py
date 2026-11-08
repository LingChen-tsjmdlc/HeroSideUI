"""Shared icon boundary: offline resources, compatibility and dependency rules."""

import ast
from dataclasses import asdict
from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from pyside_iconify import IconData, get_default_config, get_icon_data, set_default_config
from pyside_iconify.network import client as network

from hero_side_ui.icons import builtin_icon_names, get_icon, get_pixmap, resolve_icon
from hero_side_ui.utils import load_svg_icon

ROOT = Path(__file__).resolve().parents[2]


def _legacy_image(source):
    image = QImage(24, 24, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(source.encode("utf-8"))).render(painter)
    painter.end()
    return QPixmap.fromImage(image).toImage()


@pytest.mark.parametrize("name", builtin_icon_names())
def test_every_bundled_icon_is_pixel_compatible_without_client(qtbot, monkeypatch, name):
    def forbidden_client():
        pytest.fail("a bundled icon must not need a network client")

    monkeypatch.setattr(network, "default_client", forbidden_client)
    color = "#e11d48"
    actual = load_svg_icon(name, size=24, color=color)
    source = (ROOT / "hero_side_ui/resources/icons" / (name + ".svg")).read_text(encoding="utf-8")
    expected = _legacy_image(source.replace("currentColor", color))
    assert actual.toImage() == expected


def test_names_are_aliases_in_owned_namespace(qtbot):
    names = ["heroicons--eye-solid", "heroicons:eye-solid", "herosideui:heroicons-eye-solid"]
    assert {resolve_icon(name) for name in names} == {"herosideui:heroicons-eye-solid"}


def test_local_svg_preserves_viewport_and_inherited_paint(qtbot, tmp_path):
    path = tmp_path / "custom.svg"
    path.write_text(
        '<svg viewBox="10 20 16 8" fill="red"><rect x="10" y="20" width="16" height="8"/></svg>'
    )
    data = get_icon_data(resolve_icon(path))
    assert (data.left, data.top, data.width, data.height) == (10, 20, 16, 8)
    assert 'fill="red"' in data.body
    pix = get_pixmap(path, size=(32, 16), color={})
    assert pix.toImage().pixelColor(16, 8).red() == 255


def test_svg_path_changes_do_not_reuse_stale_data(qtbot, tmp_path):
    path = tmp_path / "custom.svg"
    path.write_text('<svg viewBox="0 0 24 24"><path fill="red" d="M0 0h24v24H0z"/></svg>')
    first = resolve_icon(path)
    path.write_text('<svg viewBox="0 0 24 24"><path fill="blue" d="M0 0h24v24H0z"/></svg>')
    assert resolve_icon(path) != first


def test_stroke_variant_does_not_mutate_shared_builtin(qtbot):
    original = resolve_icon("heroicons--chevron-down")
    before = get_icon_data(original)
    variant = resolve_icon(original, stroke_width=3)
    assert variant != original
    assert 'stroke-width="3"' in get_icon_data(variant).body
    assert get_icon_data(original) == before


def test_inline_data_and_explicit_dpr(qtbot):
    data = IconData(body='<path fill="currentColor" d="M0 0h24v24H0z"/>', width=24, height=24)
    pix = get_icon(data, size=24, color="red").pixmap(QSize(24, 24), 2.0)
    assert (pix.width(), pix.height(), pix.devicePixelRatio()) == (48, 48, 2.0)


def test_zero_stroke_remains_pixel_compatible(qtbot):
    pix = load_svg_icon("heroicons--chevron-down", color="red", stroke_width=0).toImage()
    source = (ROOT / "hero_side_ui/resources/icons/heroicons--chevron-down.svg").read_text(
        encoding="utf-8"
    )
    expected = _legacy_image(
        source.replace('stroke-width="1.5"', 'stroke-width="0"').replace("currentColor", "red")
    )
    assert pix == expected


def test_missing_legacy_icon_remains_transparent_without_client(qtbot, monkeypatch):
    monkeypatch.setattr(network, "default_client", lambda: pytest.fail("unexpected client"))
    pix = load_svg_icon("not-a-bundled-icon", color="red")
    assert all(pix.toImage().pixelColor(x, y).alpha() == 0 for x in range(24) for y in range(24))


def test_resources_do_not_change_ecosystem_defaults(qtbot):
    defaults = get_default_config()
    client = network.default_client()
    offline = client.is_offline()
    get_pixmap("heroicons--eye-solid", color="red")
    assert get_default_config() == defaults
    assert client.is_offline() == offline


def test_legacy_colors_do_not_inherit_user_global_tint_or_opacity(qtbot, tmp_path):
    defaults = get_default_config()
    path = tmp_path / "red.svg"
    path.write_text('<svg viewBox="0 0 24 24"><path fill="red" d="M0 0h24v24H0z"/></svg>')
    try:
        set_default_config(
            color="blue", color_light_theme="green", color_dark_theme="yellow", opacity=0.2
        )
        original = load_svg_icon(str(path), color="original").toImage().pixelColor(12, 12)
        assert (original.red(), original.green(), original.blue(), original.alpha()) == (
            255,
            0,
            0,
            255,
        )
        tinted = load_svg_icon("heroicons--check-solid", color="red").toImage()
        assert any(
            tinted.pixelColor(x, y).red() == 255 and tinted.pixelColor(x, y).alpha() == 255
            for x in range(24)
            for y in range(24)
        )
    finally:
        set_default_config(**asdict(defaults))


def test_only_icon_boundary_imports_iconify_public_api():
    for path in (ROOT / "hero_side_ui").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            for module in modules:
                if not module.startswith("pyside_iconify"):
                    continue
                assert module == "pyside_iconify", f"private dependency API: {path}"
                relative = path.relative_to(ROOT / "hero_side_ui").parts
                assert relative[0] == "icons" or relative[:2] == ("components", "icon"), path
