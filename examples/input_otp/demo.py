"""InputOtp 组件演示。

分节顺序对齐官方 HeroUI InputOtp 文档：
  Usage / Variants / Colors / Sizes / Radius / Length / Description /
  ErrorMessage / ReadOnly / Disabled / Password / TextAlign / Invalid
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, Button, InputOtp
from hero_side_ui.themes import (
    VALID_INPUT_OTP_RADII,
    VALID_INPUT_OTP_SIZES,
    VALID_INPUT_OTP_VARIANTS,
)

DEMO_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")


class InputOtpDemo(DemoBase):
    component_name = "InputOtp"

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
        layout.addWidget(self._section_title("Usage 基础用法（输入满 4 位触发 completed）"))
        usage = InputOtp(length=4, color="primary", description="输入验证码")
        completed_label = Body("completed: -")
        usage.completed.connect(lambda v: completed_label.setText(f"completed: {v}"))
        layout.addWidget(self._row(usage, completed_label))

        # ---------- Variants ----------
        layout.addWidget(self._section_title("Variants 变体"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(v, InputOtp(length=4, variant=v, color="primary"))
                    for v in VALID_INPUT_OTP_VARIANTS
                ]
            )
        )

        # ---------- Colors ----------
        layout.addWidget(self._section_title("Colors 颜色"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(c, InputOtp(length=4, color=c))
                    for c in DEMO_COLORS
                ]
            )
        )

        # ---------- Sizes ----------
        layout.addWidget(self._section_title("Sizes 尺寸"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(s, InputOtp(length=4, size=s, color="primary"))
                    for s in VALID_INPUT_OTP_SIZES
                ]
            )
        )

        # ---------- Radius ----------
        layout.addWidget(self._section_title("Radius 圆角"))
        layout.addWidget(
            self._row(
                *[
                    self._captioned(r, InputOtp(length=4, radius=r, color="primary"))
                    for r in VALID_INPUT_OTP_RADII
                ]
            )
        )

        # ---------- Length ----------
        layout.addWidget(self._section_title("Length 段数"))
        layout.addWidget(
            self._row(
                self._captioned("length=4", InputOtp(length=4)),
                self._captioned("length=6", InputOtp(length=6)),
            )
        )

        # ---------- ErrorMessage ----------
        layout.addWidget(self._section_title("ErrorMessage 错误态（isInvalid + errorMessage）"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "invalid",
                    InputOtp(
                        length=4,
                        color="primary",
                        is_invalid=True,
                        error_message="验证码错误，请重试",
                    ),
                )
            )
        )

        # ---------- ReadOnly / Disabled ----------
        layout.addWidget(self._section_title("ReadOnly / Disabled"))
        layout.addWidget(
            self._row(
                self._captioned("readOnly", InputOtp(length=4, value="12", is_read_only=True)),
                self._captioned("disabled", InputOtp(length=4, value="34", is_disabled=True)),
            )
        )

        # ---------- Password ----------
        layout.addWidget(self._section_title("Password 密码模式（type=password）"))
        layout.addWidget(
            self._row(
                self._captioned(
                    "password",
                    InputOtp(length=4, value="1234", type="password", color="primary"),
                )
            )
        )

        # ---------- TextAlign ----------
        layout.addWidget(self._section_title("TextAlign 对齐"))
        layout.addWidget(
            self._row(
                self._captioned("left", InputOtp(length=4, text_align="left", value="12")),
                self._captioned("center", InputOtp(length=4, text_align="center", value="12")),
                self._captioned("right", InputOtp(length=4, text_align="right", value="12")),
            )
        )


if __name__ == "__main__":
    InputOtpDemo.run()
