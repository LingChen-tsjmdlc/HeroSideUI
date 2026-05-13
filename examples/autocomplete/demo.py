"""
Autocomplete 组件示例 — contains 过滤 / 受控 / 自定义 filter / 不同 variant / 主题切换
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Autocomplete
from _base import DemoBase


ANIMALS = [
    {"key": "cat",      "label": "Cat",      "description": "Small domestic feline"},
    {"key": "dog",      "label": "Dog",      "description": "Loyal companion"},
    {"key": "elephant", "label": "Elephant", "description": "Largest land animal"},
    {"key": "fox",      "label": "Fox",      "description": "Clever forest dweller"},
    {"key": "hedgehog", "label": "Hedgehog", "description": "Spiky small mammal"},
    {"key": "horse",    "label": "Horse",    "description": "Fast runner"},
    {"key": "lion",     "label": "Lion",     "description": "King of the jungle"},
    {"key": "monkey",   "label": "Monkey",   "description": "Clever primate"},
    {"key": "penguin",  "label": "Penguin",  "description": "Flightless swimmer"},
    {"key": "tiger",    "label": "Tiger",    "description": "Majestic striped cat"},
]

FRUITS = [
    ("apple", "Apple"), ("banana", "Banana"), ("blueberry", "Blueberry"),
    ("cherry", "Cherry"), ("durian", "Durian"), ("elderberry", "Elderberry"),
    ("fig", "Fig"), ("grape", "Grape"), ("kiwi", "Kiwi"), ("lemon", "Lemon"),
    ("mango", "Mango"), ("orange", "Orange"), ("papaya", "Papaya"), ("peach", "Peach"),
]


class AutocompleteDemo(DemoBase):
    component_name = "Autocomplete"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 基础 —— 默认 variant=flat, color=default
        # ============================================================
        ac_basic = Autocomplete(
            label="Favorite Animal",
            placeholder="Search an animal",
            items=ANIMALS,
        )
        ac_basic.selection_changed.connect(lambda k: print(f"[basic] selected: {k}"))
        ac_basic.input_changed.connect(lambda t: print(f"[basic] input: {t}"))
        ac_basic.setFixedWidth(300)
        self.add_section(layout, "基础 (默认 flat, contains 过滤)",
                         [ac_basic], labels_bag)

        # ============================================================
        # 2) 6 种颜色
        # ============================================================
        colors = []
        for c in ("default", "primary", "secondary", "success", "warning", "danger"):
            ac = Autocomplete(
                label=c.capitalize(),
                placeholder=f"Pick a fruit",
                items=FRUITS,
                color=c,
            )
            ac.setFixedWidth(260)
            colors.append(ac)
        self.add_section_grid(layout, "6 种颜色 (color 同时驱动 input + listbox 高亮)",
                              colors, labels_bag, cols=3, spacing=14)

        # ============================================================
        # 3) 4 种 variant
        # ============================================================
        variants = []
        for v in ("flat", "faded", "bordered", "underlined"):
            ac = Autocomplete(
                label=v.capitalize(),
                placeholder=f"Variant: {v}",
                items=FRUITS,
                variant=v,
                color="primary",
            )
            ac.setFixedWidth(260)
            variants.append(ac)
        self.add_section_grid(layout, "4 种 variant (flat / faded / bordered / underlined)",
                              variants, labels_bag, cols=4, spacing=14)

        # ============================================================
        # 4) 3 种 size
        # ============================================================
        sizes = []
        for s in ("sm", "md", "lg"):
            ac = Autocomplete(
                label=s.upper(),
                placeholder="Search",
                items=FRUITS,
                size=s,
                color="primary",
            )
            ac.setFixedWidth(300)
            sizes.append(ac)
        self.add_section(layout, "3 种尺寸 (sm / md / lg)", sizes, labels_bag, spacing=16)

        # ============================================================
        # 5) 自定义 filter: startsWith
        # ============================================================
        def starts_with(label: str, q: str) -> bool:
            return label.lower().startswith(q.lower()) if q else True

        ac_starts = Autocomplete(
            label="Starts-with 匹配",
            placeholder="只匹配开头",
            items=FRUITS,
            color="success",
            default_filter=starts_with,
        )
        ac_starts.setFixedWidth(260)

        # allows_custom_value: 允许用户输入列表外的值，blur 不回退
        ac_custom = Autocomplete(
            label="Allows custom value",
            placeholder="输入任意内容",
            items=FRUITS,
            color="secondary",
            allows_custom_value=True,
        )
        ac_custom.setFixedWidth(260)

        self.add_section(layout, "自定义 filter / allows_custom_value",
                         [ac_starts, ac_custom], labels_bag, spacing=20)

        # ============================================================
        # 6) disabled / invalid / required / readonly 状态
        # ============================================================
        ac_disabled = Autocomplete(
            label="Disabled",
            items=FRUITS,
            default_selected_key="apple",
            is_disabled=True,
        )
        ac_disabled.setFixedWidth(260)

        ac_invalid = Autocomplete(
            label="Invalid",
            items=FRUITS,
            is_invalid=True,
            color="danger",
            description="Please select a fruit",
        )
        ac_invalid.setFixedWidth(260)

        ac_required = Autocomplete(
            label="Required",
            items=FRUITS,
            is_required=True,
            color="warning",
        )
        ac_required.setFixedWidth(260)

        ac_readonly = Autocomplete(
            label="Read-only",
            items=FRUITS,
            default_selected_key="banana",
            is_readonly=True,
        )
        ac_readonly.setFixedWidth(260)

        self.add_section_grid(layout, "状态 (disabled / invalid / required / readonly)",
                              [ac_disabled, ac_invalid, ac_required, ac_readonly],
                              labels_bag, cols=4, spacing=14)

        # ============================================================
        # 7) disabled keys + 默认选中 + 空状态
        # ============================================================
        ac_disabled_keys = Autocomplete(
            label="Disabled items",
            items=FRUITS,
            disabled_keys={"durian", "fig"},
            color="primary",
            default_selected_key="apple",
        )
        ac_disabled_keys.setFixedWidth(260)

        # 空 items 演示默认空状态 (icon + 双语)
        ac_empty = Autocomplete(
            label="Empty",
            placeholder="暂时没有数据",
            items=[],
        )
        ac_empty.setFixedWidth(260)

        self.add_section(layout, "disabled keys / 空 items (默认 empty 占位)",
                         [ac_disabled_keys, ac_empty], labels_bag, spacing=20)


if __name__ == "__main__":
    AutocompleteDemo.run()
