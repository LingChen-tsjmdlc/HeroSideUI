"""
Accordion 组件示例 - 亮色模式
展示所有变体 (light, shadow, bordered, splitted) + 不同圆角
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Accordion, AccordionItem


FAQ_DATA = [
    {
        "title": "什么是 HeroSideUI？",
        "content": "HeroSideUI 是一个使用 PySide6 复刻 HeroUI v2 设计系统的 Python 桌面组件库。只改样式，不改逻辑。",
    },
    {
        "title": "如何安装？",
        "subtitle": "使用 uv 包管理器",
        "content": "运行 uv sync 安装所有依赖，然后 uv run python examples/... 运行示例。",
    },
    {
        "title": "支持哪些组件？",
        "content": "目前支持 Button 和 Accordion 组件，更多组件正在开发中。",
    },
    {
        "title": "支持暗色模式吗？",
        "subtitle": "内置亮暗双主题",
        "content": "是的，每个组件都支持 theme='light' 和 theme='dark' 参数，自动适配颜色。",
    },
]


def create_accordion(variant: str, radius: str = "md") -> Accordion:
    """创建一个指定变体的 Accordion"""
    accordion = Accordion(variant=variant, radius=radius, theme="light")
    for data in FAQ_DATA:
        item = AccordionItem(
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            content_text=data["content"],
        )
        accordion.add_item(item)
    return accordion


def add_section(layout, title: str, widget: QWidget):
    label = QLabel(title)
    label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    label.setStyleSheet("color: #3f3f46; margin-top: 12px; margin-bottom: 4px;")
    layout.addWidget(label)
    layout.addWidget(widget)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Accordion 示例 - 亮色模式")
    window.resize(700, 900)

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

    title = QLabel("Accordion - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 8px;")
    layout.addWidget(title)

    # 四种变体
    add_section(layout, "Light", create_accordion("light"))
    add_section(layout, "Shadow (radius=md)", create_accordion("shadow", "md"))
    add_section(layout, "Bordered (radius=lg)", create_accordion("bordered", "lg"))
    add_section(layout, "Splitted (radius=sm)", create_accordion("splitted", "sm"))

    # 圆角对比
    add_section(layout, "Shadow radius=none", create_accordion("shadow", "none"))
    add_section(layout, "Shadow radius=lg", create_accordion("shadow", "lg"))

    layout.addStretch()
    main_widget.setLayout(layout)
    scroll.setWidget(main_widget)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
