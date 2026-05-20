# Themes module - 全局主题、颜色与设计 Token
from .colors import HEROUI_COLORS
from .radius import RADIUS
from .component_presets import (
    BUTTON_SIZES,
    ACCORDION_SIZES,
    INPUT_SIZES,
    TEXTAREA_SIZES,
    DIVIDER_SIZES,
    CARD_SHADOWS,
    CHECKBOX_SIZES,
    PROGRESS_SIZES,
    CIRCULAR_PROGRESS_SIZES,
    SPINNER_SIZES,
    POPOVER_SHADOWS,
    TOOLTIP_SIZES,
    TABS_SIZES,
    SWITCH_SIZES,
    LISTBOX_SIZES,
    AUTOCOMPLETE_SIZES,
)


# ----------------------------------------------------------------------
# FONT_FAMILY 延迟取值
# ----------------------------------------------------------------------
# 注意：这里**故意不**写 ``from .font import FONT_FAMILY``。
#
# ``themes.font.FONT_FAMILY`` 是一个模块级 PEP 562 动态属性，每次访问都会
# 调用 ``FontProvider.instance().font_family_css()``，进而触发
# ``QFontDatabase.addApplicationFont``。在 Qt 6 / Windows 上，**没有
# QApplication 时调用 QFontDatabase 会直接 access violation 崩进程**。
#
# 之前 ``from .font import FONT_FAMILY`` 等于把这次副作用前移到了
# ``import hero_side_ui`` 的瞬间——pytest 收集阶段只 import 模块还没建
# QApplication，于是炸掉。
#
# 现在改成包级 __getattr__：下游 18 个 ``from ...themes import FONT_FAMILY``
# 在 import 阶段不会触发任何 Qt 调用，**真正读到名字时**（一般在组件
# ``__init__`` 里拼 QSS，那时 QApplication 早就建出来了）才转发到
# ``themes.font.__getattr__('FONT_FAMILY')``。
def __getattr__(name: str):
    if name == "FONT_FAMILY":
        from .font import FONT_FAMILY as _ff

        return _ff
    raise AttributeError(f"module 'hero_side_ui.themes' has no attribute {name!r}")


__all__ = [
    "HEROUI_COLORS",
    "RADIUS",
    "FONT_FAMILY",
    "BUTTON_SIZES",
    "ACCORDION_SIZES",
    "INPUT_SIZES",
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
]
