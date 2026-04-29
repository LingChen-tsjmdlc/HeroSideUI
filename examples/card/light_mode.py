"""
Card 组件示例 - 亮色模式
展示三层结构、阴影、圆角、分割线、可按压、可悬停、Blurred 等特性
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QBrush

from hero_side_ui import Card, CardHeader, CardBody, CardFooter, Divider, Button, Input


class _GradientBackground(QWidget):
    """渐变背景容器，用于展示 Blurred Card 的磨砂玻璃效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, self.height(), self.width(), 0)
        gradient.setColorAt(0.0, QColor("#FFB457"))
        gradient.setColorAt(1.0, QColor("#FF705B"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        painter.end()


def make_card(title: str, body_text: str, footer_text: str = "", **card_kwargs):
    """快速创建一个三层 Card"""
    card = Card(**card_kwargs)

    header = CardHeader()
    title_label = QLabel(title)
    title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    title_label.setStyleSheet("color: #18181b;")
    header.layout().addWidget(title_label)
    card.add_header(header)

    card.add_divider()

    body = CardBody()
    body_label = QLabel(body_text)
    body_label.setWordWrap(True)
    body_label.setStyleSheet("color: #52525b;")
    body.layout().addWidget(body_label)
    card.add_body(body)

    if footer_text:
        card.add_divider()
        footer = CardFooter()
        footer_label = QLabel(footer_text)
        footer_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        footer.layout().addWidget(footer_label)
        card.add_footer(footer)

    return card


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f4f4f5"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#18181b"))
    app.setPalette(palette)

    window = QMainWindow()
    window.setWindowTitle("Card 示例 - 亮色模式")
    window.resize(900, 900)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("""
        QScrollArea { border: none; background: #f4f4f5; }
        QScrollBar:vertical { width: 8px; background: transparent; }
        QScrollBar::handle:vertical { background: #d4d4d8; border-radius: 4px; min-height: 40px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    """)

    main_widget = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(20)
    layout.setContentsMargins(40, 30, 40, 30)

    # 标题
    title = QLabel("Card - Light Mode")
    title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    title.setStyleSheet("color: #006FEE; margin-bottom: 16px;")
    layout.addWidget(title)

    # ---- 阴影展示 ----
    section = QLabel("Shadow Variants")
    section.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    section.setStyleSheet("color: #3f3f46;")
    layout.addWidget(section)

    row1 = QHBoxLayout()
    row1.setSpacing(16)
    for shadow in ["none", "sm", "md", "lg"]:
        card = make_card(
            f"Shadow: {shadow}",
            "Make beautiful websites regardless of your design experience.",
            f'shadow="{shadow}"',
            shadow=shadow,
        )
        card.setFixedWidth(200)
        row1.addWidget(card)
    row1.addStretch()
    layout.addLayout(row1)

    # ---- 圆角展示 ----
    section2 = QLabel("Radius Variants")
    section2.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    section2.setStyleSheet("color: #3f3f46; margin-top: 8px;")
    layout.addWidget(section2)

    row2 = QHBoxLayout()
    row2.setSpacing(16)
    for radius in ["none", "sm", "md", "lg"]:
        card = make_card(
            f"Radius: {radius}",
            "Beautiful, fast and modern React UI library.",
            f'radius="{radius}"',
            radius=radius,
        )
        card.setFixedWidth(200)
        row2.addWidget(card)
    row2.addStretch()
    layout.addLayout(row2)

    # ---- 可交互卡片 ----
    section3 = QLabel("Interactive Cards")
    section3.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    section3.setStyleSheet("color: #3f3f46; margin-top: 8px;")
    layout.addWidget(section3)

    row3 = QHBoxLayout()
    row3.setSpacing(16)

    # Hoverable
    hover_card = make_card(
        "Hoverable",
        "Hover over me to see the background change.",
        "is_hoverable=True",
        is_hoverable=True,
    )
    hover_card.setFixedWidth(200)
    row3.addWidget(hover_card)

    # Pressable
    press_card = make_card(
        "Pressable",
        "Click me! I have a ripple animation.",
        "is_pressable=True",
        is_pressable=True,
    )
    press_card.setFixedWidth(200)
    press_card.pressed.connect(lambda: print("Card pressed!"))
    row3.addWidget(press_card)

    # Disabled
    disabled_card = make_card(
        "Disabled",
        "I am disabled and cannot be interacted with.",
        "is_disabled=True",
        is_disabled=True,
    )
    disabled_card.setFixedWidth(200)
    row3.addWidget(disabled_card)

    row3.addStretch()
    layout.addLayout(row3)

    # ---- 完整登录表单 Card ----
    section4 = QLabel("Card with Input Form (Login)")
    section4.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    section4.setStyleSheet("color: #3f3f46; margin-top: 8px;")
    layout.addWidget(section4)

    btn_card = Card(shadow="md", radius="lg")
    btn_card.setFixedWidth(360)

    # Header: 标题 + 副标题
    header = CardHeader()
    header_col = QVBoxLayout()
    header_col.setContentsMargins(0, 0, 0, 0)
    header_col.setSpacing(2)
    h_title = QLabel("Welcome back")
    h_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    h_title.setStyleSheet("color: #18181b;")
    h_subtitle = QLabel("Log in to your account to continue.")
    h_subtitle.setStyleSheet("color: #71717a; font-size: 13px;")
    header_col.addWidget(h_title)
    header_col.addWidget(h_subtitle)
    header.layout().addLayout(header_col)
    btn_card.add_header(header)

    btn_card.add_divider()

    # Body: Email + Password + 忘记密码
    body = CardBody()
    body.layout().setSpacing(14)

    email_input = Input(
        label="Email",
        placeholder="you@example.com",
        variant="faded",
        color="primary",
        size="md",
        is_required=True,
        is_clearable=True,
    )

    password_input = Input(
        label="Password",
        placeholder="Enter your password",
        variant="faded",
        color="primary",
        size="md",
        is_required=True,
        end_content="heroicons--eye-slash-solid",
    )
    # 初始态: 密码隐藏
    password_input.line_edit.setEchoMode(password_input.line_edit.EchoMode.Password)

    # eye 切换: 闭眼 → 睁眼 → 明文 / 睁眼 → 闭眼 → 密文
    def toggle_password_visibility():
        le = password_input.line_edit
        if le.echoMode() == le.EchoMode.Password:
            le.setEchoMode(le.EchoMode.Normal)
            password_input.set_end_content("heroicons--eye-solid")
            password_input.set_on_end_content_click(toggle_password_visibility)
        else:
            le.setEchoMode(le.EchoMode.Password)
            password_input.set_end_content("heroicons--eye-slash-solid")
            password_input.set_on_end_content_click(toggle_password_visibility)

    password_input.set_on_end_content_click(toggle_password_visibility)

    body.layout().addWidget(email_input)
    body.layout().addWidget(password_input)

    # Remember me + Forgot password 行
    extras_row = QHBoxLayout()
    extras_row.setContentsMargins(0, 2, 0, 0)
    remember_lbl = QLabel("Remember me")
    remember_lbl.setStyleSheet("color: #52525b; font-size: 13px;")
    forgot_btn = Button("Forgot password?", color="primary", variant="light", size="sm")
    extras_row.addWidget(remember_lbl)
    extras_row.addStretch()
    extras_row.addWidget(forgot_btn)
    body.layout().addLayout(extras_row)

    btn_card.add_body(body)

    btn_card.add_divider()

    # Footer: No account? Sign up | Cancel + Sign in
    footer = CardFooter()
    no_account_lbl = QLabel("No account?")
    no_account_lbl.setStyleSheet("color: #71717a; font-size: 13px;")
    signup_btn = Button("Sign up", color="primary", variant="light", size="sm")
    footer.layout().addWidget(no_account_lbl)
    footer.layout().addWidget(signup_btn)
    footer.layout().addStretch()
    cancel_btn = Button("Cancel", color="default", variant="light", size="sm")
    login_btn = Button("Sign in", color="primary", variant="solid", size="sm")
    footer.layout().addWidget(cancel_btn)
    footer.layout().addWidget(login_btn)
    btn_card.add_footer(footer)

    # 打印演示：点击 Sign in 时拿到输入值
    def _do_login():
        print(
            f"[Login] email={email_input.text()!r} password={password_input.text()!r}"
        )

    login_btn.clicked.connect(_do_login)
    forgot_btn.clicked.connect(lambda: print("[Link] Forgot password clicked"))
    signup_btn.clicked.connect(lambda: print("[Link] Sign up clicked"))

    layout.addWidget(btn_card)

    # ---- Blurred Card (带渐变背景展示磨砂玻璃效果) ----
    section6 = QLabel("Blurred Card")
    section6.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    section6.setStyleSheet("color: #3f3f46; margin-top: 8px;")
    layout.addWidget(section6)

    note = QLabel(
        "Note: is_blurred=True with a gradient background (from-[#FFB457] to-[#FF705B])\n"
        "simulates the frosted glass effect."
    )
    note.setStyleSheet("color: #71717a; font-size: 12px;")
    note.setWordWrap(True)
    layout.addWidget(note)

    gradient_bg = _GradientBackground()
    gradient_bg.setFixedSize(420, 200)
    gradient_layout = QVBoxLayout(gradient_bg)
    gradient_layout.setContentsMargins(30, 30, 30, 30)
    gradient_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    blurred_card = Card(shadow="none", radius="lg", is_blurred=True, is_hoverable=True)
    blurred_card.setFixedWidth(340)

    blur_header = CardHeader()
    blur_title = QLabel("Daily Mix")
    blur_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    blur_title.setStyleSheet("color: #18181b;")
    blur_subtitle = QLabel("12 Tracks")
    blur_subtitle.setStyleSheet("color: #52525b; font-size: 12px;")
    blur_h_col = QVBoxLayout()
    blur_h_col.setSpacing(2)
    blur_h_col.addWidget(blur_title)
    blur_h_col.addWidget(blur_subtitle)
    blur_header.layout().addLayout(blur_h_col)
    blurred_card.add_header(blur_header)

    blur_body = CardBody()
    blur_body_label = QLabel("Frontend Radio")
    blur_body_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    blur_body_label.setStyleSheet("color: #18181b;")
    blur_body.layout().addWidget(blur_body_label)
    blurred_card.add_body(blur_body)

    gradient_layout.addWidget(blurred_card)
    layout.addWidget(gradient_bg)

    layout.addStretch()
    main_widget.setLayout(layout)
    scroll.setWidget(main_widget)
    window.setCentralWidget(scroll)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
