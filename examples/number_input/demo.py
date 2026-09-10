"""NumberInput 组件演示。

分节顺序对齐官方 HeroUI NumberInput 文档：
  Usage / Disabled / Read Only / Required / Variants / Label Placements /
  Start & End Content / With Description / With Error Message / Controlled /
  Min & Max Values / Step / Hide Steppers / Format Options。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, NumberInput
from hero_side_ui.themes import (
    VALID_DATE_INPUT_LABEL_PLACEMENTS,
    VALID_DATE_INPUT_SIZES,
    VALID_DATE_INPUT_VARIANTS,
)

# 枚举一律从 themes token 取，不在 demo 里硬编码（Input 家族共用同一组 token）。
DEMO_COLORS = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
DEMO_RADII = ("none", "sm", "md", "lg", "full")


def _fmt_num(v) -> str:
    """值的简短显示：None 显示 --。"""
    if v is None:
        return "--"
    text = f"{v:,.10f}".rstrip("0").rstrip(".")
    return text if text else "0"


class NumberInputDemo(DemoBase):
    component_name = "NumberInput"

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
        layout.addWidget(self._row(NumberInput(label="Amount")))

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用"))
        layout.addWidget(
            self._row(NumberInput(label="Amount", value=1024, is_disabled=True))
        )

        # ---------- Read Only ----------
        layout.addWidget(self._section_title("Read Only 只读"))
        layout.addWidget(
            self._row(NumberInput(label="Amount", value=2048, is_readonly=True))
        )

        # ---------- Required ----------
        layout.addWidget(self._section_title("Required 必填"))
        layout.addWidget(
            self._row(NumberInput(label="Amount", is_required=True))
        )

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._col(
                *[NumberInput(label="Amount", variant=v) for v in VALID_DATE_INPUT_VARIANTS]
            )
        )

        # ---------- Colors（HeroSideUI 扩展，官方文档无此分节）----------
        layout.addWidget(self._section_title("Colors 颜色（HeroSideUI 扩展）"))
        for variant in VALID_DATE_INPUT_VARIANTS:
            layout.addWidget(Body(variant))
            layout.addWidget(
                self._row(
                    *[
                        NumberInput(
                            label=color,
                            color=color,
                            variant=variant,
                            value=7.5,
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
                    NumberInput(
                        label=size, size=size, value=512, full_width=False
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
                    NumberInput(
                        label=radius,
                        radius=radius,
                        value=512,
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
                    NumberInput(
                        label="Amount",
                        label_placement=p,
                        description=p,
                    )
                    for p in VALID_DATE_INPUT_LABEL_PLACEMENTS
                ],
                spacing=16,
            )
        )

        # ---------- Start & End Content ----------
        layout.addWidget(self._section_title("Start & End Content 首尾内容"))
        layout.addWidget(
            self._row(
                NumberInput(
                    label="Duration",
                    label_placement="outside",
                    value=90,
                    start_content="heroicons--clock",
                ),
                NumberInput(
                    label="Duration",
                    label_placement="outside",
                    value=90,
                    end_content="heroicons--clock",
                ),
            )
        )

        # ---------- With Description ----------
        layout.addWidget(self._section_title("With Description 描述文本"))
        layout.addWidget(
            self._row(
                NumberInput(
                    label="Amount",
                    description="Enter the amount in USD.",
                )
            )
        )

        # ---------- With Error Message ----------
        layout.addWidget(self._section_title("With Error Message 错误提示"))
        layout.addWidget(
            self._row(
                NumberInput(
                    label="Amount",
                    is_invalid=True,
                    error_message="Please enter a valid amount.",
                )
            )
        )

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控"))
        controlled = NumberInput(
            label="Amount (controlled)", variant="bordered", value=10.5
        )
        selected = Body(f"Selected amount: {_fmt_num(10.5)}")

        def _on_change(value):
            selected.setText(f"Selected amount: {_fmt_num(value)}")

        controlled.value_changed.connect(_on_change)
        layout.addWidget(
            self._row(
                self._col(controlled, selected, spacing=6),
                NumberInput(
                    label="Amount (uncontrolled)",
                    variant="bordered",
                    value=33,
                ),
            )
        )

        # ---------- Min & Max Values ----------
        layout.addWidget(
            self._section_title("Min & Max Values 最小最大值")
        )
        layout.addWidget(
            self._row(
                self._captioned(
                    "Min 1000（越界 blur 夹取）",
                    NumberInput(
                        label="Price",
                        value=800,
                        min_value=1000,
                    ),
                ),
                self._captioned(
                    "Max 10000（越界 blur 夹取）",
                    NumberInput(
                        label="Price",
                        value=99999,
                        max_value=10000,
                    ),
                ),
            )
        )

        # ---------- Step ----------
        layout.addWidget(self._section_title("Step 步长"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "Step 0.5（滚轮 / 上下键 / 按钮）",
                    NumberInput(label="Progress", step=0.5),
                ),
                self._captioned(
                    "Step 10",
                    NumberInput(label="Quantity", step=10),
                ),
            )
        )

        # ---------- Hide Steppers ----------
        layout.addWidget(self._section_title("Hide Steppers 隐藏步进按钮"))
        layout.addWidget(
            self._row(
                NumberInput(
                    label="Amount", hide_stepper=True, description="仍可用上下键与滚轮步进"
                )
            )
        )

        # ---------- Format Options ----------
        layout.addWidget(self._section_title("Format Options 格式化"))
        layout.addWidget(
            self._col(
                NumberInput(
                    label="Percent",
                    label_placement="outside",
                    value=50,
                    format_options={"style": "percent"},
                ),
                NumberInput(
                    label="Currency (CNY)",
                    label_placement="outside",
                    value=1234.5,
                    format_options={"style": "currency", "currency": "CNY"},
                ),
                NumberInput(
                    label="Currency (USD, 2 位小数)",
                    label_placement="outside",
                    value=9.81,
                    format_options={"style": "currency", "currency": "USD"},
                ),
                NumberInput(
                    label="无千分位分组",
                    label_placement="outside",
                    value=1234567,
                    format_options={"use_grouping": False},
                ),
                NumberInput(
                    label="至少 2 位小数",
                    label_placement="outside",
                    value=3.1,
                    format_options={"minimum_fraction_digits": 2},
                ),
                spacing=16,
            )
        )


if __name__ == "__main__":
    NumberInputDemo.run()
