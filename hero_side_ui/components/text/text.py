"""Text 主题感知文字组件：token 解析 + 主题广播 + 共用选区调色板。
API 见 docs/text.md。
"""

from __future__ import annotations

from typing import ClassVar

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
        rich_text: bool = False,
        word_wrap: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构造主题感知文字组件并初始化字体、颜色与选区样式。

        Args:
            text: 初始文本内容。
            size: 字号 token。
            weight: 字重 token。
            color: 文字颜色输入。
            transparency: 文字透明度。
            selectable: 是否允许文本选区。
            force_selection_text_color: 是否强制选区文字色。
            selection_adapts_color: 选区色是否随文字色适配。
            rich_text: 是否按富文本渲染。
            word_wrap: 超出宽度时是否自动换行。
            theme: 明暗主题名或 auto。
            parent: Qt 父对象。

        Note:
            无论 theme 是否为 auto 都注册到 FontProvider，以跟随全局字体切换刷新。
        """
        super().__init__(text, parent)

        # ---- 状态 ----
        self._size = size
        self._weight = weight
        self._color_input: ColorInput = color
        self._transparency = self._clamp01(transparency)
        self._selectable: bool = selectable
        self._force_selection_text_color: bool = force_selection_text_color
        self._selection_adapts_color: bool = selection_adapts_color
        self._rich_text: bool = rich_text
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 超出宽度时是否自动换行（QLabel 默认截断）
        self.setWordWrap(word_wrap)

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
        """把数值夹到 0~1，非数值时回退为 1.0。"""
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
        """把主题模式解析为具体的明暗主题。

        Args:
            mode: 主题模式，light / dark / auto。

        Returns:
            light 或 dark；auto 时取 ThemeProvider 的当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # 字体
    # ============================================================
    def _apply_font(self) -> None:
        """按 size/weight/富文本设置 QFont，输入未变时跳过重建。

        Note:
            以 size/weight/rich_text/全局 family 做幂等守卫，避免表格虚拟滚动
            高频复用时反复重建 QFont 掉帧；富文本模式不锁 styleName。
        """
        # FontProvider 会走 setStyleName 精确选 VF 原生 instance。
        # 富文本模式关闭 styleName 锁定，让内联 <b>/<i> 能切到 VF 对应物理档。
        # 幂等守卫：size/weight/rich_text/全局 family 均未变时跳过 QFont 重建——
        # 表格虚拟滚动会高频复用同一 Text 且字号不变，重建 QFont（含 QFontDatabase
        # 查询）是主要掉帧源；family 纳入签名保证全局字体切换仍能刷新。
        sig = (self._size, self._weight, self._rich_text, FontProvider.instance().family)
        if sig == getattr(self, "_font_sig", None):
            return
        self._font_sig = sig
        font = make_text_qfont(self._size, self._weight, style_name=not self._rich_text)
        self.setFont(font)

    # ============================================================
    # 颜色 / 选区
    # ============================================================
    def _current_color(self) -> QColor:
        """返回叠加透明度后的实际文字色。"""
        c = resolve_text_color(self._color_input, self._theme)
        # 透明度叠加
        if self._transparency < 1.0:
            new_alpha = c.alphaF() * self._transparency
            c.setAlphaF(new_alpha)
        return c

    def _apply_color(self) -> None:
        """把当前文字色与选区色写入 QPalette 和 QSS。

        Note:
            QSS 颜色是创建时快照，主题切换必须重写；颜色签名未变时跳过
            setPalette/setStyleSheet，避免表格滚动时高频样式重算。
        """
        # 同时写 QPalette（a11y/测试读取）和 QSS（实际渲染）——
        # QSS 颜色是创建时快照，主题切换必须重写。
        # 幂等守卫：影响输出的输入维度均未变时跳过 setPalette + setStyleSheet——
        # 二者都会触发样式重算，表格滚动时高频复用同一 Text 且色值不变，跳过省开销。
        c = self._current_color()
        sig = (
            c.rgba(),
            self._theme,
            self._force_selection_text_color,
            self._selection_adapts_color,
        )
        if sig == getattr(self, "_color_sig", None):
            return
        self._color_sig = sig
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
        """设置主题，auto 时注册到 ThemeProvider 跟随广播。"""
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
        """响应 ThemeProvider 的主题广播并刷新文字色。

        Note:
            ThemeProvider 广播专用入口，不重新 register/unregister。
        """
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._apply_color()

    # ============================================================
    # 选区管理
    # ============================================================

    def _clear_selection(self) -> None:
        """清空当前选区，通过置空文本再赋回实现。

        Note:
            QLabel 没有 clearSelection() API，只能置空文本再赋回，并临时关闭
            updates 避免闪烁。
        """
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
        """非 Shift 点击时先清空选区再交给父类处理。"""
        # 非 Shift 点击 → 单选行为，先清自己的选区。
        if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._clear_selection()
        super().mousePressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """失去焦点时清空选区。"""
        self._clear_selection()
        super().focusOutEvent(event)

    # ============================================================
    # 公共动态 setter
    # ============================================================
    def set_size(self, size: SizeInput) -> None:
        """设置字号并刷新字体。"""
        self._size = size
        self._apply_font()

    def set_weight(self, weight: WeightInput) -> None:
        """设置字重并刷新字体。"""
        self._weight = weight
        self._apply_font()

    def set_color(self, color: ColorInput) -> None:
        """设置文字色并刷新样式。"""
        self._color_input = color
        self._apply_color()

    def set_transparency(self, transparency: float) -> None:
        """设置透明度，夹到 0~1 后刷新样式。"""
        self._transparency = self._clamp01(transparency)
        self._apply_color()

    def set_force_selection_text_color(self, force: bool) -> None:
        """设置是否强制选区文字色并刷新样式。"""
        self._force_selection_text_color = bool(force)
        self._apply_color()

    def set_selection_adapts_color(self, enabled: bool) -> None:
        """设置选区色是否随文字色适配并刷新样式。"""
        self._selection_adapts_color = bool(enabled)
        self._apply_color()

    # ============================================================
    # selectable
    # ============================================================
    def _apply_selectable(self) -> None:
        """按 selectable 设置文本交互标志与焦点策略。"""
        if self._selectable:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        else:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_selectable(self, selectable: bool) -> None:
        """设置是否允许文本选区并刷新交互标志。"""
        self._selectable = bool(selectable)
        self._apply_selectable()

    # ============================================================
    # 只读访问器
    # ============================================================
    @property
    def text_color(self) -> QColor:
        """返回已叠加 transparency 的实际渲染色。"""
        # 已叠加 transparency 的实际渲染色。
        return self._current_color()

    @property
    def theme(self) -> str:
        """返回当前生效的明暗主题名。"""
        return self._theme


