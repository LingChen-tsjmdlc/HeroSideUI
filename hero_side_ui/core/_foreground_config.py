"""color_foreground 的校验：嵌套写法、名单检查、"没有组件读取"提示、对比度提示。

写法见 docs/foreground-variants-proposal.md。校验遵守既有约定：错误一次列全，
警告只提示、不改写颜色。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..themes import theme_values
from ..themes.colors import HEROUI_COLORS
from ..themes.foreground_spec import (
    DEFAULT_SLOTS,
    FOREGROUND_SLOTS,
    FOREGROUND_STATES,
    FOREGROUND_VARIANTS,
    READS,
    is_read,
)

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# 位置对应的对比度要求：图标 3:1，其余文字 4.5:1
# 规范来自于：https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
_ICON_MIN = 3.0
_TEXT_MIN = 4.5


# ---------------------------------------------------------------- 色彩计算


def is_hex(v) -> bool:
    """是否为 #RRGGBB。"""
    return isinstance(v, str) and bool(_HEX.match(v))


def luminance(h: str) -> float:
    """相对亮度（WCAG）。"""

    def f(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(h[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    """两个颜色的 WCAG 对比度，不做四舍五入。"""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(top: str, alpha: float, under: str) -> str:
    """半透明的 top 叠在不透明的 under 上之后的颜色。"""
    t = [int(top[i : i + 2], 16) for i in (1, 3, 5)]
    u = [int(under[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(a * alpha + b * (1 - alpha)) for a, b in zip(t, u, strict=True)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


# ---------------------------------------------------------------- 结构校验


def _bi(en: str, zh: str) -> str:
    """提示语统一写成"英文 / 中文"。"""
    return f"{en} / {zh}"


# 对比度提示里说明"哪类组件"的双语标签
_WHO_BUTTON = _bi("Button etc.", "按钮等")
_WHO_FIELD = _bi("input field", "输入框")


def _misplaced(key: str) -> tuple[str, str]:
    """键名放错层时的说明，返回 (英文, 中文)。"""
    if key in FOREGROUND_VARIANTS:
        return (
            "variant names can only be written at the theme level (directly under light / dark)",
            "变体名只能写在主题层（light / dark 的下一层）",
        )
    if key in FOREGROUND_STATES:
        return (
            "state names can only be written at the variant level or below",
            "状态名只能写在变体层或其下",
        )
    if key in FOREGROUND_SLOTS:
        return (
            "slot names can only be written at the variant or state level",
            "位置名只能写在变体层或状态层",
        )
    return "the name is not in the allowed list", "名字不在名单里"


def _check_node(label: str, node, layer: str, errors: list):
    """校验一层字色，返回规整后的值（hex 或 dict）；有错返回 None。

    Args:
        label: 用于报错的路径。
        node: 这一层的值。
        layer: theme（主题层）/ variant / state。
        errors: 错误收集表。
    """
    if is_hex(node):
        return node
    if not isinstance(node, dict):
        errors.append(
            f"{label}: "
            + _bi(
                f"must be #RRGGBB or an object, got {node!r}",
                f"必须是 #RRGGBB 或对象，当前 {node!r}",
            )
        )
        return None
    if not node:
        errors.append(f"{label}: " + _bi("must not be an empty object {}", "不能是空对象 {}"))
        return None
    out: dict = {}
    ok = True
    for key, val in node.items():
        sub = f"{label}[{key!r}]"
        if key == "default":
            if is_hex(val):
                out[key] = val
            else:
                errors.append(f"{sub}: " + _bi("default must be #RRGGBB", "default 必须是 #RRGGBB"))
                ok = False
        elif layer == "theme" and key in FOREGROUND_VARIANTS:
            v = _check_node(sub, val, "variant", errors)
            ok = ok and v is not None
            out[key] = v
        elif layer == "variant" and key in FOREGROUND_STATES:
            v = _check_node(sub, val, "state", errors)
            ok = ok and v is not None
            out[key] = v
        elif layer in ("variant", "state") and key in FOREGROUND_SLOTS:
            if is_hex(val):
                out[key] = val
            else:
                errors.append(
                    f"{sub}: " + _bi("a slot value must be #RRGGBB", "位置的值必须是 #RRGGBB")
                )
                ok = False
        else:
            names_en = {
                "theme": f"one of the variant names {FOREGROUND_VARIANTS}, or default",
                "variant": (
                    f"state names {FOREGROUND_STATES}, slot names {FOREGROUND_SLOTS}, or default"
                ),
                "state": f"slot names {FOREGROUND_SLOTS}, or default",
            }[layer]
            names_zh = {
                "theme": f"变体名之一 {FOREGROUND_VARIANTS}，或 default",
                "variant": f"状态名 {FOREGROUND_STATES}、位置名 {FOREGROUND_SLOTS}，或 default",
                "state": f"位置名 {FOREGROUND_SLOTS}，或 default",
            }[layer]
            why_en, why_zh = _misplaced(key)
            errors.append(
                f"{sub}: "
                + _bi(
                    f"{why_en}; this level only accepts {names_en}",
                    f"{why_zh}；这一层只能写 {names_zh}",
                )
            )
            ok = False
    return out if ok else None


def check_color_foreground(value, errors: list) -> dict:
    """校验字色配置，返回 {色名: {light, dark}}，每个主题的值是 hex 或规整后的对象。"""
    out: dict = {}
    if not isinstance(value, dict):
        errors.append(
            "color_foreground: "
            + _bi(
                "must be a dict of {color name: hex or {light, dark}}",
                "必须是 {色名: 色值或 {light, dark}} 字典",
            )
        )
        return out
    for name, v in value.items():
        label = f"color_foreground[{name!r}]"
        if name not in theme_values.COLOR_NAMES:
            errors.append(
                "color_foreground: "
                + _bi(
                    f"unknown color name {name!r}, expected one of {theme_values.COLOR_NAMES}",
                    f"未知色名 {name!r}，只能是 {theme_values.COLOR_NAMES}",
                )
            )
        elif is_hex(v):
            out[name] = {"light": v, "dark": v}
        elif not isinstance(v, dict) or sorted(v) != ["dark", "light"]:
            errors.append(
                f"{label}: "
                + _bi(
                    "both light and dark are required, e.g. {'light': '#RRGGBB', 'dark': '#RRGGBB'}",
                    "必须同时写 light 与 dark，如 {'light': '#RRGGBB', 'dark': '#RRGGBB'}",
                )
            )
        else:
            sides = {s: _check_node(f"{label}[{s!r}]", v[s], "theme", errors) for s in v}
            if all(n is not None for n in sides.values()):
                out[name] = sides
    return out


# ---------------------------------------------------------------- 提示


def _walk(node, variant=None, state=None):
    """遍历一个主题的字色对象，逐个产出 (变体, 状态, 位置, 色值)；位置为 None 表示 default。"""
    if isinstance(node, str):
        yield variant, state, None, node
        return
    for key, val in node.items():
        if key == "default":
            yield variant, state, None, val
        elif key in FOREGROUND_VARIANTS:
            yield from _walk(val, key, state)
        elif key in FOREGROUND_STATES:
            yield from _walk(val, variant, key)
        else:
            yield variant, state, key, val


def _button_bg(variant: str, state, name: str, side: str, ramps: dict, parent: str) -> str:
    """按钮、Chip、Alert 一类组件里，某个变体下字的背景色。"""
    ramp = ramps[name]
    deep = 700 if (name == "default" and side == "dark") else 500
    strong = ramp[deep]
    hover = state == "hover"
    if variant in ("solid", "shadow"):
        return ramp[600] if hover else strong
    if variant == "ghost":
        return strong if hover else parent
    if variant == "flat":
        alpha = (0.3 if hover else 0.2) if side == "dark" else (0.25 if hover else 0.15)
        return blend(strong, alpha, parent)
    if variant == "light":
        if not hover:
            return parent
        return blend(strong, 0.2 if side == "dark" else 0.15, parent)
    if variant == "faded":
        return HEROUI_COLORS["default"][800 if side == "dark" else 100]
    return parent  # bordered / dot / underlined


def _field_bg(variant: str, name: str, side: str, ramps: dict, parent: str) -> str:
    """输入框一族里，某个变体下字的背景色（普通状态）。"""
    if variant in ("flat", "faded"):
        if name == "default":
            return ramps["default"][800 if side == "dark" else 100]
        if side == "dark":
            return blend(ramps[name][500], 0.15, parent)
        return ramps[name][100]
    return parent  # bordered / underlined


def _backgrounds(variant: str, state, slot, name: str, side: str, ramps: dict, parent: str) -> list:
    """一个 (变体, 状态, 位置) 下，所有读它的组件各自的背景色，[(说明, 色值), ...]。"""
    out: list = []
    field_variant = variant in ("flat", "faded", "bordered", "underlined")
    if slot in ("label", "label_resting", "placeholder"):
        out.append((_WHO_FIELD, _field_bg(variant, name, side, ramps, parent)))
        return out
    out.append((_WHO_BUTTON, _button_bg(variant, state, name, side, ramps, parent)))
    if field_variant and slot in ("text", "description") and state is None:
        out.append((_WHO_FIELD, _field_bg(variant, name, side, ramps, parent)))
    return out


# ---------------------------------------------------------------- 提示的人话写法

_SIDE_ZH = {"light": "亮色", "dark": "暗色"}
_SIDE_EN = {"light": "Light", "dark": "Dark"}
_VARIANT_ZH = {
    "solid": "实心",
    "shadow": "带阴影的实心",
    "bordered": "描边",
    "flat": "浅底",
    "light": "无底色",
    "faded": "浅灰底",
    "ghost": "鼠标悬停时变实心的描边",
    "dot": "圆点",
    "underlined": "下划线",
}
_STATE_ZH = {
    "hover": "悬停",
    "focus": "聚焦",
    "selected": "选中",
    "invalid": "出错",
    "disabled": "禁用",
}
_STATE_EN = {"hover": "hover", "focus": "focus", "selected": "selected", "invalid": "invalid"}
_SLOT_ZH = {
    "text": "正文",
    "icon": "图标",
    "title": "标题",
    "description": "说明文字",
    "label": "标签",
    "label_resting": "未浮起的标签",
    "placeholder": "占位符",
}


def _what(variant, state, slot, zh: bool) -> str:
    """把 (变体, 状态, 位置) 写成一句话里的名词，如"实心 · 悬停 · 正文"。"""
    parts = []
    if variant:
        parts.append(f"{_VARIANT_ZH.get(variant, variant)}（{variant}）" if zh else variant)
    if state:
        parts.append(_STATE_ZH[state] if zh else _STATE_EN.get(state, state))
    parts.append(_SLOT_ZH.get(slot or "text", slot) if zh else (slot or "text"))
    return " · ".join(parts)


@dataclass(frozen=True)
class ContrastIssue:
    """一处对比度过低：某个主题下，某个颜色、变体、位置的字色放在底色上不够清楚。

    Attributes:
        side: "light" 或 "dark"。
        color: 语义色名。
        variants: 实际出问题的变体。写在具体变体上时只有它自己；写在默认字色上时是所有
            "没有单独写"的、且看不清的变体。
        explicit: 用户是否直接写在这个变体上（False 表示来自默认字色）。
        state: 状态名，普通状态为 None。
        slot: 位置名。
        fg: 字色。
        ratio: 对比度（多个变体时取最低的），没有四舍五入。
        need: 推荐的最低对比度。
    """

    side: str
    color: str
    variants: tuple
    explicit: bool
    state: str | None
    slot: str
    fg: str
    ratio: float
    need: float


@dataclass(frozen=True)
class UnreadEntry:
    """一条没有任何组件会读的配置：写了也不会有变化。"""

    side: str
    color: str
    variant: str | None
    state: str | None
    slot: str | None


def collect_foreground_issues(cfg_fg: dict, cfg: dict) -> tuple[list, list]:
    """检查用户写的对象写法字色，返回 (对比度过低的清单, 没有组件读取的清单)。

    Args:
        cfg_fg: check_color_foreground 的返回值。
        cfg: 整份校验结果（取用户改过的色阶与底色）。

    Note:
        旧写法（单个 hex）的对比度提示仍由 _theme_config 负责，这里只看对象写法。
        禁用状态不检查；出错（invalid）状态的底色是 danger 色，这里不检查。
        背景口径：实色取 500（暗色 default 取 700），flat / light 把 500 按透明度叠在窗口底色上，
        faded 取 default 的 100 / 800，输入框一族取各自的输入框底色，其余取窗口底色。
    """
    surfaces = {k: dict(v) for k, v in theme_values.DEFAULT_SURFACES.items()}
    surfaces.update(cfg.get("surfaces", {}))
    ramps = {n: dict(HEROUI_COLORS[n]) for n in theme_values.COLOR_NAMES}
    ramps.update(cfg.get("colors", {}))
    issues: list = []
    unread: list = []
    for name, sides in cfg_fg.items():
        for side, node in sides.items():
            if isinstance(node, str):
                continue
            parent = surfaces["background"][side]
            # 主题层的 default 只落到"没有单独写"的变体上，已经单独写了的不用再按它检查
            explicit = {k for k in node if k in FOREGROUND_VARIANTS}
            for variant, state, slot, color in _walk(node):
                if state == "disabled":
                    continue
                if not is_read(variant, state, slot):
                    unread.append(UnreadEntry(side, name, variant, state, slot))
                    continue
                if state == "invalid":
                    continue
                need = _ICON_MIN if slot == "icon" else _TEXT_MIN
                targets = (
                    (variant,)
                    if variant
                    else tuple(v for v in READS if v not in explicit and is_read(v, None, None))
                )
                bad: list = []
                for v in targets:
                    if not is_read(v, state, slot):
                        continue
                    for _who, bg in _backgrounds(v, state, slot, name, side, ramps, parent):
                        ratio = contrast(color, bg)
                        if ratio < need:
                            bad.append((v, ratio))
                            break
                if bad:
                    issues.append(
                        ContrastIssue(
                            side=side,
                            color=name,
                            variants=tuple(v for v, _ in bad),
                            explicit=bool(variant),
                            state=state,
                            slot=slot or "text",
                            fg=color,
                            ratio=min(r for _, r in bad),
                            need=need,
                        )
                    )
    return issues, unread


def _variant_text(issue: ContrastIssue, zh: bool) -> str:
    """ "XX 变体"里的 XX。"""
    if issue.explicit:
        v = issue.variants[0]
        return f"{_VARIANT_ZH.get(v, v)}（{v}）" if zh else v
    if len(issue.variants) > 3:
        return "未单独设置的大多数" if zh else "most unset"
    names = "、".join(issue.variants) if zh else ", ".join(issue.variants)
    return f"未单独设置的 {names} " if zh else f"unset ({names})"


def _slot_text(issue: ContrastIssue, zh: bool) -> str:
    """ "XX 位置"里的 XX；有状态时写成"悬停状态的正文"。"""
    slot = _SLOT_ZH.get(issue.slot, issue.slot) if zh else issue.slot
    if not issue.state:
        return slot
    if zh:
        return f"{_STATE_ZH[issue.state]}状态的{slot}"
    return f"{_STATE_EN.get(issue.state, issue.state)} {slot}"


def format_contrast_report(issues: list) -> tuple[str, str, str, str]:
    """把对比度问题清单拼成"标题 + 描述"，返回 (中文标题, 英文标题, 中文描述, 英文描述)。

    格式：
        标题：有 X 处配色对比度过低
        描述：当前亮色模式下，XX 颜色 XX 变体 XX 位置对比度是 XX，推荐 XX 对比度；……。
              当前暗色模式下，……。
    """
    n = len(issues)
    title_zh = f"有 {n} 处配色对比度过低"
    title_en = f"{n} color pair(s) with too low contrast"
    zh_groups: list = []
    en_groups: list = []
    for side in ("light", "dark"):
        items = [i for i in issues if i.side == side]
        if not items:
            continue
        zh_items = [
            f"{i.color} 颜色 {_variant_text(i, True)}变体 {_slot_text(i, True)}位置"
            f"对比度是 {i.ratio:.2f}，推荐 {i.need:g} 对比度"
            for i in items
        ]
        en_items = [
            f"{i.color} color, {_variant_text(i, False)} variant, {_slot_text(i, False)} slot: "
            f"contrast is {i.ratio:.2f}, recommended {i.need:g}"
            for i in items
        ]
        zh_groups.append(f"当前{_SIDE_ZH[side]}模式下，" + "；".join(zh_items) + "。")
        en_groups.append(f"In {_SIDE_EN[side].lower()} mode, " + "; ".join(en_items) + ".")
    return title_zh, title_en, "".join(zh_groups), " ".join(en_groups)


def unread_message(entry: UnreadEntry) -> str:
    """ "没有任何组件会读这一项"的提示，中英各一行。"""
    zh = (
        f"{entry.color} · {_SIDE_ZH[entry.side]} · "
        f"{_what(entry.variant, entry.state, entry.slot, True)}：目前没有任何组件会读这一项，"
        f"写了也不会有变化。检查一下是不是写错了位置。"
    )
    en = (
        f"{entry.color} · {_SIDE_EN[entry.side]} · "
        f"{_what(entry.variant, entry.state, entry.slot, False)}: no component reads "
        f"this entry, so it has no effect. Check whether it is in the wrong place."
    )
    return f"{zh}\n{en}"


def hint_messages(issues: list, unread: list) -> list:
    """把问题清单变成 setup() 里发出的警告文本：一条汇总的对比度警告 + 每条无效配置一条。"""
    out: list = []
    if issues:
        tz, te, dz, de = format_contrast_report(issues)
        out.append(f"{tz}：{dz}\n{te}: {de}")
    out.extend(unread_message(u) for u in unread)
    return out


def check_foreground_hints(cfg_fg: dict, cfg: dict, warns: list) -> None:
    """对用户写了的对象写法字色给出提示，追加到 warns。

    Args:
        cfg_fg: check_color_foreground 的返回值。
        cfg: 整份校验结果。
        warns: 警告收集表。
    """
    issues, unread = collect_foreground_issues(cfg_fg, cfg)
    warns.extend(hint_messages(issues, unread))


__all__ = [
    "DEFAULT_SLOTS",
    "ContrastIssue",
    "UnreadEntry",
    "blend",
    "check_color_foreground",
    "check_foreground_hints",
    "collect_foreground_issues",
    "contrast",
    "format_contrast_report",
    "hint_messages",
    "is_hex",
    "luminance",
    "unread_message",
]
