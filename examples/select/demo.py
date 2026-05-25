"""
Select 组件示例 — 单选 / 多选 / 6 色 4 变体 3 尺寸 / 状态 / 主题
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Select
from _base import DemoBase

ANIMALS = [
    {"key": "cat", "label": "Cat", "description": "Small domestic feline"},
    {"key": "dog", "label": "Dog", "description": "Loyal companion"},
    {"key": "elephant", "label": "Elephant", "description": "Largest land animal"},
    {"key": "fox", "label": "Fox", "description": "Clever forest dweller"},
    {"key": "hedgehog", "label": "Hedgehog", "description": "Spiky small mammal"},
    {"key": "horse", "label": "Horse", "description": "Fast runner"},
    {"key": "lion", "label": "Lion", "description": "King of the jungle"},
    {"key": "monkey", "label": "Monkey", "description": "Clever primate"},
    {"key": "penguin", "label": "Penguin", "description": "Flightless swimmer"},
    {"key": "tiger", "label": "Tiger", "description": "Majestic striped cat"},
]

FRUITS = [
    ("apple", "Apple"),
    ("banana", "Banana"),
    ("blueberry", "Blueberry"),
    ("cherry", "Cherry"),
    ("durian", "Durian"),
    ("elderberry", "Elderberry"),
    ("fig", "Fig"),
    ("grape", "Grape"),
    ("kiwi", "Kiwi"),
    ("lemon", "Lemon"),
    ("mango", "Mango"),
    ("orange", "Orange"),
    ("papaya", "Papaya"),
    ("peach", "Peach"),
]


class SelectDemo(DemoBase):
    component_name = "Select"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 基础（单选）
        # ============================================================
        sel_basic = Select(
            label="Favorite Animal",
            placeholder="Select an animal",
            items=ANIMALS,
        )
        sel_basic.selection_changed.connect(lambda k: print(f"[basic] selected: {k}"))
        sel_basic.setFixedWidth(300)
        self.add_section(
            layout, "基础（单选，点击 trigger 展开）", [sel_basic], labels_bag
        )

        # ============================================================
        # 1.1) 无 placeholder = 默认模式：label 居中（resting），选中后浮起
        # ============================================================
        sel_no_ph_single = Select(
            label="Favorite Animal",
            items=ANIMALS,
        )
        sel_no_ph_single.setFixedWidth(300)

        sel_no_ph_multi = Select(
            label="Favorite Fruits",
            items=FRUITS,
            selection_mode="multiple",
            color="secondary",
        )
        sel_no_ph_multi.setFixedWidth(300)

        self.add_section(
            layout,
            "无 placeholder = 默认模式 (label 居中，选中后浮起；多选取消所有项 label 自动归位)",
            [sel_no_ph_single, sel_no_ph_multi],
            labels_bag,
            spacing=20,
        )

        # ============================================================
        # 2) 6 种颜色
        # ============================================================
        colors = []
        for c in ("default", "primary", "secondary", "success", "warning", "danger"):
            sel = Select(
                label=c.capitalize(),
                placeholder="Pick a fruit",
                items=FRUITS,
                color=c,
            )
            sel.setFixedWidth(260)
            colors.append(sel)
        self.add_section_grid(
            layout,
            "6 种颜色 (color 同时驱动 trigger 边框 + listbox 高亮)",
            colors,
            labels_bag,
            cols=3,
            spacing=14,
        )

        # ============================================================
        # 3) 4 种 variant
        # ============================================================
        variants = []
        for v in ("flat", "faded", "bordered", "underlined"):
            sel = Select(
                label=v.capitalize(),
                placeholder=f"Variant: {v}",
                items=FRUITS,
                variant=v,
                color="primary",
            )
            sel.setFixedWidth(260)
            variants.append(sel)
        self.add_section_grid(
            layout,
            "4 种 variant (flat / faded / bordered / underlined)",
            variants,
            labels_bag,
            cols=4,
            spacing=14,
        )

        # ============================================================
        # 4) 3 种 size
        # ============================================================
        sizes = []
        for s in ("sm", "md", "lg"):
            sel = Select(
                label=s.upper(),
                placeholder="Pick one",
                items=FRUITS,
                size=s,
                color="primary",
            )
            sel.setFixedWidth(300)
            sizes.append(sel)
        self.add_section(
            layout, "3 种尺寸 (sm / md / lg)", sizes, labels_bag, spacing=16
        )

        # ============================================================
        # 4.1) 5 种圆角
        # ============================================================
        radii = []
        for r in ("none", "sm", "md", "lg", "full"):
            sel = Select(
                label=r,
                placeholder="Pick one",
                items=FRUITS,
                radius=r,
                color="primary",
            )
            sel.setFixedWidth(220)
            radii.append(sel)
        self.add_section_grid(
            layout,
            "5 种圆角 (none / sm / md / lg / full)",
            radii,
            labels_bag,
            cols=5,
            spacing=14,
        )

        # ============================================================
        # 5) 多选
        # ============================================================
        sel_multi = Select(
            label="Favorite Fruits",
            placeholder="Pick multiple",
            items=FRUITS,
            selection_mode="multiple",
            color="secondary",
            default_selected_keys={"apple", "banana"},
        )
        sel_multi.selection_changed.connect(
            lambda keys: print(f"[multi] selected: {keys}")
        )
        sel_multi.setFixedWidth(300)

        sel_multi_clearable = Select(
            label="Tags",
            placeholder="Pick tags",
            items=ANIMALS,
            selection_mode="multiple",
            color="success",
            is_clearable=True,
        )
        sel_multi_clearable.setFixedWidth(300)

        self.add_section(
            layout,
            "多选 (selection_mode='multiple', 选中保持打开)",
            [sel_multi, sel_multi_clearable],
            labels_bag,
            spacing=20,
        )

        # ============================================================
        # 6) is_clearable / disallow_empty_selection
        # ============================================================
        sel_clearable = Select(
            label="With Clear",
            placeholder="Select",
            items=FRUITS,
            color="primary",
            is_clearable=True,
            default_selected_keys={"apple"},
        )
        sel_clearable.setFixedWidth(260)

        sel_no_empty = Select(
            label="Disallow empty",
            items=FRUITS,
            color="warning",
            disallow_empty_selection=True,
            default_selected_keys={"apple"},
        )
        sel_no_empty.setFixedWidth(260)

        self.add_section(
            layout,
            "is_clearable / disallow_empty_selection",
            [sel_clearable, sel_no_empty],
            labels_bag,
            spacing=20,
        )

        # ============================================================
        # 7) disabled / invalid / required / readonly
        # ============================================================
        sel_disabled = Select(
            label="Disabled",
            items=FRUITS,
            default_selected_keys={"apple"},
            is_disabled=True,
        )
        sel_disabled.setFixedWidth(260)

        sel_invalid = Select(
            label="Invalid",
            items=FRUITS,
            is_invalid=True,
            color="danger",
            description="Please select a fruit",
        )
        sel_invalid.setFixedWidth(260)

        sel_required = Select(
            label="Required",
            items=FRUITS,
            is_required=True,
            color="warning",
        )
        sel_required.setFixedWidth(260)

        sel_readonly = Select(
            label="Read-only",
            items=FRUITS,
            default_selected_keys={"banana"},
            is_readonly=True,
        )
        sel_readonly.setFixedWidth(260)

        self.add_section_grid(
            layout,
            "状态 (disabled / invalid / required / readonly)",
            [sel_disabled, sel_invalid, sel_required, sel_readonly],
            labels_bag,
            cols=4,
            spacing=14,
        )

        # ============================================================
        # 8) disabled keys + 默认选中 + 空状态
        # ============================================================
        sel_dkeys = Select(
            label="Disabled items",
            items=FRUITS,
            disabled_keys={"durian", "fig"},
            color="primary",
            default_selected_keys={"apple"},
        )
        sel_dkeys.setFixedWidth(260)

        sel_empty = Select(
            label="Empty",
            placeholder="No data",
            items=[],
        )
        sel_empty.setFixedWidth(260)

        self.add_section(
            layout,
            "disabled keys / 空 items",
            [sel_dkeys, sel_empty],
            labels_bag,
            spacing=20,
        )


if __name__ == "__main__":
    SelectDemo.run()
