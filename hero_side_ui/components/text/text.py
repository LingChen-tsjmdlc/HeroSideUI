"""主题感知的文字组件 ``Text``。完整 API / 示例见 ``docs/text.md``。

本文件只负责：
- token 解析（size / weight / color）
- 选区底色的 HSL 适配算法
- 主题广播接入 + selection 清除等 QLabel 行为调整
“为什么这样写”的坑记在各函数内联。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFocusEvent, QFont, QMouseEvent, QPalette
from PySide6.QtWidgets import QLabel, QWidget

from ...core import FontProvider, ThemeProvider, make_qfont
from ...themes import HEROUI_COLORS

# ============================================================
# 常量映射
# ============================================================

# Tailwind text-xs ~ text-9xl 对齐；md=16px=1rem。
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

# 6 档物理字重 token，与思源 VF 原生 instance 一一对应。
# regular / heavy 是 normal / black 的 alias。其他 token 在 _resolve_weight() 报错。
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

# 默认正文色（不传 color 时使用）
_DEFAULT_TEXT_COLORS: dict = {
    "light": "#27272a",  # default-800
    "dark": "#e4e4e7",  # default-200
}


ColorInput = Union[str, QColor, Tuple[int, int, int], Tuple[int, int, int, int], None]
SizeInput = Union[str, int, float]
WeightInput = Union[str, int, "QFont.Weight"]


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
    # 默认走 500（HeroUI 各 color 的"主色"档）
    shade = 500
    if len(parts) >= 2:
        try:
            shade = int(parts[1])
        except ValueError:
            return None
    if shade not in palette:
        return None
    return QColor(palette[shade])


def _resolve_color(color: ColorInput, theme: str) -> QColor:
    """任意颜色输入 → QColor；None 走主题默认正文色。"""
    if color is None:
        return QColor(_DEFAULT_TEXT_COLORS.get(theme, _DEFAULT_TEXT_COLORS["light"]))

    if isinstance(color, QColor):
        return QColor(color)

    if isinstance(color, (tuple, list)):
        if len(color) == 3:
            r, g, b = color
            return QColor(int(r), int(g), int(b))
        if len(color) == 4:
            r, g, b, a = color
            return QColor(int(r), int(g), int(b), int(a))
        # 长度不对就回退到默认
        return QColor(_DEFAULT_TEXT_COLORS.get(theme, _DEFAULT_TEXT_COLORS["light"]))

    if isinstance(color, str):
        s = color.strip()
        # 1) HeroUI token: "primary" / "primary-500" / ...
        token = _parse_token(s)
        if token is not None:
            return token
        # 2) rgb()/rgba()
        m = _RGBA_RE.match(s)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            a_str = m.group(4)
            if a_str is None:
                return QColor(r, g, b)
            a_f = float(a_str)
            # 若 alpha 是 0~1 浮点，按 CSS 标准 *255；若是 0~255 整数，直接取
            if 0.0 <= a_f <= 1.0:
                return QColor(r, g, b, int(round(a_f * 255)))
            return QColor(r, g, b, int(a_f))
        # 3) HEX 和 Qt 命名色（如 "red"）：交给 QColor
        c = QColor(s)
        if c.isValid():
            return c

    # 兜底：默认正文色
    return QColor(_DEFAULT_TEXT_COLORS.get(theme, _DEFAULT_TEXT_COLORS["light"]))


# ============================================================
# 尺寸 / 字重解析
# ============================================================


def _resolve_size(size: SizeInput) -> int:
    if isinstance(size, (int, float)):
        return max(1, int(size))
    if isinstance(size, str):
        s = size.strip().lower()
        if s in SIZE_MAP:
            return SIZE_MAP[s]
    return SIZE_MAP["md"]


def _resolve_weight(weight: WeightInput) -> int:
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
# 选区底色计算
# ============================================================


def _adapt_selection_bg(text_color: QColor, theme: str) -> QColor:
    """文字色 → 适配的选区底色（亮色出pastel 淡色 / 暗色出低亮度色）。

    用 HSL 而非 RGB：才能同时压饱和度又反转亮度，避免品牌色深色背景出现高饱和药丸色。
    """
    h = text_color.hueF()  # 0–1，灰色时为 -1（设为 0）
    s = text_color.saturationF()  # 0–1
    # 灰色（无 hue）处理：h 设为 0，s 保持 0
    if h < 0:
        h = 0.0
    if theme == "light":
        # 淡色：亮度 88%，饱和度降到原来的 65%（更鲜艳，不脏）
        new_l = 0.88
        new_s = s * 0.65
        alpha = 1.0
    else:
        # 暗色：亮度 15%，饱和度降到原来的 60%
        new_l = 0.15
        new_s = s * 0.60
        alpha = 1.0
    result = QColor()
    result.setHslF(h, new_s, new_l)
    result.setAlphaF(alpha)
    return result


def _selection_palette(
    theme: str,
    force_selection_text_color: bool = True,
    selection_adapts_color: bool = False,
    text_color: Optional[QColor] = None,
) -> Tuple[QColor, QColor]:
    """返 (选区底色, 选中文字色)；语义参考 docs/text.md 中 Selection 一节。"""
    # ---- 选区底色 ----
    if selection_adapts_color and text_color is not None:
        bg = _adapt_selection_bg(text_color, theme)
    else:
        # 默认：主品牌蓝 + 透明度
        primary = QColor(HEROUI_COLORS["primary"][500])
        bg = QColor(primary)
        if theme == "dark":
            bg.setAlphaF(0.35)
        else:
            bg.setAlphaF(0.22)
    # ---- 选中文字色 ----
    if force_selection_text_color:
        fg = QColor("#18181b" if theme == "light" else "#fafafa")
    else:
        if text_color is not None:
            fg = QColor(text_color)
        else:
            default_hex = _DEFAULT_TEXT_COLORS.get(theme, "#27272a")
            fg = QColor(default_hex)
    return bg, fg


# ============================================================
# Text 组件
# ============================================================


class Text(QLabel):
    """主题感知的统一文字组件。API/示例见 ``docs/text.md``。"""

    def __init__(
        self,
        text: str = "",
        *,
        size: SizeInput = "md",
        weight: WeightInput = "normal",
        color: ColorInput = None,
        transparency: float = 1.0,
        selectable: bool = True,
        force_selection_text_color: bool = True,
        selection_adapts_color: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)

        # ---- 状态 ----
        self._size = size
        self._weight = weight
        self._color_input: ColorInput = color
        self._transparency = self._clamp01(transparency)
        self._selectable: bool = selectable
        self._force_selection_text_color: bool = force_selection_text_color
        self._selection_adapts_color: bool = selection_adapts_color
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # ---- 字体 ----
        self._apply_font()

        # ---- QLabel 行为 ----
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._apply_selectable()

        # ---- 颜色 / 选区 palette ----
        self._apply_color()

        # auto 模式注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        # 任何主题模式都注册到 FontProvider，这样全局字体切换时能同步刷新。
        FontProvider.instance().register(self)

    # ============================================================
    # 静态工具
    # ============================================================
    @staticmethod
    def _clamp01(v: float) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 1.0
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # 字体
    # ============================================================
    def _apply_font(self) -> None:
        # FontProvider 会走 setStyleName 精确选 VF 原生 instance。
        font = make_qfont(
            size_px=_resolve_size(self._size),
            weight=_resolve_weight(self._weight),
        )
        self.setFont(font)

    # ============================================================
    # 颜色 / 选区
    # ============================================================
    def _current_color(self) -> QColor:
        c = _resolve_color(self._color_input, self._theme)
        # 透明度叠加
        if self._transparency < 1.0:
            new_alpha = c.alphaF() * self._transparency
            c.setAlphaF(new_alpha)
        return c

    def _apply_color(self) -> None:
        # 同时写 QPalette（a11y/测试读取）和 QSS（实际渲染）——
        # QSS 颜色是创建时快照，主题切换必须重写。
        c = self._current_color()
        rgba_str = f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alphaF():.4f})"
        # 选区色：返回 QColor 对象（含 alpha）
        bg, fg = _selection_palette(
            self._theme,
            force_selection_text_color=self._force_selection_text_color,
            selection_adapts_color=self._selection_adapts_color,
            text_color=c,
        )
        # 1) 写 QPalette（测试 + 无障碍 读取）
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Highlight, bg)
        pal.setColor(QPalette.ColorRole.HighlightedText, fg)
        self.setPalette(pal)
        # 2) 写 QSS（视觉渲染）
        bg_css = f"rgba({bg.red()}, {bg.green()}, {bg.blue()}, {bg.alphaF():.4f})"
        fg_css = f"rgba({fg.red()}, {fg.green()}, {fg.blue()}, {fg.alphaF():.4f})"
        self.setStyleSheet(
            f"QLabel {{ "
            f"color: {rgba_str}; "
            f"background: transparent; "
            f"selection-color: {fg_css}; "
            f"selection-background-color: {bg_css}; "
            f"}}"
        )

    # ============================================================
    # 主题切换
    # ============================================================
    def set_theme(self, theme: str) -> None:
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_color()

    def _apply_provider_theme(self, theme: str) -> None:
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._apply_color()

    # ============================================================
    # 选区管理
    # ============================================================

    def _clear_selection(self) -> None:
        # QLabel 无 clearSelection() API；重置内部 QTextControl 的唯一手段是
        # “置空文本再赋回”，顺便关 updates 避免闪烁。
        text = self.text()
        if not text:
            return
        self.setUpdatesEnabled(False)
        self.setText("")
        self.setText(text)
        self.setUpdatesEnabled(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # 非 Shift 点击 → 单选行为，先清自己的选区。
        if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._clear_selection()
        super().mousePressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._clear_selection()
        super().focusOutEvent(event)

    # ============================================================
    # 公共动态 setter
    # ============================================================
    def set_size(self, size: SizeInput) -> None:
        self._size = size
        self._apply_font()

    def set_weight(self, weight: WeightInput) -> None:
        self._weight = weight
        self._apply_font()

    def set_color(self, color: ColorInput) -> None:
        self._color_input = color
        self._apply_color()

    def set_transparency(self, transparency: float) -> None:
        self._transparency = self._clamp01(transparency)
        self._apply_color()

    def set_force_selection_text_color(self, force: bool) -> None:
        self._force_selection_text_color = bool(force)
        self._apply_color()

    def set_selection_adapts_color(self, enabled: bool) -> None:
        self._selection_adapts_color = bool(enabled)
        self._apply_color()

    # ============================================================
    # selectable
    # ============================================================
    def _apply_selectable(self) -> None:
        if self._selectable:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        else:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_selectable(self, selectable: bool) -> None:
        self._selectable = bool(selectable)
        self._apply_selectable()

    # ============================================================
    # 只读访问器
    # ============================================================
    @property
    def text_color(self) -> QColor:
        # 已叠加 transparency 的实际渲染色。
        return self._current_color()

    @property
    def theme(self) -> str:
        return self._theme


# ============================================================
# 向后兼容：Title / Subtitle / Caption / Body
# ============================================================


class Title(Text):
    """主标题 — level=1/2/3 → 2xl/xl/lg Bold。"""

    _LEVEL_SIZE = {1: "2xl", 2: "xl", 3: "lg"}

    def __init__(
        self,
        text: str = "",
        level: int = 1,
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        size = self._LEVEL_SIZE.get(level, "2xl")
        super().__init__(
            text,
            size=size,
            weight="bold",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


class Subtitle(Text):
    """副标题 — sm + 主题感知灰色。"""

    def __init__(
        self,
        text: str = "",
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        if color is None:
            theme_now = self._resolve_theme(theme)
            color = "#71717a" if theme_now == "light" else "#a1a1aa"
        super().__init__(
            text,
            size="sm",  # 14px
            weight="normal",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


class Caption(Text):
    """辅助提示 — xs + 最低对比度灰色。"""

    def __init__(
        self,
        text: str = "",
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        if color is None:
            theme_now = self._resolve_theme(theme)
            color = "#a1a1aa" if theme_now == "light" else "#71717a"
        super().__init__(
            text,
            size="xs",  # 12px
            weight="normal",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


class Body(Text):
    """正文 — 语义化 alias，等价 ``Text(size='md')``。"""

    def __init__(
        self,
        text: str = "",
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        parent: Optional[QWidget] = None,
        **kwargs,
    ):
        super().__init__(
            text,
            size="md",
            weight="normal",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


__all__ = [
    "Text",
    "Title",
    "Subtitle",
    "Caption",
    "Body",
    "SIZE_MAP",
    "WEIGHT_MAP",
]
