"""Toast 配色 token：暗色取色统一走 _shade()（色阶索引镜像反转，DEFAULT 除外）。"""

from __future__ import annotations

from collections.abc import Mapping

from ...themes import HEROUI_COLORS
from ...themes.theme_values import (
    get_background,
    get_color_foreground,
    get_content_background,
    get_foreground,
)

# 语义色阶（HeroUI common.* 只有这 10 档，暗色 swap 靠首尾反转）
_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)


class _TokenView(Mapping):
    """亮/暗两侧的只读视图：键 light/dark，值每次取自当前主题取值。"""

    def __init__(self, getter):
        self._get = getter

    def __getitem__(self, side: str) -> str:
        if side not in ("light", "dark"):
            raise KeyError(side)
        return self._get(side)

    def __iter__(self):
        return iter(("light", "dark"))

    def __len__(self) -> int:
        return 2


# 窗口底 / 默认文字 / 内容面：随 setup 配置变化
_BACKGROUND = _TokenView(get_background)
_FOREGROUND = _TokenView(get_foreground)
_CONTENT1 = _TokenView(get_content_background)

# default.DEFAULT 不参与暗色 swap
_DEFAULT_SOLID_BG = {"light": "#d4d4d8", "dark": "#3f3f46"}
_DEFAULT_SOLID_FG = _FOREGROUND


def _solid_fg(color: str, side: str) -> str:
    """solid 变体的文字色。

    Args:
        color: 语义色名。
        side: "light" 或 "dark"。

    Note:
        success 底色偏亮，浅字对比度不足，固定用深色文字；其余取 color_foreground。
    """
    if color == "success":
        return get_foreground("light")
    return get_color_foreground(color, side)


def _shade(scale: dict, n: int, is_dark: bool) -> str:
    """取语义色阶；暗色下按 HeroUI 的 swap 规则首尾反转（50 ↔ 900）。"""
    if not is_dark:
        return scale[n]
    idx = _SHADES.index(n)
    return scale[_SHADES[len(_SHADES) - 1 - idx]]


def build_toast_styles(variant: str, color: str, theme: str) -> dict:
    """返回各子元素颜色 token。

    Keys: base_bg, border_color, border_width, title_color, desc_color,
    icon_color, close_color, close_hover_color, progress_color。
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
    """组装 flat 变体的颜色 token。"""
    if color == "default":
        bg = _CONTENT1["dark" if is_dark else "light"]
        fg = _FOREGROUND["dark" if is_dark else "light"]
        return _pack(
            bg=bg,
            border=_shade(d, 100, is_dark),
            border_w=1,
            title=fg,
            desc=_shade(d, 500, is_dark),
            icon=fg,
            close=_shade(d, 400, is_dark),
            close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    if color == "foreground":
        fg = _BACKGROUND["dark" if is_dark else "light"]
        return _pack(
            bg=_FOREGROUND["dark" if is_dark else "light"],
            border=_shade(d, 100, is_dark),
            border_w=1,
            title=fg,
            desc=fg,
            icon=fg,
            close=_shade(d, 400, is_dark),
            close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    return _pack(
        bg=_shade(c, 50, is_dark),
        border=_shade(c, 100, is_dark),
        border_w=1,
        title=_shade(c, 600, is_dark),
        desc=_shade(c, 500, is_dark),
        icon=_shade(c, 600, is_dark),
        close=_shade(c, 400, is_dark),
        close_hover=_shade(c, 600, is_dark),
        progress=_shade(c, 400, is_dark),
    )


# ---- bordered：背景色底 + 主色边框 ----


def _bordered(c: dict, d: dict, is_dark: bool, color: str) -> dict:
    """组装 bordered 变体的颜色 token。"""
    bg_key = "dark" if is_dark else "light"
    if color == "default":
        return _pack(
            bg=_BACKGROUND[bg_key],
            border=_shade(d, 200, is_dark),
            border_w=1,
            title=_FOREGROUND[bg_key],
            desc=_shade(d, 500, is_dark),
            icon=_FOREGROUND[bg_key],
            close=_shade(d, 400, is_dark),
            close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    if color == "foreground":
        fg = _BACKGROUND[bg_key]
        return _pack(
            bg=_FOREGROUND[bg_key],
            border=_shade(d, 400, is_dark),
            border_w=1,
            title=fg,
            desc=fg,
            icon=fg,
            close=_shade(d, 400, is_dark),
            close_hover=_shade(d, 600, is_dark),
            progress=_shade(d, 400, is_dark),
        )
    return _pack(
        bg=_BACKGROUND[bg_key],
        border=_shade(c, 400, is_dark),
        border_w=1,
        title=_shade(c, 600, is_dark),
        desc=_shade(c, 500, is_dark),
        icon=_shade(c, 600, is_dark),
        close=_shade(c, 400, is_dark),
        close_hover=_shade(c, 600, is_dark),
        progress=_shade(c, 400, is_dark),
    )


# ---- solid：纯色底 + 反色文字 ----


def _solid(c: dict, d: dict, is_dark: bool, color: str) -> dict:
    """组装 solid 变体的颜色 token。"""
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
        fg = _solid_fg(color, bg_key)
    return _pack(
        bg=bg,
        border=None,
        border_w=0,
        title=fg,
        desc=fg,
        icon=fg,
        close=fg,
        close_hover=fg,
        progress=fg,
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
    """把各子元素颜色打包为 token 字典。"""
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
