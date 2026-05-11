"""
Tooltip 组件示例 — 12 placement / 6 colors / offset / delay / arrow / size / radius / 自定义 widget
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget

from hero_side_ui import Tooltip, Button, Title, Body, Caption
from _base import DemoBase


class TooltipDemo(DemoBase):
    component_name = "Tooltip"

    def __init__(self):
        # 持有 tooltip 引用避免被 GC
        self._tooltips: list = []
        super().__init__()

    def _attach(self, btn, tooltip):
        tooltip.attach(btn)
        self._tooltips.append(tooltip)
        return btn

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 12 placements
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        placements = [
            "top-start", "top", "top-end",
            "bottom-start", "bottom", "bottom-end",
            "right-start", "right", "right-end",
            "left-start", "left", "left-end",
        ]
        for i, place in enumerate(placements):
            btn = Button(place, color="primary", variant="flat")
            t = Tooltip(content=f"Tooltip at {place}", placement=place, show_arrow=True)
            self._attach(btn, t)
            grid.addWidget(btn, i // 3, i % 3)
        self.add_full_width(layout, "12 placements", grid_w, labels_bag)

        # 6 colors
        color_btns = []
        for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
            btn = Button(c, color=c, variant="flat")
            self._attach(btn, Tooltip(content=f"{c} tooltip", color=c))
            color_btns.append(btn)
        self.add_section(layout, "6 colors", color_btns, labels_bag, spacing=12)

        # offset
        offset_btns = []
        for off in [0, 3, 7, 14, 24]:
            btn = Button(f"offset={off}", color="primary", variant="flat")
            self._attach(btn, Tooltip(content=f"Offset: {off}px", offset=off,
                                       color="primary", show_arrow=True))
            offset_btns.append(btn)
        self.add_section(layout, "offset (距离控制)", offset_btns, labels_bag, spacing=12)

        # delay
        delay_specs = [
            ("默认 (0/150ms)", "success", {}, "open_delay=0, close_delay=150"),
            ("慢开 (500/150ms)", "warning", {"open_delay": 500}, "open_delay=500"),
            ("快关 (0/0ms)", "danger", {"close_delay": 0}, "open_delay=0, close_delay=0"),
            ("慢速 (300/500ms)", "secondary", {"open_delay": 300, "close_delay": 500},
             "open_delay=300, close_delay=500"),
        ]
        delay_btns = []
        for label, color, kwargs, content in delay_specs:
            btn = Button(label, color=color, variant="flat")
            self._attach(btn, Tooltip(content=content, color=color, **kwargs))
            delay_btns.append(btn)
        self.add_section(layout, "open_delay / close_delay", delay_btns, labels_bag, spacing=12)

        # arrow
        arrow_btns = [
            Button("无箭头", color="primary", variant="flat"),
            Button("有箭头", color="primary", variant="flat"),
        ]
        self._attach(arrow_btns[0], Tooltip(content="没有箭头", color="primary", show_arrow=False))
        self._attach(arrow_btns[1], Tooltip(content="带箭头指向 trigger", color="primary", show_arrow=True))
        self.add_section(layout, "show_arrow", arrow_btns, labels_bag, spacing=12)

        # size
        size_btns = []
        for sz in ["sm", "md", "lg"]:
            btn = Button(f"size={sz}", color="default", variant="flat")
            self._attach(btn, Tooltip(content=f"Size: {sz}", size=sz))
            size_btns.append(btn)
        self.add_section(layout, "size (sm / md / lg)", size_btns, labels_bag, spacing=12)

        # radius
        radius_btns = []
        for r in ["none", "sm", "md", "lg", "full"]:
            btn = Button(f"radius={r}", color="primary", variant="flat", radius=r)
            self._attach(btn, Tooltip(content=f"Radius: {r}", radius=r, color="primary"))
            radius_btns.append(btn)
        self.add_section(layout, "radius (none / sm / md / lg / full)",
                         radius_btns, labels_bag, spacing=12)

        # 自定义 widget 内容
        custom_btns = []

        # 富文本
        btn_rich = Button("富文本", color="secondary", variant="flat")
        rich_widget = QWidget()
        rich_layout = QVBoxLayout(rich_widget)
        rich_layout.setContentsMargins(10, 8, 10, 8)
        rich_layout.setSpacing(4)
        # 彩色 Tooltip 内的标题/描述：在 secondary 实底背景上显式用白色系
        # （这不是主题分支决策——彩色实底永远要白字，没有 light/dark 分歧）
        rich_title = Title("提示标题", level=3)
        rich_title.set_color("#ffffff")
        rich_desc = Body("这是一段多行描述文字，\n演示自定义 widget 的能力。")
        rich_desc.set_color("#e4e4e7")
        rich_layout.addWidget(rich_title)
        rich_layout.addWidget(rich_desc)
        t_rich = Tooltip(color="secondary", placement="bottom", show_arrow=True)
        t_rich.set_content(rich_widget)
        self._attach(btn_rich, t_rich)
        custom_btns.append(btn_rich)

        # 图标 + 文字
        btn_icon = Button("图标+文字", color="success", variant="flat")
        icon_widget = QWidget()
        icon_layout = QHBoxLayout(icon_widget)
        icon_layout.setContentsMargins(8, 6, 8, 6)
        icon_layout.setSpacing(6)
        icon_label = Title("✓", level=3)
        icon_label.set_color("#ffffff")
        text_label = Body("操作成功！")
        text_label.set_color("#ffffff")
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(text_label)
        t_icon = Tooltip(color="success", placement="bottom", show_arrow=True)
        t_icon.set_content(icon_widget)
        self._attach(btn_icon, t_icon)
        custom_btns.append(btn_icon)

        # 动态计数
        btn_dyn = Button("点击 +1 (count=0)", color="warning", variant="flat")
        t_dyn = Tooltip(content="当前计数: 0", color="warning", placement="bottom", show_arrow=True)
        self._attach(btn_dyn, t_dyn)
        counter = {"v": 0}
        def inc():
            counter["v"] += 1
            btn_dyn.setText(f"点击 +1 (count={counter['v']})")
            t_dyn.set_content(f"当前计数: {counter['v']}")
        btn_dyn.clicked.connect(inc)
        custom_btns.append(btn_dyn)

        self.add_section(layout, "自定义 widget 内容 (set_content)",
                         custom_btns, labels_bag, spacing=12)


if __name__ == "__main__":
    TooltipDemo.run()
