"""
Checkbox 组件示例 - 亮色模式
展示 6 种颜色 × 3 尺寸 × 5 圆角，以及 lineThrough / indeterminate / disabled / invalid / CheckboxGroup
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Checkbox, CheckboxGroup


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #3f3f46; margin-top: 12px;")
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Checkbox 示例 - 亮色模式")
    window.resize(820, 900)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(10)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Checkbox - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # --- 颜色 ---
    layout.addWidget(section("6 种颜色（默认选中）"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
        row.addWidget(Checkbox(c.capitalize(), is_selected=True, color=c, theme="light"))
    row.addStretch()
    layout.addLayout(row)

    # --- 尺寸 ---
    layout.addWidget(section("3 种尺寸"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for s in ["sm", "md", "lg"]:
        row.addWidget(Checkbox(f"Size {s}", is_selected=True, color="primary", size=s))
    row.addStretch()
    layout.addLayout(row)

    # --- 圆角 ---
    layout.addWidget(section("5 种圆角"))
    row = QHBoxLayout()
    row.setSpacing(20)
    for r in ["none", "sm", "md", "lg", "full"]:
        row.addWidget(Checkbox(f"radius={r}", is_selected=True, color="secondary", radius=r))
    row.addStretch()
    layout.addLayout(row)

    # --- lineThrough ---
    layout.addWidget(section("lineThrough（选中时 label 加下划线并变暗）"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Buy groceries", is_selected=True, line_through=True, color="success"))
    row.addWidget(Checkbox("Read book", line_through=True, color="primary"))
    row.addWidget(Checkbox("Finish project", is_selected=True, line_through=True, color="danger"))
    row.addStretch()
    layout.addLayout(row)

    # --- indeterminate ---
    layout.addWidget(section("indeterminate 未定态"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Select all", is_indeterminate=True, color="primary"))
    row.addWidget(Checkbox("Partial", is_indeterminate=True, color="success"))
    row.addWidget(Checkbox("Some items", is_indeterminate=True, color="warning"))
    row.addStretch()
    layout.addLayout(row)

    # --- 状态组合 ---
    layout.addWidget(section("状态：disabled / invalid"))
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(Checkbox("Disabled (off)", is_disabled=True, color="primary"))
    row.addWidget(Checkbox("Disabled (on)", is_selected=True, is_disabled=True, color="primary"))
    row.addWidget(Checkbox("Invalid required", is_invalid=True, color="primary"))
    row.addStretch()
    layout.addLayout(row)

    # --- CheckboxGroup vertical ---
    layout.addWidget(section("CheckboxGroup (vertical)"))
    g1 = CheckboxGroup(
        label="Select your favorite frameworks",
        description="You may choose multiple",
        color="primary",
        default_value=["react", "vue"],
    )
    g1.create_checkbox("React", "react")
    g1.create_checkbox("Vue", "vue")
    g1.create_checkbox("Angular", "angular")
    g1.create_checkbox("Svelte", "svelte")
    layout.addWidget(g1)

    # --- CheckboxGroup horizontal, invalid ---
    layout.addWidget(section("CheckboxGroup (horizontal, invalid state)"))
    g2 = CheckboxGroup(
        label="Pick at least one",
        error_message="You must choose at least one option",
        orientation="horizontal",
        color="danger",
        is_required=True,
        is_invalid=True,
    )
    g2.create_checkbox("Email", "email")
    g2.create_checkbox("SMS", "sms")
    g2.create_checkbox("Phone", "phone")
    layout.addWidget(g2)

    layout.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #fafafa; }")
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
