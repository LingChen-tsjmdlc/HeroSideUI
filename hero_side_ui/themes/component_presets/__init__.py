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
from .date_input import (
    DATE_INPUT_SIZES,
    VALID_DATE_INPUT_LABEL_PLACEMENTS,
    VALID_DATE_INPUT_SIZES,
    VALID_DATE_INPUT_VARIANTS,
)
from .textarea import TEXTAREA_SIZES
from .divider import DIVIDER_SIZES
from .card import CARD_SHADOWS
from .checkbox import CHECKBOX_SIZES
from .progress import PROGRESS_SIZES, CIRCULAR_PROGRESS_SIZES
from .spinner import SPINNER_SIZES
from .popover import POPOVER_SHADOWS
from .tooltip import TOOLTIP_SIZES
from .tabs import TABS_SIZES
from .switch import SWITCH_SIZES
from .listbox import LISTBOX_SIZES
from .autocomplete import AUTOCOMPLETE_SIZES
from .select import SELECT_SIZES
from .slider import SLIDER_SIZES
from .radio import RADIO_SIZES
from .pagination import PAGINATION_SIZES
from .table import TABLE_SIZES
from .calendar import CALENDAR_SIZES
from .image import IMAGE_SHADOWS
from .chip import (
    CHIP_SIZES,
    CHIP_DOT_SIZE,
    VALID_CHIP_SIZES,
    VALID_CHIP_VARIANTS,
    VALID_CHIP_RADII,
)
from .avatar import (
    AVATAR_SIZES,
    AVATAR_RING_WIDTH,
    AVATAR_RING_OFFSET,
    AVATAR_GROUP_OVERLAP,
    AVATAR_GROUP_HOVER_SHIFT,
    AVATAR_GROUP_GRID_GAP,
    AVATAR_GROUP_GRID_COLS,
    VALID_AVATAR_SIZES,
    VALID_AVATAR_COLORS,
    VALID_AVATAR_RADII,
)
from .kbd import (
    KBD_SIZES,
    KBD_SIZE_TABLE,
    VALID_KBD_SIZES,
    VALID_KBD_RADII,
    KBD_SHADOW,
)
from .link import (
    LINK_SIZES,
    VALID_LINK_SIZES,
    VALID_LINK_COLORS,
    VALID_LINK_UNDERLINES,
    LINK_OPACITY,
    LINK_BLOCK,
    LINK_OPACITY_DURATION,
)
from .markdown import (
    HEADING_SPEC,
    MARKDOWN_SPACING,
    MARKDOWN_LIST,
    MARKDOWN_QUOTE,
    MARKDOWN_INLINE_CODE,
)
from .code_block import CODE_BLOCK_SPEC, CODE_BLOCK_SYNTAX

__all__ = [
    "BUTTON_SIZES",
    "ACCORDION_SIZES",
    "INPUT_SIZES",
    "DATE_INPUT_SIZES",
    "VALID_DATE_INPUT_SIZES",
    "VALID_DATE_INPUT_VARIANTS",
    "VALID_DATE_INPUT_LABEL_PLACEMENTS",
    "TEXTAREA_SIZES",
    "DIVIDER_SIZES",
    "CARD_SHADOWS",
    "CHECKBOX_SIZES",
    "PROGRESS_SIZES",
    "CIRCULAR_PROGRESS_SIZES",
    "SPINNER_SIZES",
    "POPOVER_SHADOWS",
    "TOOLTIP_SIZES",
    "TABS_SIZES",
    "SWITCH_SIZES",
    "LISTBOX_SIZES",
    "AUTOCOMPLETE_SIZES",
    "SELECT_SIZES",
    "SLIDER_SIZES",
    "RADIO_SIZES",
    "PAGINATION_SIZES",
    "TABLE_SIZES",
    "CALENDAR_SIZES",
    "IMAGE_SHADOWS",
    "CHIP_SIZES",
    "CHIP_DOT_SIZE",
    "VALID_CHIP_SIZES",
    "VALID_CHIP_VARIANTS",
    "VALID_CHIP_RADII",
    "AVATAR_SIZES",
    "AVATAR_RING_WIDTH",
    "AVATAR_RING_OFFSET",
    "AVATAR_GROUP_OVERLAP",
    "AVATAR_GROUP_HOVER_SHIFT",
    "AVATAR_GROUP_GRID_GAP",
    "AVATAR_GROUP_GRID_COLS",
    "VALID_AVATAR_SIZES",
    "VALID_AVATAR_COLORS",
    "VALID_AVATAR_RADII",
    "KBD_SIZES",
    "KBD_SIZE_TABLE",
    "VALID_KBD_SIZES",
    "VALID_KBD_RADII",
    "KBD_SHADOW",
    "LINK_SIZES",
    "VALID_LINK_SIZES",
    "VALID_LINK_COLORS",
    "VALID_LINK_UNDERLINES",
    "LINK_OPACITY",
    "LINK_BLOCK",
    "LINK_OPACITY_DURATION",
    "HEADING_SPEC",
    "MARKDOWN_SPACING",
    "MARKDOWN_LIST",
    "MARKDOWN_QUOTE",
    "MARKDOWN_INLINE_CODE",
    "CODE_BLOCK_SPEC",
    "CODE_BLOCK_SYNTAX",
]
