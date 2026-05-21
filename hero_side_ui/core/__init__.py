"""
HeroSideUI 核心基础设施
"""

from .theme_provider import ThemeProvider
from .font_provider import FontProvider, make_qfont
from .scroll_style import ScrollStyle
from .smooth_scroll import SmoothScroll
from .state_palette import StatePalette
from .text_style import (
    ColorInput,
    SizeInput,
    WeightInput,
    SIZE_MAP,
    WEIGHT_MAP,
    DEFAULT_TEXT_COLORS,
    resolve_text_color,
    resolve_text_size,
    resolve_text_weight,
    make_text_qfont,
)

__all__ = [
    "ThemeProvider",
    "FontProvider",
    "make_qfont",
    "ScrollStyle",
    "SmoothScroll",
    "StatePalette",
    # text_style
    "ColorInput",
    "SizeInput",
    "WeightInput",
    "SIZE_MAP",
    "WEIGHT_MAP",
    "DEFAULT_TEXT_COLORS",
    "resolve_text_color",
    "resolve_text_size",
    "resolve_text_weight",
    "make_text_qfont",
]
