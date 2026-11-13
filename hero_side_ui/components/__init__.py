"""全部组件的公开入口，按名称延迟加载。

`from hero_side_ui.components import Button` 只会加载 button 包及其依赖，
未使用的组件（如日历、Markdown）及其第三方库不会被导入。
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .accordion import Accordion, AccordionItem
    from .alert import Alert
    from .autocomplete import Autocomplete, AutocompleteItem, AutocompleteSection
    from .avatar import Avatar, AvatarGroup
    from .badge import Badge
    from .breadcrumbs import BreadcrumbItem, Breadcrumbs
    from .button import Button
    from .calendar import Calendar, CalendarDate, RangeCalendar
    from .card import Card, CardBody, CardFooter, CardHeader
    from .checkbox import Checkbox, CheckboxGroup
    from .chip import Chip
    from .code_block import CodeBlock
    from .code_editor import CodeEditor
    from .date_input import (
        DateInput,
        DateTimeValue,
        now,
        parse_absolute_to_local,
        parse_date,
        parse_datetime,
        parse_zoned_datetime,
        today,
    )
    from .date_picker import DatePicker, DateRangePicker
    from .divider import Divider
    from .drawer import Drawer
    from .dropdown import Dropdown, DropdownItem, DropdownSection
    from .icon import Icon
    from .image import Image
    from .input import Input
    from .input_otp import InputOtp
    from .kbd import Kbd
    from .link import Link
    from .listbox import Listbox, ListboxItem, ListboxSection
    from .markdown import Markdown
    from .number_input import NumberInput
    from .pagination import Pagination
    from .popover import Popover, PopoverContent
    from .progress import CircularProgress, Progress
    from .radio import Radio, RadioBase, RadioGroup
    from .scroll_shadow import ScrollShadow
    from .select import Select, SelectItem, SelectSection
    from .skeleton import Skeleton
    from .slider import Slider
    from .spacer import Spacer
    from .spinner import Spinner
    from .switch import Switch
    from .table import Table
    from .tabs import TabItem, Tabs
    from .text import Body, Caption, Subtitle, Text, Title
    from .textarea import Textarea
    from .theme_switcher import ThemeSwitcher
    from .time_input import TimeInput
    from .toast import (
        Toast,
        ToastProvider,
        ToastRegion,
        add_toast,
        clear_toasts,
        close_toast,
        configure_toasts,
        get_toast_provider,
    )
    from .tooltip import Tooltip

_EXPORTS = {
    "Accordion": ".accordion",
    "AccordionItem": ".accordion",
    "Alert": ".alert",
    "Autocomplete": ".autocomplete",
    "AutocompleteItem": ".autocomplete",
    "AutocompleteSection": ".autocomplete",
    "Avatar": ".avatar",
    "AvatarGroup": ".avatar",
    "Badge": ".badge",
    "Body": ".text",
    "BreadcrumbItem": ".breadcrumbs",
    "Breadcrumbs": ".breadcrumbs",
    "Button": ".button",
    "Calendar": ".calendar",
    "CalendarDate": ".calendar",
    "Caption": ".text",
    "Card": ".card",
    "CardBody": ".card",
    "CardFooter": ".card",
    "CardHeader": ".card",
    "Checkbox": ".checkbox",
    "CheckboxGroup": ".checkbox",
    "Chip": ".chip",
    "CircularProgress": ".progress",
    "CodeBlock": ".code_block",
    "CodeEditor": ".code_editor",
    "DateInput": ".date_input",
    "DatePicker": ".date_picker",
    "DateRangePicker": ".date_picker",
    "DateTimeValue": ".date_input",
    "Divider": ".divider",
    "Drawer": ".drawer",
    "Dropdown": ".dropdown",
    "DropdownItem": ".dropdown",
    "DropdownSection": ".dropdown",
    "Icon": ".icon",
    "Image": ".image",
    "Input": ".input",
    "InputOtp": ".input_otp",
    "Kbd": ".kbd",
    "Link": ".link",
    "Listbox": ".listbox",
    "ListboxItem": ".listbox",
    "ListboxSection": ".listbox",
    "Markdown": ".markdown",
    "NumberInput": ".number_input",
    "Pagination": ".pagination",
    "Popover": ".popover",
    "PopoverContent": ".popover",
    "Progress": ".progress",
    "Radio": ".radio",
    "RadioBase": ".radio",
    "RadioGroup": ".radio",
    "RangeCalendar": ".calendar",
    "ScrollShadow": ".scroll_shadow",
    "Select": ".select",
    "SelectItem": ".select",
    "SelectSection": ".select",
    "Skeleton": ".skeleton",
    "Slider": ".slider",
    "Spacer": ".spacer",
    "Spinner": ".spinner",
    "Subtitle": ".text",
    "Switch": ".switch",
    "TabItem": ".tabs",
    "Table": ".table",
    "Tabs": ".tabs",
    "Text": ".text",
    "Textarea": ".textarea",
    "ThemeSwitcher": ".theme_switcher",
    "TimeInput": ".time_input",
    "Title": ".text",
    "Toast": ".toast",
    "ToastProvider": ".toast",
    "ToastRegion": ".toast",
    "Tooltip": ".tooltip",
    "add_toast": ".toast",
    "clear_toasts": ".toast",
    "close_toast": ".toast",
    "configure_toasts": ".toast",
    "get_toast_provider": ".toast",
    "now": ".date_input",
    "parse_absolute_to_local": ".date_input",
    "parse_date": ".date_input",
    "parse_datetime": ".date_input",
    "parse_zoned_datetime": ".date_input",
    "today": ".date_input",
}

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
    "Select",
    "SelectItem",
    "SelectSection",
    "Skeleton",
    "Slider",
    "Spacer",
    "Spinner",
    "Subtitle",
    "Switch",
    "TabItem",
    "Table",
    "Tabs",
    "Text",
    "Textarea",
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
    """首次访问公开名称时加载所属组件包，并缓存到模块。

    Args:
        name: 公开名称。

    Returns:
        对应的类或函数。

    Raises:
        AttributeError: 名称不是公开导出。
    """
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """补全时同时列出尚未加载的公开名称。"""
    return sorted({*globals(), *__all__})
