"""
Card 组件示例 — 三层结构、阴影、圆角、可按压、可悬停、Blurred、登录表单、TodoList

文字层全部使用语义化组件 Title / Subtitle / Caption / Body，主题自动跟随。
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QBrush
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget

from hero_side_ui import (
    Card, CardHeader, CardBody, CardFooter, Divider,
    Button, Input, Checkbox,
    Title, Subtitle, Caption, Body,
)
from _base import DemoBase


class _GradientBackground(QWidget):
    """用于展示 Blurred Card 的渐变背景（这里的颜色是装饰意图，不是主题色）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, self.height(), self.width(), 0)
        g.setColorAt(0.0, QColor("#FFB457"))
        g.setColorAt(1.0, QColor("#FF705B"))
        p.setBrush(QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.end()


def make_card(title_text: str, body_text: str, footer_text: str = "", **card_kwargs) -> Card:
    """快速创建一个三层 Card"""
    card = Card(**card_kwargs)

    header = CardHeader()
    header.layout().addWidget(Title(title_text, level=3))
    card.add_header(header)
    card.add_divider()

    body = CardBody()
    body_label = Body(body_text)
    body_label.setWordWrap(True)
    body.layout().addWidget(body_label)
    card.add_body(body)

    if footer_text:
        card.add_divider()
        footer = CardFooter()
        footer.layout().addWidget(Caption(footer_text))
        card.add_footer(footer)

    return card


def build_login_card() -> Card:
    card = Card(shadow="md", radius="lg")
    card.setFixedWidth(360)

    header = CardHeader()
    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)
    col.addWidget(Title("Welcome back", level=2))
    col.addWidget(Subtitle("Log in to your account to continue."))
    header.layout().addLayout(col)
    card.add_header(header)
    card.add_divider()

    body = CardBody()
    body.layout().setSpacing(14)

    email_input = Input(label="Email", placeholder="you@example.com",
                       variant="faded", color="primary", is_required=True, is_clearable=True)
    password_input = Input(label="Password", placeholder="Enter your password",
                          variant="faded", color="primary", is_required=True,
                          end_content="heroicons--eye-slash-solid")
    password_input.line_edit.setEchoMode(password_input.line_edit.EchoMode.Password)

    def toggle_pw():
        le = password_input.line_edit
        if le.echoMode() == le.EchoMode.Password:
            le.setEchoMode(le.EchoMode.Normal)
            password_input.set_end_content("heroicons--eye-solid")
        else:
            le.setEchoMode(le.EchoMode.Password)
            password_input.set_end_content("heroicons--eye-slash-solid")
        password_input.set_on_end_content_click(toggle_pw)
    password_input.set_on_end_content_click(toggle_pw)

    body.layout().addWidget(email_input)
    body.layout().addWidget(password_input)

    extras = QHBoxLayout()
    extras.setContentsMargins(0, 2, 0, 0)
    extras.addWidget(Checkbox("Remember me", color="primary", size="sm"))
    extras.addStretch()
    extras.addWidget(Button("Forgot password?", color="primary", variant="light", size="sm"))
    body.layout().addLayout(extras)
    card.add_body(body)
    card.add_divider()

    footer = CardFooter()
    footer.layout().addWidget(Subtitle("No account?"))
    footer.layout().addWidget(Button("Sign up", color="primary", variant="light", size="sm"))
    footer.layout().addStretch()
    footer.layout().addWidget(Button("Cancel", color="default", variant="light", size="sm"))
    footer.layout().addWidget(Button("Sign in", color="primary", variant="solid", size="sm"))
    card.add_footer(footer)

    return card


def build_todo_card() -> Card:
    card = Card(shadow="sm", radius="lg")
    card.setFixedWidth(360)

    header = CardHeader()
    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)
    col.addWidget(Title("Today's Tasks", level=3))
    col.addWidget(Caption("Check items off as you complete them"))
    header.layout().addLayout(col)
    card.add_header(header)
    card.add_divider()

    body = CardBody()
    body.layout().setSpacing(8)
    items = [
        ("Buy groceries", True, "success"),
        ("Finish HeroSideUI checkbox", False, "primary"),
        ("Read a book for 30 minutes", False, "secondary"),
        ("Go to the gym", False, "warning"),
        ("Reply to emails", True, "danger"),
    ]
    for text, sel, color in items:
        body.layout().addWidget(Checkbox(text, is_selected=sel, line_through=True, color=color))
    card.add_body(body)
    card.add_divider()

    footer = CardFooter()
    footer.layout().addWidget(Caption("Tip: click any item to toggle."))
    footer.layout().addStretch()
    footer.layout().addWidget(Button("Clear done", color="danger", variant="light", size="sm"))
    card.add_footer(footer)
    return card


