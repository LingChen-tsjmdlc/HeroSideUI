"""DateInput 组件演示。

分节顺序对齐官方 HeroUI DateInput 文档：
  Usage / Disabled / Read Only / Required / Variants / Label Placements /
  Start & End Content / With Description / With Error Message / Controlled /
  Time Zones / Granularity / Min Date And Max Date / International Calendar /
  Hide Time Zone / Hourly Cycle。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import (
    Body,
    DateInput,
    now,
    parse_absolute_to_local,
    parse_date,
    parse_zoned_datetime,
    today,
)
from hero_side_ui.themes import (
    VALID_DATE_INPUT_SIZES,
    VALID_DATE_INPUT_VARIANTS,
)

BIRTH_PLACEHOLDER = parse_date("1995-11-06")

# 枚举一律从 themes token 取，不在 demo 里硬编码。
# HEROUI_COLORS 含 neutral（调色板色阶，非组件语义色），故显式列语义色；
# RADIUS 含 no/small/medium/large 别名且不含动态算的 full，故按主 key 列举后补 full。
DEMO_COLORS = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
DEMO_RADII = ("none", "sm", "md", "lg", "full")


class DateInputDemo(DemoBase):
    component_name = "DateInput"

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

    def _captioned(self, caption: str, widget: QWidget):
        return self._col(Body(caption), widget, spacing=6)

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法"))
        layout.addWidget(
            self._row(
                DateInput(label="Birth date", placeholder_value=BIRTH_PLACEHOLDER)
            )
        )

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Birth date",
                    value=parse_date("2024-04-04"),
                    is_disabled=True,
                )
            )
        )

        # ---------- Read Only ----------
        layout.addWidget(self._section_title("Read Only 只读"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Birth date",
                    value=parse_date("2024-04-04"),
                    is_readonly=True,
                )
            )
        )

        # ---------- Required ----------
        layout.addWidget(self._section_title("Required 必填"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Birth date",
                    placeholder_value=BIRTH_PLACEHOLDER,
                    is_required=True,
                )
            )
        )

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._col(
                *[
                    DateInput(
                        label="Birth date",
                        variant=v,
                        placeholder_value=BIRTH_PLACEHOLDER,
                    )
                    for v in VALID_DATE_INPUT_VARIANTS
                ]
            )
        )

        # ---------- Colors（HeroSideUI 扩展，官方文档无此分节）----------
        layout.addWidget(self._section_title("Colors 颜色（HeroSideUI 扩展）"))
        for variant in VALID_DATE_INPUT_VARIANTS:
            layout.addWidget(Body(variant))
            layout.addWidget(
                self._row(
                    *[
                        DateInput(
                            label=color,
                            color=color,
                            variant=variant,
                            value=parse_date("2024-04-04"),
                            full_width=False,
                        )
                        for color in DEMO_COLORS
                    ],
                    spacing=12,
                )
            )

        # ---------- Sizes（HeroSideUI 扩展，官方文档无此分节）----------
        layout.addWidget(self._section_title("Sizes 尺寸（HeroSideUI 扩展）"))
        layout.addWidget(
            self._row(
                *[
                    DateInput(
                        label=size,
                        size=size,
                        value=parse_date("2024-04-04"),
                        full_width=False,
                    )
                    for size in VALID_DATE_INPUT_SIZES
                ],
                spacing=12,
            )
        )

        # ---------- Radius（HeroSideUI 扩展，官方文档无此分节）----------
        layout.addWidget(self._section_title("Radius 圆角（HeroSideUI 扩展）"))
        layout.addWidget(
            self._row(
                *[
                    DateInput(
                        label=radius,
                        radius=radius,
                        value=parse_date("2024-04-04"),
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
                    DateInput(
                        label="Birth date",
                        label_placement=p,
                        description=p,
                        placeholder_value=BIRTH_PLACEHOLDER,
                    )
                    for p in ("inside", "outside", "outside-left", "outside-top")
                ],
                spacing=16,
            )
        )

        # ---------- Start & End Content ----------
        layout.addWidget(self._section_title("Start & End Content 首尾内容"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Date Input",
                    label_placement="outside",
                    value=parse_date("2024-04-04"),
                    start_content="solar--calendar-bold",
                ),
                DateInput(
                    label="Date Input",
                    label_placement="outside",
                    value=parse_date("2024-04-04"),
                    end_content="solar--calendar-bold",
                ),
            )
        )

        # ---------- With Description ----------
        layout.addWidget(self._section_title("With Description 描述文本"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Birth date",
                    placeholder_value=BIRTH_PLACEHOLDER,
                    description="This is my birth date.",
                )
            )
        )

        # ---------- With Error Message ----------
        layout.addWidget(self._section_title("With Error Message 错误提示"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Birth date",
                    placeholder_value=BIRTH_PLACEHOLDER,
                    is_invalid=True,
                    error_message="Please enter a valid date.",
                )
            )
        )

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控"))
        controlled = DateInput(
            label="Date (controlled)",
            variant="bordered",
            value=parse_date("2024-04-04"),
        )
        selected = Body("Selected date: 2024-04-04")

        def _on_change(value):
            if value is None:
                selected.setText("Selected date: --")
            else:
                selected.setText(f"Selected date: {value.format('yMMMMd')}")

        controlled.value_changed.connect(_on_change)
        layout.addWidget(
            self._row(
                self._col(controlled, selected, spacing=6),
                DateInput(
                    label="Date (uncontrolled)",
                    variant="bordered",
                    value=parse_date("2024-04-04"),
                ),
            )
        )

        # ---------- Time Zones ----------
        layout.addWidget(self._section_title("Time Zones 时区"))
        layout.addWidget(
            self._col(
                DateInput(
                    label="Event date",
                    label_placement="outside",
                    granularity="minute",
                    value=parse_zoned_datetime(
                        "2022-11-07T00:45[America/Los_Angeles]"
                    ),
                ),
                DateInput(
                    label="Event date",
                    label_placement="outside",
                    granularity="minute",
                    value=parse_absolute_to_local("2021-11-07T07:45:00Z"),
                ),
                spacing=16,
            )
        )

        # ---------- Granularity ----------
        layout.addWidget(self._section_title("Granularity 粒度"))
        granularity_value = parse_absolute_to_local("2021-04-07T18:45:22Z")
        layout.addWidget(
            self._col(
                DateInput(
                    label="Date and time",
                    granularity="second",
                    value=granularity_value,
                ),
                DateInput(label="Date", granularity="day", value=granularity_value),
                DateInput(label="Event date", granularity="second"),
                DateInput(
                    label="Event date",
                    granularity="second",
                    placeholder_value=now("America/New_York"),
                ),
                spacing=16,
            )
        )

        # ---------- Min Date And Max Date ----------
        layout.addWidget(self._section_title("Min Date And Max Date 日期范围"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "Min date",
                    DateInput(
                        label="Date and time",
                        value=parse_date(_shift_today(-1)),
                        min_value=today(),
                    ),
                ),
                self._captioned(
                    "Max date",
                    DateInput(
                        label="Date and time",
                        value=parse_date(_shift_today(1)),
                        max_value=today(),
                    ),
                ),
            )
        )

        # ---------- International Calendar ----------
        layout.addWidget(self._section_title("International Calendar 国际历法"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Appointment date",
                    locale="hi_IN",
                    calendar="indian",
                    value=parse_absolute_to_local("2021-04-07T18:45:22Z"),
                )
            )
        )

        # ---------- Hide Time Zone ----------
        layout.addWidget(self._section_title("Hide Time Zone 隐藏时区"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Appointment time",
                    granularity="minute",
                    hide_time_zone=True,
                    value=parse_zoned_datetime(
                        "2022-11-07T00:45[America/Los_Angeles]"
                    ),
                )
            )
        )

        # ---------- Hourly Cycle ----------
        layout.addWidget(self._section_title("Hourly Cycle 小时制"))
        layout.addWidget(
            self._row(
                DateInput(
                    label="Appointment time",
                    granularity="minute",
                    hour_cycle=24,
                    value=parse_zoned_datetime(
                        "2022-11-07T00:45[America/Los_Angeles]"
                    ),
                )
            )
        )


def _shift_today(days: int) -> str:
    """返回相对今天偏移若干天的 ISO 日期串。"""
    d = today().date.add(days=days)
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


if __name__ == "__main__":
    DateInputDemo.run()
