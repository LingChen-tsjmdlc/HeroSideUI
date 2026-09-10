"""TimeInput 组件演示。

分节顺序对齐官方 HeroUI TimeInput 文档：
  Usage / Disabled / Read Only / Required / Variants / Label Placements /
  Start & End Content / With Description / With Error Message / Controlled /
  Time Zones / Granularity / Min Time And Max Time / Hide Time Zone /
  Hourly Cycle。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import (
    Body,
    TimeInput,
    now,
    parse_zoned_datetime,
)
from hero_side_ui.components.date_input._value import parse_datetime
from hero_side_ui.themes import (
    VALID_DATE_INPUT_SIZES,
    VALID_DATE_INPUT_VARIANTS,
)

MORNING = parse_datetime("2024-04-04T09:30:00")
EVENING = parse_datetime("2024-04-04T18:45:00")

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


def _fmt_time(v) -> str:
    """值的简短显示：hh:mm。"""
    if v is None:
        return "--:--"
    return f"{v.hour:02d}:{v.minute:02d}"


class TimeInputDemo(DemoBase):
    component_name = "TimeInput"

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
        layout.addWidget(self._row(TimeInput(label="Event time")))

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用"))
        layout.addWidget(
            self._row(TimeInput(label="Event time", value=MORNING, is_disabled=True))
        )

        # ---------- Read Only ----------
        layout.addWidget(self._section_title("Read Only 只读"))
        layout.addWidget(
            self._row(TimeInput(label="Event time", value=MORNING, is_readonly=True))
        )

        # ---------- Required ----------
        layout.addWidget(self._section_title("Required 必填"))
        layout.addWidget(
            self._row(TimeInput(label="Event time", is_required=True))
        )

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._col(
                *[
                    TimeInput(label="Event time", variant=v)
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
                        TimeInput(
                            label=color,
                            color=color,
                            variant=variant,
                            value=MORNING,
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
                    TimeInput(
                        label=size, size=size, value=MORNING, full_width=False
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
                    TimeInput(
                        label=radius,
                        radius=radius,
                        value=MORNING,
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
                    TimeInput(
                        label="Event time",
                        label_placement=p,
                        description=p,
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
                TimeInput(
                    label="Event time",
                    label_placement="outside",
                    value=MORNING,
                    start_content="heroicons--clock",
                ),
                TimeInput(
                    label="Event time",
                    label_placement="outside",
                    value=MORNING,
                    end_content="heroicons--clock",
                ),
            )
        )

        # ---------- With Description ----------
        layout.addWidget(self._section_title("With Description 描述文本"))
        layout.addWidget(
            self._row(
                TimeInput(
                    label="Event time",
                    description="Please enter the event start time.",
                )
            )
        )

        # ---------- With Error Message ----------
        layout.addWidget(self._section_title("With Error Message 错误提示"))
        layout.addWidget(
            self._row(
                TimeInput(
                    label="Event time",
                    is_invalid=True,
                    error_message="Please enter a valid time.",
                )
            )
        )

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控"))
        controlled = TimeInput(
            label="Time (controlled)", variant="bordered", value=MORNING
        )
        selected = Body(f"Selected time: {_fmt_time(MORNING)}")

        def _on_change(value):
            selected.setText(f"Selected time: {_fmt_time(value)}")

        controlled.value_changed.connect(_on_change)
        layout.addWidget(
            self._row(
                self._col(controlled, selected, spacing=6),
                TimeInput(
                    label="Time (uncontrolled)",
                    variant="bordered",
                    value=MORNING,
                ),
            )
        )

        # ---------- Time Zones ----------
        layout.addWidget(self._section_title("Time Zones 时区"))
        layout.addWidget(
            self._row(
                TimeInput(
                    label="Event time",
                    label_placement="outside",
                    value=parse_zoned_datetime(
                        "2022-11-07T00:45[America/Los_Angeles]"
                    ),
                ),
                TimeInput(
                    label="Event time",
                    label_placement="outside",
                    placeholder_value=now("America/New_York"),
                ),
            )
        )

        # ---------- Granularity ----------
        layout.addWidget(self._section_title("Granularity 粒度"))
        layout.addWidget(
            self._col(
                TimeInput(label="Hour", granularity="hour", value=EVENING),
                TimeInput(label="Minute", value=EVENING),
                TimeInput(label="Second", granularity="second", value=EVENING),
                TimeInput(label="Second (empty)", granularity="second"),
                spacing=16,
            )
        )

        # ---------- Min Time And Max Time ----------
        layout.addWidget(
            self._section_title("Min Time And Max Time 时刻范围")
        )
        layout.addWidget(
            self._row(
                self._captioned(
                    "Min time 09:00",
                    TimeInput(
                        label="Event time",
                        value=parse_datetime("2024-04-04T08:00:00"),
                        min_value=parse_datetime("2000-01-01T09:00:00"),
                    ),
                ),
                self._captioned(
                    "Max time 18:00",
                    TimeInput(
                        label="Event time",
                        value=parse_datetime("2024-04-04T20:00:00"),
                        max_value=parse_datetime("2000-01-01T18:00:00"),
                    ),
                ),
            )
        )

        # ---------- Hide Time Zone ----------
        layout.addWidget(self._section_title("Hide Time Zone 隐藏时区"))
        layout.addWidget(
            self._row(
                TimeInput(
                    label="Event time",
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
                TimeInput(
                    label="Event time (24h)",
                    hour_cycle=24,
                    value=MORNING,
                ),
                TimeInput(
                    label="Event time (12h)",
                    hour_cycle=12,
                    value=MORNING,
                ),
            )
        )


if __name__ == "__main__":
    TimeInputDemo.run()
