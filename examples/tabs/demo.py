"""
Tabs 组件示例 — 4 variants × 6 colors × 3 sizes × 5 radius × 4 placement +
TabItem 三档（纯文本 / icon+文本 / 完全自定义 widget）

content 区域用 Card + CardBody 包裹，对齐 HeroUI v2 docs 用法
（https://v2.heroui.com/docs/components/tabs）：
Tabs 组件本身不渲染卡片底，由用户在 content 里自己组合 Card —— 保留
完整自定义性，跟原版语义一致。
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget

from hero_side_ui import Tabs, Card, CardBody, Body
from _base import DemoBase


def panel(text: str) -> Card:
    """构造一个标准 Card+CardBody 的 tab 内容面板（对齐 HeroUI docs 用法）。"""
    card = Card()
    body = CardBody()
    msg = Body(text)
    msg.setWordWrap(True)
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    body.layout().addWidget(msg)
    card.add_body(body)
    return card


def labeled_row(label_text: str, *widgets: QWidget) -> QWidget:
    """一行：文字标签 + widget(s)"""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(QLabel(label_text))
    for ww in widgets:
        h.addWidget(ww)
    h.addStretch()
    return w


class TabsDemo(DemoBase):
    component_name = "Tabs"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 4 种 variant
        variants_widgets = []
        for v in ["solid", "bordered", "light", "underlined"]:
            t = Tabs(variant=v, color="primary")
            t.add_tab("Photos", panel(f"Photos - {v}"))
            t.add_tab("Music", panel(f"Music - {v}"))
            t.add_tab("Videos", panel(f"Videos - {v}"))
            variants_widgets.append(labeled_row(f"{v}:", t))
        self.add_full_width_group(layout, "4 种 variant", variants_widgets, labels_bag)

        # 6 colors × solid
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        for i, c in enumerate(["default", "primary", "secondary", "success", "warning", "danger"]):
            t = Tabs(["A", "B", "C"], variant="solid", color=c)
            grid.addWidget(QLabel(c), i // 3, (i % 3) * 2)
            grid.addWidget(t, i // 3, (i % 3) * 2 + 1)
        self.add_full_width(layout, "6 colors × solid", grid_w, labels_bag)

        # 6 colors × underlined
        grid_w2 = QWidget()
        grid2 = QGridLayout(grid_w2)
        grid2.setContentsMargins(0, 0, 0, 0)
        for i, c in enumerate(["default", "primary", "secondary", "success", "warning", "danger"]):
            t = Tabs(["A", "B", "C"], variant="underlined", color=c)
            grid2.addWidget(QLabel(c), i // 3, (i % 3) * 2)
            grid2.addWidget(t, i // 3, (i % 3) * 2 + 1)
        self.add_full_width(layout, "6 colors × underlined", grid_w2, labels_bag)

        # 3 sizes
        size_rows = []
        for s in ["sm", "md", "lg"]:
            size_rows.append(labeled_row(
                f"{s}:", Tabs(["Photos", "Music", "Videos"], size=s, color="primary")
            ))
        self.add_full_width_group(layout, "3 sizes (sm / md / lg)", size_rows, labels_bag)

        # 5 radius
        radius_rows = []
        for r in ["none", "sm", "md", "lg", "full"]:
            radius_rows.append(labeled_row(
                f"radius={r}:", Tabs(["A", "B", "C"], color="secondary", radius=r)
            ))
        self.add_full_width_group(layout, "5 radius (none/sm/md/lg/full)",
                                  radius_rows, labels_bag)

        # 4 placements
        place_w = QWidget()
        grid3 = QGridLayout(place_w)
        grid3.setContentsMargins(0, 0, 0, 0)
        for i, p in enumerate(["top", "bottom", "start", "end"]):
            t = Tabs(placement=p, color="primary", variant="solid")
            t.add_tab("Photos", panel(f"Photos - {p}"))
            t.add_tab("Music", panel(f"Music - {p}"))
            t.add_tab("Videos", panel(f"Videos - {p}"))
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.addWidget(QLabel(p))
            wl.addWidget(t)
            grid3.addWidget(wrap, i // 2, i % 2)
        self.add_full_width(layout, "4 placements (top / bottom / start / end)",
                           place_w, labels_bag)

        # full_width
        self.add_full_width(layout, "full_width",
            Tabs(["Login", "Sign Up", "Forgot password"],
                 variant="bordered", color="primary", full_width=True),
            labels_bag)

        # is_disabled
        self.add_full_width_group(layout, "is_disabled (整体) / 单 tab disabled", [
            labeled_row("is_disabled=True",
                        Tabs(["A", "B", "C"], color="primary", is_disabled=True)),
            labeled_row("中间 disabled:", self._tabs_with_disabled()),
        ], labels_bag)

        # disable_animation
        self.add_full_width(layout, "disable_animation=True",
            Tabs(["A", "B", "C"], color="success", disable_animation=True),
            labels_bag)

        # TabItem 档 2: icon + 文本
        t_icon = Tabs(color="primary", variant="bordered")
        t_icon.add_tab("Next", panel("Next panel"),
                       start_icon="heroicons--chevron-right-solid")
        t_icon.add_tab("Show", panel("Show panel"),
                       end_icon="heroicons--eye-solid")
        t_icon.add_tab("Hide", panel("Hide panel"),
                       start_icon="heroicons--eye-slash-solid",
                       end_icon="heroicons--check-solid")

        t_icon2 = Tabs(color="success", variant="underlined")
        t_icon2.add_tab("Done", panel("Done"), start_icon="heroicons--check-solid")
        t_icon2.add_tab("Next", panel("Next"), end_icon="heroicons--chevron-right-solid")
        t_icon2.add_tab("Hide", panel("Hide"), start_icon="heroicons--eye-slash-solid")

        self.add_full_width_group(
            layout, "TabItem 档 2 — start_icon / end_icon",
            [t_icon, t_icon2], labels_bag,
        )

        # TabItem 档 3: custom widget
        t_custom = Tabs(color="primary", variant="bordered")
        t_custom.add_tab("Inbox", panel("Inbox"))
        t_custom.add_tab(custom=self._dot_widget("📬", "Notifications"),
                        content=panel("Notifications"), key="noti")
        t_custom.add_tab(custom=self._dot_widget("💬", "Messages", "#f5a524"),
                        content=panel("Messages"), key="msg")
        t_custom.add_tab("Trash", panel("Trash"))
        self.add_full_width(layout, "TabItem 档 3 — custom widget", t_custom, labels_bag)

    def _tabs_with_disabled(self) -> Tabs:
        t = Tabs(color="primary")
        t.add_tab("Active", panel("Active"))
        t.add_tab("Disabled", panel("Disabled"), disabled=True)
        t.add_tab("Active 2", panel("Active 2"))
        return t

    def _dot_widget(self, emoji: str, label: str, dot_color: str = "#f31260") -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(6)
        ic = QLabel(emoji)
        ic.setFont(QFont("Segoe UI Emoji", 13))
        lay.addWidget(ic)
        tx = QLabel(label)
        tx.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        lay.addWidget(tx)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{dot_color}; border-radius:4px;")
        lay.addWidget(dot)
        return w


if __name__ == "__main__":
    TabsDemo.run()
