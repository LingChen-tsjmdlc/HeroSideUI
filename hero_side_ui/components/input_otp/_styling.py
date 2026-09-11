"""InputOtp 配色 token（4 variants × 6 colors × 2 themes × invalid 状态）。

对照 HeroUI inputOtp.ts 的 variants + compoundVariants：
- flat:    透明边框 + bg-*-100，active bg-*-200，文字语义色
- faded:   bg-*-100 + border-*-200(2px)，active border 语义色
- bordered: bg-background + border-*-200(2px)，active border 语义色
- underlined: bg-background + 底边 2px + active 下划线展开，文字语义色
- isInvalid: flat→bg-danger-50/active bg-danger-100；bordered/underlined→
  border-danger-200 + active danger-400；faded 保留原配色只覆盖文字；
  caret/passwordChar 一律 danger
- isReadOnly: caret 透明（组件层处理）
注意：官方 segment 的 hover:bg-danger 为源码瑕疵，桌面端不采纳。
暗色规则：HEROUI_COLORS 存亮色原始值，浅阶引用需做索引镜像反转
（50↔900 / 100↔800 / 200↔700 / 300↔600 / 400↔500），DEFAULT(500) 不反转。
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS

# 色阶镜像序列（暗色取反：_SHADES[i] ↔ _SHADES[9-i]）
_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)


def _shade(c: dict, shade: int, is_dark: bool) -> str:
    """取色阶；暗色下按索引镜像反转（对齐官方 swapColorValues）。"""
    if not is_dark:
        return c[shade]
    return c[_SHADES[9 - _SHADES.index(shade)]]


def _foreground(theme: str) -> str:
    """default-foreground：亮黑暗白（有值文字色，注意与 bg-background 相反）。"""
    return "#ffffff" if theme == "dark" else "#000000"


def build_input_otp_styles(
    variant: str, color: str, theme: str, is_invalid: bool = False, is_read_only: bool = False
) -> dict:
    """返回段/光标/密码点的配色 token。

    Keys: bg, border, border_w, text, text_filled, active_bg,
    active_border, caret_color, dot_color, underline_base, underline_active
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["default"])
    d = HEROUI_COLORS["default"]
    danger = HEROUI_COLORS["danger"]
    # bg-background：亮白暗黑（注意与 default-foreground 正好相反）
    fg_bg = "#000000" if is_dark else "#ffffff"
    border_w = 2 if variant in ("faded", "bordered", "underlined") else 1
    filled_fg = _foreground(theme) if color == "default" else c[500]

    if is_invalid:
        if variant == "flat":
            return _tok(_shade(danger, 50, is_dark), "none", 1, danger[500],
                        _shade(danger, 100, is_dark), "none", danger[500])
        if variant == "faded":
            # 官方 faded invalid 只覆盖文字与 caret，底/边保持 variant 配色
            return _tok(_shade(c, 100, is_dark), _shade(c, 200, is_dark), 2,
                        danger[500], None, c[500], danger[500],
                        filled_fg=danger[500])
        if variant == "bordered":
            return _tok(fg_bg, _shade(danger, 200, is_dark), 2, danger[500], None,
                        _shade(danger, 400, is_dark), danger[500],
                        filled_fg=danger[500])
        return _tok(fg_bg, _shade(danger, 200, is_dark), 2, danger[500], None,
                    _shade(danger, 400, is_dark), danger[500],
                    underline_base=_shade(danger, 200, is_dark),
                    underline_active=_shade(danger, 400, is_dark),
                    filled_fg=danger[500])

    if variant == "flat":
        return _tok(_shade(c, 100, is_dark), "none", 1, c[500],
                    _shade(c, 200, is_dark), "none", c[500],
                    filled_fg=filled_fg)
    if variant == "faded":
        return _tok(_shade(c, 100, is_dark), _shade(c, 200, is_dark), 2, c[500],
                    None, c[500], c[500],
                    filled_fg=filled_fg)
    if variant == "bordered":
        return _tok(fg_bg, _shade(c, 200, is_dark), 2, c[500], None, c[500], c[500],
                    filled_fg=filled_fg)
    # underlined
    return _tok(fg_bg, _shade(c, 200, is_dark), 2, c[500], None, None, c[500],
                underline_base=_shade(c, 200, is_dark), underline_active=c[500],
                filled_fg=filled_fg)


def _tok(bg, border, border_w, text, active_bg, active_border, caret_color,
         underline_base=None, underline_active=None, filled_fg=None) -> dict:
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
