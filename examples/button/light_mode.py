"""
Button 组件示例 - 亮色模式
展示所有颜色、变体、尺寸、圆角的效果
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
    label.setStyleSheet("color: #3f3f46; margin-top: 10px; margin-bottom: 2px;")
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

    # 亮色调色板
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Button 示例 - 亮色模式")
    window.resize(1000, 780)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("""
        QScrollArea { border: none; background: #fafafa; }
        QScrollBar:vertical { width: 8px; background: transparent; }
        QScrollBar::handle:vertical { background: #d4d4d8; border-radius: 4px; min-height: 40px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    """)

    main_widget = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(8)
    layout.setContentsMargins(40, 30, 40, 30)

    # 标题
    title = QLabel("Button - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    colors = ["default", "primary", "secondary", "success", "warning", "danger"]

    # 各种变体
    for variant in ["solid", "bordered", "flat", "light", "faded", "ghost"]:
        add_section(layout, variant.capitalize(), [
            {"text": c.capitalize(), "color": c, "variant": variant} for c in colors
        ])

    # 尺寸
    add_section(layout, "Sizes", [
        {"text": "Small", "color": "primary", "size": "sm"},
        {"text": "Medium", "color": "primary", "size": "md"},
        {"text": "Large", "color": "primary", "size": "lg"},
    ])

    # 圆角
    add_section(layout, "Radius", [
        {"text": "None", "color": "primary", "radius": "none"},
        {"text": "Small", "color": "primary", "radius": "sm"},
        {"text": "Medium", "color": "primary", "radius": "md"},
        {"text": "Large", "color": "primary", "radius": "lg"},
        {"text": "Full", "color": "primary", "radius": "full"},
    ])

    # 禁用
    add_section(layout, "Disabled", [
        {"text": c.capitalize(), "color": c, "is_disabled": True}
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
