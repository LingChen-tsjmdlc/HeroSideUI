"""
Input 组件示例 - 亮色模式
展示 4 变体 × 6 颜色 × 3 尺寸 × 4 label 位置 × 各种状态的完整效果
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette

from hero_side_ui import Input


THEME = "light"
BG = "#fafafa"
FG = "#18181b"
SECTION_COLOR = "#3f3f46"


def section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color: {SECTION_COLOR}; margin-top: 16px; margin-bottom: 4px;")
    return lbl


def sub_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 10))
    lbl.setStyleSheet(f"color: {SECTION_COLOR}; margin-top: 4px;")
    return lbl


def build_content() -> QWidget:
    w = QWidget()
    root = QVBoxLayout(w)
    root.setContentsMargins(24, 16, 24, 24)
    root.setSpacing(8)

    colors = ["default", "primary", "secondary", "success", "warning", "danger"]
    variants = ["flat", "faded", "bordered", "underlined"]

    # ---- 4 变体 × 6 颜色 ----
    root.addWidget(section_title("4 variants × 6 colors (size=md, inside label)"))
    for v in variants:
        root.addWidget(sub_title(f"variant = {v}"))
        grid = QGridLayout()
        grid.setSpacing(12)
        cols = 3  # 每行 3 个，避免挤压
        for i, c in enumerate(colors):
            inp = Input(
                label=c.title(),
                variant=v,
                color=c,
                size="md",
                is_clearable=True,
                theme=THEME,
            )
            grid.addWidget(inp, i // cols, i % cols)
        row = QWidget()
        row.setLayout(grid)
        root.addWidget(row)

    # ---- 3 尺寸 ----
    root.addWidget(section_title("3 sizes (variant=flat, color=primary)"))
    size_row = QHBoxLayout()
    for s in ["sm", "md", "lg"]:
        inp = Input(
            label=f"Size {s}",
            variant="flat",
            color="primary",
            size=s,
            is_clearable=True,
            theme=THEME,
        )
        size_row.addWidget(inp)
    size_wrap = QWidget()
    size_wrap.setLayout(size_row)
    root.addWidget(size_wrap)

    # ---- 4 label placements ----
    root.addWidget(section_title("4 label placements × 4 variants × 6 colors"))
    for lp in ["inside", "outside", "outside-top", "outside-left"]:
        root.addWidget(sub_title(f"label_placement = {lp}"))
        for v in variants:
            grid = QGridLayout()
            grid.setSpacing(12)
            cols = 3
            for i, c in enumerate(colors):
                inp = Input(
                    label=c.title(),
                    variant=v,
                    color=c,
                    size="md",
                    label_placement=lp,
                    is_clearable=True,
                    theme=THEME,
                )
                grid.addWidget(inp, i // cols, i % cols)
            row = QWidget()
            row.setLayout(grid)
            # 加一行小标签说明当前是哪个 variant
            mini = QLabel(f"  variant = {v}")
            mini.setStyleSheet("color: #71717a; font-size: 11px; margin-top: 4px;")
            root.addWidget(mini)
            root.addWidget(row)

    # ---- Placeholder 展示 ----
    root.addWidget(section_title("Placeholder 演示"))
    root.addWidget(sub_title("未聚焦且空值时，placeholder 显示在输入框里"))
    root.addWidget(Input(
        label="Email",
        placeholder="you@example.com",
        variant="flat",
        color="primary",
        size="md",
        is_clearable=True,
        theme=THEME,
    ))

    # ---- 状态 ----
    root.addWidget(section_title("States"))
    # 禁用
    root.addWidget(sub_title("is_disabled = True"))
    root.addWidget(Input(
        label="Disabled", variant="flat",
        is_disabled=True, theme=THEME,
    ))
    # 只读
    root.addWidget(sub_title("is_readonly = True"))
    root.addWidget(Input(
        label="Readonly", value="这是只读内容", variant="flat",
        is_readonly=True, theme=THEME,
    ))
    # 必填
    root.addWidget(sub_title("is_required = True"))
    root.addWidget(Input(
        label="Username", variant="bordered", color="primary",
        is_required=True, theme=THEME,
    ))
    # 无效 + 错误消息
    root.addWidget(sub_title("is_invalid + error_message"))
    for v in variants:
        root.addWidget(Input(
            label=f"Email ({v})", variant=v,
            is_invalid=True, error_message="请输入合法的邮箱地址", theme=THEME,
        ))

    # ---- start/end content ----
    root.addWidget(section_title("Start / End content (icons / buttons / 可点击)"))
    root.addWidget(sub_title("静态图标 (string)"))
    root.addWidget(Input(
        label="Search", variant="flat", color="default",
        start_content="heroicons--chevron-right-solid",
        is_clearable=True, theme=THEME,
    ))

    # 密码框可点击眼睛：经典 use case
    root.addWidget(sub_title("字符串图标 + 点击回调 (密码框眼睛示意)"))
    pwd_inp = Input(
        label="Password", variant="bordered", color="primary",
        end_content="heroicons--eye-solid",
        theme=THEME,
    )
    pwd_inp.line_edit.setEchoMode(pwd_inp.line_edit.EchoMode.Password)
    # 点击眼睛切换显示/隐藏
    pwd_state = {"visible": False}
    def toggle_pwd():
        pwd_state["visible"] = not pwd_state["visible"]
        em = pwd_inp.line_edit.EchoMode
        pwd_inp.line_edit.setEchoMode(em.Normal if pwd_state["visible"] else em.Password)
        pwd_inp.set_end_content(
            "heroicons--eye-slash-solid" if pwd_state["visible"] else "heroicons--eye-solid",
            on_click=toggle_pwd,
        )
    pwd_inp.set_on_end_content_click(toggle_pwd)
    root.addWidget(pwd_inp)

    # 直接塞自定义 Button
    root.addWidget(sub_title("直接塞 Button 组件作为 end_content"))
    from hero_side_ui import Button
    go_btn = Button("GO", size="sm", variant="flat", color="primary", theme=THEME)
    go_btn.clicked.connect(lambda: print("[GO] clicked"))
    root.addWidget(Input(
        label="Query", variant="flat", color="default",
        end_content=go_btn, theme=THEME,
    ))

    # ---- 事件测试 ----
    root.addWidget(section_title("Event demo (打开控制台查看输出)"))
    event_inp = Input(
        label="Type here",
        variant="flat", color="primary", is_clearable=True, theme=THEME,
    )
    event_inp.text_changed.connect(lambda t: print(f"[changed] {t!r}"))
    event_inp.returned.connect(lambda: print("[enter]"))
    event_inp.cleared.connect(lambda: print("[cleared]"))
    event_inp.editing_finished.connect(lambda: print("[editing_finished]"))
    root.addWidget(event_inp)

    return w


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(FG))
    app.setPalette(pal)

    window = QMainWindow()
    window.setWindowTitle("HeroSideUI Input — Light Mode")
    window.resize(1080, 820)
    window.setStyleSheet(f"QMainWindow {{ background: {BG}; }}")

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(build_content())
    scroll.setStyleSheet(f"QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; border: none; }}")
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
