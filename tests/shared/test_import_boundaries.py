"""ARCH-02 的可执行边界：组件之间的私有依赖与共享层的依赖方向。"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "hero_side_ui"
COMPONENTS = ROOT / "components"

# 有理由保留的跨组件私有依赖：(引用方相对路径, 被引用模块)。当前为空。
ALLOWED_PRIVATE_IMPORTS: set[tuple[str, str]] = set()

# 已清除的私有属性穿透，防止回归：相对 hero_side_ui 的 glob -> 禁止出现的模式。
FORBIDDEN_REACH_THROUGH = {
    "components/select/*.py": [r"\b_listbox\._\w", r"\b_popover\._\w", r"\b_input\._\w"],
    "components/autocomplete/*.py": [r"\b_listbox\._\w", r"\b_popover\._\w", r"\b_input\._\w"],
    "components/dropdown/*.py": [r"\b_listbox\._\w", r"\b_popover\._\w"],
    "components/date_input/date_input.py": [r"\b_state\._\w"],
    "components/date_picker/*.py": [r"\b_state\._\w", r"\b_end_state\._\w"],
    "components/textarea/*.py": [r"\b_label_anim\._\w"],
    "_shared/fields/*.py": [r"\b_label_anim\._\w"],
}


def _module_of(path: Path, node: ast.ImportFrom) -> list[str]:
    """把 import 语句解析为以 hero_side_ui 开头的模块路径。"""
    package = ["hero_side_ui", *path.relative_to(ROOT).parts[:-1]]
    if node.level:
        package = package[: len(package) - (node.level - 1)]
        return package + (node.module.split(".") if node.module else [])
    return node.module.split(".") if node.module else []


def _imports(path: Path, tree: ast.AST | None = None):
    tree = tree or ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            yield node, _module_of(path, node)


def test_components_do_not_import_private_modules_of_other_components():
    violations = []
    for path in sorted(COMPONENTS.rglob("*.py")):
        parts = path.relative_to(COMPONENTS).parts
        if len(parts) < 2:
            continue
        owner = parts[0]
        for node, module in _imports(path):
            if module[:2] != ["hero_side_ui", "components"] or len(module) < 3:
                continue
            target, rest = module[2], module[3:]
            if target == owner:
                continue
            private = any(p.startswith("_") for p in rest) or (
                not rest and any(a.name.startswith("_") for a in node.names)
            )
            rel = path.relative_to(ROOT).as_posix()
            if private and (rel, ".".join(module)) not in ALLOWED_PRIVATE_IMPORTS:
                violations.append(f"{rel}:{node.lineno} -> {'.'.join(module)}")
    assert not violations, "Move the capability to _shared/ or use a public entry: " + ", ".join(
        violations
    )


def test_shared_layer_has_no_runtime_dependency_on_components():
    violations = []
    for path in sorted((ROOT / "_shared").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        type_only = {
            id(child)
            for node in ast.walk(tree)
            if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test)
            for child in ast.walk(node)
        }
        for node, module in _imports(path, tree):
            if id(node) in type_only:
                continue
            if module[:2] == ["hero_side_ui", "components"]:
                violations.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    assert not violations, "_shared must not import components at runtime: " + ", ".join(violations)


def test_private_attribute_reach_through_is_not_reintroduced():
    violations = []
    for pattern, forbidden in FORBIDDEN_REACH_THROUGH.items():
        for path in sorted(ROOT.glob(pattern)):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if any(re.search(p, line) for p in forbidden):
                    violations.append(f"{path.relative_to(ROOT).as_posix()}:{lineno}")
    assert not violations, "Use the owner's public API instead: " + ", ".join(violations)