def build_prefs_card() -> Card:
    card = Card(shadow="sm", radius="lg")
    card.setFixedWidth(360)

    header = CardHeader()
    header.layout().addWidget(Title("Notification preferences", level=3))
    card.add_header(header)
    card.add_divider()

    body = CardBody()
    body.layout().setSpacing(8)
    body.layout().addWidget(Checkbox("Select all (indeterminate)", is_indeterminate=True, color="primary"))
    body.layout().addWidget(Divider())
    body.layout().addWidget(Checkbox("Email", is_selected=True, color="primary", size="sm"))
    body.layout().addWidget(Checkbox("SMS", color="primary", size="sm"))
    body.layout().addWidget(Checkbox("Push (mobile)", is_selected=True, color="primary", size="sm"))
    body.layout().addWidget(Checkbox("Slack", color="primary", size="sm"))
    card.add_body(body)
    return card


def build_blurred_card_in_gradient() -> QWidget:
    bg = _GradientBackground()
    bg.setFixedSize(420, 200)
    bg_layout = QVBoxLayout(bg)
    bg_layout.setContentsMargins(30, 30, 30, 30)
    bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    card = Card(shadow="none", radius="lg", is_blurred=True, is_hoverable=True)
    card.setFixedWidth(340)

    header = CardHeader()
    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(Title("Daily Mix", level=3))
    col.addWidget(Caption("12 Tracks"))
    header.layout().addLayout(col)
    card.add_header(header)

    body = CardBody()
    body.layout().addWidget(Title("Frontend Radio", level=3))
    card.add_body(body)

    bg_layout.addWidget(card)
    return bg


class CardDemo(DemoBase):
    component_name = "Card"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # Shadow
        cards = []
        for shadow in ["none", "sm", "md", "lg"]:
            c = make_card(f"Shadow: {shadow}",
                          "Make beautiful websites regardless of your design experience.",
                          f'shadow="{shadow}"', shadow=shadow)
            c.setFixedWidth(200)
            cards.append(c)
        self.add_section(layout, "Shadow Variants", cards, labels_bag, spacing=16)

        # Radius
        cards = []
        for radius in ["none", "sm", "md", "lg"]:
            c = make_card(f"Radius: {radius}",
                          "Beautiful, fast and modern UI library.",
                          f'radius="{radius}"', radius=radius)
            c.setFixedWidth(200)
            cards.append(c)
        self.add_section(layout, "Radius Variants", cards, labels_bag, spacing=16)

        # Interactive
        hover = make_card("Hoverable", "Hover over me to see the background change.",
                         "is_hoverable=True", is_hoverable=True)
        hover.setFixedWidth(200)
        press = make_card("Pressable", "Click me! I have a ripple animation.",
                         "is_pressable=True", is_pressable=True)
        press.setFixedWidth(200)
        press.pressed.connect(lambda: print("Card pressed!"))
        disabled = make_card("Disabled", "I am disabled and cannot be interacted with.",
                            "is_disabled=True", is_disabled=True)
        disabled.setFixedWidth(200)
        self.add_section(layout, "Interactive Cards", [hover, press, disabled],
                         labels_bag, spacing=16)

        self.add_full_width(layout, "Card with Input Form (Login)",
                           build_login_card(), labels_bag)
        self.add_full_width(layout, "Card with Checkbox List (Todo)",
                           build_todo_card(), labels_bag)
        self.add_full_width(layout, "Card with indeterminate + CheckboxGroup-like layout",
                           build_prefs_card(), labels_bag)
        self.add_full_width(layout, "Blurred Card (with gradient background)",
                           build_blurred_card_in_gradient(), labels_bag)


if __name__ == "__main__":
    CardDemo.run()
