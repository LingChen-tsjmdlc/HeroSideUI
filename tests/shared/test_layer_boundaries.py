"""ARCH-03：底层模块不得依赖运行时设施或组件。"""

import ast
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "hero_side_ui"

# 低层包可以依赖的上层包。
FORBIDDEN = {
    "themes": {"core", "components", "utils"},
    "animation": {"core", "components"},
    "icons": {"core", "components"},
    "utils": {"core", "components"},
    "core": {"components"},
}

# 有理由保留的例外：文件 -> 允许依赖的包。
ALLOWED = {
    # 旧静态图标 API 的兼容边界：只读取已存在的 ThemeProvider，不创建。
    "utils/icon_utils.py": {"core"},
}


def _targets(path: Path):
    package = ["hero_side_ui", *path.relative_to(ROOT).parts[:-1]]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            base = package[: len(package) - (node.level - 1)]
            module = base + (node.module.split(".") if node.module else [])
        else:
            module = node.module.split(".") if node.module else []
        if module[:1] == ["hero_side_ui"] and len(module) > 1:
            yield module[1], node.lineno


def test_low_layers_do_not_depend_on_higher_layers():
    violations = []
    for layer, forbidden in FORBIDDEN.items():
        for path in sorted((ROOT / layer).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            allowed = ALLOWED.get(rel, set())
            for target, line in _targets(path):
                if target in forbidden - allowed:
                    violations.append(f"{rel}:{line} -> {target}")
    assert not violations, "Pass values in explicitly or move the code up: " + ", ".join(violations)


def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"},
        check=True,
    )
    return result.stdout.strip()


def test_theme_layer_exposes_only_the_static_default_font_stack():
    import hero_side_ui.themes as themes

    assert themes.DEFAULT_FONT_FAMILY
    assert not hasattr(themes, "FONT_FAMILY")


def test_default_icon_color_does_not_create_the_theme_provider():
    out = _run(
        """
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from hero_side_ui.core import ThemeProvider
        from hero_side_ui.utils import load_svg_icon
        load_svg_icon("heroicons--check-solid", size=16)
        print(ThemeProvider.peek() is None)
        """
    )
    assert out == "True"
