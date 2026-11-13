"""ARCH-03：公开入口按名称延迟加载，名称表与导出保持一致。"""

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import hero_side_ui
from hero_side_ui import components

ROOT = Path(__file__).resolve().parents[2] / "hero_side_ui"
CORE_NAMES = {"HeroSideUIProvider", "ScrollStyle", "SmoothScroll", "StatePalette", "ThemeProvider"}


def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=True,
    )
    return result.stdout.strip()


def _type_checking_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    names = set()
    for node in tree.body:
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom):
                    names |= {a.asname or a.name for a in child.names}
    return names


def test_export_tables_match_public_names():
    assert set(components._EXPORTS) == set(components.__all__)
    assert _type_checking_names(ROOT / "components" / "__init__.py") == set(components.__all__)
    assert set(hero_side_ui.__all__) == set(components.__all__) | CORE_NAMES
    assert _type_checking_names(ROOT / "__init__.py") == set(components.__all__)


@pytest.mark.parametrize("package", [hero_side_ui, components])
def test_every_public_name_resolves(package):
    missing = [n for n in package.__all__ if getattr(package, n, None) is None]
    assert not missing


def test_unknown_names_raise_attribute_error():
    for package in (hero_side_ui, components):
        with pytest.raises(AttributeError):
            package.NotAComponent  # noqa: B018


def test_star_import_and_dir_cover_all_names():
    namespace: dict = {}
    exec("from hero_side_ui import *", namespace)
    assert set(hero_side_ui.__all__) <= set(namespace)
    assert set(hero_side_ui.__all__) <= set(dir(hero_side_ui))


def test_importing_the_package_loads_no_component():
    out = _run(
        """
        import sys, hero_side_ui
        print(sorted(m for m in sys.modules if m.startswith("hero_side_ui.components.")))
        """
    )
    assert out == "[]"


def test_basic_component_does_not_pull_in_date_or_markdown_stacks():
    out = _run(
        """
        import sys
        from hero_side_ui import Text
        heavy = ["icu", "markdown_it", "mdit_py_plugins", "pygments"]
        loaded = [m for m in heavy if m in sys.modules]
        siblings = sorted(m for m in sys.modules if m.startswith("hero_side_ui.components.")
                          and m.count(".") == 2)
        print(loaded, siblings)
        """
    )
    assert out == "[] ['hero_side_ui.components.text']"


def test_date_components_load_their_own_dependencies_on_demand():
    out = _run(
        """
        import sys
        from hero_side_ui import Calendar
        print("icu" in sys.modules, "markdown_it" in sys.modules)
        """
    )
    assert out == "True False"
