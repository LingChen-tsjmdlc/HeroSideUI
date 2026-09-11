"""Breadcrumbs 组件演示。

分节对齐官方 HeroUI Breadcrumbs 文档目录：
  Usage / Disabled / Sizes / Colors / Variants / Underlines / Radius /
  Routing / Controlled / Menu Type / Start & End Content /
  Custom Separator / Custom Items / Collapsing Items /
  Customizing the Ellipsis Item
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import (
    BreadcrumbItem,
    Breadcrumbs,
    Body,
    Button,
    Dropdown,
    ThemeProvider,
)
from hero_side_ui.themes import (
    VALID_BREADCRUMBS_COLORS,
    VALID_BREADCRUMBS_RADII,
    VALID_BREADCRUMBS_SIZES,
    VALID_BREADCRUMBS_UNDERLINES,
    VALID_BREADCRUMBS_VARIANTS,
)
from hero_side_ui.utils import load_svg_icon

DEMO_COLORS = ("foreground", "primary", "secondary", "success", "warning", "danger")


class ThemeIcon(QLabel):
    """主题感知图标：ThemeProvider 切换亮暗时自动重载对比色。"""

    def __init__(self, name: str, size: int = 14):
        super().__init__()
        self._name = name
        self._size = size
        self.setFixedWidth(size + 2)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 纯装饰：鼠标穿透让点击落在所在面包屑项上
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        ThemeProvider.instance().register(self)

    def set_theme(self, theme: str):
        # color=None → icon_utils 主题感知对比色（暗浅/亮深）；register 时
        # 会立即同步一次，构造早于 setup 也能拿到正确配色
        self.setPixmap(load_svg_icon(self._name, size=self._size))


def _icon_label(name: str) -> QLabel:
    """start/end content 用的小图标（主题感知）。"""
    return ThemeIcon(name)


class BreadcrumbsDemo(DemoBase):
    component_name = "Breadcrumbs"

    def _row(self, *widgets, spacing=32):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(spacing)
        for w in widgets:
            h.addWidget(w)
        h.addStretch()
        return row

    def _captioned(self, caption: str, widget: QWidget):
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.addWidget(Body(caption))
        v.addWidget(widget)
        return col

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法"))
        layout.addWidget(
            self._row(
                Breadcrumbs(items=[
                    BreadcrumbItem("Home", key="home"),
                    BreadcrumbItem("Music", key="music"),
                    BreadcrumbItem("Artist", key="artist"),
                    BreadcrumbItem("Album", key="album"),
                    BreadcrumbItem("Song", key="song"),
                ])
            )
        )

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用（last 项保持可用，官方语义）"))
        layout.addWidget(
            self._row(
                Breadcrumbs(items=[
                    BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                    BreadcrumbItem("Artist"), BreadcrumbItem("Album"),
                    BreadcrumbItem("Song"),
                ], is_disabled=True)
            )
        )

        # ---------- Sizes ----------
        layout.addWidget(self._section_title("Sizes 尺寸"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        s,
                        Breadcrumbs(items=[
                            BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                            BreadcrumbItem("Artist"),
                        ], size=s, color="primary"),
                    )
                    for s in VALID_BREADCRUMBS_SIZES
                ]
            )
        )

        # ---------- Colors ----------
        layout.addWidget(self._section_title("Colors 颜色（非 current 半透明，current 全色）"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        c,
                        Breadcrumbs(items=[
                            BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                            BreadcrumbItem("Games"),
                        ], color=c),
                    )
                    for c in DEMO_COLORS
                ],
                spacing=24,
            )
        )

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        v,
                        Breadcrumbs(items=[
                            BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                            BreadcrumbItem("Games"),
                        ], variant=v, color="primary"),
                    )
                    for v in VALID_BREADCRUMBS_VARIANTS
                ]
            )
        )

        # ---------- Underlines ----------
        layout.addWidget(self._section_title("Underlines 下划线模式（hover/active 需鼠标交互）"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        u,
                        Breadcrumbs(items=[
                            BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                            BreadcrumbItem("Games"),
                        ], underline=u, color="primary"),
                    )
                    for u in VALID_BREADCRUMBS_UNDERLINES
                ],
                spacing=24,
            )
        )

        # ---------- Radius ----------
        layout.addWidget(self._section_title("Radius 圆角（solid 变体下可见）"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(
                        r,
                        Breadcrumbs(items=[
                            BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                            BreadcrumbItem("Games"),
                        ], variant="solid", radius=r, color="primary"),
                    )
                    for r in VALID_BREADCRUMBS_RADII
                ],
                spacing=24,
            )
        )

        # ---------- Routing ----------
        layout.addWidget(self._section_title("Routing 路由（on_action 回调，桌面以 key 分发）"))
        routing_label = Body("route: -")
        bc_route = Breadcrumbs(items=[
            BreadcrumbItem("Home", key="/home"),
            BreadcrumbItem("Music", key="/music"),
            BreadcrumbItem("Artist", key="/artist"),
        ], on_action=lambda key: routing_label.setText(f"route: {key}"))
        layout.addWidget(self._row(bc_route, routing_label))

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控 current（点击切换当前位置）"))
        # 官方 ControlledTemplate：所有项显式传 isCurrent（受控模式），点击全量更新
        controlled_items = [
            BreadcrumbItem("Home", key="home", is_current=False),
            BreadcrumbItem("Music", key="music", is_current=False),
            BreadcrumbItem("Artist", key="artist", is_current=False),
            BreadcrumbItem("Album", key="album", is_current=False),
            BreadcrumbItem("Song", key="song", is_current=True),
        ]
        bc_ctrl = Breadcrumbs(items=controlled_items)
        ctrl_label = Body("current: song")

        def _set_current(key):
            for it in controlled_items:
                it.is_current = it.key == key
            bc_ctrl.set_items(controlled_items)
            ctrl_label.setText(f"current: {key}")

        bc_ctrl.action_triggered.connect(_set_current)
        layout.addWidget(self._row(bc_ctrl, ctrl_label))

        # ---------- Menu Type ----------
        # 官方 Menu Type：每项 border 胶囊（itemClasses）；桌面等价 = bordered 项，
        # current 反白边框、Song 禁用灰底
        layout.addWidget(self._section_title("Menu Type 菜单型（bordered 胶囊项，点击切换 current）"))
        menu_items = [
            BreadcrumbItem("Home", key="home", bordered=True),
            BreadcrumbItem("Music", key="music", bordered=True),
            BreadcrumbItem("Artist", key="artist", bordered=True, is_current=True),
            BreadcrumbItem("Album", key="album", bordered=True),
            BreadcrumbItem("Song", key="song", bordered=True, is_disabled=True),
        ]
        bc_menu = Breadcrumbs(items=menu_items, hide_separator=True)
        menu_label = Body("current: artist")

        def _menu_pick(key):
            for it in menu_items:
                it.is_current = it.key == key
            bc_menu.set_items(menu_items)
            menu_label.setText(f"current: {key}")

        bc_menu.action_triggered.connect(_menu_pick)
        layout.addWidget(self._row(bc_menu, menu_label))

        # ---------- Start & End Content ----------
        layout.addWidget(self._section_title("Start & End Content 项首/尾图标"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "startContent",
                    Breadcrumbs(items=[
                        BreadcrumbItem("Home", start_content=_icon_label("heroui--avatar-person")),
                        BreadcrumbItem("Music", start_content=_icon_label("heroicons--clock")),
                        BreadcrumbItem("Artist", start_content=_icon_label("heroicons--information-circle-solid")),
                        BreadcrumbItem("Album", start_content=_icon_label("heroicons--check-solid")),
                        BreadcrumbItem("Song", start_content=_icon_label("icon-park-outline--share")),
                    ], color="primary"),
                ),
                self._captioned(
                    "endContent",
                    Breadcrumbs(items=[
                        BreadcrumbItem("Home", end_content=_icon_label("heroui--avatar-person")),
                        BreadcrumbItem("Music", end_content=_icon_label("heroicons--clock")),
                        BreadcrumbItem("Artist", end_content=_icon_label("heroicons--information-circle-solid")),
                    ], color="primary"),
                ),
            )
        )

        # ---------- Custom Separator ----------
        layout.addWidget(self._section_title("Custom Separator 自定义分隔符"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "slash",
                    Breadcrumbs(items=[
                        BreadcrumbItem("Home"), BreadcrumbItem("Music"),
                        BreadcrumbItem("Games"),
                    ], separator="/"),
                ),
                self._captioned(
                    "item-level chevron-double",
                    Breadcrumbs(items=[
                        BreadcrumbItem("Home"),
                        BreadcrumbItem("Music"),
                        BreadcrumbItem("Games"),
                    ]),
                ),
            )
        )

        # ---------- Custom Items ----------
        # 官方 Custom Items：项内嵌 Dropdown 触发按钮（用现成 Dropdown 组件）
        layout.addWidget(self._section_title("Custom Items 自定义项（项内嵌 Dropdown 下拉按钮）"))
        songs_dd = Dropdown(
            trigger=Button(
                "Songs",
                icon="heroicons--chevron-down",
                size="sm",
                variant="light",
                radius="full",
            ),
            items=[
                {"key": "song1", "label": "Song 1"},
                {"key": "song2", "label": "Song 2"},
                {"key": "song3", "label": "Song 3"},
            ],
        )
        layout.addWidget(
            self._row(
                Breadcrumbs(items=[
                    BreadcrumbItem("Home", key="home"),
                    BreadcrumbItem("Music", key="music"),
                    BreadcrumbItem("Artist", key="artist"),
                    BreadcrumbItem("Album", key="album"),
                    BreadcrumbItem("", key="songs", start_content=songs_dd),
                ])
            )
        )

        # ---------- Collapsing Items ----------
        layout.addWidget(self._section_title("Collapsing Items 折叠（7 项 maxItems=3）"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "before=1 after=2",
                    Breadcrumbs(items=[
                        BreadcrumbItem(f"Level {i}", key=f"k{i}") for i in range(7)
                    ], max_items=3),
                ),
                self._captioned(
                    "before=2 after=1",
                    Breadcrumbs(items=[
                        BreadcrumbItem(f"Level {i}", key=f"k{i}") for i in range(7)
                    ], max_items=3, items_before_collapse=2, items_after_collapse=1),
                ),
            )
        )

        # ---------- Customizing the Ellipsis Item ----------
        # 官方示例：省略号渲染为 icon_only 方按钮，点开 Dropdown 列出折叠项
        # （Breadcrumbs × Button(icon_only) × Dropdown 组合）
        layout.addWidget(
            self._section_title(
                "Customizing the Ellipsis Item 自定义省略号（icon_only 方按钮 + Dropdown 列出折叠项）"
            )
        )
        ellipsis_label = Body("collapsed: -")

        def _ellipsis_with_dropdown(collapsed):
            menu_items = [
                {"key": it.key or it.label, "label": it.label} for it in collapsed
            ]
            dd = Dropdown(
                trigger=Button(
                    icon_only=True,
                    icon="heroicons--ellipsis-horizontal",
                    size="sm",
                    variant="flat",
                ),
                items=menu_items,
            )
            dd.action.connect(lambda k: ellipsis_label.setText(f"collapsed: {k}"))
            return dd

        bc_ell = Breadcrumbs(
            items=[BreadcrumbItem(f"Item {i}", key=f"e{i}") for i in range(6)],
            max_items=3,
            render_ellipsis=_ellipsis_with_dropdown,
        )
        layout.addWidget(self._row(bc_ell, ellipsis_label))


if __name__ == "__main__":
    BreadcrumbsDemo.run()
