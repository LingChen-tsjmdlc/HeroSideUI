"""Chip 组件示例 — 对齐 HeroUI Chip 页面示例。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import Chip
from _base import DemoBase

COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
VARIANTS = ["solid", "bordered", "light", "flat", "faded", "shadow", "dot"]
RADII = ["none", "sm", "md", "lg", "full"]
SIZES = ["sm", "md", "lg"]


class ChipDemo(DemoBase):
    component_name = "Chip"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 1. Usage
        self.add_section(layout, "Usage", [Chip("Chip")])

        # 2. Colors
        self.add_section(
            layout, "Colors",
            [Chip(c.capitalize(), color=c) for c in COLORS],
        )

        # 3. Variants
        self.add_section(
            layout, "Variants",
            [Chip(v.capitalize(), color="primary", variant=v) for v in VARIANTS],
        )

        # 4. Sizes
        self.add_section(
            layout, "Sizes",
            [Chip(s.upper(), color="secondary", variant="flat", size=s) for s in SIZES],
        )

        # 5. Radius
        self.add_section(
            layout, "Radius",
            [Chip(r, color="success", variant="flat", radius=r) for r in RADII],
        )

        # 6. Disabled
        self.add_section(
            layout, "Disabled",
            [
                Chip("Disabled", color="primary", is_disabled=True),
                Chip("Disabled", color="danger", variant="flat", is_disabled=True),
            ],
        )

        # 7. Closable
        self._build_closable(layout)

        # 8. With Dot
        self.add_section(
            layout, "Dot Variant",
            [Chip(c.capitalize(), color=c, variant="dot") for c in COLORS],
        )

        # 8b. Dot Variant（中文）
        self.add_section(
            layout, "Dot Variant（中文）",
            [
                Chip("已上线", color="success", variant="dot"),
                Chip("处理中", color="warning", variant="dot"),
                Chip("已下线", color="danger", variant="dot"),
                Chip("草稿箱", color="default", variant="dot"),
            ],
        )

        # 9. One Char
        self.add_section(
            layout, "One Char (圆形)",
            [
                Chip("A", color="primary"),
                Chip("B", color="secondary", variant="flat"),
                Chip("9", color="danger", variant="solid", size="lg"),
            ],
        )

    def _build_closable(self, layout):
        from hero_side_ui import Button

        labels = [
            ("设计", "primary"),
            ("前端", "success"),
            ("后端", "secondary"),
            ("测试", "warning"),
            ("运维", "danger"),
        ]
        chips = [
            Chip(name, color=c, variant="flat", is_closable=True)
            for name, c in labels
        ]

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for ch in chips:
            rl.addWidget(ch)

        # 恢复按钮：把所有关闭的 Chip 重新显示
        restore_btn = Button("恢复全部", color="primary", variant="flat", size="sm")
        restore_btn.clicked.connect(lambda: [ch.show() for ch in chips])

        restore_row = QWidget()
        rrl = QHBoxLayout(restore_row)
        rrl.setContentsMargins(0, 0, 0, 0)
        rrl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        rrl.addWidget(restore_btn)

        layout.addWidget(self._section_title("Closable"))
        layout.addWidget(row)
        layout.addWidget(restore_row)


if __name__ == "__main__":
    ChipDemo.run()
