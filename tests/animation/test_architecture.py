"""Executable boundaries of ARCH-01; semantic effects live in animation/."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "hero_side_ui"


def calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    aliases = {
        alias.asname or alias.name: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        yield aliases.get(name, name), node.lineno


def test_components_use_shared_transition_entry_points():
    violations = []
    for directory in (ROOT / "components", ROOT / "_shared"):
        for path in directory.rglob("*.py"):
            for name, line in calls(path):
                if name in ("QPropertyAnimation", "QVariantAnimation"):
                    violations.append(f"{path.relative_to(ROOT)}:{line}")
    assert not violations, (
        "Use animation/ drivers or define a shared semantic effect: " + ", ".join(violations)
    )


def test_repeating_interpolation_has_one_implementation():
    owners = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.py")
        for name, _ in calls(path)
        if name == "setLoopCount"
    }
    assert owners == {"animation/loop.py"}


def test_old_selector_paths_only_reexport_the_shared_button():
    from hero_side_ui._shared.selection import SelectorButton
    from hero_side_ui.components.autocomplete._selector_button import _SelectorButton as A
    from hero_side_ui.components.select._selector_button import _SelectorButton as S

    assert A is S is SelectorButton
