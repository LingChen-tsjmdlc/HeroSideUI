"""
Textarea 组件示例 — 3 变体 × 6 颜色 × 3 尺寸 × 4 label 位置 × auto-resize × 各种状态
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget

from hero_side_ui import Textarea, Button
from _base import DemoBase


COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
# Textarea 不支持 underlined
VARIANTS = ["flat", "faded", "bordered"]


def grid_of_textareas(variant: str, label_placement: str = "inside") -> QWidget:
    """6 个颜色的 Textarea 排成 3 列网格"""
    w = QWidget()
    grid = QGridLayout(w)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(12)
    for i, c in enumerate(COLORS):
        ta = Textarea(
            label=c.title(), variant=variant, color=c, size="md",
            label_placement=label_placement,
            placeholder=f"Type something in {c}...",
        )
        grid.addWidget(ta, i // 3, i % 3)
    return w


class TextareaDemo(DemoBase):
    component_name = "Textarea"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 3 变体 × 6 颜色
        for v in VARIANTS:
            self.add_full_width(layout, f"Variant: {v}",
                               grid_of_textareas(v), labels_bag)

        # 3 尺寸
        size_row = QWidget()
        hl = QHBoxLayout(size_row)
        hl.setContentsMargins(0, 0, 0, 0)
        for s in ["sm", "md", "lg"]:
            hl.addWidget(Textarea(label=f"Size {s}", variant="flat", color="primary",
                                  size=s, placeholder="Tell us a bit..."))
        self.add_full_width(layout, "3 sizes (variant=flat, color=primary)",
                           size_row, labels_bag)

        # 4 label placements
        for lp in ["inside", "outside", "outside-top", "outside-left"]:
            self.add_full_width(layout, f"label_placement = {lp}",
                               grid_of_textareas("flat", lp), labels_bag)

        # Auto-resize 演示
        self.add_full_width(layout, "Auto-resize (min_rows=3, max_rows=8) — 默认行为",
            Textarea(label="Description",
                     placeholder="从 3 行起步，输入更多内容会自动长高，超过 8 行出现滚动条...",
                     variant="flat", color="primary"),
            labels_bag)

        self.add_full_width(layout, "disable_autosize=True — 固定 4 行",
            Textarea(label="Fixed 4 rows",
                     placeholder="高度锁死，超出内容会滚动",
                     variant="bordered", color="secondary",
                     min_rows=4, disable_autosize=True),
            labels_bag)

        self.add_full_width(layout, "min_rows=1, max_rows=12 — 从单行到 12 行",
            Textarea(label="Flexible",
                     placeholder="试试从一行写到很多行...",
                     variant="flat", color="success",
                     min_rows=1, max_rows=12),
            labels_bag)

        # Placeholder
        self.add_full_width(layout, "Placeholder 演示",
            Textarea(label="Bio", placeholder="Tell us a bit about yourself...",
                     variant="flat", color="primary"),
            labels_bag)

        # States
        self.add_full_width(layout, "is_disabled",
            Textarea(label="Disabled", value="This is disabled content.",
                     variant="flat", is_disabled=True),
            labels_bag)

        self.add_full_width(layout, "is_readonly",
            Textarea(label="Readonly",
                     value="这是只读内容。\n无法编辑，但可以复制。",
                     variant="flat", is_readonly=True),
            labels_bag)

        self.add_full_width(layout, "is_required",
            Textarea(label="Description", placeholder="Required field",
                     variant="bordered", color="primary", is_required=True),
            labels_bag)

        self.add_full_width(layout, "is_clearable",
            Textarea(label="Clearable",
                     value="点击右上角的 × 按钮清空内容",
                     variant="flat", color="primary", is_clearable=True),
            labels_bag)

        # is_invalid 跨三种 variant
        invalid_widgets = [
            Textarea(label=f"Description ({v})", variant=v,
                     placeholder="必须填写...",
                     is_invalid=True, error_message="描述不能为空，请填写至少 10 个字")
            for v in VARIANTS
        ]
        self.add_full_width_group(layout, "is_invalid + error_message",
                                  invalid_widgets, labels_bag)

        # Description
        self.add_full_width(layout, "description 辅助文字",
            Textarea(label="Feedback",
                     placeholder="请告诉我们你的想法...",
                     variant="flat", color="primary",
                     description="你的反馈会帮助我们改进产品"),
            labels_bag)

        # ============================================================
        # 三个新的内容槽：top_right / center_right / bottom_right
        # ============================================================
        # top_right —— wrapper 右上角（layout 内）
        send_top = Button("Send", size="sm", variant="flat", color="primary")
        send_top.clicked.connect(lambda: print("[Send@top_right] clicked"))
        self.add_full_width(layout, "top_right_content = Button（wrapper 右上角）",
            Textarea(label="Message",
                     placeholder="按钮永远贴右上角...",
                     variant="flat", color="default",
                     top_right_content=send_top),
            labels_bag)

        # top_right 字符串图标
        self.add_full_width(layout, "top_right_content = 字符串图标 + 点击回调",
            Textarea(label="Note",
                     placeholder="点击右上角 × 触发自定义回调",
                     variant="bordered", color="primary",
                     top_right_content="heroicons--x-circle-solid",
                     on_top_right_content_click=lambda: print("[top_right icon] clicked")),
            labels_bag)

        # center_right —— wrapper 垂直居中（绝对定位，随高度实时居中）
        send_center = Button("Send", size="sm", variant="flat", color="primary")
        send_center.clicked.connect(lambda: print("[Send@center_right] clicked"))
        self.add_full_width(layout, "center_right_content = Button（垂直居中，随高度变化实时居中）",
            Textarea(label="Message",
                     placeholder="多输入几行，看 Send 永远在垂直中线上",
                     variant="flat", color="default",
                     min_rows=3, max_rows=10,
                     center_right_content=send_center),
            labels_bag)

        # bottom_right —— wrapper 右下角（绝对定位）
        send_bottom = Button("Send", size="sm", variant="solid", color="primary")
        send_bottom.clicked.connect(lambda: print("[Send@bottom_right] clicked"))
        self.add_full_width(layout, "bottom_right_content = Button（右下角，类似 Tailwind absolute right-X bottom-X）",
            Textarea(label="Message",
                     placeholder="Chat 输入框风格 —— Send 永远贴右下角",
                     variant="flat", color="default",
                     min_rows=3, max_rows=10,
                     bottom_right_content=send_bottom,
                     bottom_right_offset=(10, 10)),
            labels_bag)

        # 双槽并存 (top_right + bottom_right)
        counter_widget = Button("0/200", size="sm", variant="flat", color="default")
        counter_widget.setEnabled(False)
        send_combo = Button("Send", size="sm", variant="solid", color="primary")
        send_combo.clicked.connect(lambda: print("[Combo Send] clicked"))
        self.add_full_width(layout, "双槽并存 (top_right=计数器 / bottom_right=Send)",
            Textarea(label="Tweet",
                     placeholder="说点什么...",
                     variant="flat", color="primary",
                     min_rows=4, max_rows=8,
                     top_right_content=counter_widget,
                     bottom_right_content=send_combo,
                     bottom_right_offset=(10, 10)),
            labels_bag)

        # 事件
        ev = Textarea(label="Type here", placeholder="事件演示",
                      variant="flat", color="primary", is_clearable=True)
        ev.text_changed.connect(lambda t: print(f"[changed] {t!r}"))
        ev.cleared.connect(lambda: print("[cleared]"))
        ev.height_changed.connect(lambda h, r: print(f"[height_changed] h={h} row_h={r}"))
        ev.focus_in.connect(lambda: print("[focus_in]"))
        ev.focus_out.connect(lambda: print("[focus_out]"))
        self.add_full_width(layout, "Event demo (控制台查看输出)", ev, labels_bag)

        # 手动 resize
        self.add_full_width(layout, "resizable=True — 拖右下角小手柄改变高度（默认关闭）",
            Textarea(label="Drag bottom-right",
                     placeholder="在我的右下角小手柄上按住鼠标向下拖...",
                     variant="flat", color="primary",
                     min_rows=3, max_rows=10,
                     resizable=True),
            labels_bag)

        self.add_full_width(layout, 'resizable=False (默认) — 无手柄',
            Textarea(label="No grip",
                     placeholder="右下角没有手柄（默认行为）",
                     variant="flat", color="default"),
            labels_bag)


if __name__ == "__main__":
    TextareaDemo.run()
