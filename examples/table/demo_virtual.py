"""Table 虚拟化示例 — 一万行流畅滚动。

演示 ``is_virtualized=True``：只渲染可视区 ± 缓冲的行，无论数据多大，
内存里始终只有几十个行槽。配合 sticky 表头。
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from hero_side_ui import HeroSideUIProvider, ThemeSwitcher, Title, Table, Text


COLUMNS = [
    {"key": "id", "label": "ID"},
    {"key": "name", "label": "NAME"},
    {"key": "email", "label": "EMAIL"},
    {"key": "score", "label": "SCORE", "align": "end"},
]

N_ROWS = 10000
ROWS = [
    {
        "key": str(i),
        "id": i,
        "name": f"User {i:05d}",
        "email": f"user{i}@example.com",
        "score": (i * 37) % 1000,
    }
    for i in range(1, N_ROWS + 1)
]


class VirtualDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table — 虚拟化（一万行）")
        self.resize(900, 640)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 20, 32, 24)
        root.setSpacing(12)

        from PySide6.QtWidgets import QHBoxLayout
        head = QHBoxLayout()
        title = Title(f"虚拟化：{N_ROWS:,} 行流畅滚动", level=1)
        title.set_color("#006FEE")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(ThemeSwitcher(size="md"))
        root.addLayout(head)

        root.addWidget(Text(
            "只渲染可视区行，滚动时复用行槽。试着拖动滚动条——始终丝滑。",
            size="sm", color="default-400",
        ))

        table = Table(
            color="primary",
            selection_mode="multiple",
            is_virtualized=True,
            is_header_sticky=True,
            max_height=460,
        )
        table.set_columns(COLUMNS)
        table.set_rows(ROWS)
        root.addWidget(table)

        self.setCentralWidget(central)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    HeroSideUIProvider.setup(app, theme="light")
    win = VirtualDemo()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
