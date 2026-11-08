"""InputOtp 配色 token：4 variants × 6 colors × 2 themes × invalid。
暗色浅阶引用需索引镜像反转（50↔900 等）。
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS

# 色阶镜像序列（暗色取反：_SHADES[i] ↔ _SHADES[9-i]）
_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)


def _shade(c: dict, shade: int, is_dark: bool) -> str:
    """取色阶；暗色下按索引镜像反转（对齐官方 swapColorValues）。

    Args:
        c: 色阶字典（如 HEROUI_COLORS[color]）。
        shade: 目标色阶档位（50~900）。
        is_dark: 是否深色主题。

    Returns:
        str: 对应色阶的十六进制色串；暗色按 50↔900 镜像互换。
    """
    if not is_dark:
        return c[shade]
    return c[_SHADES[9 - _SHADES.index(shade)]]


def _foreground(theme: str) -> str:
    """default-foreground：亮黑暗白（有值文字色，注意与 bg-background 相反）。

    Args:
        theme: 主题名（light / dark）。

    Returns:
        str: 亮色返回黑、暗色返回白。
    """
    return "#ffffff" if theme == "dark" else "#000000"


def build_input_otp_styles(
    variant: str,
    color: str,
    theme: str,
    is_invalid: bool = False,
    is_read_only: bool = False,
) -> dict:
    """返回段 / 光标 / 密码点配色 token 字典。

    Args:
        variant: flat / faded / bordered / underlined。
        color: 语义色名（default / primary / danger 等）。
        theme: light / dark。
        is_invalid: 是否错误态（覆盖配色为 danger）。
        is_read_only: 是否只读（影响 underline 等非活跃态）。

    Returns:
        dict: 含 bg / border / border_w / text / text_filled / active_bg /
        active_border / caret_color / dot_color / underline_base /
        underline_active 的配色 token。
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["default"])
    HEROUI_COLORS["default"]
    danger = HEROUI_COLORS["danger"]
    # bg-background：亮白暗黑（注意与 default-foreground 正好相反）
    fg_bg = "#000000" if is_dark else "#ffffff"
    filled_fg = _foreground(theme) if color == "default" else c[500]

    if is_invalid:
        if variant == "flat":
            return _tok(
                _shade(danger, 50, is_dark),
                "none",
                1,
                danger[500],
                _shade(danger, 100, is_dark),
                "none",
                danger[500],
            )
        if variant == "faded":
            # 官方 faded invalid 只覆盖文字与 caret，底/边保持 variant 配色
            return _tok(
                _shade(c, 100, is_dark),
                _shade(c, 200, is_dark),
                2,
                danger[500],
                None,
                c[500],
                danger[500],
                filled_fg=danger[500],
            )
        if variant == "bordered":
            return _tok(
                fg_bg,
                _shade(danger, 200, is_dark),
                2,
                danger[500],
                None,
                _shade(danger, 400, is_dark),
                danger[500],
                filled_fg=danger[500],
            )
        return _tok(
            fg_bg,
            _shade(danger, 200, is_dark),
            2,
            danger[500],
            None,
            _shade(danger, 400, is_dark),
            danger[500],
            underline_base=_shade(danger, 200, is_dark),
            underline_active=_shade(danger, 400, is_dark),
            filled_fg=danger[500],
        )

    if variant == "flat":
        return _tok(
            _shade(c, 100, is_dark),
            "none",
            1,
            c[500],
            _shade(c, 200, is_dark),
            "none",
            c[500],
            filled_fg=filled_fg,
        )
    if variant == "faded":
        return _tok(
            _shade(c, 100, is_dark),
            _shade(c, 200, is_dark),
            2,
            c[500],
            None,
            c[500],
            c[500],
            filled_fg=filled_fg,
        )
    if variant == "bordered":
        return _tok(
            fg_bg,
            _shade(c, 200, is_dark),
            2,
            c[500],
            None,
            c[500],
            c[500],
            filled_fg=filled_fg,
        )
    # underlined
    return _tok(
        fg_bg,
        _shade(c, 200, is_dark),
        2,
        c[500],
        None,
        None,
        c[500],
        underline_base=_shade(c, 200, is_dark),
        underline_active=c[500],
        filled_fg=filled_fg,
    )


def _tok(
    bg,
    border,
    border_w,
    text,
    active_bg,
    active_border,
    caret_color,
    underline_base=None,
    underline_active=None,
    filled_fg=None,
) -> dict:
    """把散落参数打包成配色 token 字典。

    Args:
        bg: 段背景色（"none" 表示不画）。
        border: 段边框色（"none" 表示不画）。
        border_w: 边框宽度（像素）。
        text: 未填值时的文字色。
        active_bg: 活动段背景色（可空）。
        active_border: 活动段边框色（可空）。
        caret_color: 光标 / 密码点颜色。
        underline_base: underlined 静止下划线色（可空）。
        underline_active: underlined 活动下划线色（可空）。
        filled_fg: 有值文字色（默认回退到 text）。

    Returns:
        dict: 含全部字段的配色 token。
    """
    return {
        "bg": bg,
        "border": border,
        "border_w": border_w,
        "text": text,
        # bordered/underlined default 色有值时文字转 default-foreground（官方
        # data-[has-value=true]:text-default-foreground）
        "text_filled": filled_fg or text,
        "active_bg": active_bg,
        "active_border": active_border,
        "caret_color": caret_color,
        # passwordChar 与 caret 同色（官方 compound 一致）
        "dot_color": caret_color,
        "underline_base": underline_base,
        "underline_active": underline_active,
    }
