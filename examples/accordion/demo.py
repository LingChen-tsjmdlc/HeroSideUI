"""
Accordion 组件示例 — 四种变体（light/shadow/bordered/splitted）+ 不同圆角
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Accordion, AccordionItem
from _base import DemoBase


FAQ_DATA = [
    {
        "title": "什么是 HeroSideUI？",
        "content": "HeroSideUI 是一个使用 PySide6 复刻 HeroUI v2 设计系统的 Python 桌面组件库。只改样式，不改逻辑。",
    },
    {
        "title": "如何安装？",
        "subtitle": "使用 uv 包管理器",
        "content": "运行 uv sync 安装所有依赖，然后 uv run python examples/... 运行示例。",
    },
    {
        "title": "支持哪些组件？",
        "content": "目前支持 Button、Accordion、Card、Input 等组件，更多正在开发中。",
    },
    {
        "title": "支持暗色模式吗？",
        "subtitle": "内置亮暗双主题",
        "content": "是的，每个组件都支持 theme='auto' 跟随 ThemeProvider 全局切换。",
    },
]


def create_accordion(variant: str, radius: str = "md") -> Accordion:
    acc = Accordion(variant=variant, radius=radius)
    for data in FAQ_DATA:
        acc.add_item(AccordionItem(
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            content_text=data["content"],
        ))
    return acc


class AccordionDemo(DemoBase):
    component_name = "Accordion"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        self.add_full_width(layout, "Light", create_accordion("light"), labels_bag)
        self.add_full_width(layout, "Shadow (radius=md)", create_accordion("shadow", "md"), labels_bag)
        self.add_full_width(layout, "Bordered (radius=lg)", create_accordion("bordered", "lg"), labels_bag)
        self.add_full_width(layout, "Splitted (radius=sm)", create_accordion("splitted", "sm"), labels_bag)
        self.add_full_width(layout, "Shadow radius=none", create_accordion("shadow", "none"), labels_bag)
        self.add_full_width(layout, "Shadow radius=lg", create_accordion("shadow", "lg"), labels_bag)


if __name__ == "__main__":
    AccordionDemo.run()
