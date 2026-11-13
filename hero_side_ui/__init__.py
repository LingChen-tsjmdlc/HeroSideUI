"""
HeroSideUI - PySide6 component library inspired by HeroUI v2
"""

__version__ = "0.17.4"

from importlib import import_module
from typing import TYPE_CHECKING

from .core import (
    HeroSideUIProvider,
    ScrollStyle,
    SmoothScroll,
    StatePalette,
    ThemeProvider,
)

if TYPE_CHECKING:
    from .components import (
        Accordion,
        AccordionItem,
        Alert,
        Autocomplete,
        AutocompleteItem,
        AutocompleteSection,
        Avatar,
        AvatarGroup,
        Badge,
        Body,
        BreadcrumbItem,
        Breadcrumbs,
        Button,
        Calendar,
        CalendarDate,
        Caption,
        Card,
        CardBody,
        CardFooter,
        CardHeader,
        Checkbox,
        CheckboxGroup,
        Chip,
        CircularProgress,
        CodeBlock,
        CodeEditor,
        DateInput,
        DatePicker,
        DateRangePicker,
        DateTimeValue,
        Divider,
        Drawer,
        Dropdown,
        DropdownItem,
        DropdownSection,
        Icon,
        Image,
        Input,
        InputOtp,
        Kbd,
        Link,
        Listbox,
        ListboxItem,
        ListboxSection,
        Markdown,
        NumberInput,
        Pagination,
        Popover,
        PopoverContent,
        Progress,
        Radio,
        RadioBase,
        RadioGroup,
        RangeCalendar,
        ScrollShadow,
        Select,
        SelectItem,
        SelectSection,
        Skeleton,
        Slider,
        Spacer,
        Spinner,
        Subtitle,
        Switch,
        TabItem,
        Table,
        Tabs,
        Text,
        Textarea,
        ThemeSwitcher,
        TimeInput,
        Title,
        Toast,
        ToastProvider,
        ToastRegion,
        Tooltip,
        add_toast,
        clear_toasts,
        close_toast,
        configure_toasts,
        get_toast_provider,
        now,
        parse_absolute_to_local,
        parse_date,
        parse_datetime,
        parse_zoned_datetime,
        today,
    )

# 组件名称按需从 components 加载，导入本包不会加载全部组件。
_COMPONENT_NAMES = frozenset(import_module(".components", __name__).__all__)

__all__ = [
    "Accordion",
    "AccordionItem",
    "Alert",
    "Autocomplete",
    "AutocompleteItem",
    "AutocompleteSection",
    "Avatar",
    "AvatarGroup",
    "Badge",
    "Body",
    "BreadcrumbItem",
    "Breadcrumbs",
    "Button",
    "Calendar",
    "CalendarDate",
    "Caption",
    "Card",
    "CardBody",
    "CardFooter",
    "CardHeader",
    "Checkbox",
    "CheckboxGroup",
    "Chip",
    "CircularProgress",
    "CodeBlock",
    "CodeEditor",
    "DateInput",
    "DatePicker",
    "DateRangePicker",
    "DateTimeValue",
    "Divider",
    "Drawer",
    "Dropdown",
    "DropdownItem",
    "DropdownSection",
    "HeroSideUIProvider",
    "Icon",
    "Image",
    "Input",
    "InputOtp",
    "Kbd",
    "Link",
    "Listbox",
    "ListboxItem",
    "ListboxSection",
    "Markdown",
    "NumberInput",
    "Pagination",
    "Popover",
    "PopoverContent",
    "Progress",
    "Radio",
    "RadioBase",
    "RadioGroup",
    "RangeCalendar",
    "ScrollShadow",
    "ScrollStyle",
    "Select",
    "SelectItem",
    "SelectSection",
    "Skeleton",
    "Slider",
    "SmoothScroll",
    "Spacer",
    "Spinner",
    "StatePalette",
    "Subtitle",
    "Switch",
    "TabItem",
    "Table",
    "Tabs",
    "Text",
    "Textarea",
    "ThemeProvider",
    "ThemeSwitcher",
    "TimeInput",
    "Title",
    "Toast",
    "ToastProvider",
    "ToastRegion",
    "Tooltip",
    "add_toast",
    "clear_toasts",
    "close_toast",
    "configure_toasts",
    "get_toast_provider",
    "now",
    "parse_absolute_to_local",
    "parse_date",
    "parse_datetime",
    "parse_zoned_datetime",
    "today",
]


def __getattr__(name: str):
    """首次访问组件名称时从 components 加载，并缓存到本模块。

    Args:
        name: 公开名称。

    Returns:
        对应的类或函数。

    Raises:
        AttributeError: 名称不是公开导出。
    """
    if name not in _COMPONENT_NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".components", __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """补全时同时列出尚未加载的公开名称。"""
    return sorted({*globals(), *__all__})
