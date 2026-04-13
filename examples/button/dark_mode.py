"""
Button 组件示例 - 暗色模式
展示所有颜色、变体、尺寸、圆角在暗色背景下的效果
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Button


def add_section(layout: QVBoxLayout, title: str, buttons_data: list):
    """添加一个展示区域"""
    label = QLabel(title)
    label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    label.setStyleSheet("color: #a1a1aa; margin-top: 10px; margin-bottom: 2px;")
    layout.addWidget(label)

    row = QHBoxLayout()
    row.setSpacing(10)
    row.setAlignment(Qt.AlignmentFlag.AlignLeft)
    for data in buttons_data:
        row.addWidget(Button(**data))
    layout.addLayout(row)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 暗色调色板
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#27272a"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#3f3f46"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#27272a"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#fafafa"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Button 示例 - 暗色模式")
    window.resize(1000, 780)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("""
        QScrollArea { border: none; background: #18181b; }
        QScrollBar:vertical { width: 8px; background: transparent; }
        QScrollBar::handle:vertical { background: #3f3f46; border-radius: 4px; min-height: 40px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    """)

    main_widget = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(8)
    layout.setContentsMargins(40, 30, 40, 30)

    # 标题
    title = QLabel("Button - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    colors = ["default", "primary", "secondary", "success", "warning", "danger"]

    # 各种变体
    for variant in ["solid", "bordered", "flat", "light", "faded", "ghost"]:
        add_section(layout, variant.capitalize(), [
            {"text": c.capitalize(), "color": c, "variant": variant, "theme": "dark"} for c in colors
        ])

    # 尺寸
    add_section(layout, "Sizes", [
        {"text": "Small", "color": "primary", "size": "sm", "theme": "dark"},
        {"text": "Medium", "color": "primary", "size": "md", "theme": "dark"},
        {"text": "Large", "color": "primary", "size": "lg", "theme": "dark"},
    ])

    # 圆角
    add_section(layout, "Radius", [
        {"text": "None", "color": "primary", "radius": "none", "theme": "dark"},
        {"text": "Small", "color": "primary", "radius": "sm", "theme": "dark"},
        {"text": "Medium", "color": "primary", "radius": "md", "theme": "dark"},
        {"text": "Large", "color": "primary", "radius": "lg", "theme": "dark"},
        {"text": "Full", "color": "primary", "radius": "full", "theme": "dark"},
    ])

    # 禁用
    add_section(layout, "Disabled", [
        {"text": c.capitalize(), "color": c, "is_disabled": True, "theme": "dark"}
        for c in ["primary", "secondary", "success", "warning", "danger"]
    ])

    layout.addStretch()
    main_widget.setLayout(layout)
    scroll.setWidget(main_widget)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
