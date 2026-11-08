"""
HeroSideUI 核心基础设施
"""

from .font_provider import FontProvider, make_qfont
from .provider import HeroSideUIProvider
from .scroll_style import ScrollStyle
from .smooth_scroll import SmoothScroll
from .state_palette import StatePalette
from .text_style import (
    DEFAULT_TEXT_COLORS,
    SIZE_MAP,
    WEIGHT_MAP,
    ColorInput,
    SizeInput,
    WeightInput,
    make_text_qfont,
    resolve_text_color,
    resolve_text_size,
    resolve_text_weight,
    selection_palette,
)
from .theme_provider import ThemeProvider

__all__ = [
    "DEFAULT_TEXT_COLORS",
    "SIZE_MAP",
    "WEIGHT_MAP",
    # text_style
    "ColorInput",
    "FontProvider",
    "HeroSideUIProvider",
    "ScrollStyle",
    "SizeInput",
    "SmoothScroll",
    "StatePalette",
    "ThemeProvider",
    "WeightInput",
    "make_qfont",
    "make_text_qfont",
    "resolve_text_color",
    "resolve_text_size",
    "resolve_text_weight",
    "selection_palette",
]
