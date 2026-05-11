"""
HeroSideUI 语义化文字组件

提供 4 个主题感知的文字组件（继承 QLabel）：
- Title    : 主标题（默认 24px Bold）
- Subtitle : 副标题（13px Medium，中性灰）
- Caption  : 辅助提示（12px，浅灰，最低对比度）
- Body     : 正文（跟随窗口前景色）

所有组件支持 theme="auto"（默认）跟随 ThemeProvider，或 "light"/"dark" 硬锁。
颜色 token 经过亮暗色双向校准：
- 暗色模式: title=#fafafa  subtitle=#a1a1aa  caption=#71717a  body=#e4e4e7
- 亮色模式: title=#18181b  subtitle=#71717a  caption=#a1a1aa  body=#27272a

用户也可以传 color="#xxx" 覆盖默认（语义色仍跟主题，自定义色不变）。
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QLabel, QWidget

from ..themes import FONT_FAMILY
from ..core import ThemeProvider


# ============================================================
# 主题感知颜色常量
# ============================================================
_TITLE_COLORS = {"light": "#18181b", "dark": "#fafafa"}
_SUBTITLE_COLORS = {"light": "#71717a", "dark": "#a1a1aa"}
_CAPTION_COLORS = {"light": "#a1a1aa", "dark": "#71717a"}
_BODY_COLORS = {"light": "#27272a", "dark": "#e4e4e7"}


class _ThemedLabel(QLabel):
    """主题感知的 QLabel 基类

    子类负责定义 _palette_map（theme→hex）和默认 font。
    支持用户传 color 覆盖默认（覆盖后不再随主题切换）。
    """

    _palette_map: dict = {}  # 子类必填
    _default_font_size: int = 14
    _default_font_weight = QFont.Weight.Normal

    def __init__(
        self,
        text: str = "",
        font_size: Optional[int] = None,
        font_weight=None,
        color=None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)

        self._color_override = color  # 用户显式传则覆盖
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 字体
        font_size = font_size if font_size is not None else self._default_font_size
        font_weight = font_weight if font_weight is not None else self._default_font_weight
        font = QFont(FONT_FAMILY)
        font.setPixelSize(font_size)
        font.setWeight(font_weight)
        self.setFont(font)

        # 不让 QLabel 继承父级 stylesheet 污染（Card 子节点等场景）
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self._apply_color()

        # auto 模式注册
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 主题
    # ============================================================
    def _apply_color(self):
        """根据当前主题/用户覆盖刷新文字颜色"""
        if self._color_override is not None:
            c = self._color_override
            if isinstance(c, QColor):
                c = c.name()
        else:
            c = self._palette_map.get(self._theme, self._palette_map.get("light", "#000000"))
        self.setStyleSheet(f"QLabel {{ color: {c}; background: transparent; }}")

    def set_theme(self, theme: str):
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

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._apply_color()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_color(self, color):
        """覆盖默认颜色。传 None 恢复主题感知默认色。"""
        self._color_override = color
        self._apply_color()


class Title(_ThemedLabel):
    """主标题文字 — 高对比度（亮色 #18181b / 暗色 #fafafa）

    用法::

        Title("Welcome back")              # 24px Bold (level=1)
        Title("Section title", level=2)    # 18px Bold
        Title("Card title", level=3)       # 16px Bold

    Args:
        level: 1（24px）/ 2（18px）/ 3（16px）
    """

    _palette_map = _TITLE_COLORS
    _default_font_weight = QFont.Weight.Bold

    _LEVEL_SIZE = {1: 24, 2: 18, 3: 16}

    def __init__(
        self,
        text: str = "",
        level: int = 1,
        color=None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        size = self._LEVEL_SIZE.get(level, 24)
        super().__init__(
            text=text, font_size=size,
            font_weight=QFont.Weight.Bold,
            color=color, theme=theme, parent=parent,
        )


class Subtitle(_ThemedLabel):
    """副标题文字 — 中性灰（亮色 #71717a / 暗色 #a1a1aa）

    用法::

        Subtitle("Log in to your account to continue.")
    """

    _palette_map = _SUBTITLE_COLORS
    _default_font_size = 13
    _default_font_weight = QFont.Weight.Normal


class Caption(_ThemedLabel):
    """辅助提示文字 — 浅灰（亮色 #a1a1aa / 暗色 #71717a），最低对比度

    用法::

        Caption("Tip: click to toggle.")
    """

    _palette_map = _CAPTION_COLORS
    _default_font_size = 12
    _default_font_weight = QFont.Weight.Normal


class Body(_ThemedLabel):
    """正文文字 — 接近窗口前景色（亮色 #27272a / 暗色 #e4e4e7）

    用法::

        Body("Make beautiful websites regardless of your design experience.")
    """

    _palette_map = _BODY_COLORS
    _default_font_size = 14
    _default_font_weight = QFont.Weight.Normal


__all__ = ["Title", "Subtitle", "Caption", "Body"]
