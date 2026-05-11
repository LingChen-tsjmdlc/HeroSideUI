"""
Listbox 组件示例 — 6 variants × 6 colors × 3 sizes × 状态 × 分组 × 选择模式
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame, QWidget
from PySide6.QtCore import Qt

from hero_side_ui import Listbox, ListboxItem, ListboxSection, Card, CardBody, Body, Caption, Title
from _base import DemoBase


def _frame(child: QWidget, *, width: int = 260) -> Card:
    """把 Listbox 套进 Card 里展示，Card 提供主题感知底色。"""
    card = Card()
    card.setFixedWidth(width)
    body = CardBody()
    body.layout().setContentsMargins(0, 0, 0, 0)
    body.layout().addWidget(child)
    card.add_body(body)
    return card


class ListboxDemo(DemoBase):
    component_name = "Listbox"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 基础：默认 (variant=solid, color=default, mode=none)
        # ============================================================
        lb = Listbox()
        lb.add_item("New file", key="new", description="Create a new file", shortcut="Ctrl+N")
        lb.add_item("Copy link", key="copy", description="Copy item link to clipboard", shortcut="Ctrl+L")
        lb.add_item("Edit file", key="edit", description="Allows you to edit the file", shortcut="Ctrl+E")
        lb.add_item("Delete file", key="delete", description="Permanently delete the file",
                    shortcut="Ctrl+D", is_disabled=False)
        lb.action.connect(lambda key: print(f"[default] action: {key}"))
        self.add_section(layout, "默认 (solid / default / no selection)", [_frame(lb)], labels_bag)

        # ============================================================
        # 2) 6 种颜色 × variant=flat（最常用组合）
        # ============================================================
        flats = []
        for c in ("default", "primary", "secondary", "success", "warning", "danger"):
            lb = Listbox(variant="flat", color=c, selection_mode="single")
            lb.add_item("First", key="a")
            lb.add_item("Second", key="b")
            lb.add_item("Third", key="c")
            lb.set_selected_keys({"b"})
            flats.append(_frame(lb, width=200))
        self.add_section_grid(layout, "6 colors × variant=flat (single 选中第二项)",
                              flats, labels_bag, cols=3, spacing=12)

        # ============================================================
        # 3) 6 种 variant × color=primary
        # ============================================================
        variants_grid = []
        for v in ("solid", "shadow", "bordered", "flat", "faded", "light"):
            lb = Listbox(variant=v, color="primary", selection_mode="single")
            lb.add_item("Item One", key="1")
            lb.add_item("Item Two", key="2")
            lb.add_item("Item Three", key="3")
            lb.set_selected_keys({"2"})
            variants_grid.append(_frame(lb, width=200))
        self.add_section_grid(layout, "6 variants × color=primary",
                              variants_grid, labels_bag, cols=3, spacing=12)

        # ============================================================
        # 4) 3 种尺寸
        # ============================================================
        sizes = []
        for s in ("sm", "md", "lg"):
            lb = Listbox(variant="flat", color="primary", size=s, selection_mode="single")
            lb.add_item("Tiny", key="t")
            lb.add_item("Medium", key="m")
            lb.add_item("Large", key="l")
            lb.set_selected_keys({"m"})
            sizes.append(_frame(lb, width=220))
        self.add_section(layout, "3 sizes (sm / md / lg)", sizes, labels_bag, spacing=16)

        # ============================================================
        # 5) 多选 + 自定义 emptyContent
        # ============================================================
        multi = Listbox(variant="flat", color="success", selection_mode="multiple")
        multi.add_item("Option A", key="a", description="Free trial")
        multi.add_item("Option B", key="b", description="Pro plan")
        multi.add_item("Option C", key="c", description="Enterprise")
        multi.action.connect(lambda k: print(f"[multi] action: {k}"))
        multi.selection_changed.connect(lambda s: print(f"[multi] selected: {s}"))

        empty_default = Listbox(variant="flat", color="default")  # 默认 emptyContent: icon + 中英双语
        empty_custom = Listbox(variant="flat", color="default", empty_content="🍂 No items found.")

        self.add_section(layout, "Multiple selection / 默认 empty / 自定义 empty",
                         [_frame(multi), _frame(empty_default), _frame(empty_custom)],
                         labels_bag, spacing=24)

        # ============================================================
        # 6) 分组 + showDivider —— 菜单语义（点完就执行动作，不留选中态）
        # ============================================================
        # 这里是"右键菜单 / 命令面板"的典型用法：每项是动作而非选项，
        # 因此用 selection_mode="none"（默认）+ action 信号驱动业务逻辑，
        # 不画对勾。hover 高亮告诉用户"鼠标在这一项上"已经足够。
        sec_box = Listbox(variant="flat", color="primary")
        sec_actions = ListboxSection("Actions", show_divider=True)
        sec_actions.add_item("New file", key="new", shortcut="Ctrl+N")
        sec_actions.add_item("Copy link", key="copy", shortcut="Ctrl+L")
        sec_actions.add_item("Edit file", key="edit", shortcut="Ctrl+E")
        sec_box.add_section(sec_actions)

        sec_danger = ListboxSection("Danger zone")
        sec_danger.add_item("Delete file", key="del", description="Permanently delete this file",
                            shortcut="⌫", is_disabled=False)
        sec_box.add_section(sec_danger)
        sec_box.action.connect(lambda k: print(f"[menu] action: {k}"))

        self.add_section(layout, "菜单语义 (sections + shortcut，点完就执行不留选中)",
                         [_frame(sec_box, width=300)], labels_bag)

        # ============================================================
        # 7) showDivider per item + disabledKeys
        # ============================================================
        divided = Listbox(variant="flat", color="primary", selection_mode="single")
        divided.add_item("Read", key="read", show_divider=True)
        divided.add_item("Write", key="write", show_divider=True)
        divided.add_item("Admin", key="admin")
        divided.set_disabled_keys({"admin"})
        self.add_section(layout, "Per-item showDivider + disabledKeys",
                         [_frame(divided, width=240)], labels_bag)


if __name__ == "__main__":
    ListboxDemo.run()
