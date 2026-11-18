"""字色配置的名单与"哪些组件读哪些键"表。

color_foreground 的写法：颜色 -> 主题(light/dark) -> 变体 -> 状态 -> 位置，每一层可以直接写
#RRGGBB，也可以写成对象继续细分。详细规则见 docs/foreground-variants-proposal.md。
"""

from __future__ import annotations

FOREGROUND_VARIANTS = (
    "solid",
    "bordered",
    "flat",
    "light",
    "faded",
    "ghost",
    "shadow",
    "dot",
    "underlined",
)
FOREGROUND_STATES = ("hover", "focus", "selected", "invalid", "disabled")
FOREGROUND_SLOTS = (
    "text",
    "icon",
    "title",
    "description",
    "label",
    "label_resting",
    "placeholder",
)

# 多个状态同时成立时，先查靠前的
STATE_PRIORITY = ("disabled", "invalid", "selected", "focus", "hover")

# `default` 只兜这几个位置；占位符、标签、说明不吃 default，否则会和正文变成同一种颜色
DEFAULT_SLOTS = ("text", "icon", "title")

_TEXT_ICON = frozenset({"text", "icon"})
_ALERT_SLOTS = frozenset({"title", "description", "icon"})
_FIELD_SLOTS = frozenset({"text", "placeholder", "label", "label_resting", "description"})
_OTP_SLOTS = frozenset({"text", "placeholder"})


def _merge(*tables: dict) -> dict:
    """把若干张 {变体: {状态: 位置集合}} 合并成一张。"""
    out: dict = {}
    for table in tables:
        for variant, states in table.items():
            node = out.setdefault(variant, {})
            for state, slots in states.items():
                node[state] = node.get(state, frozenset()) | slots
    return out


def _spread(variants: tuple, states: dict) -> dict:
    return {v: dict(states) for v in variants}


# 各组件实际读哪些键。有任何一个组件读，写法就合法。
READS: dict = _merge(
    # Button：六个变体；悬停与禁用
    _spread(
        ("solid", "bordered", "flat", "light", "faded", "ghost"),
        {None: _TEXT_ICON, "hover": _TEXT_ICON, "disabled": _TEXT_ICON},
    ),
    # Chip：七个变体；Badge 是其中四个，只读 text
    _spread(("solid", "bordered", "light", "flat", "faded", "shadow", "dot"), {None: _TEXT_ICON}),
    # Alert / Toast：标题、说明、图标
    _spread(("solid", "bordered", "flat", "faded"), {None: _ALERT_SLOTS}),
    # Listbox / Dropdown / Table 的行：标题字色（灰色 default 不读）
    _spread(
        ("solid", "shadow", "flat", "bordered", "faded", "light"),
        {s: frozenset({"title"}) for s in (None, "hover", "focus", "selected", "disabled")},
    ),
    # 只在彩色实底上画字的组件（Avatar、Calendar、Pagination、Tabs、Checkbox、Switch、
    # Popover、Tooltip、Slider）统一当作 solid；被选中的那种用 selected
    {"solid": {None: _TEXT_ICON, "selected": _TEXT_ICON}},
    # 输入框一族：Input / NumberInput / Select / Autocomplete / Textarea /
    # DateInput / TimeInput / DatePicker 读 _FIELD_SLOTS；InputOtp 只读 _OTP_SLOTS
    _spread(
        ("flat", "faded", "bordered", "underlined"),
        {None: _FIELD_SLOTS, "invalid": _FIELD_SLOTS},
    ),
)


def is_read(variant: str, state: str | None, slot: str | None) -> bool:
    """某个 (变体, 状态, 位置) 是否至少被一个组件读取。

    Args:
        variant: 变体名；None 表示不限变体（主题层的 default）。
        state: 状态名；None 表示普通状态。
        slot: 位置名；None 表示这一层的 default（只要有一个 default 兜的位置被读就算）。
    """
    variants = (variant,) if variant else tuple(READS)
    for v in variants:
        slots = READS.get(v, {}).get(state)
        if not slots:
            continue
        if slot is None:
            if slots & set(DEFAULT_SLOTS):
                return True
        elif slot in slots:
            return True
    return False


__all__ = [
    "DEFAULT_SLOTS",
    "FOREGROUND_SLOTS",
    "FOREGROUND_STATES",
    "FOREGROUND_VARIANTS",
    "READS",
    "STATE_PRIORITY",
    "is_read",
]
