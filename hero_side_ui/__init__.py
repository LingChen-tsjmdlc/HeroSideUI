"""
HeroSideUI - PySide6 component library inspired by HeroUI v2
"""

__version__ = "0.2.0"

from .core import ThemeProvider, ScrollStyle, SmoothScroll, StatePalette

from .components import (
    Button, Accordion, AccordionItem, Input, Textarea, Divider,
    Card, CardHeader, CardBody, CardFooter,
    Checkbox, CheckboxGroup,
    Progress, CircularProgress, Spinner,
    Popover, PopoverContent,
    Tooltip,
    Tabs, TabItem,
    ThemeSwitcher,
    Text, Title, Subtitle, Caption, Body,
    Switch,
    ScrollShadow,
    Listbox, ListboxItem, ListboxSection,
    Autocomplete, AutocompleteItem, AutocompleteSection,
)

__all__ = [
    "ThemeProvider", "ScrollStyle", "SmoothScroll", "StatePalette",
    "Button", "Accordion", "AccordionItem", "Input", "Textarea",
    "Divider",
    "Card", "CardHeader", "CardBody", "CardFooter",
    "Checkbox", "CheckboxGroup",
    "Progress", "CircularProgress", "Spinner",
    "Popover", "PopoverContent",
    "Tooltip",
    "Tabs", "TabItem",
    "ThemeSwitcher",
    "Text", "Title", "Subtitle", "Caption", "Body",
    "Switch",
    "ScrollShadow",
    "Listbox", "ListboxItem", "ListboxSection",
    "Autocomplete", "AutocompleteItem", "AutocompleteSection",
]
