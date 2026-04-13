#!/usr/bin/env python3
"""
Git commit-msg 钩子：根据提交消息自动递增版本号

规则:
  - 默认提交:          z+1  (0.0.1 → 0.0.2)
  - 消息末尾 (y)/(Y):  y+1, z归零  (0.0.2 → 0.1.0)
  - 消息末尾 (x)/(X):  x+1, y和z归零  (0.1.0 → 1.0.0)

支持中英文括号: (y) （y） (Y) （Y） (x) （x） (X) （X）
"""

import re
import subprocess
import sys
from pathlib import Path


def get_current_version(root: Path) -> str:
    """从 pyproject.toml 读取当前版本号"""
    content = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', content)
    return match.group(1) if match else "0.0.0"


def detect_bump_type(message: str) -> str:
    """根据提交消息末尾标记判断版本递增类型"""
    msg = message.rstrip()
    if re.search(r'[（(]\s*[xX]\s*[）)]$', msg):
        return "major"
    if re.search(r'[（(]\s*[yY]\s*[）)]$', msg):
        return "minor"
    return "patch"


def bump_version(version: str, bump_type: str) -> str:
    """递增版本号"""
    x, y, z = (int(p) for p in version.split("."))
    if bump_type == "major":
        return f"{x + 1}.0.0"
    elif bump_type == "minor":
        return f"{x}.{y + 1}.0"
    else:
        return f"{x}.{y}.{z + 1}"


def update_file(path: Path, pattern: str, replacement: str):
    """正则替换文件内容"""
    content = path.read_text(encoding="utf-8")
    content = re.sub(pattern, replacement, content)
    path.write_text(content, encoding="utf-8")


def main():
    # commit-msg 钩子接收消息文件路径作为参数
    if len(sys.argv) < 2:
        print("用法: commit-msg <message-file>")
        sys.exit(0)

    msg_file = Path(sys.argv[1])
    message = msg_file.read_text(encoding="utf-8").strip()

    # 找到项目根目录
    root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip())

    old_version = get_current_version(root)
    bump_type = detect_bump_type(message)
    new_version = bump_version(old_version, bump_type)

    if old_version == new_version:
        sys.exit(0)

    # 更新 pyproject.toml
    update_file(
        root / "pyproject.toml",
        r'version\s*=\s*"\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
    )

    # 更新 hero_side_ui/__init__.py
    update_file(
        root / "hero_side_ui" / "__init__.py",
        r'__version__\s*=\s*"\d+\.\d+\.\d+"',
        f'__version__ = "{new_version}"',
    )

    # 将修改的文件加入暂存区
    subprocess.run(["git", "add", "pyproject.toml", "hero_side_ui/__init__.py"], cwd=root)

    bump_label = {"major": "x (主版本)", "minor": "y (次版本)", "patch": "z (补丁)"}
    print(f"版本号自动递增: {old_version} → {new_version} ({bump_label[bump_type]})")


if __name__ == "__main__":
    main()
