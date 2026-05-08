"""
Popover 组件示例 - 暗色模式
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import (
    Popover,
    PopoverContent,
    Button,
    Input,
    Checkbox,
    Spinner,
)


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #d4d4d8; margin-top: 16px;")
    return lbl


def make_simple_popover(text: str, **kwargs) -> Popover:
    p = Popover(theme="dark", **kwargs)
    c = PopoverContent()
    label = QLabel(text)
    # 不要显式设 color —— Popover 会根据 color 自动给内部 QLabel 刷反色
    c.layout().addWidget(label)
    p.set_content(c)
    return p


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0a0a0b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ecedee"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Popover 示例 - 暗色模式")
    window.resize(900, 700)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(12)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Popover - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    layout.addWidget(section("12 placements"))
    grid = QGridLayout()
    grid.setSpacing(12)
    placements = [
        "top-start",    "top",    "top-end",
        "bottom-start", "bottom", "bottom-end",
        "right-start",  "right",  "right-end",
        "left-start",   "left",   "left-end",
    ]
    poppers = []
    for i, place in enumerate(placements):
        btn = Button(place, color="primary", variant="flat", theme="dark")
        p = make_simple_popover(f"Popover at {place}", placement=place, color="default")
        p.attach(btn)
        poppers.append(p)
        grid.addWidget(btn, i // 3, i % 3)
    layout.addLayout(grid)

    layout.addWidget(section("7 colors"))
    color_row = QHBoxLayout()
    color_row.setSpacing(12)
    colors = [
        "default",
        "primary",
        "secondary",
        "success",
        "warning",
        "danger",
    ]
    color_pops = []
    for c in colors:
        b = Button(c.capitalize(), color="primary", variant="flat", theme="dark")
        p = make_simple_popover(f"Color = {c}", color=c, placement="bottom")
        p.attach(b)
        color_pops.append(p)
        color_row.addWidget(b)
    color_row.addStretch()
    layout.addLayout(color_row)

    layout.addWidget(section("插槽：表单 / Spinner"))
    slot_row = QHBoxLayout()
    slot_row.setSpacing(12)

    form_btn = Button("Settings", color="primary", variant="solid", theme="dark")
    form_pop = Popover(
        placement="bottom-start", shadow="lg", color="default", theme="dark"
    )
    form = PopoverContent()
    form.setMinimumWidth(240)
    form.layout().setSpacing(10)
    title_lbl = QLabel("Account Settings")
    form.layout().addWidget(title_lbl)
    form.layout().addWidget(
        Input(
            label="Username",
            placeholder="@you",
            size="sm",
            theme="dark",
            color="secondary",
        )
    )
    form.layout().addWidget(
        Input(
            label="Email",
            placeholder="you@example.com",
            size="sm",
            theme="dark",
            color="secondary",
        )
    )
    form.layout().addWidget(
        Checkbox("Receive emails", color="primary", size="sm", theme="dark")
    )
    save_btn = Button("Save", color="primary", variant="solid", size="sm", theme="dark")
    form.layout().addWidget(save_btn)
    form_pop.set_content(form)
    form_pop.attach(form_btn)
    slot_row.addWidget(form_btn)

    spin_btn = Button("Loading...", color="success", variant="flat", theme="dark")
    spin_pop = Popover(placement="bottom", color="default", shadow="md", theme="dark")
    sc = PopoverContent()
    sc.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
    sc.layout().addWidget(Spinner(label="Working...", theme="dark"))
    spin_pop.set_content(sc)
    spin_pop.attach(spin_btn)
    slot_row.addWidget(spin_btn)

    slot_row.addStretch()
    layout.addLayout(slot_row)

    # ---- arrow=True ----
    layout.addWidget(section("arrow=True（显示箭头）"))
    arrow_row = QHBoxLayout()
    arrow_row.setSpacing(12)
    arrow_pops = []
    for place in ["top", "bottom", "left", "right"]:
        b = Button(f"{place} + arrow", color="primary", variant="flat", theme="dark")
        p = make_simple_popover(
            f"arrow @ {place}",
            placement=place, color="default", arrow=True,
        )
        p.attach(b)
        arrow_pops.append(p)
        arrow_row.addWidget(b)
    arrow_row.addStretch()
    layout.addLayout(arrow_row)

    arrow_row2 = QHBoxLayout()
    arrow_row2.setSpacing(12)
    for c in ["primary", "success", "warning", "danger"]:
        b = Button(f"arrow {c}", color=c, variant="flat", theme="dark")
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
    scroll.setStyleSheet("QScrollArea { border: none; background: #0a0a0b; }")
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
