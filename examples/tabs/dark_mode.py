"""
Tabs 组件示例 - 暗色模式
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Tabs


def section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #d4d4d8; margin-top: 16px;")
    return lbl


def panel(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setMinimumHeight(80)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("color:#a1a1aa; background:#27272a; border-radius:8px;")
    lbl.setFont(QFont("Segoe UI", 12))
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#27272a"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#fafafa"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Tabs 示例 - 暗色模式")
    window.resize(1000, 1000)
    window.setStyleSheet("background:#18181b; color:#fafafa;")

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("background:#18181b;")
    root = QWidget()
    root.setStyleSheet("background:#18181b; color:#fafafa;")
    layout = QVBoxLayout(root)
    layout.setSpacing(8)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Tabs - Dark Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #338ef7; margin-bottom: 16px;")
    layout.addWidget(title)

    THEME = "dark"

    # variants
    layout.addWidget(section("4 种 variant"))
    for v in ("solid", "bordered", "light", "underlined"):
        row = QHBoxLayout()
        lbl = QLabel(f"{v}:"); lbl.setStyleSheet("color:#a1a1aa;")
        row.addWidget(lbl)
        t = Tabs(variant=v, color="primary", theme=THEME)
        t.add_tab("Photos", panel(f"Photos - {v}"))
        t.add_tab("Music", panel(f"Music - {v}"))
        t.add_tab("Videos", panel(f"Videos - {v}"))
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # colors × solid
    layout.addWidget(section("6 colors × solid"))
    grid = QGridLayout()
    for i, c in enumerate(("default", "primary", "secondary", "success", "warning", "danger")):
        t = Tabs(["A", "B", "C"], variant="solid", color=c, theme=THEME)
        l = QLabel(c); l.setStyleSheet("color:#a1a1aa;")
        grid.addWidget(l, i // 3, (i % 3) * 2)
        grid.addWidget(t, i // 3, (i % 3) * 2 + 1)
    layout.addLayout(grid)

    # colors × underlined
    layout.addWidget(section("6 colors × underlined"))
    grid2 = QGridLayout()
    for i, c in enumerate(("default", "primary", "secondary", "success", "warning", "danger")):
        t = Tabs(["A", "B", "C"], variant="underlined", color=c, theme=THEME)
        l = QLabel(c); l.setStyleSheet("color:#a1a1aa;")
        grid2.addWidget(l, i // 3, (i % 3) * 2)
        grid2.addWidget(t, i // 3, (i % 3) * 2 + 1)
    layout.addLayout(grid2)

    # sizes
    layout.addWidget(section("3 sizes (sm / md / lg)"))
    for s in ("sm", "md", "lg"):
        row = QHBoxLayout()
        l = QLabel(f"{s}:"); l.setStyleSheet("color:#a1a1aa;")
        row.addWidget(l)
        t = Tabs(["Photos", "Music", "Videos"], size=s, color="primary", theme=THEME)
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # radius
    layout.addWidget(section("5 radius (none/sm/md/lg/full)"))
    for r in ("none", "sm", "md", "lg", "full"):
        row = QHBoxLayout()
        l = QLabel(f"radius={r}:"); l.setStyleSheet("color:#a1a1aa;")
        row.addWidget(l)
        t = Tabs(["A", "B", "C"], color="secondary", radius=r, theme=THEME)
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # placement
    layout.addWidget(section("4 placements"))
    grid3 = QGridLayout()
    for i, p in enumerate(("top", "bottom", "start", "end")):
        t = Tabs(placement=p, color="primary", variant="solid", theme=THEME)
        t.add_tab("Photos", panel(f"Photos - {p}"))
        t.add_tab("Music", panel(f"Music - {p}"))
        t.add_tab("Videos", panel(f"Videos - {p}"))
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        l = QLabel(p); l.setStyleSheet("color:#a1a1aa;")
        wl.addWidget(l)
        wl.addWidget(t)
        grid3.addWidget(wrap, i // 2, i % 2)
    layout.addLayout(grid3)

    # full_width
    layout.addWidget(section("full_width"))
    t_fw = Tabs(["Login", "Sign Up", "Forgot password"],
                variant="bordered", color="primary", full_width=True, theme=THEME)
    layout.addWidget(t_fw)

    # is_disabled / 单 tab disabled
    layout.addWidget(section("is_disabled / 单 tab disabled"))
    row = QHBoxLayout()
    t_dis = Tabs(["A", "B", "C"], color="primary", is_disabled=True, theme=THEME)
    row.addWidget(QLabel("is_disabled=True"))
    row.addWidget(t_dis); row.addStretch(); layout.addLayout(row)

    row = QHBoxLayout()
    t_one = Tabs(color="primary", theme=THEME)
    t_one.add_tab("Active", panel("Active"))
    t_one.add_tab("Disabled", panel("Disabled"), disabled=True)
    t_one.add_tab("Active 2", panel("Active 2"))
    row.addWidget(QLabel("中间 disabled:"))
    row.addWidget(t_one); row.addStretch(); layout.addLayout(row)

    # disable_animation
    layout.addWidget(section("disable_animation=True"))
    t_no = Tabs(["A", "B", "C"], color="success", disable_animation=True, theme=THEME)
    layout.addWidget(t_no)

    # TabItem 三档插槽
    layout.addWidget(section("TabItem 档 2 — start_icon / end_icon（自动跟随主题着色）"))
    t_icon = Tabs(color="primary", variant="bordered", theme=THEME)
    t_icon.add_tab("Next", panel("Next panel"),
                   start_icon="heroicons--chevron-right-solid")
    t_icon.add_tab("Show", panel("Show panel"),
                   end_icon="heroicons--eye-solid")
    t_icon.add_tab("Hide", panel("Hide panel"),
                   start_icon="heroicons--eye-slash-solid",
                   end_icon="heroicons--check-solid")
    layout.addWidget(t_icon)

    t_icon2 = Tabs(color="success", variant="underlined", theme=THEME)
    t_icon2.add_tab("Done", panel("Done"), start_icon="heroicons--check-solid")
    t_icon2.add_tab("Next", panel("Next"), end_icon="heroicons--chevron-right-solid")
    t_icon2.add_tab("Hide", panel("Hide"), start_icon="heroicons--eye-slash-solid")
    layout.addWidget(t_icon2)

    layout.addWidget(section("TabItem 档 3 — custom widget（完全自定义 tab 标签）"))

    def make_dot_widget(emoji: str, label: str, dot_color: str = "#f31260") -> QWidget:
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

    t_custom = Tabs(color="primary", variant="bordered", theme=THEME)
    t_custom.add_tab("Inbox", panel("Inbox"))
    t_custom.add_tab(custom=make_dot_widget("📬", "Notifications"),
                     content=panel("Notifications"), key="noti")
    t_custom.add_tab(custom=make_dot_widget("💬", "Messages", "#f5a524"),
                     content=panel("Messages"), key="msg")
    t_custom.add_tab("Trash", panel("Trash"))
    layout.addWidget(t_custom)

    layout.addStretch()
    scroll.setWidget(root)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
