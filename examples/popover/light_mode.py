"""
Popover 组件示例 - 亮色模式
展示 12 种 placement、各种 color/shadow/radius，以及"插槽什么都能放"的能力。
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import (
    Popover, PopoverContent,
    Button, Input, Checkbox, Spinner,
    Card, CardHeader, CardBody,
)


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #3f3f46; margin-top: 16px;")
    return lbl


def make_simple_popover(text: str, **kwargs) -> Popover:
    p = Popover(**kwargs)
    c = PopoverContent()
    label = QLabel(text)
    c.layout().addWidget(label)
    p.set_content(c)
    return p


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Popover 示例 - 亮色模式")
    window.resize(900, 800)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(12)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Popover - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # ---- 12 种 placement ----
    layout.addWidget(section("12 placements"))
    grid = QGridLayout()
    grid.setSpacing(12)
    # 按图里的 4x3 排序：
    #   Row 1: top-start    top     top-end
    #   Row 2: bottom-start bottom  bottom-end
    #   Row 3: right-start  right   right-end
    #   Row 4: left-start   left    left-end
    placements = [
        "top-start",    "top",    "top-end",
        "bottom-start", "bottom", "bottom-end",
        "right-start",  "right",  "right-end",
        "left-start",   "left",   "left-end",
    ]
    poppers = []
    for i, place in enumerate(placements):
        btn = Button(place, color="primary", variant="flat")
        p = make_simple_popover(
            f"Popover at {place}",
            placement=place, color="default",
        )
        p.attach(btn)
        poppers.append(p)
        grid.addWidget(btn, i // 3, i % 3)
    layout.addLayout(grid)

    # ---- 7 种颜色 ----
    layout.addWidget(section("7 colors"))
    color_row = QHBoxLayout()
    color_row.setSpacing(12)
    colors = ["default", "primary", "secondary", "success", "warning", "danger"]
    color_pops = []
    for c in colors:
        b = Button(c.capitalize(), color="primary", variant="flat")
        p = make_simple_popover(
            f"Color = {c}",
            color=c, placement="bottom",
        )
        p.attach(b)
        color_pops.append(p)
        color_row.addWidget(b)
    color_row.addStretch()
    layout.addLayout(color_row)

    # ---- 阴影 / 圆角 ----
    layout.addWidget(section("Shadow / Radius"))
    sr_row = QHBoxLayout()
    sr_row.setSpacing(12)
    sr_pops = []
    for s in ["none", "sm", "md", "lg"]:
        b = Button(f"shadow={s}", variant="flat", color="primary")
        p = make_simple_popover(
            f"shadow={s}", shadow=s, placement="bottom",
        )
        p.attach(b)
        sr_pops.append(p)
        sr_row.addWidget(b)
    sr_row.addStretch()
    layout.addLayout(sr_row)

    sr2_row = QHBoxLayout()
    sr2_row.setSpacing(12)
    for r in ["none", "sm", "md", "lg", "full"]:
        b = Button(f"radius={r}", variant="flat", color="secondary")
        p = make_simple_popover(
            f"radius={r}", radius=r, placement="bottom",
        )
        p.attach(b)
        sr_pops.append(p)
        sr2_row.addWidget(b)
    sr2_row.addStretch()
    layout.addLayout(sr2_row)

    # ---- backdrop ----
    layout.addWidget(section("Backdrop"))
    bd_row = QHBoxLayout()
    bd_row.setSpacing(12)
    bd_pops = []
    for kind in ["transparent", "opaque", "blur"]:
        b = Button(f"backdrop={kind}", variant="flat", color="warning")
        p = make_simple_popover(
            f"backdrop = {kind} (click outside to close)",
            backdrop=kind, placement="bottom",
        )
        p.attach(b)
        bd_pops.append(p)
        bd_row.addWidget(b)
    bd_row.addStretch()
    layout.addLayout(bd_row)

    # ---- 插槽: 任意内容 ----
    layout.addWidget(section("插槽：什么都能放（Form / Spinner / Card）"))
    slot_row = QHBoxLayout()
    slot_row.setSpacing(12)

    # 1) 表单
    form_btn = Button("Settings", color="primary", variant="solid")
    form_pop = Popover(placement="bottom-start", shadow="lg", color="default")
    form = PopoverContent()
    form.setMinimumWidth(240)
    form.layout().setSpacing(10)
    form.layout().addWidget(QLabel("Account Settings"))
    form.layout().addWidget(Input(label="Username", placeholder="@you", size="sm"))
    form.layout().addWidget(Input(label="Email", placeholder="you@example.com", size="sm"))
    form.layout().addWidget(Checkbox("Receive emails", color="primary", size="sm"))
    save_btn = Button("Save", color="primary", variant="solid", size="sm")
    form.layout().addWidget(save_btn)
    form_pop.set_content(form)
    form_pop.attach(form_btn)
    slot_row.addWidget(form_btn)

    # 2) Spinner
    spin_btn = Button("Loading...", color="success", variant="flat")
    spin_pop = Popover(placement="bottom", color="default", shadow="md")
    sc = PopoverContent()
    sc.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
    sc.layout().addWidget(Spinner(label="Working..."))
    spin_pop.set_content(sc)
    spin_pop.attach(spin_btn)
    slot_row.addWidget(spin_btn)

    # 3) 完整 Card
    card_btn = Button("Profile Card", color="secondary", variant="flat")
    card_pop = Popover(placement="bottom", color="default", shadow="lg")
    cc = PopoverContent()
    cc.layout().setContentsMargins(0, 0, 0, 0)
    inner_card = Card(shadow="none", radius="md")
    inner_card.setFixedWidth(260)
    h = CardHeader()
    h.layout().addWidget(QLabel("Jerry Lu"))
    inner_card.add_header(h)
    b = CardBody()
    b.layout().addWidget(QLabel("Senior Tech Artist @ Tencent\nWorking on HeroSideUI"))
    inner_card.add_body(b)
    cc.layout().addWidget(inner_card)
    card_pop.set_content(cc)
    card_pop.attach(card_btn)
    slot_row.addWidget(card_btn)

    slot_row.addStretch()
    layout.addLayout(slot_row)

    # ---- hover trigger ----
    layout.addWidget(section("hover 触发"))
    hover_row = QHBoxLayout()
    hover_btn = Button("Hover me", color="danger", variant="flat")
    hover_pop = make_simple_popover(
        "Triggered by hover",
        placement="bottom", color="danger",
    )
    hover_pop.attach(hover_btn, event="hover")
    hover_row.addWidget(hover_btn)
    hover_row.addStretch()
    layout.addLayout(hover_row)

    # ---- arrow=True ----
    layout.addWidget(section("arrow=True（显示箭头）"))
    arrow_row = QHBoxLayout()
    arrow_row.setSpacing(12)
    arrow_pops = []
    arrow_places = ["top", "bottom", "left", "right"]
    for place in arrow_places:
        b = Button(f"{place} + arrow", color="primary", variant="flat")
        p = make_simple_popover(
            f"arrow @ {place}",
            placement=place, color="default", arrow=True,
        )
        p.attach(b)
        arrow_pops.append(p)
        arrow_row.addWidget(b)
    arrow_row.addStretch()
    layout.addLayout(arrow_row)

    # 彩色 arrow（背景色 popover）
    arrow_row2 = QHBoxLayout()
    arrow_row2.setSpacing(12)
    for c in ["primary", "success", "warning", "danger"]:
        b = Button(f"arrow {c}", color=c, variant="flat")
        p = make_simple_popover(
            f"{c} popover with arrow",
            placement="bottom", color=c, arrow=True,
        )
        p.attach(b)
        arrow_pops.append(p)
        arrow_row2.addWidget(b)
    arrow_row2.addStretch()
    layout.addLayout(arrow_row2)

    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #fafafa; }")
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
