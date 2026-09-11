"""Badge 组件演示。

分节顺序对齐官方 HeroUI Badge 文档：
  Usage / Variants / Colors / Sizes / Shape / Placement / Dot /
  One Char & Multi Char / Outline / Invisible（桌面扩展交互切换）。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Avatar, Badge, Body, Button
from hero_side_ui.themes import (
    VALID_BADGE_PLACEMENTS,
    VALID_BADGE_SHAPES,
    VALID_BADGE_SIZES,
    VALID_BADGE_VARIANTS,
)

DEMO_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")


class BadgeDemo(DemoBase):
    component_name = "Badge"

    def _row(self, *widgets, spacing=24):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(spacing)
        for w in widgets:
            h.addWidget(w)
        h.addStretch()
        return row

    def _col(self, *widgets, spacing=12):
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(spacing)
        for w in widgets:
            v.addWidget(w)
        return col

    def _captioned(self, caption: str, widget: QWidget):
        return self._col(Body(caption), widget, spacing=6)

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "Button + content",
                    Badge(Button("消息"), content="5", color="danger"),
                ),
                self._captioned(
                    "Avatar + content",
                    Badge(
                        Avatar(name="JW", color="primary"),
                        content="3",
                        color="primary",
                        shape="circle",
                    ),
                ),
            )
        )

        # ---------- Variants ----------
        # 按钮用中性色：flat 角标是 20% 透明底，压同色 solid 按钮会透出按钮色
        # （与 solid 角标无法区分），中性底才能呈现 flat 的淡雾质感
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        v,
                        Badge(
                            Button("通知", size="sm"),
                            content="9",
                            variant=v,
                            color="primary",
                        ),
                    )
                    for v in VALID_BADGE_VARIANTS
                ]
            )
        )

        # ---------- Colors ----------
        layout.addWidget(self._section_title("Colors 颜色"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        c, Badge(Button("通知", size="sm"), content="9", color=c)
                    )
                    for c in DEMO_COLORS
                ]
            )
        )

        # ---------- Sizes ----------
        layout.addWidget(self._section_title("Sizes 尺寸"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        s,
                        Badge(
                            Avatar(name="JW", size="lg"),
                            content="9",
                            size=s,
                            color="primary",
                            shape="circle",
                        ),
                    )
                    for s in VALID_BADGE_SIZES
                ]
            )
        )

        # ---------- Shape ----------
        layout.addWidget(
            self._section_title("Shape 形状（影响锚点偏移：rectangle 5% / circle 10%）")
        )
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        s,
                        Badge(
                            Avatar(name="JW", size="lg"),
                            content="99+",
                            shape=s,
                            color="success",
                        ),
                    )
                    for s in VALID_BADGE_SHAPES
                ]
            )
        )

        # ---------- Placement ----------
        layout.addWidget(self._section_title("Placement 位置（四角）"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        p,
                        Badge(
                            Button("通知", size="lg", variant="bordered"),
                            content="9",
                            color="danger",
                            placement=p,
                        ),
                    )
                    for p in VALID_BADGE_PLACEMENTS
                ]
            )
        )

        # ---------- Dot ----------
        layout.addWidget(self._section_title("Dot 圆点（content 为空自动判定）"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "default",
                    Badge(
                        Avatar(name="JW", color="secondary"),
                        content="",
                        color="default",
                        shape="circle",
                    ),
                ),
                self._captioned(
                    "success",
                    Badge(
                        Avatar(name="JW", color="secondary"),
                        content="",
                        color="success",
                        shape="circle",
                    ),
                ),
                self._captioned(
                    "danger",
                    Badge(Button("消息", size="sm"), content="", color="danger"),
                ),
            )
        )

        # ---------- One Char & Multi Char ----------
        layout.addWidget(
            self._section_title("One Char / Multi Char（单字符正方形，多字符圆角矩形）")
        )
        layout.addWidget(
            self._row(
                self._captioned(
                    "1 字符",
                    Badge(
                        Avatar(name="JW", size="lg"),
                        content="5",
                        color="primary",
                        shape="circle",
                    ),
                ),
                self._captioned(
                    "多字符",
                    Badge(
                        Avatar(name="JW", size="lg"),
                        content="99+",
                        color="primary",
                        shape="circle",
                    ),
                ),
            )
        )

        # ---------- Outline ----------
        layout.addWidget(
            self._section_title("Outline 描边（默认开启，宿主背景色 2px）")
        )
        layout.addWidget(
            self._row(
                self._captioned(
                    "show_outline=True",
                    Badge(
                        Avatar(name="JW", size="lg"),
                        content="9",
                        color="warning",
                        shape="circle",
                    ),
                ),
                self._captioned(
                    "show_outline=False",
                    Badge(
                        Avatar(name="JW", size="lg"),
                        content="9",
                        color="warning",
                        show_outline=False,
                        shape="circle",
                    ),
                ),
            )
        )

        # ---------- Invisible ----------
        layout.addWidget(
            self._section_title("Invisible 隐藏（点击按钮切换，带 300ms 过渡）")
        )
        toggle_host = self._row()
        layout.addWidget(toggle_host)
        inv_badge = Badge(
            Avatar(name="JW", size="lg"), content="9", color="primary", shape="circle"
        )
        toggle_btn = Button("切换角标可见性", variant="flat", color="default")
        toggle_host.layout().addWidget(inv_badge)
        toggle_host.layout().addWidget(toggle_btn)
        # clicked 带 checked 参数，槽用 lambda 折叠
        toggle_btn.clicked.connect(
            lambda *_: inv_badge.set_invisible(not inv_badge.is_invisible())
        )


if __name__ == "__main__":
    BadgeDemo.run()
