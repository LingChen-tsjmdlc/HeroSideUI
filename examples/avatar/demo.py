"""Avatar / AvatarGroup 组件示例 — 对齐 HeroUI Avatar 页面全部示例。

示例:
 1. Default          — 默认人像图标兜底
 2. Sizes            — sm / md / lg
 3. Colors           — 6 语义色
 4. Radius           — none / sm / md / lg / full
 5. Bordered         — 彩色描边环
 6. Disabled         — 禁用半透明
 7. WithText         — name 首字母缩写
 8. WithImage        — 图片头像
 9. Fallback         — 图片加载中显示首字母兜底
10. Group            — 头像组（重叠堆叠 + max/total）
11. Group Grid       — 网格排布
12. Custom Count     — 自定义计数控件

远程图源使用 https://uapis.cn/api/v1/random/image —— 每次请求随机返回一张图片。
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Avatar, AvatarGroup, Text
from _base import DemoBase

logging.basicConfig(
    level=logging.WARNING, format="[%(name)s] %(levelname)s: %(message)s"
)

_IMG = "https://uapis.cn/api/v1/random/image"

COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
RADII = ["none", "sm", "md", "lg", "full"]
SIZES = ["sm", "md", "lg"]


class AvatarDemo(DemoBase):
    component_name = "Avatar"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 1. Default — 默认人像图标
        self.add_section(layout, "Default", [Avatar()])

        # 2. Sizes
        self.add_section(
            layout, "Sizes",
            [Avatar(name="JW", size=s) for s in SIZES],
        )

        # 3. Colors
        self.add_section(
            layout, "Colors",
            [Avatar(name=c[0].upper(), color=c) for c in COLORS],
        )

        # 4. Radius
        self.add_section(
            layout, "Radius",
            [Avatar(name="R", color="primary", radius=r) for r in RADII],
        )

        # 5. Bordered
        self.add_section(
            layout, "Bordered",
            [Avatar(name=c[0].upper(), color=c, is_bordered=True) for c in COLORS],
        )

        # 6. Disabled
        self.add_section(
            layout, "Disabled",
            [
                Avatar(name="JW", color="secondary", is_bordered=True, is_disabled=True),
                Avatar(name="AB", color="danger", is_disabled=True),
            ],
        )

        # 7. WithText — 首字母缩写
        self.add_section(
            layout, "With Text (首字母)",
            [
                Avatar(name="Jane Wu", color="danger"),
                Avatar(name="张伟", color="primary"),
                Avatar(name="Junior", color="success"),
            ],
        )

        # 8. WithImage — 图片头像
        self.add_section(
            layout, "With Image",
            [Avatar(src=_IMG, size="lg") for _ in range(3)],
        )

        # 9. Fallback — 图片加载中/失败显示首字母
        self.add_section(
            layout, "Fallback (加载中显示首字母)",
            [
                Avatar(src=_IMG, name="Junior", color="warning", show_fallback=True),
                Avatar(src="https://invalid.example/broken.png", name="404",
                       color="danger", show_fallback=True),
            ],
        )

        # 10. Pressable / Hover — 自定义点击与 hover 事件
        self._build_interactive(layout)

        # 11. AvatarGroup
        layout.addWidget(self._section_title("Group (重叠堆叠)"))
        layout.addWidget(
            AvatarGroup(
                [Avatar(src=_IMG) for _ in range(5)],
                color="primary",
                is_bordered=True,
            )
        )

        # 12. Group with max/total
        layout.addWidget(self._section_title("Group with max=3, total=10"))
        layout.addWidget(
            AvatarGroup(
                [Avatar(src=_IMG) for _ in range(8)],
                color="primary",
                is_bordered=True,
                max=3,
                total=10,
            )
        )

        # 12. Group Grid
        layout.addWidget(self._section_title("Group Grid"))
        layout.addWidget(
            AvatarGroup(
                [Avatar(name=f"{i}") for i in range(9)],
                color="secondary",
                is_bordered=True,
                max=7,
                is_grid=True,
            )
        )

        # 13. Custom Count
        layout.addWidget(self._section_title("Custom Count"))

        def _count(n: int) -> Text:
            # 对齐 HeroUI 官方示例：+N others，小号中等字重
            return Text(f"+{n} others", size="sm", weight="medium")

        layout.addWidget(
            AvatarGroup(
                [Avatar(src=_IMG) for _ in range(6)],
                color="primary",
                is_bordered=True,
                max=3,
                total=10,
                render_count=_count,
            )
        )

    def _build_interactive(self, layout):
        """可点击 + hover 事件示例。"""
        from hero_side_ui import Caption

        status = Caption("点击或悬停上面的头像试试")

        def _on_click():
            status.setText("头像被点击了！")

        def _on_hover(hovered: bool):
            if hovered:
                status.setText("鼠标悬停中…")
            else:
                status.setText("鼠标已离开")

        clickable = Avatar(
            name="Click Me",
            color="primary",
            is_bordered=True,
            is_pressable=True,
            on_click=_on_click,
            on_hover=_on_hover,
        )

        # 用信号方式连接另一个头像
        signal_av = Avatar(name="Signal", color="success", is_pressable=True)
        signal_av.clicked.connect(lambda: status.setText("（信号）Signal 头像被点击！"))

        self.add_section(layout, "Pressable / Hover", [clickable, signal_av])
        layout.addWidget(status)


if __name__ == "__main__":
    AvatarDemo.run()
