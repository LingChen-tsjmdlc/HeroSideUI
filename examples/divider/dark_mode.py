"""
Divider 组件示例 - 暗色模式
展示水平/垂直分割线、自定义颜色
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Divider


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#fafafa"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Divider 示例 - 暗色模式")
    window.resize(600, 500)

    main_widget = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(16)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Divider - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    # 水平分割线
    section_label = QLabel("水平分割线 (默认)")
    section_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label.setStyleSheet("color: #d4d4d8;")
    layout.addWidget(section_label)

    lbl1 = QLabel("上方内容")
    lbl1.setStyleSheet("color: #d4d4d8;")
    layout.addWidget(lbl1)
    layout.addWidget(Divider(theme="dark"))
    lbl2 = QLabel("下方内容")
    lbl2.setStyleSheet("color: #d4d4d8;")
    layout.addWidget(lbl2)

    # 自定义颜色
    section_label2 = QLabel("自定义颜色分割线")
    section_label2.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label2.setStyleSheet("color: #d4d4d8; margin-top: 12px;")
    layout.addWidget(section_label2)

    colors = ["#338ef7", "#9353d3", "#45d483", "#f7b750", "#f54180"]
    for c in colors:
        layout.addWidget(Divider(theme="dark", color=c))
        layout.addSpacing(4)

    # 带文字的水平分割线
    section_label_text = QLabel("带文字的分割线")
    section_label_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label_text.setStyleSheet("color: #d4d4d8; margin-top: 12px;")
    layout.addWidget(section_label_text)

    lbl_head = QLabel("Sign in with your account")
    lbl_head.setStyleSheet("color: #d4d4d8;")
    layout.addWidget(lbl_head)
    layout.addWidget(Divider(theme="dark", text="OR"))
    lbl_tail = QLabel("Sign in with social providers")
    lbl_tail.setStyleSheet("color: #d4d4d8;")
    layout.addWidget(lbl_tail)

    layout.addSpacing(8)
    layout.addWidget(Divider(theme="dark", text="Continue with email", text_size=13))

    layout.addSpacing(8)
    layout.addWidget(Divider(theme="dark", text="Section Title", text_size=16, color="#338ef7"))

    layout.addSpacing(8)
    layout.addWidget(Divider(theme="dark", text="或", text_size=12))

    # 垂直分割线
    section_label3 = QLabel("垂直分割线")
    section_label3.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label3.setStyleSheet("color: #d4d4d8; margin-top: 12px;")
    layout.addWidget(section_label3)

    row = QHBoxLayout()
    row.setSpacing(16)
    for text, color in [("左侧", None), ("中间", "#338ef7"), ("右侧", None)]:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #d4d4d8;")
        row.addWidget(lbl)
        if text != "右侧":
            row.addWidget(Divider(orientation="vertical", theme="dark", color=color))
    layout.addLayout(row)

    layout.addStretch()
    main_widget.setLayout(layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #18181b; }")
    scroll.setWidget(main_widget)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
