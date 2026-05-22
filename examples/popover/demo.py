"""
Popover 组件示例 — 12 placement / 7 colors / shadow / radius / backdrop /
插槽（任意内容）/ hover trigger / arrow
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget

from hero_side_ui import (
    Popover,
    PopoverContent,
    Button,
    Input,
    Checkbox,
    Spinner,
    Card,
    CardHeader,
    CardBody,
    Body,
    Subtitle,
)
from _base import DemoBase


def make_popover(text: str, **kwargs) -> Popover:
    p = Popover(**kwargs)
    c = PopoverContent()
    # 用 Body：跟随 ThemeProvider 自动配色 + 走 FontProvider 思源黑体
    c.layout().addWidget(Body(text))
    p.set_content(c)
    return p


class PopoverDemo(DemoBase):
    component_name = "Popover"

    def __init__(self):
        # 持有 popover 引用避免被 GC
        self._popovers: list = []
        super().__init__()

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 12 placements
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        placements = [
            "top-start",
            "top",
            "top-end",
            "bottom-start",
            "bottom",
            "bottom-end",
            "right-start",
            "right",
            "right-end",
            "left-start",
            "left",
            "left-end",
        ]
        for i, place in enumerate(placements):
            btn = Button(place, color="primary", variant="flat")
            p = make_popover(f"Popover at {place}", placement=place, color="default")
            p.attach(btn)
            self._popovers.append(p)
            grid.addWidget(btn, i // 3, i % 3)
        self.add_full_width(layout, "12 placements", grid_w, labels_bag)

        # 7 colors
        color_btns = []
        for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
            b = Button(c.capitalize(), color="primary", variant="flat")
            p = make_popover(f"Color = {c}", color=c, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            color_btns.append(b)
        self.add_section(layout, "7 colors", color_btns, labels_bag, spacing=12)

        # 滚动行为：close_on_scroll
        # 默认 close_on_scroll=True：祖先滚动时自动 fade-out + 跟随；
        # close_on_scroll=False：popover 始终跟着 trigger 滚动，不关闭
        scroll_btns = []

        # 左：跟随不关闭
        follow_btn = Button(
            "跟随不关闭 (close_on_scroll=False)", color="primary", variant="flat"
        )
        follow_pop = Popover(
            placement="bottom",
            color="default",
            shadow="md",
            arrow=True,
            close_on_scroll=False,  # ★ 关键参数
        )
        fc = PopoverContent()
        fc.layout().addWidget(Subtitle("Sticky Popover"))
        fc.layout().addWidget(
            Body("点开后滚动页面，我会一直跟着按钮走\n不会自动消失。")
        )
        follow_pop.set_content(fc)
        follow_pop.attach(follow_btn)
        self._popovers.append(follow_pop)
        scroll_btns.append(follow_btn)

        # 右：默认行为（关闭 + 淡出）作对比
        close_btn = Button("滚动即关闭（默认）", color="warning", variant="flat")
        close_pop = make_popover(
            "点开后滚动页面，我会带 fade-out 关闭。",
            placement="bottom",
            color="default",
            arrow=True,
        )
        close_pop.attach(close_btn)
        self._popovers.append(close_pop)
        scroll_btns.append(close_btn)

        self.add_section(
            layout,
            "滚动行为对比（打开后滚动页面观察）",
            scroll_btns,
            labels_bag,
            spacing=12,
        )

        # Shadow
        shadow_btns = []
        for s in ["none", "sm", "md", "lg"]:
            b = Button(f"shadow={s}", variant="flat", color="primary")
            p = make_popover(f"shadow={s}", shadow=s, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            shadow_btns.append(b)
        self.add_section(layout, "Shadow", shadow_btns, labels_bag, spacing=12)

        # Radius
        radius_btns = []
        for r in ["none", "sm", "md", "lg", "full"]:
            b = Button(f"radius={r}", variant="flat", color="secondary")
            p = make_popover(f"radius={r}", radius=r, placement="bottom")
            p.attach(b)
            self._popovers.append(p)
            radius_btns.append(b)
        self.add_section(layout, "Radius", radius_btns, labels_bag, spacing=12)

        # Backdrop × close_on_scroll 矩阵：3 kinds × 2 滚动行为
        # 上排：滚动即关闭 (close_on_scroll=True，默认)
        # 下排：滚动跟随不关闭 (close_on_scroll=False)
        # 直接点开后滚动主页面观察 backdrop 的两种表现：
        #   - True：backdrop 与 popover 一起 fade-out
        #   - False：backdrop 保持显示，popover 跟着 trigger 走
        #     （blur+sticky 是已 warn 的不推荐组合，best-effort 4x box-blur 重抓）
        bd_grid_w = QWidget()
        bd_grid = QGridLayout(bd_grid_w)
        bd_grid.setContentsMargins(0, 0, 0, 0)
        bd_grid.setSpacing(12)
        for col, kind in enumerate(["transparent", "opaque", "blur"]):
            # 跟随：close_on_scroll=False
            follow_b = Button(f"{kind} · 跟随", variant="flat", color="warning")
            follow_p = make_popover(
                f"backdrop={kind}\nclose_on_scroll=False\n滚动主页面：跟着按钮走，不关闭",
                backdrop=kind,
                placement="bottom",
                close_on_scroll=False,
            )
            follow_p.attach(follow_b)
            self._popovers.append(follow_p)
            bd_grid.addWidget(follow_b, 0, col)

            # 不跟随（默认）：close_on_scroll=True，滚动 fade-out
            close_b = Button(f"{kind} · 不跟随", variant="flat", color="primary")
            close_p = make_popover(
                f"backdrop={kind}\nclose_on_scroll=True\n滚动主页面：fade-out 关闭",
                backdrop=kind,
                placement="bottom",
                close_on_scroll=True,
            )
            close_p.attach(close_b)
            self._popovers.append(close_p)
            bd_grid.addWidget(close_b, 1, col)

        self.add_full_width(
            layout,
            "Backdrop × 滚动行为（上=跟随 / 下=不跟随，打开后滚动主页面观察）",
            bd_grid_w,
            labels_bag,
        )

        # Blur 质量档对比：blur_quality 4 档
        # 4 个按钮的唯一区别是 blur_quality；都开 backdrop=blur + close_on_scroll=False
        # 强制走"滚动节流帧重抓 blur"路径方便对比柔和度 / 流畅度。
        # 打开任一按钮后滚动主页面（鼠标滚轮 / 拖动滚动条均可）感受差异。
        #   low      — 2 级金字塔，~5-7ms     最快但边缘略糙
        #   fast     — 3 级金字塔，~8-12ms    默认；甜区
        #   great    — 4 级金字塔，~12-16ms   细腻度肉眼可辨
        #   high     — QGraphicsBlurEffect，~30-60ms 真高斯，可能掉帧
        blur_cmp_btns = []
        _quality_specs = [
            (
                "low",
                "low (2级)",
                "default",
                "blur_quality='low'\n2 级金字塔 box blur\n~5-7ms/帧 · 最快，但边缘略糙",
            ),
            (
                "fast",
                "fast (3级,默认)",
                "primary",
                "blur_quality='fast'\n3 级金字塔 box blur\n~8-12ms/帧 · 默认甜区",
            ),
            (
                "great",
                "great (4级)",
                "success",
                "blur_quality='great'\n4 级金字塔 box blur\n~12-16ms/帧 · 细腻度肉眼可辨",
            ),
            (
                "high",
                "high (高斯)",
                "secondary",
                "blur_quality='high'\nQGraphicsBlurEffect QualityHint\n~30-60ms/帧 · 最柔和但可能掉帧",
            ),
        ]
        for quality, btn_text, btn_color, popover_text in _quality_specs:
            btn = Button(btn_text, color=btn_color, variant="flat")
            pop = make_popover(
                popover_text,
                backdrop="blur",
                placement="bottom",
                close_on_scroll=False,
                blur_quality=quality,
            )
            pop.attach(btn)
            self._popovers.append(pop)
            blur_cmp_btns.append(btn)

        self.add_section(
            layout,
            "Blur 质量档对比（打开后滚动主页面观察柔和度 / 流畅度）",
            blur_cmp_btns,
            labels_bag,
            spacing=8,
        )

        # 插槽：任意内容
        # 1) 表单
        form_btn = Button("Settings", color="primary", variant="solid")
        form_pop = Popover(placement="bottom-start", shadow="lg", color="default")
        form = PopoverContent()
        form.setMinimumWidth(240)
        form.layout().setSpacing(10)
        # 表单小标题用 Subtitle
        form.layout().addWidget(Subtitle("Account Settings"))
        form.layout().addWidget(Input(label="Username", placeholder="@you", size="sm"))
        form.layout().addWidget(
            Input(label="Email", placeholder="you@example.com", size="sm")
        )
        form.layout().addWidget(Checkbox("Receive emails", color="primary", size="sm"))
        form.layout().addWidget(
            Button("Save", color="primary", variant="solid", size="sm")
        )
        form_pop.set_content(form)
        form_pop.attach(form_btn)
        self._popovers.append(form_pop)

        # 2) Spinner
        spin_btn = Button("Loading...", color="success", variant="flat")
        spin_pop = Popover(placement="bottom", color="default", shadow="md")
        sc = PopoverContent()
        sc.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.layout().addWidget(Spinner(label="Working..."))
        spin_pop.set_content(sc)
        spin_pop.attach(spin_btn)
        self._popovers.append(spin_pop)

        # 3) 完整 Card
        card_btn = Button("Profile Card", color="secondary", variant="flat")
        card_pop = Popover(placement="bottom", color="default", shadow="lg")
        cc = PopoverContent()
        cc.layout().setContentsMargins(0, 0, 0, 0)
        inner_card = Card(shadow="none", radius="md")
        inner_card.setFixedWidth(260)
        h = CardHeader()
        # Card 头/正文：Subtitle + Body 语义化
        h.layout().addWidget(Subtitle("Jerry Lu"))
        inner_card.add_header(h)
        bb = CardBody()
        bb.layout().addWidget(
            Body("Senior Tech Artist @ Tencent\nWorking on HeroSideUI")
        )
        inner_card.add_body(bb)
        cc.layout().addWidget(inner_card)
        card_pop.set_content(cc)
        card_pop.attach(card_btn)
        self._popovers.append(card_pop)

        self.add_section(
            layout,
            "插槽：什么都能放（Form / Spinner / Card）",
            [form_btn, spin_btn, card_btn],
            labels_bag,
            spacing=12,
        )

        # hover trigger
        hover_btn = Button("Hover me", color="danger", variant="flat")
        hover_pop = make_popover(
            "Triggered by hover", placement="bottom", color="danger"
        )
        hover_pop.attach(hover_btn, event="hover")
        self._popovers.append(hover_pop)
        self.add_section(layout, "hover 触发", [hover_btn], labels_bag, spacing=12)

        # arrow=True
        arrow_btns = []
        for place in ["top", "bottom", "left", "right"]:
            b = Button(f"{place} + arrow", color="primary", variant="flat")
            p = make_popover(
                f"arrow @ {place}", placement=place, color="default", arrow=True
            )
            p.attach(b)
            self._popovers.append(p)
            arrow_btns.append(b)
        self.add_section(
            layout, "arrow=True（显示箭头）", arrow_btns, labels_bag, spacing=12
        )

        # 彩色 arrow
        color_arrow_btns = []
        for c in ["primary", "success", "warning", "danger"]:
            b = Button(f"arrow {c}", color=c, variant="flat")
            p = make_popover(
                f"{c} popover with arrow", placement="bottom", color=c, arrow=True
            )
            p.attach(b)
            self._popovers.append(p)
            color_arrow_btns.append(b)
        self.add_section(layout, "彩色 arrow", color_arrow_btns, labels_bag, spacing=12)


if __name__ == "__main__":
    PopoverDemo.run()
