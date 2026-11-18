"""主题取值存放层：默认值、当前值、读取入口、应用与还原。

组件只通过本模块取值，每次调用都读当前值，不在 import 时缓存。
色板与圆角原地改写 HEROUI_COLORS / RADIUS；其余取值存在本模块的状态里。
"""

from __future__ import annotations

import copy
import re

from .colors import HEROUI_COLORS
from .foreground_spec import DEFAULT_SLOTS, STATE_PRIORITY
from .radius import RADIUS
from .shadow import DEFAULT_SHADOW, SHADOW_TIERS

COLOR_STEPS = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)
COLOR_NAMES = ("default", "primary", "secondary", "success", "warning", "danger")
FONT_TIERS = ("xs", "sm", "md", "lg", "xl")

DEFAULT_SURFACES: dict = {
    "background": {"light": "#FAFBFD", "dark": "#0D0D0F"},
    "foreground": {"light": "#11181C", "dark": "#ECEDEE"},
    "content_background": {"light": "#FEFEFF", "dark": "#18181B"},
    "popup_background": {"light": "#FEFEFF", "dark": "#27272A"},
}
DEFAULT_COLOR_FOREGROUND: dict = {
    "default": {"light": "#FEFEFF", "dark": "#D4D4D8"},
    "primary": {"light": "#FEFEFF", "dark": "#FEFEFF"},
    "secondary": {"light": "#FEFEFF", "dark": "#FEFEFF"},
    "success": {"light": "#FEFEFF", "dark": "#FEFEFF"},
    "warning": {"light": "#11181C", "dark": "#11181C"},
    "danger": {"light": "#FEFEFF", "dark": "#FEFEFF"},
}
DEFAULT_FONT_SIZE: dict = {"xs": 10, "sm": 13, "md": 16, "lg": 19, "xl": 22}
DEFAULT_RADIUS: dict = {"sm": 4, "md": 8, "lg": 14}

DEFAULT_COLORS = copy.deepcopy(HEROUI_COLORS)

_state: dict = {}
_read = False

# 预设里的字号槽位：(容器, 键, 档位, 是否带 px 后缀)
_FONT_KEY = re.compile(r"^(?:[a-z_]*font[a-z_]*|text_size)$")
_font_slots: list = []


def _fresh_state() -> dict:
    """生成一份全默认的状态。"""
    return {
        "surfaces": copy.deepcopy(DEFAULT_SURFACES),
        "color_foreground": copy.deepcopy(DEFAULT_COLOR_FOREGROUND),
        "fg_user": set(),  # 用户在 setup() 里写过字色的颜色名
        "font_size": dict(DEFAULT_FONT_SIZE),
        "shadow": copy.deepcopy(DEFAULT_SHADOW),
        "mono_family": None,
    }


_state.update(_fresh_state())


def _side(theme: str) -> str:
    """把任意主题名规整为 light / dark。"""
    return "dark" if theme == "dark" else "light"


def _surface(name: str, theme: str, mark: bool = True) -> str:
    """读取一个面/文字取值。

    Args:
        name: 取值名（background / foreground / content_background / popup_background）。
        theme: 主题名。
        mark: False 时不记为"已被组件读取"（基础设施自己读取用）。
    """
    global _read
    if mark:
        _read = True
    return _state["surfaces"][name][_side(theme)]


def get_background(theme: str, *, mark: bool = True) -> str:
    """窗口底色。

    Args:
        theme: "light" 或 "dark"。
        mark: False 时不记为"已被组件读取"。
    """
    return _surface("background", theme, mark)


def get_foreground(theme: str, *, mark: bool = True) -> str:
    """默认文字与图标色。

    Args:
        theme: "light" 或 "dark"。
        mark: False 时不记为"已被组件读取"。
    """
    return _surface("foreground", theme, mark)


def get_content_background(theme: str) -> str:
    """内容面底色（Card 等）。

    Args:
        theme: "light" 或 "dark"。
    """
    return _surface("content_background", theme)


def get_popup_background(theme: str) -> str:
    """弹出层底色（Popover、Tooltip、Toast 等）。

    Args:
        theme: "light" 或 "dark"。
    """
    return _surface("popup_background", theme)


def _as_states(states) -> tuple:
    """把状态参数规整成按优先级排好的元组；接受 None、单个状态名或可迭代对象。"""
    if not states:
        return ()
    if isinstance(states, str):
        states = (states,)
    return tuple(s for s in STATE_PRIORITY if s in states)


