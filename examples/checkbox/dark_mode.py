"""
Checkbox 组件示例 - 暗色模式
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Checkbox, CheckboxGroup


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #d4d4d8; margin-top: 12px;")
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ecedee"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Checkbox 示例 - 暗色模式")
    window.resize(820, 900)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(10)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Checkbox - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    layout.addWidget(section("6 种颜色（默认选中）"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
        row.addWidget(Checkbox(c.capitalize(), is_selected=True, color=c, theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("3 种尺寸"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for s in ["sm", "md", "lg"]:
        row.addWidget(Checkbox(f"Size {s}", is_selected=True, color="primary", size=s, theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("5 种圆角"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for r in ["none", "sm", "md", "lg", "full"]:
        row.addWidget(Checkbox(f"radius={r}", is_selected=True, color="secondary", radius=r, theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("lineThrough"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Buy groceries", is_selected=True, line_through=True, color="success", theme="dark"))
    row.addWidget(Checkbox("Read book", line_through=True, color="primary", theme="dark"))
    row.addWidget(Checkbox("Finish project", is_selected=True, line_through=True, color="danger", theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("indeterminate 未定态"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Select all", is_indeterminate=True, color="primary", theme="dark"))
    row.addWidget(Checkbox("Partial", is_indeterminate=True, color="success", theme="dark"))
    row.addWidget(Checkbox("Some items", is_indeterminate=True, color="warning", theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("状态：disabled / invalid"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Disabled (off)", is_disabled=True, color="primary", theme="dark"))
    row.addWidget(Checkbox("Disabled (on)", is_selected=True, is_disabled=True, color="primary", theme="dark"))
    row.addWidget(Checkbox("Invalid required", is_invalid=True, color="primary", theme="dark"))
    row.addStretch()
    layout.addLayout(row)

    layout.addWidget(section("CheckboxGroup (vertical)"))
    g1 = CheckboxGroup(
        label="Select your favorite frameworks",
        description="You may choose multiple",
        color="primary",
        default_value=["react", "vue"],
        theme="dark",
    )
    g1.create_checkbox("React", "react")
    g1.create_checkbox("Vue", "vue")
    g1.create_checkbox("Angular", "angular")
    g1.create_checkbox("Svelte", "svelte")
    layout.addWidget(g1)

    layout.addWidget(section("CheckboxGroup (horizontal, invalid)"))
    g2 = CheckboxGroup(
        label="Pick at least one",
        error_message="You must choose at least one option",
        orientation="horizontal",
        color="danger",
        is_required=True,
        is_invalid=True,
        theme="dark",
    )
    g2.create_checkbox("Email", "email")
    g2.create_checkbox("SMS", "sms")
    g2.create_checkbox("Phone", "phone")
    layout.addWidget(g2)

    layout.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #18181b; }")
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
