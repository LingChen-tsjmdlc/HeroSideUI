"""Alert 组件示例 — 对齐 HeroUI Alert 页面全部 11 个示例。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import Qt

from hero_side_ui import Alert, Button, Title, Subtitle, Body
from _base import DemoBase

COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
VARIANTS = ["solid", "bordered", "flat", "faded"]
RADII = ["none", "sm", "md", "lg", "full"]


class AlertDemo(DemoBase):
    component_name = "Alert"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 1. Usage — 基本用法
        self.add_section_vertical(
            layout,
            "Usage",
            [
                Alert(
                    title="注意",
                    description="这是一个基本的 Alert 通知横幅。",
                ),
            ],
            spacing=8,
        )

        # 2. Colors
        self._add_alerts(
            layout,
            "Colors",
            COLORS,
            color_tpl="{}",
            variant="flat",
            title_tpl="{}",
            desc="用于传达不同语义的临时通知。",
        )

        # 3. Variants
        self._add_alerts(
            layout,
            "Variants",
            VARIANTS,
            variant_tpl="{}",
            color="warning",
            title_tpl="Warning",
            desc="4 种视觉样式：solid / bordered / flat / faded。",
        )

        # 4. Radius
        self._add_alerts(
            layout,
            "Radius",
            RADII,
            radius_tpl="{}",
            color="primary",
            variant="flat",
            title_tpl="Radius: {}",
            desc="5 种圆角大小。",
        )

        # 5. Custom Icon
        self.add_section_vertical(
            layout,
            "Custom Icon",
            [
                Alert(
                    title="自定义图标",
                    description='使用 icon="heroicons--check-solid" 覆盖默认图标。',
                    color="primary",
                    variant="flat",
                    icon="heroicons--check-solid",
                ),
            ],
            spacing=8,
        )

        # 6. Without Icon
        self.add_section_vertical(
            layout,
            "Without Icon",
            [
                Alert(
                    title="无图标",
                    description="hide_icon=True，icon 和圆形底色都不要，文字左对齐。",
                    color="secondary",
                    variant="flat",
                    hide_icon=True,
                ),
            ],
            spacing=8,
        )

        # 7. Without Icon Wrapper
        self.add_section_vertical(
            layout,
            "Without Icon Wrapper",
            [
                Alert(
                    title="无图标容器",
                    description="hide_icon_wrapper=True，去掉圆形底色，只留 icon 图标。",
                    color="success",
                    variant="flat",
                    hide_icon_wrapper=True,
                ),
            ],
            spacing=8,
        )

        # 8. With Action
        btn = Button("操作", color="primary", variant="light", size="sm")
        self.add_section_vertical(
            layout,
            "With Action",
            [
                Alert(
                    title="带操作按钮",
                    description="通过 end_content 传入操作按钮。",
                    color="warning",
                    variant="flat",
                    end_content=btn,
                ),
            ],
            spacing=8,
        )

        # 9. Controlled Visibility
        self._build_controlled_visibility(layout)

        # 10. Custom Styles
        self._build_custom_styles(layout)

        # 11. Custom Implementation
        self._build_custom_implementation(layout)

    # ---- Controlled Visibility ----
    def _build_controlled_visibility(self, layout):
        ctrl_alert = Alert(
            title="受控可见性",
            description="通过 is_visible + 外部按钮控制显隐，而非 is_closable。",
            color="primary",
            variant="flat",
            is_visible=True,
        )
        toggle_btn = Button("切换可见性", color="primary", variant="flat", size="sm")
        toggle_btn.clicked.connect(lambda: ctrl_alert.set_visible(not ctrl_alert.is_visible()))

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        rl.addWidget(toggle_btn)

        self.add_section_vertical(
            layout,
            "Controlled Visibility",
            [ctrl_alert, row],
            spacing=8,
        )

    # ---- Custom Styles ----
    def _build_custom_styles(self, layout):
        """通过 set_stylesheet 覆盖 QSS 实现自定义渐变背景等样式。"""
        styled = Alert(
            title="自定义样式",
            description="通过 set_stylesheet 覆盖渐变背景、边框等样式。",
            color="danger",
            variant="flat",
        )
        # 覆盖 QSS：渐变背景 + 无边框 + 白色文字（set_stylesheet 防止主题切换覆盖）
        styled.set_stylesheet(
            "QWidget#HeroAlert {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "    stop:0 #e879f9, stop:1 #7c3aed);"
            "  border: none;"
            "  border-radius: 8px;"
            "}"
            "QWidget#HeroAlertIconWrapper {"
            "  background-color: rgba(255,255,255,0.2);"
            "  border: none;"
            "  border-radius: 14px;"
            "}"
        )
        styled._title_label.set_color("#ffffff")
        styled._desc_label.set_color("rgba(255,255,255,0.85)")
        styled._close_btn.set_icon_color("#ffffff")
        styled._icon_color = "#ffffff"
        styled._refresh_icon()

        self.add_section_vertical(
            layout,
            "Custom Styles",
            [styled],
            spacing=8,
        )

    # ---- Custom Implementation ----
    def _build_custom_implementation(self, layout):
        """用 start_content + end_content 构建完全自定义的 Alert 布局。"""
        custom = Alert(
            title="自定义实现",
            description="使用 start_content / end_content 组合完全自定义布局。",
            color="success",
            variant="bordered",
        )
        # 在右侧追加自定义按钮组
        action_row = QWidget()
        arl = QHBoxLayout(action_row)
        arl.setContentsMargins(0, 0, 0, 0)
        arl.setSpacing(4)
        arl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn1 = Button("确认", color="success", variant="flat", size="sm")
        btn2 = Button("取消", color="default", variant="flat", size="sm")
        arl.addWidget(btn1)
        arl.addWidget(btn2)
        custom.set_end_content(action_row)

        self.add_section_vertical(
            layout,
            "Custom Implementation",
            [custom],
            spacing=8,
        )

    # ---- helpers ----
    def _add_alerts(self, layout, section_title, values, **base_kwargs):
        """生成一组 Alert 用不同 param 值渲染。"""
        title_tpl = base_kwargs.pop("title_tpl", "{}")
        desc = base_kwargs.pop("desc", "")
        color_tpl = base_kwargs.pop("color_tpl", None)
        variant_tpl = base_kwargs.pop("variant_tpl", None)
        radius_tpl = base_kwargs.pop("radius_tpl", None)

        alerts = []
        for v in values:
            kw = dict(base_kwargs)
            if color_tpl:
                kw["color"] = color_tpl.format(v)
            if variant_tpl:
                kw["variant"] = variant_tpl.format(v)
            if radius_tpl:
                kw["radius"] = radius_tpl.format(v)
            title = title_tpl.format(v.capitalize() if isinstance(v, str) else v)
            alerts.append(Alert(title=title, description=desc, **kw))

        self.add_section_vertical(layout, section_title, alerts, spacing=6)


if __name__ == "__main__":
    AlertDemo.run()
