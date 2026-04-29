"""
Divider 组件示例 - 亮色模式
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
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Divider 示例 - 亮色模式")
    window.resize(600, 500)

    main_widget = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(16)
    layout.setContentsMargins(40, 30, 40, 30)

    # 标题
    title = QLabel("Divider - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # 水平分割线
    section_label = QLabel("水平分割线 (默认)")
    section_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label.setStyleSheet("color: #3f3f46;")
    layout.addWidget(section_label)

    layout.addWidget(QLabel("上方内容"))
    layout.addWidget(Divider())
    layout.addWidget(QLabel("下方内容"))

    # 自定义颜色
    section_label2 = QLabel("自定义颜色分割线")
    section_label2.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label2.setStyleSheet("color: #3f3f46; margin-top: 12px;")
    layout.addWidget(section_label2)

    colors = ["#006FEE", "#7828c8", "#17c964", "#f5a524", "#f31260"]
    for c in colors:
        layout.addWidget(Divider(color=c))
        layout.addSpacing(4)

    # 带文字的水平分割线
    section_label_text = QLabel("带文字的分割线")
    section_label_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label_text.setStyleSheet("color: #3f3f46; margin-top: 12px;")
    layout.addWidget(section_label_text)

    # 1) 最常见：OR
    layout.addWidget(QLabel("Sign in with your account"))
    layout.addWidget(Divider(text="OR"))
    layout.addWidget(QLabel("Sign in with social providers"))

    layout.addSpacing(8)

    # 2) 更长的文字 + 自定义字号
    layout.addWidget(Divider(text="Continue with email", text_size=13))

    layout.addSpacing(8)

    # 3) 大字号 + 自定义颜色（文字颜色仍跟随主题，线条跟随 color）
    layout.addWidget(Divider(text="Section Title", text_size=16, color="#006FEE"))

    layout.addSpacing(8)

    # 4) 中文
    layout.addWidget(Divider(text="或", text_size=12))

    # 垂直分割线
    section_label3 = QLabel("垂直分割线")
    section_label3.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    section_label3.setStyleSheet("color: #3f3f46; margin-top: 12px;")
    layout.addWidget(section_label3)

    row = QHBoxLayout()
    row.setSpacing(16)
    row.addWidget(QLabel("左侧"))
    row.addWidget(Divider(orientation="vertical"))
    row.addWidget(QLabel("中间"))
    row.addWidget(Divider(orientation="vertical", color="#006FEE"))
    row.addWidget(QLabel("右侧"))
    layout.addLayout(row)

    layout.addStretch()
    main_widget.setLayout(layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #fafafa; }")
    scroll.setWidget(main_widget)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
