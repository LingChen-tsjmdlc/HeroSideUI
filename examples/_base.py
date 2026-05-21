"""
HeroSideUI 示例公用基类与工具

DemoBase 就是普通 QMainWindow —— 因为 HeroSideUI 的 ThemeProvider 已经
在主题变化时自动同步 QApplication palette，所以窗口背景/文字色完全自动跟。
基类只负责示例特有的章节布局工具方法。
"""

import sys
from typing import Iterable

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
)
from PySide6.QtCore import Qt

from hero_side_ui import HeroSideUIProvider, ThemeSwitcher, Title


class DemoBase(QMainWindow):
    """组件 demo 通用基类

    窗口背景 / 文字色 / 按钮色全部由 ThemeProvider 自动同步 QApplication palette
    搞定 —— 此处无需做任何 palette 管理。

    子类要做：
    1. 设 `component_name`
    2. 重写 `build_content(layout, labels_bag)` 添加内容
        - 用 Title/Subtitle/Caption/Body 等主题感知文字组件
        - labels_bag 已废弃，保留参数向后兼容
    """

    component_name: str = "Component"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.component_name} 示例")
        self.resize(1100, 820)

        # scroll area 承载内容
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(40, 24, 40, 30)

        # 顶栏: 左 Title + 右 ThemeSwitcher
        header = QHBoxLayout()
        title_widget = Title(self.component_name, level=1)
        title_widget.set_color("#006FEE")  # 装饰性主品牌蓝
        header.addWidget(title_widget)
        header.addStretch()
        header.addWidget(ThemeSwitcher(size="md"))
        layout.addLayout(header)

        # 内容（子类填充）
        labels_bag: list = []  # 仅向后兼容
        self.build_content(layout, labels_bag)

        layout.addStretch()
        scroll.setWidget(main_widget)
        self.setCentralWidget(scroll)

    # ---- 子类要重写 ----
    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        raise NotImplementedError

    # ============================================================
    # 章节布局工具（示例特有）
    # ============================================================
    @staticmethod
    def _section_title(text: str) -> Title:
        return Title(text, level=3)

    @classmethod
    def add_full_width(cls, layout, title, widget, labels_bag=None):
        layout.addWidget(cls._section_title(title))
        layout.addWidget(widget)

    @classmethod
    def add_full_width_group(cls, layout, title, widgets, labels_bag=None):
        layout.addWidget(cls._section_title(title))
        for w in widgets:
            layout.addWidget(w)

    @classmethod
    def add_section(cls, layout, title, widgets, labels_bag=None, spacing=10):
        layout.addWidget(cls._section_title(title))
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setSpacing(spacing)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for w in widgets:
            if isinstance(w, QWidget):
                row.addWidget(w)
            else:
                from hero_side_ui import Button

                row.addWidget(Button(**w))
        # 行容器宽度由内部按钮决定，绝不允许被父 layout 拉伸压缩
        from PySide6.QtWidgets import QSizePolicy

        row_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(row_widget)

    @classmethod
    def add_section_grid(
        cls, layout, title, widgets, labels_bag=None, cols=4, spacing=10
    ):
        layout.addWidget(cls._section_title(title))
        widgets_list = list(widgets)
        for i in range(0, len(widgets_list), cols):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setSpacing(spacing)
            row.setAlignment(Qt.AlignmentFlag.AlignLeft)
            for w in widgets_list[i : i + cols]:
                row.addWidget(w)
            # 行容器宽度由内部按钮决定，绝不允许被父 layout 拉伸压缩
            from PySide6.QtWidgets import QSizePolicy

            row_widget.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
            )
            layout.addWidget(row_widget)

    @classmethod
    def add_section_vertical(cls, layout, title, widgets, labels_bag=None, spacing=8):
        layout.addWidget(cls._section_title(title))
        col = QVBoxLayout()
        col.setSpacing(spacing)
        col.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for w in widgets:
            col.addWidget(w)
        layout.addLayout(col)

    # ---- 启动器 ----
    @classmethod
    def run(cls):
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        # 推荐写法：用 HeroSideUIProvider.setup() 显式初始化全套 core 基础设施。
        # 这里顺手 theme="light" 锁亮色，保证首屏可预期（不想锁可去掉 theme= 参数）。
        # 不调 setup() 也能用——任何组件构造都会触发 _boot 钩子降级激活，
        # 但会发一次双语 warning 提示存在显式入口。
        HeroSideUIProvider.setup(app, theme="light")
        win = cls()
        win.show()
        sys.exit(app.exec())
