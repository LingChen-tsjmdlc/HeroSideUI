"""
HeroUI v2 组件级主题预设 (Component Presets)

此目录收纳每个组件独有的主题化配置 —— 尺寸规格 (XXX_SIZES)、阴影预设
(XXX_SHADOWS) 等。与 colors/fonts/radius 这类跨组件通用 design token
不同，这里的常量是"组件级"的：只服务单个组件的视觉规格。

命名约定：
  - 尺寸配置：<COMPONENT>_SIZES       如 BUTTON_SIZES / CHECKBOX_SIZES
  - 阴影配置：<COMPONENT>_SHADOWS     如 CARD_SHADOWS / POPOVER_SHADOWS
  - 其他变体：<COMPONENT>_<VARIANT>   按需扩展

新增组件时在本文件夹新建一个 `<component>.py`，并在下方 re-export。

使用方式：
    from hero_side_ui.themes.component_presets import BUTTON_SIZES, POPOVER_SHADOWS
    # 或从 themes 顶层直接取（推荐，themes/__init__.py 已 re-export）：
    from hero_side_ui.themes import BUTTON_SIZES
"""

from .button import BUTTON_SIZES
from .accordion import ACCORDION_SIZES
from .input import INPUT_SIZES
from .divider import DIVIDER_SIZES
from .card import CARD_SHADOWS
from .checkbox import CHECKBOX_SIZES
from .progress import PROGRESS_SIZES, CIRCULAR_PROGRESS_SIZES
from .popover import POPOVER_SHADOWS
from .tabs import TABS_SIZES

__all__ = [
    "BUTTON_SIZES",
    "ACCORDION_SIZES",
    "INPUT_SIZES",
    "DIVIDER_SIZES",
    "CARD_SHADOWS",
    "CHECKBOX_SIZES",
    "PROGRESS_SIZES",
    "CIRCULAR_PROGRESS_SIZES",
    "POPOVER_SHADOWS",
    "TABS_SIZES",
]
