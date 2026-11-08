"""按铁律 8 口径检查单文件物理行数，供 pre-commit 钩子调用。"""

import sys

MAX_LINES = 1000


def main(paths: list[str]) -> int:
    """检查给定文件的物理行数，返回进程退出码。

    Args:
        paths: 待检查的文件路径；非 .py 入参与已删除的路径会被跳过。

    Returns:
        0 表示全部合规，1 表示存在超过 MAX_LINES 行的文件。
    """
    offenders = []
    for path in paths:
        if not path.endswith(".py"):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                lines = sum(1 for _ in handle)
        except OSError:
            continue
        if lines > MAX_LINES:
            offenders.append((path, lines))
    for path, lines in offenders:
        print(
            f"{path}: {lines} 行 > {MAX_LINES}（口径见 REFACTORING.md 13.7）",
            file=sys.stderr,
        )
    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
