"""
Tabs 组件示例 - 亮色模式
覆盖 4 variants × 6 colors × 3 sizes × 5 radius × 4 placement × full_width × is_disabled × disable_animation
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
    lbl.setStyleSheet("color: #3f3f46; margin-top: 16px;")
    return lbl


def panel(text: str, bg: str = "transparent") -> QLabel:
    lbl = QLabel(text)
    lbl.setMinimumHeight(80)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"color:#52525b; background:{bg}; border-radius:8px;")
    lbl.setFont(QFont("Segoe UI", 12))
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Tabs 示例 - 亮色模式")
    window.resize(1000, 1000)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setSpacing(8)
    layout.setContentsMargins(40, 30, 40, 30)

    title = QLabel("Tabs - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # ============ 4 种 variant ============
    layout.addWidget(section("4 种 variant"))
    for v in ("solid", "bordered", "light", "underlined"):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"{v}:"))
        t = Tabs(variant=v, color="primary")
        t.add_tab("Photos", panel(f"Photos - {v}"))
        t.add_tab("Music", panel(f"Music - {v}"))
        t.add_tab("Videos", panel(f"Videos - {v}"))
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # ============ 6 种 color × solid ============
    layout.addWidget(section("6 colors × solid"))
    grid = QGridLayout()
    for i, c in enumerate(("default", "primary", "secondary", "success", "warning", "danger")):
        t = Tabs(["A", "B", "C"], variant="solid", color=c)
        grid.addWidget(QLabel(c), i // 3, (i % 3) * 2)
        grid.addWidget(t, i // 3, (i % 3) * 2 + 1)
    layout.addLayout(grid)

    # ============ 6 colors × underlined ============
    layout.addWidget(section("6 colors × underlined"))
    grid2 = QGridLayout()
    for i, c in enumerate(("default", "primary", "secondary", "success", "warning", "danger")):
        t = Tabs(["A", "B", "C"], variant="underlined", color=c)
        grid2.addWidget(QLabel(c), i // 3, (i % 3) * 2)
        grid2.addWidget(t, i // 3, (i % 3) * 2 + 1)
    layout.addLayout(grid2)

    # ============ 3 种 size ============
    layout.addWidget(section("3 sizes (sm / md / lg)"))
    for s in ("sm", "md", "lg"):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"{s}:"))
        t = Tabs(["Photos", "Music", "Videos"], size=s, color="primary")
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # ============ 5 种 radius ============
    layout.addWidget(section("5 radius (none/sm/md/lg/full)"))
    for r in ("none", "sm", "md", "lg", "full"):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"radius={r}:"))
        t = Tabs(["A", "B", "C"], color="secondary", radius=r)
        row.addWidget(t)
        row.addStretch()
        layout.addLayout(row)

    # ============ 4 种 placement ============
    layout.addWidget(section("4 placements (top / bottom / start / end)"))
    grid3 = QGridLayout()
    for i, p in enumerate(("top", "bottom", "start", "end")):
        t = Tabs(placement=p, color="primary", variant="solid")
        t.add_tab("Photos", panel(f"Photos - {p}", "#f4f4f5"))
        t.add_tab("Music", panel(f"Music - {p}", "#f4f4f5"))
        t.add_tab("Videos", panel(f"Videos - {p}", "#f4f4f5"))
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.addWidget(QLabel(p))
        wl.addWidget(t)
        grid3.addWidget(wrap, i // 2, i % 2)
    layout.addLayout(grid3)

    # ============ full_width ============
    layout.addWidget(section("full_width"))
    t_fw = Tabs(["Login", "Sign Up", "Forgot password"],
                variant="bordered", color="primary", full_width=True)
    layout.addWidget(t_fw)

    # ============ is_disabled / 单 tab disabled ============
    layout.addWidget(section("is_disabled (整体) / 单 tab disabled"))
    row = QHBoxLayout()
    t_dis = Tabs(["A", "B", "C"], color="primary", is_disabled=True)
    row.addWidget(QLabel("is_disabled=True"))
    row.addWidget(t_dis)
    row.addStretch()
    layout.addLayout(row)

    row = QHBoxLayout()
    t_one = Tabs(color="primary")
    t_one.add_tab("Active", panel("Active"))
    t_one.add_tab("Disabled", panel("Disabled"), disabled=True)
    t_one.add_tab("Active 2", panel("Active 2"))
    row.addWidget(QLabel("中间 disabled:"))
    row.addWidget(t_one)
    row.addStretch()
    layout.addLayout(row)

    # ============ disable_animation ============
    layout.addWidget(section("disable_animation=True"))
    t_no = Tabs(["A", "B", "C"], color="success", disable_animation=True)
    layout.addWidget(t_no)

    # ============ TabItem 三档插槽 ============
    layout.addWidget(section("TabItem 档 2 — start_icon / end_icon（自动跟随主题着色）"))
    t_icon = Tabs(color="primary", variant="bordered")
    t_icon.add_tab("Next", panel("Next panel"),
                   start_icon="heroicons--chevron-right-solid")
    t_icon.add_tab("Show", panel("Show panel"),
                   end_icon="heroicons--eye-solid")
    t_icon.add_tab("Hide", panel("Hide panel"),
                   start_icon="heroicons--eye-slash-solid",
                   end_icon="heroicons--check-solid")
    layout.addWidget(t_icon)

    t_icon2 = Tabs(color="success", variant="underlined")
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

    t_custom = Tabs(color="primary", variant="bordered")
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
