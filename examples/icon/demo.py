"""Icon: offline resources, theme tokens and the public iconify ecosystem."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QVBoxLayout
from pyside_iconify import IconWidget

from hero_side_ui import Button, Icon
from _base import DemoBase


class IconDemo(DemoBase):
    component_name = "Icon"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        self.add_section(layout, "内置图标：断网也可使用", [
            Icon(name, size=32) for name in [
                "heroicons--eye-solid", "heroicons--check-solid",
                "flowbite--sun-solid", "ri--moon-clear-fill",
            ]
        ], labels_bag, spacing=24)
        self.add_section(layout, "颜色 Token", [
            Icon("heroicons--check-solid", color=color, size="lg")
            for color in ["primary", "secondary", "success", "warning", "danger"]
        ], labels_bag, spacing=24)
        self.add_section(layout, "尺寸：sm / md / lg / 48px", [
            Icon("heroicons--eye-solid", size=size, color="primary")
            for size in ["sm", "md", "lg", "48px"]
        ], labels_bag, spacing=24)
        self.add_section(layout, "交互与局部主题：hover / disabled / light / dark", [
            Icon("heroicons--eye-solid", hover_color="primary", size="lg"),
            Icon("heroicons--eye-solid", is_disabled=True, size="lg"),
            Icon("heroicons--eye-solid", theme="light", size="lg"),
            Icon("heroicons--eye-solid", theme="dark", size="lg"),
        ], labels_bag, spacing=24)
        self.add_section(layout, "动画由 pyside-iconify 驱动", [
            Icon("heroicons--clock", animation="spin", size="lg", color="primary"),
            Icon("heroicons--check-solid", animation="pulse", size="lg", color="success"),
        ], labels_bag, spacing=24)
        self.add_section(layout, "现有组件复用同一图标入口", [
            Button("保存", icon="heroicons--check-solid", color="primary"),
        ], labels_bag)
        load_button = Button("加载在线图标（需要网络）", variant="bordered")

        def load_online():
            self.add_section(layout, "同一应用：HeroSideUI Icon / 原生 IconWidget", [
                Icon("mdi:home", size=32, color="primary"),
                IconWidget("mdi:home", size=32, color="#006fee"),
            ], labels_bag, spacing=24)
            load_button.setEnabled(False)

        load_button.clicked.connect(load_online)
        layout.addWidget(load_button)


if __name__ == "__main__":
    IconDemo.run()
