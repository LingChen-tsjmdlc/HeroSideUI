"""
HeroUI v2 组件尺寸系统 (Component Sizes)

每个组件的尺寸配置拆分到独立子模块。新增组件时在本文件夹新建一个 `<component>.py`,
并在这里 re-export 对应的 XXX_SIZES / XXX_SHADOWS 即可。

保持向后兼容:
    from hero_side_ui.themes.sizes import BUTTON_SIZES, INPUT_SIZES, ...
"""

from .button import BUTTON_SIZES
from .accordion import ACCORDION_SIZES
from .input import INPUT_SIZES
from .divider import DIVIDER_SIZES
from .card import CARD_SHADOWS

__all__ = [
    "BUTTON_SIZES",
    "ACCORDION_SIZES",
    "INPUT_SIZES",
    "DIVIDER_SIZES",
    "CARD_SHADOWS",
]
