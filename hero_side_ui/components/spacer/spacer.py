"""Spacer 间距填充器 — 零尺寸占位，靠 margin 撑出空白 (HeroUI v2)。

用法::

    layout.addWidget(Button("A"))
    layout.addWidget(Spacer(x=4))   # 横向 16px 间隔
    layout.addWidget(Button("B"))
"""

from __future__ import annotations

from typing import Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget

# Tailwind spacing scale（单位 ×4px；"px"=1px）
SPACING_SCALE = {
    "px": 1, 0: 0, 0.5: 2, 1: 4, 1.5: 6, 2: 8, 2.5: 10, 3: 12, 3.5: 14,
    4: 16, 5: 20, 6: 24, 7: 28, 8: 32, 9: 36, 10: 40, 11: 44, 12: 48,
    14: 56, 16: 64, 20: 80, 24: 96, 28: 112, 32: 128, 36: 144, 40: 160,
    44: 176, 48: 192, 52: 208, 56: 224, 60: 240, 64: 256, 72: 288,
    80: 320, 96: 384,
}

Space = Union[int, float, str]


def get_margin(value: Space) -> int:
    """spacing 档位转像素（数字按 scale 表，字符串按表键或原样像素）。"""
    if isinstance(value, str):
        if value in SPACING_SCALE:
            return int(SPACING_SCALE[value])
        return int(str(value).removesuffix("px"))
    return int(SPACING_SCALE.get(value, value))


class Spacer(QWidget):
    """间距填充器：零尺寸本体 + margin 撑出空白（官方 x/y spacing 档位）。"""

    def __init__(
        self,
        x: Space = 1,
        y: Space = 1,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroSpacer")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._x = x
        self._y = y
        self._apply()

    def _apply(self):
        # Qt 布局里 contentsMargins 不参与父布局几何——空白必须由本体尺寸
        # 撑出（官方 web 的 margin 语义在桌面端等价于 sizeHint）
        self.setFixedSize(get_margin(self._x), get_margin(self._y))

    def set_x(self, x: Space):
        """设置横向间距档位。"""
        self._x = x
        self._apply()

    def set_y(self, y: Space):
        """设置纵向间距档位。"""
        self._y = y
        self._apply()

    def x_space(self) -> Space:
        return self._x

    def y_space(self) -> Space:
        return self._y
