"""
Tabs 组件示例 - 登录 / 注册
展示 panel 的"插槽"特性：内容面板可以塞任意 QWidget。
这里用 Card + Input + Checkbox + Button + Divider 拼出真实可用的登录注册界面。
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
from PySide6.QtWidgets import QLineEdit

from hero_side_ui import (
    Tabs,
    Input,
    Button,
    Checkbox,
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Divider,
)

# ----------------- 构造内容面板 ------------------


def build_login_panel(theme: str = "light") -> QWidget:
    """登录面板 —— 完全是普通 QWidget，作为 Tabs 的 panel 插槽。"""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 12, 0, 0)
    layout.setSpacing(14)

    email = Input(
        label="邮箱",
        color="primary",
        is_clearable=True,
        theme=theme,
    )
    layout.addWidget(email)

    pwd = Input(
        label="密码",
        color="primary",
        theme=theme,
    )
    pwd.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd)

    # 一行：Remember + Forgot
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    remember = Checkbox("记住我", color="primary", size="sm", theme=theme)
    row.addWidget(remember)
    row.addStretch()
    forgot = Button(
        "忘记密码？", variant="light", color="primary", size="sm", theme=theme
    )
    row.addWidget(forgot)
    layout.addLayout(row)

    # 主按钮
    submit = Button(
        "登录", variant="solid", color="primary", full_width=True, theme=theme
    )
    layout.addWidget(submit)

    # 跳到注册
    bottom = QHBoxLayout()
    bottom.setContentsMargins(0, 0, 0, 0)
    bottom.addStretch()
    text_color = "#71717a" if theme == "light" else "#a1a1aa"
    hint = QLabel("还没有账号？")
    hint.setStyleSheet(f"color:{text_color}; font-size:12px;")
    bottom.addWidget(hint)
    sign_up_link = Button(
        "立即注册", variant="light", color="primary", size="sm", theme=theme
    )
    bottom.addWidget(sign_up_link)
    bottom.addStretch()
    layout.addLayout(bottom)

    return panel, sign_up_link


def build_signup_panel(theme: str = "light") -> QWidget:
    """注册面板。"""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 12, 0, 0)
    layout.setSpacing(14)

    name = Input(
        label="昵称",
        color="primary",
        theme=theme,
    )
    layout.addWidget(name)

    email = Input(
        label="邮箱",
        color="primary",
        is_clearable=True,
        theme=theme,
    )
    layout.addWidget(email)

    pwd = Input(
        label="密码",
        color="primary",
        theme=theme,
    )
    pwd.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd)

    pwd2 = Input(
        label="确认密码",
        color="primary",
        theme=theme,
    )
    pwd2.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd2)

    agree = Checkbox("我已阅读并同意服务条款", color="primary", size="sm", theme=theme)
    layout.addWidget(agree)

    submit = Button(
        "注册", variant="solid", color="primary", full_width=True, theme=theme
    )
    layout.addWidget(submit)

    # 跳到登录
    bottom = QHBoxLayout()
    bottom.setContentsMargins(0, 0, 0, 0)
    bottom.addStretch()
    text_color = "#71717a" if theme == "light" else "#a1a1aa"
    hint = QLabel("已有账号？")
    hint.setStyleSheet(f"color:{text_color}; font-size:12px;")
    bottom.addWidget(hint)
    login_link = Button(
        "立即登录", variant="light", color="primary", size="sm", theme=theme
    )
    bottom.addWidget(login_link)
    bottom.addStretch()
    layout.addLayout(bottom)

    return panel, login_link


# ----------------- 主程序 ------------------


def make_demo(theme: str) -> Card:
    """构造一张登录/注册 demo —— 用项目自己的 Card 组件包裹。"""
    # 构造两个面板
    login_panel, to_signup_btn = build_login_panel(theme)
    signup_panel, to_login_btn = build_signup_panel(theme)

    # Tabs：bordered + primary + full_width
    tabs = Tabs(
        variant="bordered",
        color="primary",
        size="md",
        full_width=True,
        theme=theme,
    )
    tabs.add_tab("登录", login_panel, key="login")
    tabs.add_tab("注册", signup_panel, key="signup")

    # 联动切换
    to_signup_btn.clicked.connect(lambda: tabs.set_selected("signup"))
    to_login_btn.clicked.connect(lambda: tabs.set_selected("login"))

    tabs.selection_changed.connect(
        lambda i, k: print(f"[{theme}] switched to {k} (#{i})")
    )

    # ---- 用自己的 Card + CardHeader + CardBody 组装 ----
    card = Card(shadow="md", radius="lg", theme=theme, full_width=False)
    card.setFixedWidth(420)

    header = CardHeader()
    title = QLabel("欢迎")
    title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet(f"color: {'#18181b' if theme == 'light' else '#fafafa'};")
    header.layout().addWidget(title)
    card.add_header(header)

    body = CardBody()
    body.layout().setContentsMargins(20, 4, 20, 20)
    body.layout().addWidget(tabs)
    card.add_body(body)

    return card


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QMainWindow()
    window.setWindowTitle("Tabs 示例 - 登录 / 注册")
    window.resize(960, 720)

    central = QWidget()
    root = QHBoxLayout(central)
    root.setContentsMargins(40, 30, 40, 30)
    root.setSpacing(40)
    root.setAlignment(Qt.AlignCenter)

    # 亮色 demo
    light_wrap = QWidget()
    lw = QVBoxLayout(light_wrap)
    lw.setContentsMargins(0, 0, 0, 0)
    lw.setSpacing(8)
    lbl_l = QLabel("Light Mode")
    lbl_l.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl_l.setStyleSheet("color:#3f3f46;")
    lbl_l.setAlignment(Qt.AlignCenter)
    lw.addWidget(lbl_l)
    lw.addWidget(make_demo("light"))

    # 用 palette 设背景色，避免 stylesheet 向下继承污染子组件
    from PySide6.QtGui import QPalette as _Pal
    lp = _Pal()
    lp.setColor(_Pal.ColorRole.Window, QColor("#fafafa"))
    light_wrap.setPalette(lp)
    light_wrap.setAutoFillBackground(True)

    # 暗色 demo
    dark_wrap = QWidget()
    dw = QVBoxLayout(dark_wrap)
    dw.setContentsMargins(0, 0, 0, 0)
    dw.setSpacing(8)
    lbl_d = QLabel("Dark Mode")
    lbl_d.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    lbl_d.setStyleSheet("color:#d4d4d8;")
    lbl_d.setAlignment(Qt.AlignCenter)
    dw.addWidget(lbl_d)
    dw.addWidget(make_demo("dark"))

    dp = _Pal()
    dp.setColor(_Pal.ColorRole.Window, QColor("#18181b"))
    dark_wrap.setPalette(dp)
    dark_wrap.setAutoFillBackground(True)

    # 给两个 wrap 各塞点 padding
    light_wrap.layout().setContentsMargins(20, 20, 20, 20)
    dark_wrap.layout().setContentsMargins(20, 20, 20, 20)

    root.addWidget(light_wrap)
    root.addWidget(dark_wrap)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#e4e4e7"))
    app.setPalette(palette)

    window.setCentralWidget(central)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
