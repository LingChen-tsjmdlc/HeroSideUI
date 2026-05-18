"""Spinner 组件示例 —— 6 种 variant、6 色、3 尺寸。"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Spinner
from _base import DemoBase


VARIANTS = ["default", "simple", "gradient", "spinner", "wave", "dots"]
COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]


class SpinnerDemo(DemoBase):
    component_name = "Spinner"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 6 个 variant 一字排开
        self.add_section(layout, "6 个 variant（默认 primary / md）", [
            Spinner(variant=v, label=v) for v in VARIANTS
        ], labels_bag, spacing=24)

        # 每个 variant × 6 color
        for v in VARIANTS:
            self.add_section(layout, f"variant={v} · 6 colors", [
                Spinner(variant=v, color=c, label=c) for c in COLORS
            ], labels_bag, spacing=20)

        # 3 sizes per variant
        for v in VARIANTS:
            self.add_section(layout, f"variant={v} · 3 sizes (sm / md / lg)", [
                Spinner(variant=v, size=s, label=s) for s in ["sm", "md", "lg"]
            ], labels_bag, spacing=24)


if __name__ == "__main__":
    SpinnerDemo.run()
