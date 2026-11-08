"""Alert 配色 token：4 variants × 6 colors × 2 themes，对照 HeroUI alert.ts。"""

from __future__ import annotations

from ...themes import HEROUI_COLORS
from ...utils import hex_to_rgba


def build_alert_styles(
    variant: str,
    color: str,
    theme: str,
    radius: str,
) -> dict:
    """按变体返回全部子元素配色 token。

    Args:
        variant: 变体名，决定走 solid / bordered / faded / flat 哪条分支。
        color: 语义色名，未命中时回退 primary。
        theme: 主题名，dark 走深色取值。
        radius: 圆角档位；配色 token 不消费它，圆角由调用方单独处理。

    Returns:
        含 base_bg/base_fg/base_border/icon_wrapper_bg/icon_color/
        title_color/desc_color/close_btn_color 的 dict。
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])
    d = HEROUI_COLORS["default"]

    if variant == "solid":
        return _solid(c, d, is_dark, color)
    if variant == "bordered":
        return _bordered(c, d, is_dark, color)
    if variant == "faded":
        return _faded(c, d, is_dark, color)
    return _flat(c, d, is_dark, color)


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    """求 solid 变体的前景色，保证实色底上文字可读。

    Args:
        color_name: 语义色名；warning 底色过亮，需改用黑字。
        is_dark: 是否深色主题，仅影响 default 分支。

    Returns:
        十六进制前景色字符串。
    """
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


# ---- solid ----


def _solid(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    """生成 solid 变体的配色 token：实色底 + 反色前景。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典，color 为 default 时兜底。
        is_dark: 是否深色主题。
        color_name: 语义色名，决定是否走 default 分支。

    Returns:
        与其他变体结构一致的 token 字典；边框为 none，图标容器底色透明。
    """
    if color_name == "default":
        bg = d[700] if is_dark else d[500]
    else:
        bg = c[500]
    fg = _fg_on_solid(color_name, is_dark)
    return {
        "base_bg": bg,
        "base_fg": fg,
        "base_border": "none",
        "icon_wrapper_bg": "transparent",
        "icon_color": fg,
        "title_color": fg,
        "desc_color": hex_to_rgba(fg, 0.85),
        "close_btn_color": fg,
    }


# ---- flat ----


def _flat(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    """生成 flat 变体的配色 token：浅色底 + 无边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题；深色下底色用色阶 500 加透明度叠加。
        color_name: 语义色名。

    Returns:
        与其他变体结构一致的 token 字典；边框为 none。
    """
    if color_name == "default":
        bg = d[100] if not is_dark else hex_to_rgba(d[500], 0.15)
        fg = d[800] if not is_dark else d[100]
        iwr = d[50] if not is_dark else hex_to_rgba(d[200], 0.15)
        ic = d[700] if not is_dark else d[300]
        dc = d[600] if not is_dark else d[400]
        cb = d[400]
    else:
        bg = c[50] if not is_dark else hex_to_rgba(c[500], 0.2)
        fg = c[600] if not is_dark else c[200]
        iwr = c[100] if not is_dark else hex_to_rgba(c[200], 0.2)
        ic = c[500] if not is_dark else c[400]
        dc = c[500] if not is_dark else c[300]
        cb = c[500] if not is_dark else c[400]
    return {
        "base_bg": bg,
        "base_fg": fg,
        "base_border": "none",
        "icon_wrapper_bg": iwr,
        "icon_color": ic,
        "title_color": fg,
        "desc_color": dc,
        "close_btn_color": cb,
    }


# ---- bordered ----
# 边框较粗(2px)、颜色较深，与 faded 的浅细边框形成对比


def _bordered(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    """生成 bordered 变体的配色 token：透明底 + 2px 深边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名。

    Returns:
        与其他变体结构一致的 token 字典，base_border 为 2px solid。

    Note:
        取值结构与 faded 相同，区别只在边框粗细与颜色深浅。
    """
    if color_name == "default":
        bd = d[300] if not is_dark else d[600]
        fg = d[800] if not is_dark else d[100]
        iwr = d[200] if not is_dark else d[100]
        ic = d[700] if not is_dark else d[300]
        dc = d[600] if not is_dark else d[400]
        cb = d[400]
    else:
        bd = c[300] if not is_dark else c[600]
        fg = c[600] if not is_dark else c[200]
        iwr = c[100] if not is_dark else hex_to_rgba(c[100], 0.15)
        ic = c[500] if not is_dark else c[400]
        dc = c[500] if not is_dark else c[300]
        cb = c[500] if not is_dark else c[400]
    return {
        "base_bg": "transparent",
        "base_fg": fg,
        "base_border": f"2px solid {bd}",
        "icon_wrapper_bg": iwr,
        "icon_color": ic,
        "title_color": fg,
        "desc_color": dc,
        "close_btn_color": cb,
    }


# ---- faded = flat 背景 + 浅色细边框 ----
# 边框较细(1px)、颜色较浅，与 bordered 形成对比


def _faded(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    """生成 faded 变体的配色 token：复用 flat 底色 + 1px 浅边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名。

    Returns:
        在 flat token 基础上覆盖 base_border 的新字典。

    Note:
        用解包新建字典而非就地改 _flat 的返回值，避免污染 flat 变体。
    """
    flat_tokens = _flat(c, d, is_dark, color_name)
    if color_name == "default":
        bd = d[200] if not is_dark else d[700]
    else:
        bd = c[200] if not is_dark else c[700]
    return {
        **flat_tokens,
        "base_border": f"1px solid {bd}",
    }
