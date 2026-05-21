"""主题感知的文字组件 ``Text``。完整 API / 示例见 ``docs/text.md``。

本文件只负责：
- token 解析（size / weight / color）
- 主题广播接入 + selection 清除等 QLabel 行为调整
- 选区调色板从 ``core.selection_palette`` 取，全项目共用

"为什么这样写"的坑记在各函数内联。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFocusEvent, QMouseEvent, QPalette
from PySide6.QtWidgets import QLabel, QWidget

from ...core import (
    FontProvider,
    ThemeProvider,
    make_text_qfont,
    resolve_text_color,
    selection_palette,
)
from ...core.text_style import (
    SIZE_MAP,
    WEIGHT_MAP,
    ColorInput,
    SizeInput,
    WeightInput,
)

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
        font = make_text_qfont(self._size, self._weight)
        self.setFont(font)

    # ============================================================
    # 颜色 / 选区
    # ============================================================
    def _current_color(self) -> QColor:
        c = resolve_text_color(self._color_input, self._theme)
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
        # 选区色：走 core.selection_palette——全项目唯一来源。
        bg, fg = selection_palette(
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
