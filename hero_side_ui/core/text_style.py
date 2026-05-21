"""文字样式解析工具：颜色 / 字号 / 字重 / QFont 构造。

`Text` 组件与少数无法用子控件承载文字的自绘组件（cursor 动画驱动定位的
tabs、checkbox 内嵌 label、switch on/off label、divider 文本）共用此模块，
确保"颜色解析口径 + 字体来源"全项目唯一。

只放纯函数，不持有任何状态。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, Union

from PySide6.QtGui import QColor, QFont

from ..themes import HEROUI_COLORS
from .font_provider import make_qfont

# ============================================================
# 公共类型
# ============================================================

ColorInput = Union[str, QColor, Tuple[int, int, int], Tuple[int, int, int, int], None]
SizeInput = Union[str, int, float]
WeightInput = Union[str, int, "QFont.Weight"]

# ============================================================
# Tailwind text-* 字号 token
# ============================================================

SIZE_MAP: dict = {
    "xs": 12,
    "sm": 14,
    "md": 16,
    "lg": 18,
    "xl": 20,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
    "5xl": 48,
    "6xl": 60,
    "7xl": 72,
    "8xl": 96,
    "9xl": 128,
}

# ============================================================
# 6 档物理字重 token（与思源 VF 原生 instance 一一对应）
# ============================================================

WEIGHT_MAP: dict = {
    "extralight": QFont.Weight.ExtraLight,  # 200
    "light": QFont.Weight.Light,  # 300
    "normal": QFont.Weight.Normal,  # 400
    "regular": QFont.Weight.Normal,  # 400 (alias)
    "medium": QFont.Weight.Medium,  # 500
    "bold": QFont.Weight.Bold,  # 700
    "black": QFont.Weight.Black,  # 900
    "heavy": QFont.Weight.Black,  # 900 (alias)
}

# ============================================================
# 默认正文色（不传 color 时使用）
# ============================================================

DEFAULT_TEXT_COLORS: dict = {
    "light": "#27272a",  # default-800
    "dark": "#e4e4e7",  # default-200
}

# ============================================================
# 颜色解析
# ============================================================

_RGBA_RE = re.compile(
    r"^\s*rgba?\(\s*"
    r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)"
    r"(?:\s*,\s*([\d.]+))?"
    r"\s*\)\s*$",
    re.IGNORECASE,
)


def _parse_token(token: str) -> Optional[QColor]:
    """HeroUI token → QColor；不匹配返 None 交给调用方继续走 HEX/QColor。"""
    parts = token.strip().split("-")
    name = parts[0].lower()
    if name not in HEROUI_COLORS:
        return None
    palette = HEROUI_COLORS[name]
    shade = 500
    if len(parts) >= 2:
        try:
            shade = int(parts[1])
        except ValueError:
            return None
    if shade not in palette:
        return None
    return QColor(palette[shade])


def resolve_text_color(color: ColorInput, theme: str) -> QColor:
    """任意颜色输入 → QColor；None 走主题默认正文色。"""
    if color is None:
        return QColor(DEFAULT_TEXT_COLORS.get(theme, DEFAULT_TEXT_COLORS["light"]))

    if isinstance(color, QColor):
        return QColor(color)

    if isinstance(color, (tuple, list)):
        if len(color) == 3:
            r, g, b = color
            return QColor(int(r), int(g), int(b))
        if len(color) == 4:
            r, g, b, a = color
            return QColor(int(r), int(g), int(b), int(a))
        return QColor(DEFAULT_TEXT_COLORS.get(theme, DEFAULT_TEXT_COLORS["light"]))

    if isinstance(color, str):
        s = color.strip()
        token = _parse_token(s)
        if token is not None:
            return token
        m = _RGBA_RE.match(s)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            a_str = m.group(4)
            if a_str is None:
                return QColor(r, g, b)
            a_f = float(a_str)
            if 0.0 <= a_f <= 1.0:
                return QColor(r, g, b, int(round(a_f * 255)))
            return QColor(r, g, b, int(a_f))
        c = QColor(s)
        if c.isValid():
            return c

    return QColor(DEFAULT_TEXT_COLORS.get(theme, DEFAULT_TEXT_COLORS["light"]))


# ============================================================
# 尺寸 / 字重解析
# ============================================================


def resolve_text_size(size: SizeInput) -> int:
    if isinstance(size, (int, float)):
        return max(1, int(size))
    if isinstance(size, str):
        s = size.strip().lower()
        if s in SIZE_MAP:
            return SIZE_MAP[s]
    return SIZE_MAP["md"]


def resolve_text_weight(weight: WeightInput) -> int:
    """字重 → Qt weight (1~1000)；未知字符串抛 ValueError（不静默兜底）。"""
    if isinstance(weight, QFont.Weight):
        return int(weight)
    if isinstance(weight, int):
        return max(1, min(1000, weight))
    if isinstance(weight, str):
        s = weight.strip().lower().replace("-", "").replace("_", "")
        if s in WEIGHT_MAP:
            return int(WEIGHT_MAP[s])
        raise ValueError(
            f"Unsupported weight token {weight!r}; "
            f"expected one of {sorted(WEIGHT_MAP.keys())} "
            "or QFont.Weight / int(1~1000)."
        )
    raise TypeError(
        f"weight must be str / int / QFont.Weight, got {type(weight).__name__}."
    )


# ============================================================
# QFont 构造（薄包装，让自绘组件不直接 import make_qfont）
# ============================================================


def make_text_qfont(size: SizeInput = "md", weight: WeightInput = "normal") -> QFont:
    """统一字体入口：走 FontProvider，自带 setStyleName 精确选 VF instance。"""
    return make_qfont(
        size_px=resolve_text_size(size),
        weight=resolve_text_weight(weight),
    )


# ============================================================
# 选区调色板（全局唯一来源）
# ============================================================
#
# 整个组件库的"框选反馈"必须从这里取色，保证：
#   1. 选中底 = 半透明 primary（不挑文字色，不挑 wrapper 底色）
#   2. 选中文字色 = 强制深色（亮）/ 浅色（暗），独立于文字本色
# 任何让 selection 与"组件状态色（hover/focus/variant）"耦合的写法都是错的，
# 早期 Input/Textarea 写死 colors[200] 与 hover 撞色就是教训。


def _adapt_selection_bg(text_color: QColor, theme: str) -> QColor:
    """文字色 → 适配的选区底色（亮色出 pastel 淡色 / 暗色出低亮度色）。

    HSL 而非 RGB：同时压饱和度又反转亮度，避免品牌色深色背景出现高饱和药丸色。
    仅在 selection_adapts_color=True 时启用。
    """
    h = text_color.hueF()
    s = text_color.saturationF()
    if h < 0:
        h = 0.0
    if theme == "light":
        new_l = 0.88
        new_s = s * 0.65
    else:
        new_l = 0.15
        new_s = s * 0.60
    result = QColor()
    result.setHslF(h, new_s, new_l)
    result.setAlphaF(1.0)
    return result


def selection_palette(
    theme: str,
    *,
    force_selection_text_color: bool = True,
    selection_adapts_color: bool = False,
    text_color: Optional[QColor] = None,
) -> Tuple[QColor, QColor]:
    """返回 (选区底色, 选中文字色)。Text/Input/Textarea 等所有可选中文字组件共用。

    默认行为（force_selection_text_color=True 且 selection_adapts_color=False）：
        - 选中底：半透明 primary-500（亮色 alpha=0.22 / 暗色 alpha=0.35）
        - 选中字：亮色一律 #18181b / 暗色一律 #fafafa
    """
    # ---- 选中底色 ----
    if selection_adapts_color and text_color is not None:
        bg = _adapt_selection_bg(text_color, theme)
    else:
        primary = QColor(HEROUI_COLORS["primary"][500])
        bg = QColor(primary)
        bg.setAlphaF(0.35 if theme == "dark" else 0.22)
    # ---- 选中文字色 ----
    if force_selection_text_color:
        fg = QColor("#18181b" if theme == "light" else "#fafafa")
    else:
        if text_color is not None:
            fg = QColor(text_color)
        else:
            fg = QColor(DEFAULT_TEXT_COLORS.get(theme, "#27272a"))
    return bg, fg


__all__ = [
    "ColorInput",
    "SizeInput",
    "WeightInput",
    "SIZE_MAP",
    "WEIGHT_MAP",
    "DEFAULT_TEXT_COLORS",
    "resolve_text_color",
    "resolve_text_size",
    "resolve_text_weight",
    "make_text_qfont",
    "selection_palette",
]
