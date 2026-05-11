"""
Button 组件示例 — 统一亮暗色切换

顶栏左侧是标题，右侧是 ThemeSwitcher。所有 Button 都是 theme="auto"，
点击右上角切换按钮即可一键切换全部样式。Button 内部自动根据 variant /
color / theme / hover 状态决定 icon 颜色，demo 里完全不写颜色判断。
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from hero_side_ui import Button
from _base import DemoBase


def make_icon_btn(icon_name: str, **btn_kwargs) -> Button:
    """便捷封装：icon_only=True 的 Button，Button 内部自动处理 icon 颜色"""
    return Button(icon_only=True, icon=icon_name, **btn_kwargs)


class ButtonDemo(DemoBase):
    component_name = "Button"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        colors = ["default", "primary", "secondary", "success", "warning", "danger"]

        # 各种变体
        for variant in ["solid", "bordered", "flat", "light", "faded", "ghost"]:
            self.add_section(
                layout, variant.capitalize(),
                [{"text": c.capitalize(), "color": c, "variant": variant} for c in colors],
                labels_bag,
            )

        # 尺寸
        self.add_section(
            layout, "Sizes",
            [
                {"text": "Small", "color": "primary", "size": "sm"},
                {"text": "Medium", "color": "primary", "size": "md"},
                {"text": "Large", "color": "primary", "size": "lg"},
            ],
            labels_bag,
        )

        # 圆角
        self.add_section(
            layout, "Radius",
            [
                {"text": "None", "color": "primary", "radius": "none"},
                {"text": "Small", "color": "primary", "radius": "sm"},
                {"text": "Medium", "color": "primary", "radius": "md"},
                {"text": "Large", "color": "primary", "radius": "lg"},
                {"text": "Full", "color": "primary", "radius": "full"},
            ],
            labels_bag,
        )

        # 禁用
        self.add_section(
            layout, "Disabled",
            [
                {"text": c.capitalize(), "color": c, "is_disabled": True}
                for c in ["primary", "secondary", "success", "warning", "danger"]
            ],
            labels_bag,
        )

        # icon_only
        icon_btns = []
        for s in ["sm", "md", "lg"]:
            icon_btns.append(make_icon_btn(
                "heroicons--check-solid", color="primary", variant="flat", size=s,
            ))
        for v in ["solid", "bordered", "flat", "light", "ghost"]:
            icon_btns.append(make_icon_btn(
                "heroicons--x-circle-solid", color="danger", variant=v, size="md",
            ))
        for c in ["default", "primary", "secondary", "success", "warning"]:
            icon_btns.append(make_icon_btn(
                "heroicons--eye-solid", color=c, variant="solid", size="md",
            ))
        icon_btns.append(make_icon_btn(
            "heroicons--chevron-right-solid",
            color="primary", variant="solid", size="md", radius="full",
        ))
        self.add_section(layout, "Icon Only (正方形图标按钮)", icon_btns, labels_bag)


if __name__ == "__main__":
    ButtonDemo.run()
