"""
ScrollShadow 组件示例 —— 对齐 HeroUI v2 docs
https://v2.heroui.com/docs/components/scroll-shadow

展示:
- 默认 vertical (auto visibility)
- horizontal 方向
- 不同 size (20 / 40 / 80)
- visibility 强制模式 (both / none / top / bottom)
- hide_scrollbar 开关
- 嵌在 Card 里使用
- 禁用 (is_enabled=False)
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget

from hero_side_ui import ScrollShadow, Card, CardBody, Body, Title, Button, Input
from _base import DemoBase

# ------------------------------------------------------------
# 工具: 生成一段很长的文本内容
# ------------------------------------------------------------

_LONG_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
    "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
    "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
    "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
) * 8


def make_long_body(text: str = _LONG_TEXT) -> QWidget:
    """生成一段很长的 Body label —— 将通过 sc.add_widget(body) 塞进 ScrollShadow。"""
    body = Body(text)
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    body.setContentsMargins(12, 12, 12, 12)
    return body


def fill_color_boxes(sc: ScrollShadow, num_boxes: int = 20) -> None:
    """往 horizontal ScrollShadow 的插槽里追加一串色块 —— 演示插槽装配方式。"""
    from hero_side_ui.themes import HEROUI_COLORS

    colors = ["primary", "secondary", "success", "warning", "danger", "default"]
    sc.layout().setContentsMargins(12, 12, 12, 12)
    sc.layout().setSpacing(10)
    for i in range(num_boxes):
        c = HEROUI_COLORS[colors[i % len(colors)]][500]
        box = QWidget()
        box.setFixedSize(120, 80)
        box.setStyleSheet(f"background: {c}; border-radius: 8px;")
        sc.add_widget(box)
    sc.add_stretch()


# ------------------------------------------------------------
# Demo
# ------------------------------------------------------------


class ScrollShadowDemo(DemoBase):
    component_name = "ScrollShadow"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):

        # --- 1. 默认 vertical —— 插槽装配 ---
        s1 = ScrollShadow()
        s1.add_widget(make_long_body())
        s1.setFixedSize(400, 260)
        self.add_full_width(layout, "默认 (vertical, auto visibility)", s1, labels_bag)

        # --- 2. horizontal —— 插槽装配一串色块 ---
        s2 = ScrollShadow(orientation="horizontal")
        fill_color_boxes(s2)
        s2.setFixedSize(560, 140)
        self.add_full_width(layout, 'orientation="horizontal"', s2, labels_bag)

        # --- 3. 不同 size ---
        size_row = QWidget()
        size_layout = QHBoxLayout(size_row)
        size_layout.setSpacing(16)
        for sz in (20, 40, 80):
            col = QWidget()
            cl = QVBoxLayout(col)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(6)
            cl.addWidget(Body(f"size = {sz}"))
            s = ScrollShadow(size=sz)
            s.add_widget(make_long_body())
            s.setFixedSize(260, 220)
            cl.addWidget(s)
            size_layout.addWidget(col)
        size_layout.addStretch()
        self.add_full_width(layout, "不同 size (20 / 40 / 80)", size_row, labels_bag)

        # --- 4. visibility 强制模式 ---
        vis_grid_w = QWidget()
        vis_grid = QGridLayout(vis_grid_w)
        vis_grid.setHorizontalSpacing(16)
        vis_grid.setVerticalSpacing(8)
        for i, v in enumerate(("auto", "both", "top", "bottom", "none")):
            vis_grid.addWidget(Body(f'visibility="{v}"'), (i // 3) * 2, i % 3)
            s = ScrollShadow(visibility=v)
            s.add_widget(make_long_body())
            s.setFixedSize(260, 180)
            vis_grid.addWidget(s, (i // 3) * 2 + 1, i % 3)
        self.add_full_width(layout, "visibility 强制模式", vis_grid_w, labels_bag)

        # --- 5. hide_scrollbar ---
        hs_row = QWidget()
        hs_layout = QHBoxLayout(hs_row)
        hs_layout.setSpacing(16)
        for hide in (False, True):
            col = QWidget()
            cl = QVBoxLayout(col)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(6)
            cl.addWidget(Body(f"hide_scrollbar={hide}"))
            s = ScrollShadow(hide_scrollbar=hide)
            s.add_widget(make_long_body())
            s.setFixedSize(300, 200)
            cl.addWidget(s)
            hs_layout.addWidget(col)
        hs_layout.addStretch()
        self.add_full_width(layout, "hide_scrollbar", hs_row, labels_bag)

        # --- 6. 嵌在 Card 里 ---
        # ScrollShadow 自动沿 parent 链找到 Card,实时读其 current_bg_color(),
        # 阴影淡出端与 Card 底色严丝合缝。Card 切主题/hover 时自动跟随,
        # 不需要 demo 传任何颜色参数或监听任何信号。
        card = Card(radius="lg")
        card.setFixedSize(520, 300)
        cb = CardBody()
        sc = ScrollShadow(size=40)
        sc.add_widget(make_long_body())
        cb.layout().setContentsMargins(0, 0, 0, 0)
        cb.layout().addWidget(sc)
        card.add_body(cb)
        self.add_full_width(layout, "嵌在 Card 内 (自动识别 Card 底色)", card, labels_bag)

        # --- 7. 插槽装配很多 Button (内容高度远超容器,触发滚动+阴影) ---
        sc_btns = ScrollShadow(size=40)
        sc_btns.setFixedSize(540, 240)
        sc_btns.layout().setContentsMargins(12, 12, 12, 12)
        sc_btns.layout().setSpacing(8)

        btn_grid_w = QWidget()
        btn_grid = QGridLayout(btn_grid_w)
        btn_grid.setContentsMargins(0, 0, 0, 0)
        btn_grid.setHorizontalSpacing(8)
        btn_grid.setVerticalSpacing(8)
        colors = ["default", "primary", "secondary", "success", "warning", "danger"]
        variants = ["solid", "bordered", "light", "flat", "ghost", "shadow"]
        # 5 块,每块一个 variant × 6 colors → 30 行 × 6 列 = 180 个按钮
        # 行数远超容器可视高度,必然触发滚动
        row = 0
        for repeat in range(5):
            for variant in variants:
                for c, color in enumerate(colors):
                    btn_grid.addWidget(
                        Button(
                            f"{variant[:3]}/{color[:3]}",
                            color=color, variant=variant, size="sm",
                        ),
                        row, c,
                    )
                row += 1
        sc_btns.add_widget(btn_grid_w)
        sc_btns.add_stretch()
        self.add_full_width(
            layout, "大量 Button 装配 (180 个,触发滚动)",
            sc_btns, labels_bag,
        )

        # --- 8. 插槽装配很多 Input (触发滚动+阴影) ---
        sc_inputs = ScrollShadow(size=40)
        sc_inputs.setFixedSize(460, 280)
        sc_inputs.layout().setContentsMargins(16, 16, 16, 16)
        sc_inputs.layout().setSpacing(12)
        input_specs = [
            ("用户名", "请输入用户名", "flat", "default"),
            ("邮箱", "you@example.com", "flat", "primary"),
            ("密码", "请输入密码", "bordered", "primary"),
            ("手机", "+86 138 0000 0000", "bordered", "secondary"),
            ("地址", "北京市...", "flat", "default"),
            ("公司", "Company Inc.", "faded", "default"),
            ("职位", "Software Engineer", "underlined", "primary"),
            ("个人主页", "https://...", "flat", "success"),
            ("生日", "YYYY-MM-DD", "bordered", "warning"),
            ("身份证号", "xxxxxx...", "faded", "danger"),
            ("紧急联系人", "联系人姓名", "flat", "default"),
            ("紧急电话", "+86 ...", "bordered", "danger"),
            ("学历", "本科 / 硕士 / 博士", "underlined", "secondary"),
            ("毕业院校", "学校名称", "flat", "default"),
            ("工作经验", "X 年", "faded", "primary"),
        ]
        for label, ph, variant, color in input_specs:
            sc_inputs.add_widget(
                Input(label=label, placeholder=ph, variant=variant, color=color)
            )
        sc_inputs.add_stretch()
        self.add_full_width(
            layout, "大量 Input 装配 (15 个,触发滚动)",
            sc_inputs, labels_bag,
        )

        # --- 9. is_enabled=False ---
        s_off = ScrollShadow(is_enabled=False)
        s_off.add_widget(make_long_body())
        s_off.setFixedSize(400, 220)
        self.add_full_width(layout, "is_enabled=False (禁用阴影)", s_off, labels_bag)


if __name__ == "__main__":
    ScrollShadowDemo.run()
