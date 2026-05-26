"""
Radio 组件示例 — 6 种颜色 × 3 尺寸，及 description / disabled / invalid / RadioGroup
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Radio, RadioGroup
from _base import DemoBase


class RadioDemo(DemoBase):
    component_name = "Radio"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 颜色（默认选中）
        self.add_section(
            layout,
            "6 种颜色（默认选中）",
            [
                Radio(c.capitalize(), is_selected=True, color=c)
                for c in [
                    "default",
                    "primary",
                    "secondary",
                    "success",
                    "warning",
                    "danger",
                ]
            ],
            labels_bag,
            spacing=20,
        )

        # 尺寸
        self.add_section(
            layout,
            "3 种尺寸",
            [
                Radio(f"Size {s}", is_selected=True, color="primary", size=s)
                for s in ["sm", "md", "lg"]
            ],
            labels_bag,
            spacing=20,
        )

        # 带 description
        self.add_section_vertical(
            layout,
            "带 description（label + 副文本）",
            [
                Radio(
                    "Free",
                    description="Up to 5 projects, community support",
                    color="primary",
                ),
                Radio(
                    "Pro",
                    description="Unlimited projects, priority support",
                    color="secondary",
                    is_selected=True,
                ),
                Radio(
                    "Enterprise",
                    description="SLA, SSO, custom contract",
                    color="success",
                ),
            ],
            labels_bag,
            spacing=10,
        )

        # 状态
        self.add_section(
            layout,
            "状态：disabled / invalid",
            [
                Radio("Disabled (off)", is_disabled=True, color="primary"),
                Radio(
                    "Disabled (on)", is_selected=True, is_disabled=True, color="primary"
                ),
                Radio("Invalid", is_invalid=True, color="primary"),
            ],
            labels_bag,
            spacing=20,
        )

        # RadioGroup vertical
        g1 = RadioGroup(
            label="Plan",
            description="Choose a subscription plan",
            color="primary",
            default_value="pro",
        )
        g1.create_radio("Free", value="free", description="Hobby projects")
        g1.create_radio("Pro", value="pro", description="For professional teams")
        g1.create_radio(
            "Enterprise", value="enterprise", description="Tailored for big org"
        )
        self.add_full_width(layout, "RadioGroup (vertical)", g1, labels_bag)

        # RadioGroup horizontal
        g2 = RadioGroup(
            label="Favorite framework",
            orientation="horizontal",
            color="secondary",
            default_value="react",
        )
        g2.create_radio("React", value="react")
        g2.create_radio("Vue", value="vue")
        g2.create_radio("Angular", value="angular")
        g2.create_radio("Svelte", value="svelte")
        self.add_full_width(layout, "RadioGroup (horizontal)", g2, labels_bag)

        # RadioGroup required + invalid
        g3 = RadioGroup(
            label="Notification channel",
            error_message="Please pick one channel",
            orientation="horizontal",
            color="danger",
            is_required=True,
            is_invalid=True,
        )
        g3.create_radio("Email", value="email")
        g3.create_radio("SMS", value="sms")
        g3.create_radio("Phone", value="phone")
        self.add_full_width(layout, "RadioGroup (required + invalid)", g3, labels_bag)


if __name__ == "__main__":
    RadioDemo.run()
