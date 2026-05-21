"""
Divider 组件示例 — 水平/垂直分割线、自定义颜色、带文字
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import Divider, Body
from _base import DemoBase


class DividerDemo(DemoBase):
    component_name = "Divider"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 1. 默认水平分割线
        self.add_section_vertical(
            layout,
            "水平分割线 (默认)",
            [
                Body("上方内容"),
                Divider(),
                Body("下方内容"),
            ],
            labels_bag,
        )

        # 2. 自定义颜色
        colors = ["#006FEE", "#7828c8", "#17c964", "#f5a524", "#f31260"]
        self.add_section_vertical(
            layout,
            "自定义颜色分割线",
            [Divider(color=c) for c in colors],
            labels_bag,
            spacing=4,
        )

        # 3. 带文字的分割线
        self.add_section_vertical(
            layout,
            "带文字的分割线",
            [
                Body("Sign in with your account"),
                Divider(text="OR"),
                Body("Sign in with social providers"),
                Divider(text="Continue with email", text_size=13),
                Divider(text="Section Title", text_size=16, color="#006FEE"),
                Divider(text="或", text_size=12),
            ],
            labels_bag,
            spacing=8,
        )

        # 4. 垂直分割线
        vrow = QWidget()
        hl = QHBoxLayout(vrow)
        hl.setSpacing(16)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(Body("左侧"))
        hl.addWidget(Divider(orientation="vertical"))
        hl.addWidget(Body("中间"))
        hl.addWidget(Divider(orientation="vertical", color="#006FEE"))
        hl.addWidget(Body("右侧"))
        hl.addStretch()
        self.add_section(layout, "垂直分割线", [vrow], labels_bag)


if __name__ == "__main__":
    DividerDemo.run()
