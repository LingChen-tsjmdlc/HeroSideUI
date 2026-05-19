"""
HeroSideUI 主题感知文字组件（Text）
====================================

提供一个统一的、主题感知的文字组件 :class:`Text`（继承 ``QLabel``），
所有组件库内部 / demo / 用户代码都应该用它来渲染文字，从而：

- 自动跟随 ``ThemeProvider`` 切换亮暗色（``theme="auto"``）。
- 颜色 token 统一走 ``hero_side_ui.themes.colors.HEROUI_COLORS``，避免 hex 散落。
- 字号 / 字重的语义化命名对齐 Tailwind 体系（``text-xs ~ text-9xl``、``font-thin ~ font-black``）。
- 鼠标框选时高亮底色根据主题 + 文字色 + 主品牌蓝自动算合理对比度，亮暗模式都好看。

为了向后兼容，旧的语义化别名 ``Title / Subtitle / Caption / Body`` 仍然导出，
全部基于新的 :class:`Text` 实现。

API 速览
--------
.. code-block:: python

    Text("Hello")                                         # 默认 md / normal / 主题字色
    Text("Big", size="3xl", weight="bold")                # 30px Bold
    Text("Brand", color="primary")                        # HeroUI primary-500
    Text("Brand 700", color="primary-700")                # HeroUI primary-700
    Text("Custom", color="#FF8800")                       # HEX
    Text("RGBA", color=(255, 0, 0, 128))                  # RGBA tuple
    Text("Half opacity", color="primary", transparency=0.5)
    Text("Forced dark", theme="dark")                     # 硬锁暗色（不受 ThemeProvider 影响）
    # 框选文字色控制
    Text("Keep color", color="danger", force_selection_text_color=False)  # 框选后文字色不变
    # 选区底色适配文字色
    Text("Adaptive bg", color="danger", selection_adapts_color=True)   # 底色随文字色变化

参数
----
- ``size``: ``"xs"`` / ``"sm"`` / ``"md"`` / ``"lg"`` / ``"xl"`` / ``"2xl"`` ~ ``"9xl"``，
  也支持直接传 ``int`` / ``float``（像素）。
- ``weight``: ``"thin"`` / ``"extralight"`` / ``"light"`` / ``"normal"`` / ``"medium"`` /
  ``"semibold"`` / ``"bold"`` / ``"extrabold"`` / ``"black"``，也支持 ``QFont.Weight`` 或
  ``int`` (1-1000)。
- ``color``: 见 "颜色解析" 一节。``None`` → 跟随主题默认正文色。
- ``transparency``: ``0.0 ~ 1.0`` 透明度，会乘到最终颜色 alpha 上（``0`` 完全透明、
  ``1`` 完全不透明，默认 ``1.0``）。
- ``force_selection_text_color``: ``bool``（默认 ``True``）。
  ``True``：框选文字色强制为暗色（亮色模式）/ 亮色（暗色模式）；
  ``False``：框选文字色与原文字色保持一致（不做任何改变）。
- ``selection_adapts_color``: ``bool``（默认 ``False``）。
  ``False``：选区底色永远用主品牌蓝（``primary-500``）；
  ``True``：选区底色根据文字颜色自动生成（HSL 算法，亮暗模式都适配）。
- ``theme``: ``"auto"`` (默认) / ``"light"`` / ``"dark"``。``auto`` 会自动注册到
  ``ThemeProvider``，主题切换时自动刷新文字色 / 选区底色。

颜色解析
--------
``color`` 接受以下任意一种：

1. HeroUI token 字符串，如 ``"primary"``、``"danger-700"``、``"default-300"``。
   不带数字时默认走 500 档；和 ``Button``/``Input`` 等其他组件的 ``color=`` 同语义。
2. HEX 字符串，如 ``"#FF8800"`` (6 位)，或 Qt 风格 ``"#80FF8800"`` (8 位 ``#AARRGGBB``)。
3. RGB / RGBA tuple，如 ``(255, 136, 0)`` 或 ``(255, 136, 0, 200)``。
4. CSS 风格 ``"rgba(r, g, b, a)"`` / ``"rgb(r, g, b)"`` 字符串。
5. ``QColor`` 对象。

不传 / 传 ``None`` 时使用主题感知的默认正文色（亮色 ``#27272a``、暗色 ``#e4e4e7``）。

选区底色（鼠标框选）
--------------------
- ``force_selection_text_color=True``（默认）：选中文字色强制为暗色（亮色模式）/
  亮色（暗色模式），与原文字色无关。
- ``force_selection_text_color=False``：选中文字色与原文字色保持一致。
- ``selection_adapts_color=False``（默认）：选区底色永远用主品牌蓝
  ``primary-500``（亮色 @22% / 暗色 @35% alpha）。
- ``selection_adapts_color=True``：选区底色根据文字颜色自动生成
  （HSL 算法：亮色模式生成淡色，暗色模式生成暗色）。

实现细节：通过 QSS ``selection-color`` / ``selection-background-color`` 设置
选区颜色，每个实例独立 QSS，不污染父级。支持 Ctrl+点击多选不同 Text 实例。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFocusEvent, QFont, QMouseEvent, QPalette
from PySide6.QtWidgets import QLabel, QWidget

from ...core import ThemeProvider
from ...themes import FONT_FAMILY, HEROUI_COLORS


# ============================================================
# 常量映射
# ============================================================

#: Tailwind 风格字号映射（像素）
SIZE_MAP: dict = {
    "xs":  12,
    "sm":  13,
    "md":  14,
    "lg":  16,
    "xl":  18,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
    "5xl": 48,
    "6xl": 60,
    "7xl": 72,
    "8xl": 96,
    "9xl": 128,
}

#: Tailwind 风格字重映射 → Qt weight 整数
WEIGHT_MAP: dict = {
    "thin":       QFont.Weight.Thin,        # 100
    "extralight": QFont.Weight.ExtraLight,  # 200
    "light":      QFont.Weight.Light,       # 300
    "normal":     QFont.Weight.Normal,      # 400
    "regular":    QFont.Weight.Normal,      # 400 (alias)
    "medium":     QFont.Weight.Medium,      # 500
    "semibold":   QFont.Weight.DemiBold,    # 600
    "demibold":   QFont.Weight.DemiBold,    # 600 (alias)
    "bold":       QFont.Weight.Bold,        # 700
    "extrabold":  QFont.Weight.ExtraBold,   # 800
    "black":      QFont.Weight.Black,       # 900
    "heavy":      QFont.Weight.Black,       # 900 (alias)
}

#: 默认正文色（不传 color 时使用）
_DEFAULT_TEXT_COLORS: dict = {
    "light": "#27272a",  # default-800
    "dark":  "#e4e4e7",  # default-200
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
    """解析 HeroUI token 字符串，如 ``"primary"``、``"danger-700"``。

    返回 None 表示这不是 HeroUI token，调用方应继续走 HEX/QColor 解析。
    """
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
    """把任意支持的颜色输入归一化为 ``QColor``。

    传 ``None`` 时返回主题默认正文色。
    """
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
    if isinstance(weight, QFont.Weight):
        return int(weight)
    if isinstance(weight, int):
        # Qt weight 范围 1~1000
        return max(1, min(1000, weight))
    if isinstance(weight, str):
        s = weight.strip().lower().replace("-", "").replace("_", "")
        if s in WEIGHT_MAP:
            return int(WEIGHT_MAP[s])
    return int(QFont.Weight.Normal)


# ============================================================
# 选区底色计算
# ============================================================

def _adapt_selection_bg(text_color: QColor, theme: str) -> QColor:
    """根据文字色生成适配的选区底色（HSL 算法，适配亮/暗色模式）。

    - 亮色模式：生成淡色（pastel 风格，高亮度、低饱和度）
    - 暗色模式：生成暗色（低亮度、中等饱和度）
    """
    h = text_color.hueF()          # 0–1，灰色时为 -1（设为 0）
    s = text_color.saturationF()   # 0–1
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
) -> Tuple[str, str]:
    """返回 (selection-background-color, selection-color) 的 CSS 字符串。

    - force_selection_text_color=True（默认）：选中文字强制暗色/亮色，与原文字色无关。
    - force_selection_text_color=False：选中文字色 = 原文字色（"不做任何改变"）。
    - selection_adapts_color=True：选区底色适配文字色（HeroUI token / 自定义均走 HSL 算法）。
    - selection_adapts_color=False（默认）：底色永远用主品牌蓝。
    """
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
    bg_css = f"rgba({bg.red()}, {bg.green()}, {bg.blue()}, {bg.alphaF():.4f})"

    # ---- 选中文字色 ----
    if force_selection_text_color:
        fg = QColor("#18181b" if theme == "light" else "#fafafa")
    else:
        if text_color is not None:
            fg = QColor(text_color)
        else:
            default_hex = _DEFAULT_TEXT_COLORS.get(theme, "#27272a")
            fg = QColor(default_hex)
    fg_css = f"rgba({fg.red()}, {fg.green()}, {fg.blue()}, {fg.alphaF():.4f})"
    return bg_css, fg_css


# ============================================================
# Text 组件
# ============================================================

class Text(QLabel):
    """主题感知的统一文字组件。

    所有 HeroSideUI 内部以及上层应用都应该用 ``Text`` 来渲染文字内容，
    而不是直接 ``QLabel + setStyleSheet("color: #...")``。这样可以保证
    主题切换时文字色自动跟随，HEX 色不再散落在业务代码里。

    详见模块顶部 docstring。
    """

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
        font = QFont(FONT_FAMILY)
        font.setPixelSize(_resolve_size(self._size))
        font.setWeight(QFont.Weight(_resolve_weight(self._weight)))
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
        """根据当前主题 / color override / transparency / selection_* 参数刷新文字色与选区底色。"""
        c = self._current_color()
        rgba_str = f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alphaF():.4f})"
        # 选区色：传入所有相关参数
        sel_bg_css, sel_fg_css = _selection_palette(
            self._theme,
            force_selection_text_color=self._force_selection_text_color,
            selection_adapts_color=self._selection_adapts_color,
            text_color=c,
        )
        self.setStyleSheet(
            f"QLabel {{ "
            f"color: {rgba_str}; "
            f"background: transparent; "
            f"selection-color: {sel_fg_css}; "
            f"selection-background-color: {sel_bg_css}; "
            f"}}"
        )

    # ============================================================
    # 主题切换
    # ============================================================
    def set_theme(self, theme: str) -> None:
        """切换主题模式: ``"auto"`` / ``"light"`` / ``"dark"``。"""
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
        """ThemeProvider 广播专用入口（不触发注册逻辑）。"""
        self._theme = theme
        self._apply_color()

    # ============================================================
    # 选区管理
    # ============================================================

    def _clear_selection(self) -> None:
        """强制清除当前文本选区。

        QLabel 没有暴露 ``clearSelection()`` API；通过临时置空文本再恢复
        来重置内部 ``QTextControl`` 的选区状态。关闭 updates 避免闪烁。
        """
        text = self.text()
        if not text:
            return
        self.setUpdatesEnabled(False)
        self.setText("")
        self.setText(text)
        self.setUpdatesEnabled(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击时：非 Shift 点击清除自身选区（单选行为）。"""
        if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._clear_selection()
        super().mousePressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """失去焦点时清除自身选区。"""
        self._clear_selection()
        super().focusOutEvent(event)

    # ============================================================
    # 公共动态 setter
    # ============================================================
    def set_size(self, size: SizeInput) -> None:
        """切换字号（接受 ``"xs" ~ "9xl"`` 或像素 int/float）。"""
        self._size = size
        self._apply_font()

    def set_weight(self, weight: WeightInput) -> None:
        """切换字重（接受 ``"thin" ~ "black"`` / ``QFont.Weight`` / int）。"""
        self._weight = weight
        self._apply_font()

    def set_color(self, color: ColorInput) -> None:
        """切换文字色。

        - 传 ``None`` 恢复主题默认正文色。
        - 传 HeroUI token / HEX / RGB(A) tuple / ``QColor`` / ``rgba(...)`` 字符串。
        """
        self._color_input = color
        self._apply_color()

    def set_transparency(self, transparency: float) -> None:
        """切换整体透明度（0.0 ~ 1.0）。"""
        self._transparency = self._clamp01(transparency)
        self._apply_color()

    def set_force_selection_text_color(self, force: bool) -> None:
        """控制框选文字色是否强制为暗色/亮色。

        - ``True``（默认）：框选文字强制暗色（亮色模式）/ 亮色（暗色模式）。
        - ``False``：框选文字色与原文字色保持一致（"不做任何改变"）。
        """
        self._force_selection_text_color = bool(force)
        self._apply_color()

    def set_selection_adapts_color(self, enabled: bool) -> None:
        """控制选区底色是否适配文字颜色。

        - ``False``（默认）：底色永远用主品牌蓝（primary-500）。
        - ``True``：底色根据文字颜色自动生成（HeroUI token / 自定义颜色均走 HSL 算法）。
        """
        self._selection_adapts_color = bool(enabled)
        self._apply_color()

    # ============================================================
    # selectable
    # ============================================================
    def _apply_selectable(self) -> None:
        """根据 ``self._selectable`` 刷新文本交互标志与焦点策略。"""
        if self._selectable:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        else:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_selectable(self, selectable: bool) -> None:
        """设置是否允许鼠标框选/复制文字。

        - ``True``（默认）：允许框选、复制，点击获得焦点。
        - ``False``：禁止框选，文字只读渲染，不可交互。
        """
        self._selectable = bool(selectable)
        self._apply_selectable()

    # ============================================================
    # 只读访问器
    # ============================================================
    @property
    def text_color(self) -> QColor:
        """当前实际渲染的文字色（已叠加 transparency）。"""
        return self._current_color()

    @property
    def theme(self) -> str:
        """当前实际生效的主题: ``"light"`` / ``"dark"``。"""
        return self._theme


