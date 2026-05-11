"""
Progress 组件示例 — Linear / Circular / Spinner，全部主题感知
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Progress, CircularProgress, Spinner
from _base import DemoBase


class ProgressDemo(DemoBase):
    component_name = "Progress"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # Linear · 6 colors
        self.add_full_width_group(layout, "Linear · 6 colors", [
            Progress(value=60, color=c, label=c.capitalize(), show_value_label=True)
            for c in ["default", "primary", "secondary", "success", "warning", "danger"]
        ], labels_bag)

        # Linear · 3 sizes
        self.add_full_width_group(layout, "Linear · 3 sizes", [
            Progress(value=65, size=s, color="primary", label=f"Size {s}", show_value_label=True)
            for s in ["sm", "md", "lg"]
        ], labels_bag)

        # Linear · 圆角
        self.add_full_width_group(layout, "Linear · 3 radius (none / sm / full)", [
            Progress(value=55, color="secondary", radius=r, label=f"radius={r}", show_value_label=True)
            for r in ["none", "sm", "full"]
        ], labels_bag)

        # Linear · striped
        self.add_full_width_group(layout, "Linear · striped", [
            Progress(value=70, color=c, is_striped=True, label=f"{c} striped", show_value_label=True)
            for c in ["primary", "success", "warning", "danger"]
        ], labels_bag)

        # Linear · indeterminate
        self.add_full_width_group(layout, "Linear · indeterminate", [
            Progress(is_indeterminate=True, color=c, label=f"{c} loading...")
            for c in ["primary", "secondary", "success"]
        ], labels_bag)

        # 自定义 formatter
        self.add_full_width(layout, "Linear · custom formatter (files X/Y)",
            Progress(
                value=3, min_value=0, max_value=10,
                color="success", size="lg",
                label="Uploading files", show_value_label=True,
                value_label_formatter=lambda v, mn, mx: f"{int(v)}/{int(mx)}",
            ), labels_bag)

        # Circular · 6 colors
        self.add_section(layout, "Circular · 6 colors", [
            CircularProgress(value=65, color=c, size="md",
                             show_value_label=True, label=c.capitalize())
            for c in ["default", "primary", "secondary", "success", "warning", "danger"]
        ], labels_bag, spacing=24)

        # Circular · 3 sizes
        self.add_section(layout, "Circular · 3 sizes", [
            CircularProgress(value=80, color="primary", size=s,
                             show_value_label=True, label=f"Size {s}")
            for s in ["sm", "md", "lg"]
        ], labels_bag, spacing=24)

        # Circular · indeterminate
        self.add_section(layout, "Circular · indeterminate (spinner)", [
            CircularProgress(is_indeterminate=True, color=c, size="md", label=c.capitalize())
            for c in ["primary", "secondary", "success", "warning", "danger"]
        ], labels_bag, spacing=24)

        # Spinner
        self.add_section(layout, "Spinner (零配置加载)", [
            Spinner(),
            Spinner(color="secondary", size="lg"),
            Spinner(color="success", label="Loading..."),
        ], labels_bag, spacing=24)

        # Dynamic
        dyn_p = Progress(value=0, label="Downloading...", show_value_label=True,
                         color="primary", size="md")
        dyn_cp = CircularProgress(value=0, color="primary", size="lg",
                                  show_value_label=True, label="Progress")
        self.add_section(layout, "Dynamic: timer-driven set_value", [dyn_p, dyn_cp],
                         labels_bag, spacing=24)

        counter = {"v": 0}
        self._timer = QTimer(self)

        def tick():
            counter["v"] = (counter["v"] + 5) % 105
            v = min(100, counter["v"])
            dyn_p.set_value(v)
            dyn_cp.set_value(v)

        self._timer.timeout.connect(tick)
        self._timer.start(300)


if __name__ == "__main__":
    ProgressDemo.run()