def _lookup(node, variant: str, states: tuple, slot: str):
    """在一个主题下的字色树里按"状态 -> 变体 -> 位置"的顺序查一个值，查不到返回 None。

    Args:
        node: 一个主题下的取值：旧写法的 #RRGGBB，或新写法的对象。
        variant: 变体名。
        states: 已按优先级排好的、当前成立的状态。
        slot: 位置名。

    Note:
        旧写法只管实色底上的字：solid（任何状态）与 ghost 悬停。
        新写法顺序：变体里的"状态.位置"、"状态.default"（逐个状态），变体里的位置、
        变体 default，最后是主题层 default。default 只兜 DEFAULT_SLOTS 里的位置。
        状态里有 disabled 时，只看明确写给 disabled 的值，后面几层兜底都不吃。
    """
    takes_default = slot in DEFAULT_SLOTS
    # 禁用态要保持"变淡"的样子：只吃明确写给 disabled 的值，不吃变体 / 主题层的兜底
    disabled = "disabled" in states
    if isinstance(node, str):
        # 旧写法只管实色底上的正文、图标、标题，不管说明、标签、占位符，也不管禁用态
        if not takes_default or disabled:
            return None
        if variant == "solid" or (variant == "ghost" and "hover" in states):
            return node
        return None
    vnode = node.get(variant)
    if isinstance(vnode, str):
        if takes_default and not disabled:
            return vnode
    elif vnode is not None:
        for state in states:
            snode = vnode.get(state)
            if isinstance(snode, str):
                if takes_default:
                    return snode
            elif snode is not None:
                if slot in snode:
                    return snode[slot]
                if takes_default and "default" in snode:
                    return snode["default"]
        if not disabled:
            if slot in vnode:
                return vnode[slot]
            if takes_default and "default" in vnode:
                return vnode["default"]
    if takes_default and "default" in node and not disabled:
        return node["default"]
    return None


def foreground_override(
    color: str, theme: str, variant: str, *, states=(), slot: str = "text"
) -> str | None:
    """用户为某个颜色明确配置过的字色；没配置返回 None，由组件走自己原来的取色规则。

    Args:
        color: 语义色名。不在六个语义色里（如 foreground）时恒返回 None。
        theme: "light" 或 "dark"。
        variant: 变体名。
        states: 当前成立的状态（单个名字或可迭代）；顺序无所谓，内部按优先级查。
        slot: 位置名。

    Note:
        没在 setup() 里写过 color_foreground 的颜色，恒返回 None，保证默认外观不变。
    """
    global _read
    _read = True
    if color not in _state["fg_user"]:
        return None
    node = _state["color_foreground"][color][_side(theme)]
    return _lookup(node, variant, _as_states(states), slot)


def foreground_is_user_set(color: str) -> bool:
    """用户是否在 setup() 里写过这个颜色的字色。"""
    return color in _state["fg_user"]


def get_color_foreground(color: str, theme: str, *, state: str | None = None) -> str:
    """实色底上的文字色；未知色名按 primary 处理。

    Args:
        color: 语义色名。
        theme: "light" 或 "dark"。
        state: 当前状态（如被选中的格子传 "selected"）；None 表示普通状态。

    Note:
        等价于 solid 变体的 text 位置。用户没写、或只写了别的变体时，回落到默认字色。
    """
    global _read
    _read = True
    table = _state["color_foreground"]
    name = color if color in table else "primary"
    side = _side(theme)
    if name in _state["fg_user"]:
        hit = _lookup(table[name][side], "solid", _as_states(state), "text")
        if hit is not None:
            return hit
    node = table[name][side]
    return node if isinstance(node, str) else DEFAULT_COLOR_FOREGROUND[name][side]


def get_font_px(tier: str) -> int:
    """读取字号档位的当前像素值。

    Args:
        tier: xs / sm / md / lg / xl。
    """
    global _read
    _read = True
    return _state["font_size"][tier]


def get_font_sizes() -> dict:
    """五档字号的当前值副本。"""
    global _read
    _read = True
    return dict(_state["font_size"])


def get_shadow_layers(tier: str, theme: str) -> tuple:
    """某档阴影的层元组；tier 不在 sm/md/lg 时返回空元组（无阴影）。

    Args:
        tier: sm / md / lg。
        theme: "light" 或 "dark"。
    """
    global _read
    _read = True
    if tier not in SHADOW_TIERS:
        return ()
    return _state["shadow"][_side(theme)][tier]


def get_mono_family() -> str | None:
    """用户指定的代码字体 family；None 表示用内置默认。"""
    return _state["mono_family"]


def was_read() -> bool:
    """是否已有组件读取过主题取值（用于晚调用 setup 的警告）。"""
    return _read


def clear_read_flag() -> None:
    """清除"已被读取"标记。"""
    global _read
    _read = False


