"""
Checkbox 组件示例 — 6 种颜色 × 3 尺寸 × 5 圆角，以及 lineThrough / indeterminate / disabled / invalid / CheckboxGroup
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Checkbox, CheckboxGroup
from _base import DemoBase


class CheckboxDemo(DemoBase):
    component_name = "Checkbox"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 颜色
        self.add_section(layout, "6 种颜色（默认选中）", [
            Checkbox(c.capitalize(), is_selected=True, color=c)
            for c in ["default", "primary", "secondary", "success", "warning", "danger"]
        ], labels_bag, spacing=20)

        # 尺寸
        self.add_section(layout, "3 种尺寸", [
            Checkbox(f"Size {s}", is_selected=True, color="primary", size=s)
            for s in ["sm", "md", "lg"]
        ], labels_bag, spacing=20)

        # 圆角
        self.add_section(layout, "5 种圆角", [
            Checkbox(f"radius={r}", is_selected=True, color="secondary", radius=r)
            for r in ["none", "sm", "md", "lg", "full"]
        ], labels_bag, spacing=20)

        # lineThrough
        self.add_section(layout, "lineThrough（选中时 label 加下划线并变暗）", [
            Checkbox("Buy groceries", is_selected=True, line_through=True, color="success"),
            Checkbox("Read book", line_through=True, color="primary"),
            Checkbox("Finish project", is_selected=True, line_through=True, color="danger"),
        ], labels_bag, spacing=20)

        # indeterminate
        self.add_section(layout, "indeterminate 未定态", [
            Checkbox("Select all", is_indeterminate=True, color="primary"),
            Checkbox("Partial", is_indeterminate=True, color="success"),
            Checkbox("Some items", is_indeterminate=True, color="warning"),
        ], labels_bag, spacing=20)

        # 状态
        self.add_section(layout, "状态：disabled / invalid", [
            Checkbox("Disabled (off)", is_disabled=True, color="primary"),
            Checkbox("Disabled (on)", is_selected=True, is_disabled=True, color="primary"),
            Checkbox("Invalid required", is_invalid=True, color="primary"),
        ], labels_bag, spacing=20)

        # CheckboxGroup vertical
        g1 = CheckboxGroup(
            label="Select your favorite frameworks",
            description="You may choose multiple",
            color="primary",
            default_value=["react", "vue"],
        )
        g1.create_checkbox("React", "react")
        g1.create_checkbox("Vue", "vue")
        g1.create_checkbox("Angular", "angular")
        g1.create_checkbox("Svelte", "svelte")
        self.add_full_width(layout, "CheckboxGroup (vertical)", g1, labels_bag)

        # CheckboxGroup horizontal, invalid
        g2 = CheckboxGroup(
            label="Pick at least one",
            error_message="You must choose at least one option",
            orientation="horizontal",
            color="danger",
            is_required=True,
            is_invalid=True,
        )
        g2.create_checkbox("Email", "email")
        g2.create_checkbox("SMS", "sms")
        g2.create_checkbox("Phone", "phone")
        self.add_full_width(layout, "CheckboxGroup (horizontal, invalid state)", g2, labels_bag)


if __name__ == "__main__":
    CheckboxDemo.run()
