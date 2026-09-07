"""
Dropdown 组件示例 — 6 colors × 6 variants 全排列 × 3 sizes × 5 radius
× 阴影 × 遮罩 × 12 方位 × 分组 × 选中模式 × 禁用 × 单项配色 × 非按钮触发器
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QWidget

from hero_side_ui import Body, Button, Caption, Dropdown, Subtitle
from _base import DemoBase

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("solid", "shadow", "bordered", "flat", "faded", "light")
SIZES = ("sm", "md", "lg")
RADII = ("none", "sm", "md", "lg", "full")
SHADOWS = ("none", "sm", "md", "lg")
BACKDROPS = ("transparent", "opaque", "blur")
PLACEMENTS = (
    "bottom",
    "bottom-start",
    "bottom-end",
    "top",
    "top-start",
    "top-end",
    "left",
    "left-start",
    "left-end",
    "right",
    "right-start",
    "right-end",
)

ITEMS_SIMPLE = [
    {"key": "a", "label": "Item A"},
    {"key": "b", "label": "Item B"},
    {"key": "c", "label": "Item C"},
]

FILE_ITEMS = [
    {
        "key": "new",
        "label": "New file",
        "description": "Create a new file",
        "shortcut": "Ctrl+N",
        "start_content": "heroicons--information-circle-solid",
    },
    {
        "key": "copy",
        "label": "Copy link",
        "description": "Copy the public link",
        "shortcut": "Ctrl+C",
        "start_content": "lucide--copy",
    },
    {
        "key": "share",
        "label": "Share file",
        "shortcut": "Ctrl+S",
        "start_content": "icon-park-outline--share",
        "show_divider": True,
    },
    {
        "key": "delete",
        "label": "Delete file",
        "description": "Permanently remove",
        "shortcut": "Ctrl+D",
        "start_content": "material-symbols--delete-outline",
        "color": "danger",
    },
]


def _dd(label: str, *, items=None, **kw) -> Dropdown:
    """造一个带 Button 触发器的 Dropdown；触发器变体 / 配色 / 尺寸跟随菜单。"""
    v = kw.get("variant", "solid")
    return Dropdown(
        trigger=Button(
            label,
            # Button 没有 shadow 变体（菜单有），触发器回落到 solid
            variant=v if v in Button.VALID_VARIANTS else "solid",
            color=kw.get("color", "default"),
            size=kw.get("size", "md"),
        ),
        items=ITEMS_SIMPLE if items is None else items,
        **kw,
    )


class DropdownDemo(DemoBase):
    component_name = "Dropdown"

    def build_content(self, layout, labels_bag: list):
        # ============================================================
        # 1) 基础：默认触发器（默认 default / solid / md / md / transparent）
        # ============================================================
        dd_basic = Dropdown(items=ITEMS_SIMPLE)
        dd_basic.action.connect(lambda key: print(f"[basic] action: {key}"))
        self.add_section(
            layout,
            "基础（默认触发器，弹出层高度由内容撑开）",
            [dd_basic],
            labels_bag,
        )

        # ============================================================
        # 2) 6 colors × 6 variants 全排列（36 组）
        # ============================================================
        self.add_section_vertical(
            layout,
            "6 colors × 6 variants 全排列（触发器与菜单同变体同配色，single 预选第二项）",
            [],
            labels_bag,
        )
        for v in VARIANTS:
            row = [
                _dd(
                    c,
                    variant=v,
                    color=c,
                    selection_mode="single",
                    default_selected_keys={"b"},
                )
                for c in COLORS
            ]
            self.add_section_grid(
                layout, f"variant = {v}", row, labels_bag, cols=6, spacing=10
            )

        # ============================================================
        # 3) 3 种尺寸
        # ============================================================
        sizes_row = [_dd(f"size {s}", size=s, color="primary") for s in SIZES]
        self.add_section(layout, "3 sizes（触发器与菜单同步）", sizes_row, labels_bag)

        # ============================================================
        # 4) 5 种圆角（菜单项与浮层同步；full 时浮层退化为 lg）
        # ============================================================
        radius_row = [
            _dd(
                f"radius {r}",
                radius=r,
                color="secondary",
                selection_mode="single",
                default_selected_keys={"b"},
            )
            for r in RADII
        ]
        self.add_section(
            layout, "5 radius（none / sm / md / lg / full）", radius_row, labels_bag
        )

        # ============================================================
        # 5) 浮层阴影
        # ============================================================
        shadow_row = [_dd(f"shadow {s}", shadow=s) for s in SHADOWS]
        self.add_section(
            layout, "4 shadow（none / sm / md / lg）", shadow_row, labels_bag
        )

        # ============================================================
        # 6) 浮层遮罩
        # ============================================================
        backdrop_row = [_dd(f"backdrop {b}", backdrop=b) for b in BACKDROPS]
        self.add_section(
            layout,
            "3 backdrop（transparent / opaque / blur）",
            backdrop_row,
            labels_bag,
        )

        # ============================================================
        # 7) 图标 / 描述 / 快捷键 / 单项配色（传入 max_height → 固定高度并滚动）
        # ============================================================
        dd_rich = Dropdown(
            trigger=Button("File", variant="flat"),
            items=FILE_ITEMS,
            variant="flat",
            max_height=160,
        )
        dd_rich.action.connect(lambda key: print(f"[rich] action: {key}"))
        self.add_section(
            layout,
            "图标 + 描述 + 快捷键 + 单项 danger 配色（max_height=160 → 滚动）",
            [dd_rich],
            labels_bag,
        )

        # ============================================================
        # 8) 点击后不关闭（单项 close_on_select=False，适合筛选）
        # ============================================================
        dd_stay = Dropdown(
            trigger=Button("筛选（不关闭）", variant="bordered"),
            items=[
                {"key": "all", "label": "All", "close_on_select": False},
                {"key": "image", "label": "Images", "close_on_select": False},
                {"key": "video", "label": "Videos", "close_on_select": False},
                {"key": "doc", "label": "Documents", "close_on_select": False},
            ],
            variant="bordered",
            selection_mode="multiple",
            default_selected_keys={"all", "image"},
        )
        dd_stay.selection_changed.connect(
            lambda keys: print(f"[stay] selection: {sorted(keys)}")
        )
        self.add_section(layout, "点击不关闭 + 多选勾选态", [dd_stay], labels_bag)

        # ============================================================
        # 9) 分组菜单
        # ============================================================
        dd_group = Dropdown(
            trigger=Button("分组菜单", variant="bordered"), variant="bordered"
        )
        sec_style = dd_group.add_section("Styles", show_divider=True)
        sec_style.add_item("Bold", key="bold", shortcut="Ctrl+B")
        sec_style.add_item("Italic", key="italic", shortcut="Ctrl+I")
        sec_align = dd_group.add_section("Align")
        sec_align.add_item("Left", key="left")
        sec_align.add_item("Center", key="center")
        dd_group.add_item("Reset", key="reset", color="danger")
        dd_group.action.connect(lambda key: print(f"[group] action: {key}"))
        self.add_section(
            layout, "分组菜单（add_section / add_item）", [dd_group], labels_bag
        )

        # ============================================================
        # 10) 选中模式
        # ============================================================
        dd_single = Dropdown(
            trigger=Button("单选", variant="bordered"),
            items=[("md", "Markdown"), ("html", "HTML"), ("txt", "Plain text")],
            variant="bordered",
            selection_mode="single",
            default_selected_keys={"md"},
        )
        dd_single.selection_changed.connect(
            lambda key: print(f"[single] selection: {key}")
        )
        dd_multi = Dropdown(
            trigger=Button("多选", variant="bordered"),
            items=[("red", "Red"), ("green", "Green"), ("blue", "Blue")],
            variant="bordered",
            selection_mode="multiple",
            default_selected_keys={"red", "blue"},
        )
        dd_multi.selection_changed.connect(
            lambda keys: print(f"[multi] selection: {sorted(keys)}")
        )
        dd_no_icon = Dropdown(
            trigger=Button("隐藏对勾", variant="bordered"),
            items=[("red", "Red"), ("green", "Green")],
            variant="bordered",
            selection_mode="multiple",
            default_selected_keys={"red"},
            hide_selected_icon=True,
        )
        self.add_section(
            layout,
            "选中模式（single / multiple / hide_selected_icon）",
            [dd_single, dd_multi, dd_no_icon],
            labels_bag,
        )

        # ============================================================
        # 11) 禁用项 / 整体禁用
        # ============================================================
        dd_disabled = Dropdown(
            trigger=Button("含禁用项", variant="bordered"),
            variant="bordered",
            items=[
                {"key": "on", "label": "Enabled"},
                {"key": "off", "label": "Disabled", "is_disabled": True},
                {"key": "more", "label": "Also enabled"},
            ],
        )
        dd_off = Dropdown(
            trigger=Button("整体禁用", variant="bordered"),
            items=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}],
            variant="bordered",
            is_disabled=True,
        )
        self.add_section(
            layout, "禁用（单项 / 整体）", [dd_disabled, dd_off], labels_bag
        )

        # ============================================================
        # 12) 12 种浮层方位
        # ============================================================
        placement_grid = [_dd(p, placement=p, color="primary") for p in PLACEMENTS]
        self.add_section_grid(
            layout,
            "12 placements",
            placement_grid,
            labels_bag,
            cols=4,
            spacing=12,
        )

        # ============================================================
        # 13) 非按钮触发器（任意 QWidget）
        # ============================================================
        custom = QWidget()
        custom_l = QHBoxLayout(custom)
        custom_l.setContentsMargins(10, 4, 10, 4)
        custom_l.setSpacing(6)
        custom_l.addWidget(Subtitle("更多操作"))
        dd_custom = Dropdown(
            trigger=custom,
            items=[
                {"key": "rename", "label": "Rename"},
                {"key": "remove", "label": "Remove"},
            ],
        )
        dd_custom.action.connect(lambda key: print(f"[custom] action: {key}"))
        self.add_section(
            layout, "非按钮触发器（任意 QWidget）", [dd_custom], labels_bag
        )

        # ============================================================
        # 14) 菜单附加内容 / 空菜单
        # ============================================================
        dd_extra = Dropdown(
            trigger=Button("账户", variant="bordered"),
            variant="bordered",
            items=[
                {"key": "profile", "label": "Profile"},
                {"key": "settings", "label": "Settings"},
            ],
            top_content=Body("jerry@example.com"),
            bottom_content=Caption("v0.8.1"),
        )
        dd_empty = Dropdown(
            trigger=Button("空菜单", variant="bordered"),
            variant="bordered",
            items=[],
            empty_content="暂无可操作项",
        )
        self.add_section(layout, "附加内容 / 空菜单", [dd_extra, dd_empty], labels_bag)


if __name__ == "__main__":
    DropdownDemo.run()
