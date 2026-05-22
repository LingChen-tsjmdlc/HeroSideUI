"""
Slider 组件示例 — 6 colors / 3 sizes / 5 radius / range / vertical / marks / 自定义 formatter
                  + 顶部插槽 (Input 直接输数字) + 底部插槽 (Body 帮助文字)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import Slider, Input, Caption
from _base import DemoBase


class SliderDemo(DemoBase):
    component_name = "Slider"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 6 colors
        self.add_full_width_group(
            layout,
            "6 colors",
            [
                Slider(value=40, color=c, label=c.capitalize())
                for c in [
                    "foreground",
                    "primary",
                    "secondary",
                    "success",
                    "warning",
                    "danger",
                ]
            ],
            labels_bag,
        )

        # 3 sizes
        self.add_full_width_group(
            layout,
            "3 sizes",
            [
                Slider(value=50, size=s, color="primary", label=f"Size {s}")
                for s in ["sm", "md", "lg"]
            ],
            labels_bag,
        )

        # 5 radius (lg 看圆角差异最明显)
        self.add_full_width_group(
            layout,
            "5 radius (size=lg, thumb 圆角随 radius 变化)",
            [
                Slider(
                    value=60,
                    color="secondary",
                    size="lg",
                    radius=r,
                    label=f"radius={r}",
                )
                for r in ["none", "sm", "md", "lg", "full"]
            ],
            labels_bag,
        )

        # 细粒度步长：1-100，step=0.1
        self.add_full_width(
            layout,
            "step=0.1（min=1, max=100, 显示 1 位小数）",
            Slider(
                value=12.5,
                min_value=1,
                max_value=100,
                step=0.1,
                color="primary",
                label="Fine-grained",
                value_formatter=lambda v: f"{v:.1f}",
            ),
            labels_bag,
        )

        # Range (双 thumb)
        self.add_full_width_group(
            layout,
            "Range mode (双 thumb, value=(20, 80))",
            [
                Slider(
                    value=(20, 80),
                    color="primary",
                    label="Price Range",
                    value_formatter=lambda v: f"${int(v[0])} – ${int(v[1])}",
                ),
                Slider(value=(30, 70), color="success", size="lg", label="Temperature"),
            ],
            labels_bag,
        )

        # marks
        self.add_full_width(
            layout,
            "marks (吸附点 + 文字)",
            Slider(
                value=50,
                color="warning",
                size="md",
                label="Volume",
                marks=[
                    {"value": 0, "label": "0%"},
                    {"value": 25, "label": "25%"},
                    {"value": 50, "label": "50%"},
                    {"value": 75, "label": "75%"},
                    {"value": 100, "label": "100%"},
                ],
            ),
            labels_bag,
        )

        # show_steps
        self.add_full_width(
            layout,
            "show_steps (step=10, 沿 track 绘制小点)",
            Slider(
                value=30,
                min_value=0,
                max_value=100,
                step=10,
                color="success",
                size="md",
                show_steps=True,
                label="Discrete steps",
            ),
            labels_bag,
        )

        # show_outline
        self.add_full_width(
            layout,
            "show_outline (thumb 多一圈 ring)",
            Slider(
                value=40, color="primary", show_outline=True, label="With ring outline"
            ),
            labels_bag,
        )

        # hide_value / hide_thumb
        self.add_full_width_group(
            layout,
            "hide_value / hide_thumb",
            [
                Slider(value=40, color="primary", hide_value=True, label="hide_value"),
                Slider(
                    value=40, color="secondary", hide_thumb=True, label="hide_thumb"
                ),
            ],
            labels_bag,
        )

        # disabled
        self.add_full_width(
            layout,
            "is_disabled",
            Slider(value=40, color="danger", is_disabled=True, label="Disabled"),
            labels_bag,
        )

        # ----------------- top_end_content：右上角插槽（Input 直接输数字） -----------------
        # Slider 与 Input 双向同步：拖滑块时 Input 文字更新；改 Input 文字时滑块跳转
        s_with_input = Slider(
            value=42,
            min_value=0,
            max_value=100,
            color="primary",
            label="Volume",
            hide_value=True,  # 不再显示自带文字 value，避免和 Input 重复
        )
        num_input = Input(value="42", size="sm", radius="md")
        num_input.setFixedWidth(64)
        s_with_input.set_top_end_content(num_input)

        def _slider_to_input(v):
            txt = str(int(v))
            if num_input.line_edit.text() != txt:
                num_input.line_edit.setText(txt)

        def _input_to_slider(t: str):
            try:
                s_with_input.set_value(float(t))
            except ValueError:
                pass

        s_with_input.value_changed.connect(_slider_to_input)
        num_input.text_changed.connect(_input_to_slider)

        self.add_full_width(
            layout,
            "top_end_content：右上角插槽（Input 双向同步数值）",
            s_with_input,
            labels_bag,
        )

        # ----------------- bottom_start_content：左下角文字提示 -----------------
        self.add_full_width(
            layout,
            "bottom_start_content：左下角帮助文字（Caption）",
            Slider(
                value=70,
                color="success",
                label="Quality",
                value_formatter=lambda v: f"{int(v)} dpi",
                bottom_start_content=Caption("数值越大画质越高，但文件体积也会更大"),
            ),
            labels_bag,
        )

        # ----------------- 两个插槽组合 -----------------
        s_combo = Slider(
            value=50,
            min_value=0,
            max_value=100,
            color="warning",
            label="Brightness",
            hide_value=True,
            bottom_start_content=Caption("拖动滑块或在右上输入框内直接输入 0–100"),
        )
        combo_input = Input(value="50", size="sm", radius="md")
        combo_input.setFixedWidth(64)
        s_combo.set_top_end_content(combo_input)

        def _s2i(v):
            t = str(int(v))
            if combo_input.line_edit.text() != t:
                combo_input.line_edit.setText(t)

        def _i2s(t: str):
            try:
                s_combo.set_value(float(t))
            except ValueError:
                pass

        s_combo.value_changed.connect(_s2i)
        combo_input.text_changed.connect(_i2s)

        self.add_full_width(
            layout,
            "组合：top_end_content + bottom_start_content",
            s_combo,
            labels_bag,
        )

        # ----------------- start_content / end_content：track 两侧 icon -----------------
        # 典型用法：音量滑块两侧放低音/高音图标（HeroUI 官网范例）。
        # Slider 直接接受 icon name 字符串 —— 内部 load_svg_icon 渲染 +
        # 跟主题自动着色，零样板。也可以传任意 QWidget 当自定义控件。
        self.add_full_width(
            layout,
            "start_content / end_content：track 两侧 icon",
            Slider(
                value=40,
                color="primary",
                label="Volume",
                start_content="simple-line-icons--volume-1",
                end_content="fluent-mdl2--volume-3",
            ),
            labels_bag,
        )

        # ----------------- fill_offset：双向条（origin 在中间）-----------------
        # 把 fill_offset 设到范围中点，filler 从中点向当前值扩展，可正可负
        self.add_full_width(
            layout,
            "fill_offset：双向条（origin=0，从中点向左/右扩展）",
            Slider(
                value=30,
                min_value=-100,
                max_value=100,
                step=1,
                color="secondary",
                label="Pan",
                fill_offset=0,
                value_formatter=lambda v: ("+" if v > 0 else "") + f"{int(v)}",
            ),
            labels_bag,
        )

        # ----------------- show_tooltip：拖拽时 thumb 上方显示当前值 -----------------
        self.add_full_width_group(
            layout,
            "show_tooltip：拖拽时 thumb 上方显示当前值",
            [
                Slider(
                    value=50,
                    color="success",
                    label="Quality",
                    show_tooltip=True,
                    value_formatter=lambda v: f"{int(v)}%",
                ),
                Slider(
                    value=(20, 80),
                    color="warning",
                    label="Range with tooltip",
                    show_tooltip=True,
                ),
            ],
            labels_bag,
        )

        # Vertical
        v_row = QWidget()
        v_layout = QHBoxLayout(v_row)
        v_layout.setSpacing(40)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for c in ("primary", "secondary", "success", "warning"):
            s = Slider(
                value=60,
                color=c,
                size="md",
                orientation="vertical",
                label=c.capitalize(),
            )
            s.setFixedHeight(220)
            v_layout.addWidget(s)
        layout.addWidget(self._section_title("Vertical orientation"))
        layout.addWidget(v_row)

        # Dynamic — slider 驱动另一个 slider
        master = Slider(value=20, color="primary", label="Master (drive others)")
        followers = [
            Slider(value=20, color=c, label=f"Follower ({c})")
            for c in ("secondary", "success", "warning", "danger")
        ]

        def _on_master(v):
            for f in followers:
                f.set_value(v)

        master.value_changed.connect(_on_master)

        self.add_full_width_group(
            layout,
            "Dynamic: master.value_changed → followers.set_value",
            [master, *followers],
            labels_bag,
        )


if __name__ == "__main__":
    SliderDemo.run()