# ============================================================
# 向后兼容：Title / Subtitle / Caption / Body
# ============================================================


class Title(Text):
    """主标题 — level=1/2/3 → 2xl/xl/lg Bold。"""

    _LEVEL_SIZE: ClassVar[dict[int, str]] = {1: "2xl", 2: "xl", 3: "lg"}

    def __init__(
        self,
        text: str = "",
        level: int = 1,
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        parent: QWidget | None = None,
        **kwargs,
    ):
        """按 level 映射 2xl/xl/lg 字号，以 Bold 字重创建主标题。"""
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
        parent: QWidget | None = None,
        **kwargs,
    ):
        """以 sm 字号创建副标题，未指定颜色时按主题取灰色。"""
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
        parent: QWidget | None = None,
        **kwargs,
    ):
        """以 xs 字号创建辅助提示，未指定颜色时按主题取灰色。"""
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
    """正文 — 语义化 alias，等价 ``Text(size='md')``；段落默认自动换行。"""

    def __init__(
        self,
        text: str = "",
        *,
        color: ColorInput = None,
        theme: str = "auto",
        selectable: bool = True,
        word_wrap: bool = True,
        parent: QWidget | None = None,
        **kwargs,
    ):
        """以 md 字号创建正文，默认开启自动换行。"""
        super().__init__(
            text,
            size="md",
            weight="normal",
            color=color,
            selectable=selectable,
            word_wrap=word_wrap,
            theme=theme,
            parent=parent,
            **kwargs,
        )


__all__ = [
    "SIZE_MAP",
    "WEIGHT_MAP",
    "Body",
    "Caption",
    "Subtitle",
    "Text",
    "Title",
]
