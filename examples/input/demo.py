"""
Input 组件示例 — 4 变体 × 6 颜色 × 3 尺寸 × 4 label 位置 × 各种状态
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget

from hero_side_ui import Input, Button
from _base import DemoBase


COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
VARIANTS = ["flat", "faded", "bordered", "underlined"]


def grid_of_inputs(variant: str, label_placement: str = "inside") -> QWidget:
    """6 个颜色的 Input 排成 3 列网格"""
    w = QWidget()
    grid = QGridLayout(w)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(12)
    for i, c in enumerate(COLORS):
        inp = Input(
            label=c.title(), variant=variant, color=c, size="md",
            label_placement=label_placement, is_clearable=True,
        )
        grid.addWidget(inp, i // 3, i % 3)
    return w


def add_sub(layout, text, labels_bag):
    """次级章节小标题（labels_bag 用 ("sub", lbl)）"""
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 10))
    labels_bag.append(("sub", lbl))
    layout.addWidget(lbl)


class InputDemo(DemoBase):
    component_name = "Input"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 4 变体 × 6 颜色
        for v in VARIANTS:
            self.add_full_width(layout, f"Variant: {v}",
                               grid_of_inputs(v), labels_bag)

        # 3 尺寸
        size_row = QWidget()
        hl = QHBoxLayout(size_row)
        hl.setContentsMargins(0, 0, 0, 0)
        for s in ["sm", "md", "lg"]:
            hl.addWidget(Input(label=f"Size {s}", variant="flat", color="primary",
                              size=s, is_clearable=True))
        self.add_full_width(layout, "3 sizes (variant=flat, color=primary)",
                           size_row, labels_bag)

        # 4 label placements
        for lp in ["inside", "outside", "outside-top", "outside-left"]:
            self.add_full_width(layout, f"label_placement = {lp}",
                               grid_of_inputs("flat", lp), labels_bag)

        # Placeholder
        self.add_full_width(layout, "Placeholder 演示",
            Input(label="Email", placeholder="you@example.com",
                  variant="flat", color="primary", is_clearable=True),
            labels_bag)

        # States
        self.add_full_width(layout, "is_disabled",
            Input(label="Disabled", variant="flat", is_disabled=True), labels_bag)

        self.add_full_width(layout, "is_readonly",
            Input(label="Readonly", value="这是只读内容", variant="flat", is_readonly=True),
            labels_bag)

        self.add_full_width(layout, "is_required",
            Input(label="Username", variant="bordered", color="primary", is_required=True),
            labels_bag)

        # is_invalid 跨四种 variant
        invalid_widgets = [
            Input(label=f"Email ({v})", variant=v,
                  is_invalid=True, error_message="请输入合法的邮箱地址")
            for v in VARIANTS
        ]
        self.add_full_width_group(layout, "is_invalid + error_message",
                                  invalid_widgets, labels_bag)

        # start/end content
        self.add_full_width(layout, "start_content = string icon",
            Input(label="Search", variant="flat", color="default",
                  start_content="heroicons--chevron-right-solid", is_clearable=True),
            labels_bag)

        # 密码 + 眼睛
        pwd = Input(label="Password", variant="bordered", color="primary",
                    end_content="heroicons--eye-solid")
        pwd.line_edit.setEchoMode(pwd.line_edit.EchoMode.Password)
        st = {"visible": False}
        def toggle():
            st["visible"] = not st["visible"]
            em = pwd.line_edit.EchoMode
            pwd.line_edit.setEchoMode(em.Normal if st["visible"] else em.Password)
            pwd.set_end_content(
                "heroicons--eye-slash-solid" if st["visible"] else "heroicons--eye-solid",
                on_click=toggle,
            )
        pwd.set_on_end_content_click(toggle)
        self.add_full_width(layout, "字符串图标 + 点击回调 (密码框眼睛)", pwd, labels_bag)

        # 直接塞 Button
        go_btn = Button("GO", size="sm", variant="flat", color="primary")
        go_btn.clicked.connect(lambda: print("[GO] clicked"))
        self.add_full_width(layout, "塞 Button 组件作为 end_content",
            Input(label="Query", variant="flat", color="default", end_content=go_btn),
            labels_bag)

        # 事件
        ev = Input(label="Type here", variant="flat", color="primary", is_clearable=True)
        ev.text_changed.connect(lambda t: print(f"[changed] {t!r}"))
        ev.returned.connect(lambda: print("[enter]"))
        ev.cleared.connect(lambda: print("[cleared]"))
        ev.editing_finished.connect(lambda: print("[editing_finished]"))
        self.add_full_width(layout, "Event demo (控制台查看输出)", ev, labels_bag)


if __name__ == "__main__":
    InputDemo.run()
