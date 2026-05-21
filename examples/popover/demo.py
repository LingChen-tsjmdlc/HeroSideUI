"""
Popover 组件示例 — 12 placement / 7 colors / shadow / radius / backdrop /
插槽（任意内容）/ hover trigger / arrow
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget

from hero_side_ui import (
    Popover,
    PopoverContent,
    Button,
    Input,
    Checkbox,
    Spinner,
    Card,
    CardHeader,
    CardBody,
    Body,
    Subtitle,
)
from _base import DemoBase


def make_popover(text: str, **kwargs) -> Popover:
    p = Popover(**kwargs)
    c = PopoverContent()
    # 用 Body：跟随 ThemeProvider 自动配色 + 走 FontProvider 思源黑体
    c.layout().addWidget(Body(text))
    p.set_content(c)
    return p


class PopoverDemo(DemoBase):
    component_name = "Popover"

    def __init__(self):
        # 持有 popover 引用避免被 GC
        self._popovers: list = []
        super().__init__()

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 12 placements
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        placements = [
            "top-start",
            "top",
            "top-end",
            "bottom-start",
            "bottom",
            "bottom-end",
            "right-start",
            "right",
            "right-end",
            "left-start",
            "left",
            "left-end",
        ]
        for i, place in enumerate(placements):
            btn = Button(place, color="primary", variant="flat")
            p = make_popover(f"Popover at {place}", placement=place, color="default")
            p.attach(btn)
            self._popovers.append(p)
            grid.addWidget(btn, i // 3, i % 3)
        self.add_full_width(layout, "12 placements", grid_w, labels_bag)

        # 7 colors
        color_btns = []
        for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
            b = Button(c.capitalize(), color="primary", variant="flat")
            p = make_popover(f"Color = {c}", color=c, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            color_btns.append(b)
        self.add_section(layout, "7 colors", color_btns, labels_bag, spacing=12)

        # Shadow
        shadow_btns = []
        for s in ["none", "sm", "md", "lg"]:
            b = Button(f"shadow={s}", variant="flat", color="primary")
            p = make_popover(f"shadow={s}", shadow=s, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            shadow_btns.append(b)
        self.add_section(layout, "Shadow", shadow_btns, labels_bag, spacing=12)

        # Radius
        radius_btns = []
        for r in ["none", "sm", "md", "lg", "full"]:
            b = Button(f"radius={r}", variant="flat", color="secondary")
            p = make_popover(f"radius={r}", radius=r, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            radius_btns.append(b)
        self.add_section(layout, "Radius", radius_btns, labels_bag, spacing=12)

        # Backdrop
        bd_btns = []
        for kind in ["transparent", "opaque", "blur"]:
            b = Button(f"backdrop={kind}", variant="flat", color="warning")
            p = make_popover(
                f"backdrop = {kind} (click outside to close)",
                backdrop=kind,
                placement="bottom",
            )
            p.attach(b)
            self._popovers.append(p)
            bd_btns.append(b)
        self.add_section(layout, "Backdrop", bd_btns, labels_bag, spacing=12)

        # 插槽：任意内容
        # 1) 表单
        form_btn = Button("Settings", color="primary", variant="solid")
        form_pop = Popover(placement="bottom-start", shadow="lg", color="default")
        form = PopoverContent()
        form.setMinimumWidth(240)
        form.layout().setSpacing(10)
        # 表单小标题用 Subtitle
        form.layout().addWidget(Subtitle("Account Settings"))
        form.layout().addWidget(Input(label="Username", placeholder="@you", size="sm"))
        form.layout().addWidget(
            Input(label="Email", placeholder="you@example.com", size="sm")
        )
        form.layout().addWidget(Checkbox("Receive emails", color="primary", size="sm"))
        form.layout().addWidget(
            Button("Save", color="primary", variant="solid", size="sm")
        )
        form_pop.set_content(form)
        form_pop.attach(form_btn)
        self._popovers.append(form_pop)

        # 2) Spinner
        spin_btn = Button("Loading...", color="success", variant="flat")
        spin_pop = Popover(placement="bottom", color="default", shadow="md")
        sc = PopoverContent()
        sc.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.layout().addWidget(Spinner(label="Working..."))
        spin_pop.set_content(sc)
        spin_pop.attach(spin_btn)
        self._popovers.append(spin_pop)

        # 3) 完整 Card
        card_btn = Button("Profile Card", color="secondary", variant="flat")
        card_pop = Popover(placement="bottom", color="default", shadow="lg")
        cc = PopoverContent()
        cc.layout().setContentsMargins(0, 0, 0, 0)
        inner_card = Card(shadow="none", radius="md")
        inner_card.setFixedWidth(260)
        h = CardHeader()
        # Card 头/正文：Subtitle + Body 语义化
        h.layout().addWidget(Subtitle("Jerry Lu"))
        inner_card.add_header(h)
        bb = CardBody()
        bb.layout().addWidget(
            Body("Senior Tech Artist @ Tencent\nWorking on HeroSideUI")
        )
        inner_card.add_body(bb)
        cc.layout().addWidget(inner_card)
        card_pop.set_content(cc)
        card_pop.attach(card_btn)
        self._popovers.append(card_pop)

        self.add_section(
            layout,
            "插槽：什么都能放（Form / Spinner / Card）",
            [form_btn, spin_btn, card_btn],
            labels_bag,
            spacing=12,
        )

        # hover trigger
        hover_btn = Button("Hover me", color="danger", variant="flat")
        hover_pop = make_popover(
            "Triggered by hover", placement="bottom", color="danger"
        )
        hover_pop.attach(hover_btn, event="hover")
        self._popovers.append(hover_pop)
        self.add_section(layout, "hover 触发", [hover_btn], labels_bag, spacing=12)

        # arrow=True
        arrow_btns = []
        for place in ["top", "bottom", "left", "right"]:
            b = Button(f"{place} + arrow", color="primary", variant="flat")
            p = make_popover(
                f"arrow @ {place}", placement=place, color="default", arrow=True
            )
            p.attach(b)
            self._popovers.append(p)
            arrow_btns.append(b)
        self.add_section(
            layout, "arrow=True（显示箭头）", arrow_btns, labels_bag, spacing=12
        )

        # 彩色 arrow
        color_arrow_btns = []
        for c in ["primary", "success", "warning", "danger"]:
            b = Button(f"arrow {c}", color=c, variant="flat")
            p = make_popover(
                f"{c} popover with arrow", placement="bottom", color=c, arrow=True
            )
            p.attach(b)
            self._popovers.append(p)
            color_arrow_btns.append(b)
        self.add_section(layout, "彩色 arrow", color_arrow_btns, labels_bag, spacing=12)


if __name__ == "__main__":
    PopoverDemo.run()
