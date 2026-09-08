"""Toast 配色 tokens：variant(flat/bordered/solid) × color(7 色) × theme。

严格对照 HeroUI v2 toast.ts 的 compoundVariants。

暗色换算规则（semantic.ts）：HeroUI 在暗色下对所有语义色做 swapColorValues，
即把色阶**按索引首尾反转**（50 ↔ 900、100 ↔ 800 … 400 ↔ 500）。本项目
``HEROUI_COLORS`` 存的是**未 swap** 的原色阶，所以取色统一走 ``_shade()``。
例外：``DEFAULT``（solid 的底色）直接用原色阶，不参与 swap。
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS

# 语义色阶（HeroUI common.* 只有这 10 档，暗色 swap 靠首尾反转）
_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)

# HeroUI semantic: background / foreground / content1 的 DEFAULT
_BACKGROUND = {"light": "#FFFFFF", "dark": "#000000"}
_FOREGROUND = {"light": "#11181C", "dark": "#ECEDEE"}
_CONTENT1 = {"light": "#FFFFFF", "dark": "#18181b"}

# solid 变体的文字色（readableColor 的结果，warning/success 为深色底浅字）
_SOLID_FG = {
    "primary": "#ffffff",
    "secondary": "#ffffff",
    "success": "#000000",
    "warning": "#000000",
    "danger": "#ffffff",
}

# default.DEFAULT 不参与暗色 swap
_DEFAULT_SOLID_BG = {"light": "#d4d4d8", "dark": "#3f3f46"}
_DEFAULT_SOLID_FG = {"light": "#000000", "dark": "#ffffff"}


def _shade(scale: dict, n: int, is_dark: bool) -> str:
    """取语义色阶；暗色下按 HeroUI 的 swap 规则首尾反转（50 ↔ 900）。"""
    if not is_dark:
        return scale[n]
    idx = _SHADES.index(n)
    return scale[_SHADES[len(_SHADES) - 1 - idx]]


def build_toast_styles(variant: str, color: str, theme: str) -> dict:
    """返回 Toast 各子元素的颜色。

    Keys: base_bg, border_color, border_width, title_color, desc_color,
          icon_color, close_color, close_hover_color, progress_color
    """
    is_dark = theme == "dark"
    d = HEROUI_COLORS["default"]
    # foreground 与 default 共用 zinc 色阶（semantic: foreground = {...common.zinc}）
    scale = HEROUI_COLORS.get(color, d) if color not in ("default", "foreground") else d

    if variant == "solid":
        return _solid(scale, d, is_dark, color)
    if variant == "bordered":
        return _bordered(scale, d, is_dark, color)
    return _flat(scale, d, is_dark, color)


# ---- flat（默认）：浅色底 + 细边框 ----

def _flat(c: dict, d: dict, is_dark: bool, color: str) -> dict:
    if color == "default":
        bg = _CONTENT1["dark" if is_dark else "light"]
        fg = _FOREGROUND["dark" if is_dark else "light"]
        return _pack(
            bg=bg, border=_shade(d, 100, is_dark), border_w=1,
            title=fg, desc=_shade(d, 500, is_dark), icon=fg,
            close=_shade(d, 400, is_dark), close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    if color == "foreground":
        fg = _BACKGROUND["dark" if is_dark else "light"]
        return _pack(
            bg=_FOREGROUND["dark" if is_dark else "light"],
            border=_shade(d, 100, is_dark), border_w=1,
            title=fg, desc=fg, icon=fg,
            close=_shade(d, 400, is_dark), close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    return _pack(
        bg=_shade(c, 50, is_dark), border=_shade(c, 100, is_dark), border_w=1,
        title=_shade(c, 600, is_dark), desc=_shade(c, 500, is_dark),
        icon=_shade(c, 600, is_dark),
        close=_shade(c, 400, is_dark), close_hover=_shade(c, 600, is_dark),
        progress=_shade(c, 400, is_dark),
    )


# ---- bordered：背景色底 + 主色边框 ----

def _bordered(c: dict, d: dict, is_dark: bool, color: str) -> dict:
    bg_key = "dark" if is_dark else "light"
    if color == "default":
        return _pack(
            bg=_BACKGROUND[bg_key], border=_shade(d, 200, is_dark), border_w=1,
            title=_FOREGROUND[bg_key], desc=_shade(d, 500, is_dark),
            icon=_FOREGROUND[bg_key],
            close=_shade(d, 400, is_dark), close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    if color == "foreground":
        fg = _BACKGROUND[bg_key]
        return _pack(
            bg=_FOREGROUND[bg_key], border=_shade(d, 400, is_dark), border_w=1,
            title=fg, desc=fg, icon=fg,
            close=_shade(d, 400, is_dark), close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    return _pack(
        bg=_BACKGROUND[bg_key], border=_shade(c, 400, is_dark), border_w=1,
        title=_shade(c, 600, is_dark), desc=_shade(c, 500, is_dark),
        icon=_shade(c, 600, is_dark),
        close=_shade(c, 400, is_dark), close_hover=_shade(c, 600, is_dark),
        progress=_shade(c, 400, is_dark),
    )


# ---- solid：纯色底 + 反色文字 ----

def _solid(c: dict, d: dict, is_dark: bool, color: str) -> dict:
    bg_key = "dark" if is_dark else "light"
    if color == "default":
        bg = _DEFAULT_SOLID_BG[bg_key]
        fg = _DEFAULT_SOLID_FG[bg_key]
    elif color == "foreground":
        bg = _FOREGROUND[bg_key]
        fg = _BACKGROUND[bg_key]
    else:
        # HeroUI: bg-${color} 取 DEFAULT（不参与暗色 swap），secondary 暗色为 400
        bg = c[400 if is_dark and color == "secondary" else 500]
        fg = _SOLID_FG.get(color, "#ffffff")
    return _pack(
        bg=bg, border=None, border_w=0,
        title=fg, desc=fg, icon=fg,
        close=fg, close_hover=fg, progress=fg,
    )


def _pack(
    bg: str,
    border: str | None,
    border_w: int,
    title: str,
    desc: str,
    icon: str,
    close: str,
    close_hover: str,
    progress: str,
) -> dict:
    return {
        "base_bg": bg,
        "border_color": border,
        "border_width": border_w,
        "title_color": title,
        "desc_color": desc,
        "icon_color": icon,
        "close_color": close,
        "close_hover_color": close_hover,
        "progress_color": progress,
    }
