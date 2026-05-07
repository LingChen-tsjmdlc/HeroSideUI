"""
Progress 组件示例 - 暗色模式
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Progress, CircularProgress, Spinner


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #d4d4d8; margin-top: 12px;")
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0a0a0b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ecedee"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Progress 示例 - 暗色模式")
    window.resize(820, 1000)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(10)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Progress - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    layout.addWidget(section("Linear · 6 colors"))
    for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
        p = Progress(value=60, color=c, label=c.capitalize(),
                     show_value_label=True, theme="dark")
        layout.addWidget(p)

    layout.addWidget(section("Linear · 3 sizes"))
    for s in ["sm", "md", "lg"]:
        p = Progress(value=65, size=s, color="primary",
                     label=f"Size {s}", show_value_label=True, theme="dark")
        layout.addWidget(p)

    layout.addWidget(section("Linear · 3 radius (none / sm / full)"))
    for r in ["none", "sm", "full"]:
        p = Progress(value=55, color="secondary", radius=r,
                     label=f"radius={r}", show_value_label=True, theme="dark")
        layout.addWidget(p)

    layout.addWidget(section("Linear · striped"))
    for c in ["primary", "success", "warning", "danger"]:
        layout.addWidget(
            Progress(value=70, color=c, is_striped=True,
                     label=f"{c} striped", show_value_label=True, theme="dark")
        )

    layout.addWidget(section("Linear · indeterminate"))
    for c in ["primary", "secondary", "success"]:
        layout.addWidget(
            Progress(is_indeterminate=True, color=c,
                     label=f"{c} loading...", theme="dark")
        )

    layout.addWidget(section("Circular · 6 colors × 3 sizes"))
    ring_row1 = QHBoxLayout()
    ring_row1.setSpacing(24)
    for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
        ring_row1.addWidget(
            CircularProgress(value=65, color=c, size="md",
                             show_value_label=True, label=c.capitalize(),
                             theme="dark")
        )
    ring_row1.addStretch()
    layout.addLayout(ring_row1)

    ring_row2 = QHBoxLayout()
    ring_row2.setSpacing(24)
    for s in ["sm", "md", "lg"]:
        ring_row2.addWidget(
            CircularProgress(value=80, color="primary", size=s,
                             show_value_label=True, label=f"Size {s}",
                             theme="dark")
        )
    ring_row2.addStretch()
    layout.addLayout(ring_row2)

    layout.addWidget(section("Circular · indeterminate"))
    ring_row3 = QHBoxLayout()
    ring_row3.setSpacing(24)
    for c in ["primary", "secondary", "success", "warning", "danger"]:
        ring_row3.addWidget(
            CircularProgress(is_indeterminate=True, color=c, size="md",
                             label=c.capitalize(), theme="dark")
        )
    ring_row3.addStretch()
    layout.addLayout(ring_row3)

    layout.addWidget(section("Spinner (零配置加载)"))
    spin_row = QHBoxLayout()
    spin_row.setSpacing(24)
    spin_row.addWidget(Spinner(theme="dark"))
    spin_row.addWidget(Spinner(color="secondary", size="lg", theme="dark"))
    spin_row.addWidget(Spinner(color="success", label="Loading...", theme="dark"))
    spin_row.addStretch()
    layout.addLayout(spin_row)

    layout.addWidget(section("Dynamic"))
    dyn_p = Progress(value=0, label="Downloading...", show_value_label=True,
                     color="primary", size="md", theme="dark")
    dyn_cp = CircularProgress(value=0, color="primary", size="lg",
                              show_value_label=True, label="Progress",
                              theme="dark")
    row = QHBoxLayout()
    row.setSpacing(24)
    row.addWidget(dyn_p)
    row.addWidget(dyn_cp)
    layout.addLayout(row)

    counter = {"v": 0}
    timer = QTimer()

    def tick():
        counter["v"] = (counter["v"] + 5) % 105
        v = min(100, counter["v"])
        dyn_p.set_value(v)
        dyn_cp.set_value(v)

    timer.timeout.connect(tick)
    timer.start(300)

    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #0a0a0b; }")
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
