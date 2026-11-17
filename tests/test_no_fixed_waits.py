"""测试规范：测试里不允许等待一段固定时长，只能等条件成立。

CI 机器的快慢不可预测。`qtbot.wait(450)` 这类写法，机器慢时偶发失败，机器快时白白浪费时间；
`time.sleep` 同理。改用 `tests/_waits.py` 里的 `until`（等条件）或 `flush`（处理已投递的事件）。
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parent
FORBIDDEN_ATTRS = {"wait", "qWait", "sleep", "msleep", "usleep", "processEvents_timeout"}


def _is_fixed_wait(node: ast.Call) -> str | None:
    """返回违规调用的名字；不是固定等待返回 None。"""
    func = node.func
    if isinstance(func, ast.Attribute):
        owner = func.value
        owner_name = owner.id if isinstance(owner, ast.Name) else getattr(owner, "attr", "")
        if func.attr == "wait" and owner_name == "qtbot":
            return "qtbot.wait"
        if func.attr == "qWait" and owner_name == "QTest":
            return "QTest.qWait"
        if func.attr == "sleep" and owner_name == "time":
            return "time.sleep"
        if func.attr in {"msleep", "usleep"}:
            return func.attr
    return None


def test_tests_never_wait_for_a_fixed_duration():
    violations = []
    for path in sorted(ROOT.rglob("*.py")):
        if path == Path(__file__) or "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (name := _is_fixed_wait(node)):
                violations.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno} {name}")
    assert not violations, (
        "测试里不能等固定时长，请改用 tests/_waits.py 的 until / flush：" + ", ".join(violations)
    )
