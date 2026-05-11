"""
Tabs 组件示例 - 登录 / 注册

展示 panel 的"插槽"特性：内容面板可以塞任意 QWidget。
这里用 Card + Input + Checkbox + Button + Divider 拼出真实可用的登录注册界面。

主题完全交给 ThemeProvider —— 单视图，亮暗色由系统/ThemeSwitcher 自动切换。
零 hex 色、零主题判断、零手动 palette 操作（铁律 1/5）。
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
)

from hero_side_ui import (
    Tabs,
    Input,
    Button,
    Checkbox,
    Card,
    CardHeader,
    CardBody,
    Title,
    Caption,
    ThemeSwitcher,
)


# ----------------- 内容面板（plain QWidget） ------------------


def build_login_panel():
    """登录面板。返回 (panel, sign_up_link_button)。"""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 12, 0, 0)
    layout.setSpacing(14)

    email = Input(label="邮箱", color="primary", is_clearable=True)
    layout.addWidget(email)

    pwd = Input(label="密码", color="primary")
    pwd.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd)

    # 一行：记住我 + 忘记密码
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(Checkbox("记住我", color="primary", size="sm"))
    row.addStretch()
    row.addWidget(Button("忘记密码？", variant="light", color="primary", size="sm"))
    layout.addLayout(row)

    # 主按钮
    layout.addWidget(Button("登录", variant="solid", color="primary", full_width=True))

    # 跳到注册
    bottom = QHBoxLayout()
    bottom.setContentsMargins(0, 0, 0, 0)
    bottom.addStretch()
    bottom.addWidget(Caption("还没有账号？"))
    sign_up_link = Button("立即注册", variant="light", color="primary", size="sm")
    bottom.addWidget(sign_up_link)
    bottom.addStretch()
    layout.addLayout(bottom)

    return panel, sign_up_link


def build_signup_panel():
    """注册面板。返回 (panel, login_link_button)。"""
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 12, 0, 0)
    layout.setSpacing(14)

    layout.addWidget(Input(label="昵称", color="primary"))
    layout.addWidget(Input(label="邮箱", color="primary", is_clearable=True))

    pwd = Input(label="密码", color="primary")
    pwd.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd)

    pwd2 = Input(label="确认密码", color="primary")
    pwd2.line_edit.setEchoMode(QLineEdit.Password)
    layout.addWidget(pwd2)

    layout.addWidget(Checkbox("我已阅读并同意服务条款", color="primary", size="sm"))
    layout.addWidget(Button("注册", variant="solid", color="primary", full_width=True))

    # 跳到登录
    bottom = QHBoxLayout()
    bottom.setContentsMargins(0, 0, 0, 0)
    bottom.addStretch()
    bottom.addWidget(Caption("已有账号？"))
    login_link = Button("立即登录", variant="light", color="primary", size="sm")
    bottom.addWidget(login_link)
    bottom.addStretch()
    layout.addLayout(bottom)

    return panel, login_link


# ----------------- 主程序 ------------------


def make_login_card() -> Card:
    """构造一张完整的登录/注册 Card —— 主题自动跟。"""
    login_panel, to_signup_btn = build_login_panel()
    signup_panel, to_login_btn = build_signup_panel()

    tabs = Tabs(variant="bordered", color="primary", size="md", full_width=True)
    tabs.add_tab("登录", login_panel, key="login")
    tabs.add_tab("注册", signup_panel, key="signup")

    # 联动切换
    to_signup_btn.clicked.connect(lambda: tabs.set_selected("signup"))
    to_login_btn.clicked.connect(lambda: tabs.set_selected("login"))
    tabs.selection_changed.connect(
        lambda i, k: print(f"switched to {k} (#{i})")
    )

    card = Card(shadow="md", radius="lg", full_width=False)
    card.setFixedWidth(420)

    header = CardHeader()
    title = Title("欢迎", level=1)
    title.setAlignment(Qt.AlignCenter)
    header.layout().addWidget(title)
    card.add_header(header)

    body = CardBody()
    body.layout().setContentsMargins(20, 4, 20, 20)
    body.layout().addWidget(tabs)
    card.add_body(body)

    return card


def main():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Tabs 示例 - 登录 / 注册")
    window.resize(640, 720)

    central = QWidget()
    root = QVBoxLayout(central)
    root.setContentsMargins(40, 24, 40, 30)
    root.setSpacing(20)

    # 顶部右上角放一个 ThemeSwitcher 让用户切主题
    top = QHBoxLayout()
    top.addStretch()
    top.addWidget(ThemeSwitcher())
    root.addLayout(top)

    # 居中放置 Card
    center_row = QHBoxLayout()
    center_row.addStretch()
    center_row.addWidget(make_login_card())
    center_row.addStretch()
    root.addLayout(center_row)
    root.addStretch()

    window.setCentralWidget(central)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