# ============================================================
# 向后兼容：Title / Subtitle / Caption / Body
# ============================================================

class Title(Text):
    """主标题 — 高对比度。

    用法::

        Title("Welcome back")              # level=1 → 2xl Bold (24px)
        Title("Section title", level=2)    # 18px Bold
        Title("Card title", level=3)       # 16px Bold

    Args:
        level: ``1`` (24px) / ``2`` (18px) / ``3`` (16px)
        selectable: 是否允许框选/复制（默认 True）
    """

    _LEVEL_SIZE = {1: "2xl", 2: "xl", 3: "lg"}  # 24 / 18 / 16

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
    """副标题 — 中性灰（亮色 ``default-500`` / 暗色 ``default-400``）。

    Args:
        selectable: 是否允许框选/复制（默认 True）
    """

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
        # 默认色: 跟随主题的副标题灰
        if color is None:
            theme_now = self._resolve_theme(theme)
            color = "#71717a" if theme_now == "light" else "#a1a1aa"
        super().__init__(
            text,
            size="sm",          # 13px
            weight="normal",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


class Caption(Text):
    """辅助提示 — 浅灰（亮色 ``default-400`` / 暗色 ``default-500``），最低对比度。

    Args:
        selectable: 是否允许框选/复制（默认 True）
    """

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
            size="xs",          # 12px
            weight="normal",
            color=color,
            selectable=selectable,
            theme=theme,
            parent=parent,
            **kwargs,
        )


class Body(Text):
    """正文 — 接近窗口前景色（亮色 ``#27272a`` / 暗色 ``#e4e4e7``）。

    本质就是 ``Text(..., size="md")``，提供语义化别名。

    Args:
        selectable: 是否允许框选/复制（默认 True）
    """

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
            size="md",          # 14px
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
