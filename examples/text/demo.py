"""
Text 组件示例 — 全 13 档字号 / 9 档字重 / HeroUI 颜色 / HEX / RGBA / 透明度 / 选区高亮
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import Text, Title, Subtitle, Caption, Body
from _base import DemoBase


class TextDemo(DemoBase):
    component_name = "Text"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 13 档字号 (xs ~ 9xl)
        # ============================================================
        sizes = [
            "xs",
            "sm",
            "md",
            "lg",
            "xl",
            "2xl",
            "3xl",
            "4xl",
            "5xl",
            "6xl",
            "7xl",
            "8xl",
            "9xl",
        ]
        size_widgets = [Text(f"{s}  Aa 文字", size=s) for s in sizes]
        self.add_section_vertical(
            layout,
            "13 档字号 (xs / sm / md / lg / xl / 2xl ~ 9xl)",
            size_widgets,
            labels_bag,
            spacing=4,
        )

        # ============================================================
        # 2) 9 档字重 (thin ~ black)
        # ============================================================
        weights = [
            "thin",
            "extralight",
            "light",
            "normal",
            "medium",
            "semibold",
            "bold",
            "extrabold",
            "black",
        ]
        weight_widgets = [
            Text(
                f"font-{w}    The quick brown fox jumps over the lazy dog",
                size="lg",
                weight=w,
            )
            for w in weights
        ]
        self.add_section_vertical(
            layout,
            "9 档字重 (thin / extralight / light / normal / medium / semibold / bold / extrabold / black)",
            weight_widgets,
            labels_bag,
            spacing=4,
        )

        # ============================================================
        # 3) HeroUI 7 套语义色 × 主色 (500)
        # ============================================================
        token_names = [
            "default",
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "neutral",
        ]
        token_widgets = [
            Text(f"color={n!r}", size="lg", weight="semibold", color=n)
            for n in token_names
        ]
        self.add_section_grid(
            layout,
            "7 套 HeroUI 语义色（默认 500 档）",
            token_widgets,
            labels_bag,
            cols=4,
            spacing=14,
        )

        # ============================================================
        # 4) primary 色阶 50 ~ 900
        # ============================================================
        shade_widgets = [
            Text(f"primary-{s}", size="md", weight="medium", color=f"primary-{s}")
            for s in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)
        ]
        self.add_section_grid(
            layout,
            "primary 全色阶 (50 ~ 900)",
            shade_widgets,
            labels_bag,
            cols=5,
            spacing=10,
        )

        # ============================================================
        # 5) HEX / RGBA / tuple / QColor 自定义
        # ============================================================
        from PySide6.QtGui import QColor

        custom_widgets = [
            Text('HEX  "#FF8800"', size="md", color="#FF8800"),
            Text('HEX-A "#800066FF" (Qt: AARRGGBB)', size="md", color="#800066FF"),
            Text('rgb()  "rgb(220, 38, 38)"', size="md", color="rgb(220, 38, 38)"),
            Text(
                'rgba() "rgba(0, 200, 100, 0.7)"',
                size="md",
                color="rgba(0, 200, 100, 0.7)",
            ),
            Text("tuple (255, 0, 0)", size="md", color=(255, 0, 0)),
            Text("tuple (255, 0, 0, 128)", size="md", color=(255, 0, 0, 128)),
            Text('QColor("teal")', size="md", color=QColor("teal")),
            Text('Qt 命名色 "indianred"', size="md", color="indianred"),
        ]
        self.add_section_grid(
            layout,
            "自定义色 — HEX / rgb() / rgba() / tuple / QColor / Qt 命名色",
            custom_widgets,
            labels_bag,
            cols=2,
            spacing=8,
        )

        # ============================================================
        # 6) 透明度阶梯 (0.1 ~ 1.0)
        # ============================================================
        opacity_widgets = [
            Text(
                f"transparency = {a:.1f}",
                size="lg",
                weight="semibold",
                color="primary",
                transparency=a,
            )
            for a in (1.0, 0.9, 0.75, 0.6, 0.4, 0.25, 0.1)
        ]
        self.add_section_vertical(
            layout,
            "transparency 阶梯（叠加在 color 自身 alpha 上）",
            opacity_widgets,
            labels_bag,
            spacing=4,
        )

        # ============================================================
        # 7) 鼠标框选 — 选区底色根据主题自动适配
        # ============================================================
        select_widgets = [
            Text(
                "尝试用鼠标框选这一行 — 亮色模式下选区底色 = primary-500 × 22% alpha",
                size="md",
            ),
            Text(
                "框选我 — 暗色模式下选区底色 = primary-500 × 35% alpha，文字保留",
                size="md",
                color="success",
            ),
            Text(
                "自定义橙色文字也能正确显示选区高亮",
                size="md",
                color="#FF8800",
                weight="semibold",
            ),
            Text(
                "带透明度的文字框选时会自动提到 0.85+ 保证可读",
                size="md",
                color="primary",
                transparency=0.4,
            ),
        ]
        self.add_section_vertical(
            layout,
            "鼠标框选 — 选区底色 / 前景自动适配主题（试试切换主题再框选）",
            select_widgets,
            labels_bag,
            spacing=6,
        )

        # ============================================================
        # 7b) force_selection_text_color=False — 框选文字色不变
        # ============================================================
        force_widgets = [
            Text(
                "force_selection_text_color=False → 框选后文字色不变（仍是 primary 蓝）",
                size="md",
                color="primary",
                force_selection_text_color=False,
            ),
            Text(
                "danger + force_selection_text_color=False → 框选后仍是红色",
                size="md",
                color="danger",
                force_selection_text_color=False,
            ),
            Text(
                "默认（True）→ 框选后文字强制暗色/亮色，与原色无关",
                size="md",
                color="secondary",
            ),
        ]
        self.add_section_vertical(
            layout,
            "force_selection_text_color=False — 框选文字色保持原色不变",
            force_widgets,
            labels_bag,
            spacing=6,
        )

        # ============================================================
        # 7c) selection_adapts_color=True — 底色适配文字颜色
        # ============================================================
        adapt_widgets = [
            Text(
                "selection_adapts_color=True, color=danger → 底色自适应淡红/暗红",
                size="md",
                color="danger",
                selection_adapts_color=True,
            ),
            Text(
                "selection_adapts_color=True, color=primary → 底色自适应淡蓝",
                size="md",
                color="primary",
                selection_adapts_color=True,
            ),
            Text(
                "selection_adapts_color=True, color=warning → 底色自适应淡黄",
                size="md",
                color="warning",
                selection_adapts_color=True,
            ),
            Text(
                "selection_adapts_color=True, 自定义橙色 → 算法生成适配底色",
                size="md",
                color="#FF8800",
                selection_adapts_color=True,
            ),
            Text(
                "默认（False）→ 永远用 primary-500 底色（不受文字色影响）",
                size="md",
                color="success",
            ),
        ]
        self.add_section_vertical(
            layout,
            "selection_adapts_color=True — 选区底色适配文字颜色",
            adapt_widgets,
            labels_bag,
            spacing=6,
        )

        # ============================================================
        # 7d) 两者组合 — 文字色不变 + 底色跟着文字色走
        # ============================================================
        combo_widgets = [
            Text(
                "force=False + adapts=True, color=danger → 红字+淡红底，框选后文字仍是红色",
                size="md",
                color="danger",
                force_selection_text_color=False,
                selection_adapts_color=True,
            ),
            Text(
                "force=False + adapts=True, color=primary → 蓝字+淡蓝底，框选后文字仍是蓝色",
                size="md",
                color="primary",
                force_selection_text_color=False,
                selection_adapts_color=True,
            ),
            Text(
                "force=False + adapts=True, 自定义橙 → 橙字+淡橙底，框选后文字仍是橙色",
                size="md",
                color="#FF8800",
                force_selection_text_color=False,
                selection_adapts_color=True,
            ),
        ]
        self.add_section_vertical(
            layout,
            "force=False + adapts=True — 文字色不变 + 底色跟着文字色走",
            combo_widgets,
            labels_bag,
            spacing=6,
        )

        # ============================================================
        # 8) 主题硬锁 vs auto
        # ============================================================
        theme_row = QWidget()
        hl = QHBoxLayout(theme_row)
        hl.setSpacing(24)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        hl.addWidget(Text("auto (跟随主题切换器)", size="lg", weight="medium"))
        hl.addWidget(
            Text('theme="light" 硬锁', size="lg", weight="medium", theme="light")
        )
        hl.addWidget(
            Text('theme="dark" 硬锁', size="lg", weight="medium", theme="dark")
        )
        self.add_section(
            layout, "主题模式 (auto / 硬锁 light / 硬锁 dark)", [theme_row], labels_bag
        )

        # ============================================================
        # 9) 向后兼容: Title / Subtitle / Caption / Body
        # ============================================================
        legacy_widgets = [
            Title("Title — level=1 (24px Bold)"),
            Title("Title — level=2 (18px Bold)", level=2),
            Title("Title — level=3 (16px Bold)", level=3),
            Subtitle("Subtitle — 13px 中性灰"),
            Body("Body — 14px 正文，跟随主题前景色。"),
            Caption("Caption — 12px 浅灰，最低对比度。"),
        ]
        self.add_section_vertical(
            layout,
            "语义化别名（基于 Text 实现，向后兼容）",
            legacy_widgets,
            labels_bag,
            spacing=4,
        )

        # ============================================================
        # 10) 动态 setter 演示
        # ============================================================
        dyn = Text(
            "Click buttons to mutate me", size="2xl", weight="semibold", color="default"
        )
        from hero_side_ui import Button

        btn_color = Button("color=primary", size="sm", variant="flat", color="primary")
        btn_color.clicked.connect(lambda: dyn.set_color("primary"))

        btn_danger = Button("color=danger", size="sm", variant="flat", color="danger")
        btn_danger.clicked.connect(lambda: dyn.set_color("danger"))

        btn_hex = Button('color="#FF8800"', size="sm", variant="flat")
        btn_hex.clicked.connect(lambda: dyn.set_color("#FF8800"))

        btn_size = Button("size=4xl", size="sm", variant="flat")
        btn_size.clicked.connect(lambda: dyn.set_size("4xl"))

        btn_size_md = Button("size=md", size="sm", variant="flat")
        btn_size_md.clicked.connect(lambda: dyn.set_size("md"))

        btn_weight = Button("weight=black", size="sm", variant="flat")
        btn_weight.clicked.connect(lambda: dyn.set_weight("black"))

        btn_weight_thin = Button("weight=thin", size="sm", variant="flat")
        btn_weight_thin.clicked.connect(lambda: dyn.set_weight("thin"))

        btn_alpha = Button("transparency=0.4", size="sm", variant="flat")
        btn_alpha.clicked.connect(lambda: dyn.set_transparency(0.4))

        btn_alpha_full = Button("transparency=1.0", size="sm", variant="flat")
        btn_alpha_full.clicked.connect(lambda: dyn.set_transparency(1.0))

        btn_reset = Button("reset color", size="sm", variant="bordered")
        btn_reset.clicked.connect(lambda: dyn.set_color(None))

        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        bl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for b in (
            btn_color,
            btn_danger,
            btn_hex,
            btn_size,
            btn_size_md,
            btn_weight,
            btn_weight_thin,
            btn_alpha,
            btn_alpha_full,
            btn_reset,
        ):
            bl.addWidget(b)
        # 行容器宽度由内部按钮决定，拒绝被父 layout 拉伸压缩
        from PySide6.QtWidgets import QSizePolicy
        btns.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.add_section_vertical(
            layout,
            "动态 setter (set_color / set_size / set_weight / set_transparency)",
            [dyn, btns],
            labels_bag,
            spacing=10,
        )

        # ============================================================
        # 8) selectable=False — 禁止框选/复制
        # ============================================================
        non_selectable = [
            Text("这段文字不允许框选（selectable=False）", size="md", selectable=False),
            Text("primary 色 + 不可框选", size="md", color="primary", selectable=False),
            Text("可以框选的正常文字（selectable=True，默认）", size="md", color="secondary"),
        ]
        self.add_section_vertical(
            layout,
            "selectable=False — 禁止框选/复制",
            non_selectable,
            labels_bag,
            spacing=6,
        )


    TextDemo.run()
