"""
Radio 组件示例 — 对齐 HeroUI v2 文档 (https://v2.heroui.com/docs/components/radio-group)

包含 9 个 v2 文档示例小节：
    Usage / Disabled / Default Value / With Description /
    Horizontal / Controlled / Invalid /
    Custom Styles / Custom Implementation
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Body, Radio, RadioBase, RadioGroup
from hero_side_ui.themes import HEROUI_COLORS
from _base import DemoBase


class RadioDemo(DemoBase):
    component_name = "Radio"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 1) Usage
        g_usage = RadioGroup(label="Select your favorite city")
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_usage.create_radio(txt, value=val)
        self.add_full_width(layout, "Usage", g_usage, labels_bag)

        # 2) Disabled
        g_disabled = RadioGroup(label="Select your favorite city", is_disabled=True)
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_disabled.create_radio(txt, value=val)
        self.add_full_width(layout, "Disabled", g_disabled, labels_bag)

        # 3) Default Value
        g_default = RadioGroup(
            label="Select your favorite city",
            default_value="london",
        )
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_default.create_radio(txt, value=val)
        self.add_full_width(layout, "Default Value", g_default, labels_bag)

        # 4) With Description
        g_desc = RadioGroup(label="Plans")
        g_desc.create_radio(
            "Free",
            value="free",
            description="Up to 20 items",
        )
        g_desc.create_radio(
            "Pro",
            value="pro",
            description="Unlimited items. $10 per month.",
        )
        g_desc.create_radio(
            "Enterprise",
            value="enterprise",
            description="24/7 support. Contact us for pricing.",
        )
        self.add_full_width(layout, "With Description", g_desc, labels_bag)

        # 5) Horizontal
        g_h = RadioGroup(
            label="Select your favorite city",
            orientation="horizontal",
        )
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_h.create_radio(txt, value=val)
        self.add_full_width(layout, "Horizontal", g_h, labels_bag)

        # 6) Controlled
        g_ctrl = RadioGroup(
            label="Select your favorite city",
            default_value="london",
        )
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_ctrl.create_radio(txt, value=val)
        selected_text = Body("Selected: london", color="primary")
        g_ctrl.value_changed.connect(lambda v: selected_text.setText(f"Selected: {v}"))
        self.add_section_vertical(
            layout, "Controlled", [g_ctrl, selected_text], labels_bag, spacing=8
        )

        # 7) Invalid
        g_invalid = RadioGroup(
            label="Select your favorite city",
            is_invalid=True,
            error_message="The selected city is invalid, please try again.",
            color="danger",
        )
        for txt, val in [
            ("Buenos Aires", "buenos-aires"),
            ("Sydney", "sydney"),
            ("San Francisco", "san-francisco"),
            ("London", "london"),
            ("Tokyo", "tokyo"),
        ]:
            g_invalid.create_radio(txt, value=val)
        self.add_full_width(layout, "Invalid", g_invalid, labels_bag)

        # 8) Custom Styles —— 卡片式 Radio（对齐 v2 Custom Styles 示例）
        g_card = RadioGroup(
            label="Plans",
            description="Selected plan can be changed at any time.",
            variant="card",
        )
        g_card.create_radio("Free", value="free", description="Up to 20 items")
        g_card.create_radio(
            "Pro", value="pro", description="Unlimited items. $10 per month."
        )
        g_card.create_radio(
            "Enterprise",
            value="enterprise",
            description="24/7 support. Contact us for pricing.",
        )
        self.add_full_width(layout, "Custom Styles", g_card, labels_bag)

        # 9) Custom Implementation —— 继承 RadioBase 自造视觉
        g_custom = RadioGroup(label="Plans")
        g_custom.add_radio(MyRadio("Free", value="free", description="Up to 20 items"))
        g_custom.add_radio(
            MyRadio("Pro", value="pro", description="Unlimited items. $10 per month.")
        )
        g_custom.add_radio(
            MyRadio(
                "Enterprise",
                value="enterprise",
                description="24/7 support. Contact us for pricing.",
            )
        )
        self.add_full_width(layout, "Custom Implementation", g_custom, labels_bag)


# 自定义 Radio：横向反向布局，左侧标签 + 右侧空心选中点
class MyRadio(RadioBase):
    """演示如何继承 RadioBase 自造视觉，状态/互斥仍由 RadioGroup 托管"""

    PAD = 12
    GAP = 12
    DOT = 18
    INNER = 8
    RADIUS = 12
    MAX_W = 300

    def sizeHint(self):
        from PySide6.QtCore import QSize

        fm_label = QFontMetrics(self.font())
        label_h = fm_label.height() if self.text() else 0
        desc_h = fm_label.height() if self._description else 0
        h = self.PAD + max(self.DOT, label_h + desc_h) + self.PAD
        return QSize(self.MAX_W, h)

    def paintEvent(self, _event):
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        primary = QColor(HEROUI_COLORS["primary"][500])

        bg = QColor("#ffffff" if not is_dark else dc[900])
        border = QColor(dc[300] if not is_dark else dc[700])
        if self._hover and not self.isChecked():
            bg = QColor(dc[100] if not is_dark else dc[800])
        if self.isChecked():
            border = primary

        label_color = QColor("#11181c" if not is_dark else "#ecedee")
        desc_color = QColor(dc[500] if not is_dark else dc[400])

        rect = self.rect()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._is_disabled:
            p.setOpacity(0.5)

        # 卡片底
        p.setPen(QPen(border, 2))
        p.setBrush(bg)
        p.drawRoundedRect(
            QRectF(1, 1, rect.width() - 2, rect.height() - 2),
            self.RADIUS,
            self.RADIUS,
        )

        # 右侧圆环 + 内点
        dot_x = rect.width() - self.PAD - self.DOT
        dot_y = (rect.height() - self.DOT) // 2
        p.setPen(QPen(primary if self.isChecked() else border, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(dot_x + 1, dot_y + 1, self.DOT - 2, self.DOT - 2))
        if self._control_progress > 0.001:
            p.save()
            p.setOpacity(self._control_progress)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(primary)
            cx = dot_x + self.DOT / 2.0
            cy = dot_y + self.DOT / 2.0
            r = self.INNER / 2.0
            p.drawEllipse(QRectF(cx - r, cy - r, self.INNER, self.INNER))
            p.restore()

        # 左侧 label / description
        text_x = self.PAD
        text_right = dot_x - self.GAP
        fm = QFontMetrics(self.font())
        label_h = fm.height() if self.text() else 0
        desc_h = fm.height() if self._description else 0
        block_h = label_h + desc_h
        top = (rect.height() - block_h) // 2

        if self.text():
            p.setPen(QPen(label_color))
            p.drawText(
                QRectF(text_x, top, max(0, text_right - text_x), label_h),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )
        if self._description:
            p.setPen(QPen(desc_color))
            p.drawText(
                QRectF(text_x, top + label_h, max(0, text_right - text_x), desc_h),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self._description,
            )
        p.end()


if __name__ == "__main__":
    RadioDemo.run()
