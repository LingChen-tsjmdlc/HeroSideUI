"""DatePicker / DateRangePicker 组件演示。

以 DateInput 为基底，在首尾槽位注入日历图标按钮；点击按钮弹出 Calendar
（DateRangePicker 为 RangeCalendar，两次点击选起止），选择日期后写回输入框。分节顺序：

Usage / Range / Disabled / Read Only / Required / Variants / Colors /
Sizes / Radius / Label Placements / Selector Placement / Calendar Config /
Min & Max Date / Controlled。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import (
    Body,
    DatePicker,
    DateRangePicker,
    parse_date,
    today,
)
from hero_side_ui.themes import (
    VALID_DATE_INPUT_SIZES,
    VALID_DATE_INPUT_VARIANTS,
)

BIRTH_VALUE = parse_date("2000-01-01")

# 枚举一律从 themes token 取，不在 demo 里硬编码。
DEMO_COLORS = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
DEMO_RADII = ("none", "sm", "md", "lg", "full")


class DatePickerDemo(DemoBase):
    component_name = "DatePicker / DateRangePicker"

    def _row(self, *widgets, spacing=16):
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

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法"))
        layout.addWidget(
            self._row(DatePicker(label="Birth date", value=BIRTH_VALUE))
        )

        # ---------- Range ----------
        layout.addWidget(self._section_title("Range 范围选择（RangeCalendar 两次点击选起止）"))
        layout.addWidget(
            Body("DateRangePicker 内部使用 RangeCalendar：第一次点击选起点，第二次点击选终点，"
                 "两次点击之间 hover 实时预览高亮范围。")
        )
        layout.addWidget(
            self._row(
                DateRangePicker(
                    label="带初始范围",
                    start_value=parse_date("2024-04-01"),
                    end_value=parse_date("2024-04-10"),
                    full_width=False,
                ),
                DateRangePicker(
                    label="点击选择范围",
                    full_width=False,
                ),
            )
        )

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用"))
        layout.addWidget(
            self._row(
                DatePicker(label="Birth date", value=BIRTH_VALUE, is_disabled=True)
            )
        )

        # ---------- Read Only ----------
        layout.addWidget(self._section_title("Read Only 只读"))
        layout.addWidget(
            self._row(
                DatePicker(label="Birth date", value=BIRTH_VALUE, is_readonly=True)
            )
        )

        # ---------- Required ----------
        layout.addWidget(self._section_title("Required 必填"))
        layout.addWidget(
            self._row(
                DatePicker(label="Birth date", value=BIRTH_VALUE, is_required=True)
            )
        )

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._col(
                *[
                    DatePicker(
                        label="Birth date",
                        variant=v,
                        value=BIRTH_VALUE,
                    )
                    for v in VALID_DATE_INPUT_VARIANTS
                ]
            )
        )

        # ---------- Colors（HeroSideUI 扩展）----------
        layout.addWidget(self._section_title("Colors 颜色（HeroSideUI 扩展）"))
        for variant in VALID_DATE_INPUT_VARIANTS:
            layout.addWidget(Body(variant))
            layout.addWidget(
                self._row(
                    *[
                        DatePicker(
                            label=color,
                            color=color,
                            variant=variant,
                            value=BIRTH_VALUE,
                            full_width=False,
                        )
                        for color in DEMO_COLORS
                    ],
                    spacing=12,
                )
            )

        # ---------- Sizes（HeroSideUI 扩展）----------
        layout.addWidget(self._section_title("Sizes 尺寸（HeroSideUI 扩展）"))
        layout.addWidget(
            self._row(
                *[
                    DatePicker(
                        label=size,
                        size=size,
                        value=BIRTH_VALUE,
                        full_width=False,
                    )
                    for size in VALID_DATE_INPUT_SIZES
                ],
                spacing=12,
            )
        )

        # ---------- Radius（HeroSideUI 扩展）----------
        layout.addWidget(self._section_title("Radius 圆角（HeroSideUI 扩展）"))
        layout.addWidget(
            self._row(
                *[
                    DatePicker(
                        label=radius,
                        radius=radius,
                        value=BIRTH_VALUE,
                        full_width=False,
                    )
                    for radius in DEMO_RADII
                ],
                spacing=12,
            )
        )

        # ---------- Label Placements ----------
        layout.addWidget(self._section_title("Label Placements 标签位置"))
        layout.addWidget(
            self._col(
                *[
                    DatePicker(
                        label="Birth date",
                        label_placement=p,
                        value=BIRTH_VALUE,
                    )
                    for p in ("inside", "outside", "outside-left", "outside-top")
                ],
                spacing=16,
            )
        )

        # ---------- Selector Placement ----------
        layout.addWidget(
            self._section_title("Selector Placement 日历按钮位置")
        )
        layout.addWidget(
            self._row(
                DatePicker(
                    label="End (default)",
                    value=BIRTH_VALUE,
                    selector_button_placement="end",
                    full_width=False,
                ),
                DatePicker(
                    label="Start",
                    value=BIRTH_VALUE,
                    selector_button_placement="start",
                    full_width=False,
                ),
            )
        )

        # ---------- Calendar Config ----------
        layout.addWidget(self._section_title("Calendar Config 日历配置"))
        layout.addWidget(
            self._col(
                DatePicker(
                    label="Two months",
                    value=BIRTH_VALUE,
                    visible_months=2,
                ),
                DatePicker(
                    label="Month & year pickers",
                    value=BIRTH_VALUE,
                    show_month_and_year_pickers=True,
                    calendar_header_default_expanded=True,
                ),
                DatePicker(
                    label="Week starts Monday",
                    value=BIRTH_VALUE,
                    first_day_of_week="mon",
                ),
                spacing=12,
            )
        )

        # ---------- Min & Max Date ----------
        layout.addWidget(self._section_title("Min & Max Date 日期范围"))
        layout.addWidget(
            self._row(
                DatePicker(
                    label="Not before today",
                    value=today(),
                    min_value=today(),
                ),
                DatePicker(
                    label="Not after today",
                    value=today(),
                    max_value=today(),
                ),
            )
        )

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控"))
        controlled = DatePicker(label="Pick a date", value=BIRTH_VALUE)
        selected = Body("Selected date: 2000-01-01")

        def _on_change(value):
            if value is None:
                selected.setText("Selected date: --")
            else:
                selected.setText(f"Selected date: {value.format('y-MM-dd')}")

        controlled.value_changed.connect(_on_change)
        layout.addWidget(self._row(self._col(controlled, selected, spacing=6)))


if __name__ == "__main__":
    DatePickerDemo.run()
