"""FontProvider 字体诊断脚本。

启动后立刻打印：

1. ``FontProvider.dump_diagnostics()``。
2. 6 档物理字重对应的 VF 原生 instance 实际效果（``QFontInfo`` resolved）。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontInfo
from PySide6.QtWidgets import QApplication

from hero_side_ui.core import FontProvider, make_qfont

# 6 档物理字重 —— 思源 VF 原生 instance
_WEIGHT_TOKENS = [
    ("extralight", 200),
    ("light", 300),
    ("normal", 400),
    ("medium", 500),
    ("bold", 700),
    ("black", 900),
]


def _run_diagnostics() -> None:
    provider = FontProvider.instance()
    print(provider.dump_diagnostics())

    print()
    print("=" * 72)
    print("[make_qfont] requested weight -> resolved by Qt (QFontInfo)")
    print("=" * 72)
    for name, w in _WEIGHT_TOKENS:
        f = make_qfont(weight=w)
        info = QFontInfo(f)
        print(
            f"  {name:>10} ({w:>3})  req: weight={int(f.weight()):>3} "
            f"styleName={f.styleName()!r:<12}"
            f"  -> actual: family={info.family()!r:<28} "
            f"weight={int(info.weight()):>3} styleName={info.styleName()!r}"
        )
    print("=" * 72)
    print("Diagnostics done. Quit by closing this terminal.")
    QApplication.instance().quit()


def main() -> int:
    app = QApplication(sys.argv)
    QTimer.singleShot(0, _run_diagnostics)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
