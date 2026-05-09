"""
Tooltip 组件示例 - 暗色模式
展示 12 种 placement、各种 color、offset、delay 配置。
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Tooltip, Button


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #a1a1aa; margin-top: 16px;")
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#fafafa"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Tooltip 示例 - 暗色模式")
    window.resize(900, 800)

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(12)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Tooltip - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # ---- 12 种 placement ----
    layout.addWidget(section("12 placements"))
    grid = QGridLayout()
    grid.setSpacing(12)
    placements = [
        "top-start",    "top",    "top-end",
        "bottom-start", "bottom", "bottom-end",
        "right-start",  "right",  "right-end",
        "left-start",   "left",   "left-end",
    ]
    tooltips = []
    for i, place in enumerate(placements):
        btn = Button(place, color="primary", variant="flat", theme="dark")
        tooltip = Tooltip(
            content=f"Tooltip at {place}",
            placement=place,
            show_arrow=True,
            theme="dark",
        )
        tooltip.attach(btn)
        tooltips.append(tooltip)
        grid.addWidget(btn, i // 3, i % 3)
    layout.addLayout(grid)

    # ---- 6 种颜色 ----
    layout.addWidget(section("6 colors"))
    color_row = QHBoxLayout()
    color_row.setSpacing(12)
    colors = ["default", "primary", "secondary", "success", "warning", "danger"]
    for c in colors:
        btn = Button(c, color=c, variant="flat", theme="dark")
        tooltip = Tooltip(content=f"{c} tooltip", color=c, theme="dark")
        tooltip.attach(btn)
        tooltips.append(tooltip)
        color_row.addWidget(btn)
    layout.addLayout(color_row)

    # ---- offset 效果 ----
    layout.addWidget(section("offset (距离控制)"))
    offset_row = QHBoxLayout()
    offset_row.setSpacing(12)
    for offset_val in [0, 3, 7, 14, 24]:
        btn = Button(f"offset={offset_val}", color="primary", variant="flat", theme="dark")
        tooltip = Tooltip(
            content=f"Offset: {offset_val}px",
            offset=offset_val,
            color="primary",
            show_arrow=True,
            theme="dark",
        )
        tooltip.attach(btn)
        tooltips.append(tooltip)
        offset_row.addWidget(btn)
    layout.addLayout(offset_row)

    # ---- delay 效果 ----
    layout.addWidget(section("open_delay / close_delay"))
    delay_row = QHBoxLayout()
    delay_row.setSpacing(12)

    btn1 = Button("默认 (0/150ms)", color="success", variant="flat", theme="dark")
    t1 = Tooltip(content="open_delay=0, close_delay=150", color="success", theme="dark")
    t1.attach(btn1)
    tooltips.append(t1)
    delay_row.addWidget(btn1)

    btn2 = Button("慢开 (500/150ms)", color="warning", variant="flat", theme="dark")
    t2 = Tooltip(content="open_delay=500, close_delay=150", color="warning", open_delay=500, theme="dark")
    t2.attach(btn2)
    tooltips.append(t2)
    delay_row.addWidget(btn2)

    btn3 = Button("快关 (0/0ms)", color="danger", variant="flat", theme="dark")
    t3 = Tooltip(content="open_delay=0, close_delay=0", color="danger", close_delay=0, theme="dark")
    t3.attach(btn3)
    tooltips.append(t3)
    delay_row.addWidget(btn3)

    btn4 = Button("慢速 (300/500ms)", color="secondary", variant="flat", theme="dark")
    t4 = Tooltip(content="open_delay=300, close_delay=500", color="secondary", open_delay=300, close_delay=500, theme="dark")
    t4.attach(btn4)
    tooltips.append(t4)
    delay_row.addWidget(btn4)

    layout.addLayout(delay_row)

    # ---- 无箭头 vs 有箭头 ----
    layout.addWidget(section("show_arrow"))
    arrow_row = QHBoxLayout()
    arrow_row.setSpacing(12)

    btn_no_arrow = Button("无箭头", color="primary", variant="flat", theme="dark")
    t_no = Tooltip(content="没有箭头", color="primary", show_arrow=False, theme="dark")
    t_no.attach(btn_no_arrow)
    tooltips.append(t_no)
    arrow_row.addWidget(btn_no_arrow)

    btn_arrow = Button("有箭头", color="primary", variant="flat", theme="dark")
    t_yes = Tooltip(content="带箭头指向 trigger", color="primary", show_arrow=True, theme="dark")
    t_yes.attach(btn_arrow)
    tooltips.append(t_yes)
    arrow_row.addWidget(btn_arrow)

    layout.addLayout(arrow_row)

    # ---- 尺寸 ----
    layout.addWidget(section("size (sm / md / lg)"))
    size_row = QHBoxLayout()
    size_row.setSpacing(12)
    for sz in ["sm", "md", "lg"]:
        btn = Button(f"size={sz}", color="default", variant="flat", theme="dark")
        tooltip = Tooltip(content=f"Size: {sz}", size=sz, theme="dark")
        tooltip.attach(btn)
        tooltips.append(tooltip)
        size_row.addWidget(btn)
    layout.addLayout(size_row)

    # ---- 圆角 ----
    layout.addWidget(section("radius (none / sm / md / lg / full)"))
    radius_row = QHBoxLayout()
    radius_row.setSpacing(12)
    for r in ["none", "sm", "md", "lg", "full"]:
        btn = Button(f"radius={r}", color="primary", variant="flat", radius=r, theme="dark")
        tooltip = Tooltip(content=f"Radius: {r}", radius=r, color="primary", theme="dark")
        tooltip.attach(btn)
        tooltips.append(tooltip)
        radius_row.addWidget(btn)
    layout.addLayout(radius_row)

    # ---- 自定义 widget 内容 ----
    layout.addWidget(section("自定义 widget 内容 (set_content)"))
    custom_row = QHBoxLayout()
    custom_row.setSpacing(12)

    # 多行富文本
    btn_rich = Button("富文本", color="secondary", variant="flat", theme="dark")
    rich_widget = QWidget()
    rich_layout = QVBoxLayout(rich_widget)
    rich_layout.setContentsMargins(10, 8, 10, 8)
    rich_layout.setSpacing(4)
    rich_title = QLabel("提示标题")
    rich_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
    rich_desc = QLabel("这是一段多行描述文字，\n演示自定义 widget 的能力。")
    rich_desc.setStyleSheet("color: #e4e4e7; font-size: 12px;")
    rich_layout.addWidget(rich_title)
    rich_layout.addWidget(rich_desc)
    tooltip_rich = Tooltip(color="secondary", placement="bottom", show_arrow=True, theme="dark")
    tooltip_rich.set_content(rich_widget)
    tooltip_rich.attach(btn_rich)
    tooltips.append(tooltip_rich)
    custom_row.addWidget(btn_rich)

    # 带图标 + 文字组合
    btn_icon = Button("图标+文字", color="success", variant="flat", theme="dark")
    icon_widget = QWidget()
    icon_layout = QHBoxLayout(icon_widget)
    icon_layout.setContentsMargins(8, 6, 8, 6)
    icon_layout.setSpacing(6)
    icon_label = QLabel("✓")
    icon_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
    text_label = QLabel("操作成功！")
    text_label.setStyleSheet("color: #ffffff; font-size: 13px;")
    icon_layout.addWidget(icon_label)
    icon_layout.addWidget(text_label)
    tooltip_icon = Tooltip(color="success", placement="bottom", show_arrow=True, theme="dark")
    tooltip_icon.set_content(icon_widget)
    tooltip_icon.attach(btn_icon)
    tooltips.append(tooltip_icon)
    custom_row.addWidget(btn_icon)

    # 使用 set_content 动态替换 — 点击按钮计数 +1
    btn_dynamic = Button("点击 +1 (count=0)", color="warning", variant="flat", theme="dark")
    tooltip_dyn = Tooltip(content="当前计数: 0", color="warning", placement="bottom", show_arrow=True, theme="dark")
    tooltip_dyn.attach(btn_dynamic)

    counter = {"value": 0}

    def on_click_increment():
        counter["value"] += 1
        n = counter["value"]
        btn_dynamic.setText(f"点击 +1 (count={n})")
        tooltip_dyn.set_content(f"当前计数: {n}")

    btn_dynamic.clicked.connect(on_click_increment)
    tooltips.append(tooltip_dyn)
    custom_row.addWidget(btn_dynamic)

    layout.addLayout(custom_row)

    layout.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(root)
    scroll.setStyleSheet("QScrollArea { border: none; background: #18181b; }")
    window.setCentralWidget(scroll)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