def bind_font_slots(containers) -> None:
    """扫描组件预设，把所有字号槽位绑定到字号档位。

    Args:
        containers: 预设字典（或其列表/元组）的可迭代对象。

    Raises:
        ValueError: 某个字号不在五档默认值上（说明预设里写了档位以外的字号）。

    Note:
        绑定后 font_size 配置变化时，槽位被原地改写，组件无需改动。
    """
    seen: set = set()
    bad: list = []

    def walk(node, path: str) -> None:
        if id(node) in seen:
            return
        if isinstance(node, dict):
            seen.add(id(node))
            for key, val in list(node.items()):
                sub = f"{path}[{key!r}]"
                if isinstance(val, (dict, list, tuple)):
                    walk(val, sub)
                elif isinstance(key, str) and "weight" not in key and _FONT_KEY.match(key):
                    _bind_one(node, key, val, sub, bad)
        elif isinstance(node, (list, tuple)):
            seen.add(id(node))
            for i, val in enumerate(node):
                walk(val, f"{path}[{i}]")

    for idx, node in enumerate(containers):
        walk(node, f"preset#{idx}")
    if bad:
        raise ValueError(
            "预设字号不在档位上（须为 "
            + "/".join(str(v) for v in DEFAULT_FONT_SIZE.values())
            + "）："
            + "；".join(bad)
        )


def _bind_one(node: dict, key: str, val, path: str, bad: list) -> None:
    """登记一个字号槽位；值须恰好等于某一档的默认值。"""
    has_px = isinstance(val, str) and val.endswith("px")
    num = val[:-2] if has_px else val
    if isinstance(num, str):
        if not num.isdigit():
            return  # 字号档位名（如 "xs"）不是像素值，运行时由 SIZE_MAP 解析
        num = int(num)
    if isinstance(num, bool) or not isinstance(num, int):
        return
    tier = next((t for t, px in DEFAULT_FONT_SIZE.items() if px == num), None)
    if tier is None:
        bad.append(f"{path}={val!r}")
        return
    _font_slots.append((node, key, tier, has_px))


def _rewrite_font_slots(sizes: dict) -> None:
    """按当前五档字号原地改写全部已绑定的预设槽位。"""
    for node, key, tier, has_px in _font_slots:
        node[key] = f"{sizes[tier]}px" if has_px else sizes[tier]


def reset() -> None:
    """全部主题取值还原为默认值（色板、圆角、预设字号原地还原）。"""
    for name, ramp in DEFAULT_COLORS.items():
        HEROUI_COLORS.setdefault(name, {})
        HEROUI_COLORS[name].clear()
        HEROUI_COLORS[name].update(ramp)
    _set_radius(DEFAULT_RADIUS)
    _state.update(_fresh_state())
    _rewrite_font_slots(_state["font_size"])


def _set_radius(values: dict) -> None:
    """原地改写 RADIUS，并同步长名别名。"""
    for key in ("sm", "md", "lg"):
        RADIUS[key] = f"{int(values[key])}px"
    RADIUS["small"] = RADIUS["sm"]
    RADIUS["medium"] = RADIUS["md"]
    RADIUS["large"] = RADIUS["lg"]


def apply(cfg: dict) -> None:
    """应用一份已校验的配置。

    Args:
        cfg: 由 core._theme_config.validate 产出，键只含用户写了的项：
            colors / color_foreground / radius / surfaces / font_size / shadow / mono_family。
    """
    for name, ramp in cfg.get("colors", {}).items():
        HEROUI_COLORS[name].clear()
        HEROUI_COLORS[name].update(ramp)
    if "radius" in cfg:
        _set_radius(cfg["radius"])
    for name, value in cfg.get("surfaces", {}).items():
        _state["surfaces"][name] = dict(value)
    for name, value in cfg.get("color_foreground", {}).items():
        _state["color_foreground"][name] = copy.deepcopy(value)
        _state["fg_user"].add(name)
    if "font_size" in cfg:
        _state["font_size"] = dict(cfg["font_size"])
        _rewrite_font_slots(_state["font_size"])
    if "shadow" in cfg:
        _state["shadow"] = cfg["shadow"]
    if cfg.get("mono_family"):
        _state["mono_family"] = cfg["mono_family"]


__all__ = [
    "COLOR_NAMES",
    "COLOR_STEPS",
    "DEFAULT_COLOR_FOREGROUND",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_RADIUS",
    "DEFAULT_SURFACES",
    "FONT_TIERS",
    "apply",
    "bind_font_slots",
    "clear_read_flag",
    "foreground_is_user_set",
    "foreground_override",
    "get_background",
    "get_color_foreground",
    "get_content_background",
    "get_font_px",
    "get_font_sizes",
    "get_foreground",
    "get_mono_family",
    "get_popup_background",
    "get_shadow_layers",
    "reset",
    "was_read",
]
