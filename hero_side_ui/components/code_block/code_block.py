"""CodeBlock 代码块：圆角外壳 + 标题栏 + pygments 高亮代码区。
配色随主题 One Light/Dark 切换；默认全高不滚动。API 见 docs/code_block.md。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ..._shared.code import mono_qfont
from ...core import FontProvider, ThemeProvider
from ...themes import CODE_BLOCK_SPEC, HEROUI_COLORS
from ..text import Text
from ._header import _CodeHeaderBar
from ._highlight import build_code_html


class _Tab:
    """单个 tab 的数据载体。"""

    __slots__ = ("code", "highlight_lines", "language", "name")

    def __init__(self, name: str, code: str, language: str, highlight_lines: list[int]):
        """创建 tab 数据。

        Args:
            name: tab 显示名 / 文件名。
            code: 源码文本。
            language: pygments lexer 名。
            highlight_lines: 需高亮背景的行号（1 基）。
        """
        self.name = name
        self.code = code
        self.language = language
        self.highlight_lines = highlight_lines


class CodeBlock(QWidget):
    """带语法高亮 / 标题栏 / 复制按钮的代码块。

    用法::

        # 单文件
        cb = CodeBlock(code, language="python", filename="main.py")

        # 高亮指定行
        cb = CodeBlock(code, language="python", filename="a.py", highlight_lines=[2, 3])

        # 自定义代码字体
        cb = CodeBlock(code, language="python", filename="a.py", font="C:/fonts/JetBrainsMono.ttf")

        # 多 tab
        cb = CodeBlock(tabs=[
            {"name": "main.py", "code": code1, "language": "python"},
            {"name": "style.css", "code": code2, "language": "css"},
        ])

    Args:
        code:            源码文本。单文件模式必填；传了 tabs 则忽略
        language:        语言名（pygments lexer 名），用于语法高亮
        filename:        标题栏显示的文件名；空则显示语言名
        highlight_lines: 需高亮背景的行号（1 基），默认 []
        font:            代码字体文件路径；None 用内置 Maple Mono NF CN
        font_size:       代码字号(px)；None 用默认（CODE_BLOCK_SPEC["font_size"]）
        tabs:            多 tab 列表，每项 dict 含 name/code，可选 language/highlight_lines；传了 tabs 则忽略 code/filename
        show_line_numbers: 是否显示行号（自动换行时依然保留行号）
        theme:           "auto" / "light" / "dark"，代码区底色随主题走 Tailwind neutral
    """

    def __init__(
        self,
        code: str = "",
        *,
        language: str = "text",
        filename: str = "",
        highlight_lines: list[int] | None = None,
        font: str | None = None,
        font_size: int | None = None,
        tabs: list[dict] | None = None,
        show_line_numbers: bool = True,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建代码块：标题栏 + 富文本高亮代码区。

        Args:
            code: 单文件模式的源码；传了 tabs 则忽略。
            language: pygments lexer 名。
            filename: 标题栏文件名；空则显示语言名。
            highlight_lines: 需高亮背景的行号（1 基）。
            font: 代码字体文件路径；None 用内置 Maple Mono NF CN。
            font_size: 代码字号（px）；None 用 CODE_BLOCK_SPEC 默认值。
            tabs: 多 tab 列表，每项含 name/code，可选 language/highlight_lines。
            show_line_numbers: 是否显示行号（自动换行时仍保留）。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Note:
            单文件也归一成一个 _Tab；代码区只开横向滚动，
            纵向高度随内容全展开。
        """
        super().__init__(parent)
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._show_line_numbers = show_line_numbers
        self._wrap = False
        self._active_tab = 0
        self._font_path = font
        self._font_size = int(font_size) if font_size else CODE_BLOCK_SPEC["font_size"]

        # 归一成 _Tab 列表：单文件模式也包成一个 tab
        if tabs:
            self._tabs = [
                _Tab(
                    t.get("name", ""),
                    t.get("code", ""),
                    t.get("language", language),
                    t.get("highlight_lines", []),
                )
                for t in tabs
            ]
            self._has_tabs = True
        else:
            self._tabs = [_Tab(filename, code, language, highlight_lines or [])]
            self._has_tabs = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏
        self._header = _CodeHeaderBar(
            filename=self._tabs[0].name or self._tabs[0].language,
            tabs=[t.name for t in self._tabs] if self._has_tabs else [],
            theme=self._theme,
            on_tab=self._on_tab,
            on_wrap=self._on_wrap,
            on_copy=self._on_copy,
            parent=self,
        )
        outer.addWidget(self._header)

        # 代码区：横向滚动容器（仅横向；纵向永不滚动——高度随内容全展开）
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 高度跟随内容：不给纵向留滚动，滚动区自身高度由内部 label 撑开
        self._scroll.setSizeAdjustPolicy(QScrollArea.SizeAdjustPolicy.AdjustToContents)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._code_label = Text(
            size="md",
            theme=self._theme,
            rich_text=True,
            selectable=True,
            parent=self._scroll,
        )
        self._code_label.setTextFormat(Qt.TextFormat.RichText)
        self._code_label.setWordWrap(False)
        self._code_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._code_label.setContentsMargins(
            CODE_BLOCK_SPEC["code_pad_x"],
            CODE_BLOCK_SPEC["code_pad_y"],
            CODE_BLOCK_SPEC["code_pad_x"],
            CODE_BLOCK_SPEC["code_pad_y"],
        )
        # 字体真正落地：QFont（CSS font-family 在富文本里不生效）
        self._code_label.setFont(mono_qfont(self._font_size, font))
        # 代码字体独立于全局字体，退出 FontProvider 广播，避免被正文字体覆盖
        FontProvider.instance().unregister(self._code_label)
        self._scroll.setWidget(self._code_label)
        # 滚动区纵向按内容撑开，不吃多余高度
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        outer.addWidget(self._scroll)

        self._render_code()
        self._sync_scroll_height()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------
    def _active(self) -> _Tab:
        """返回当前激活的 tab 数据。

        Returns:
            当前下标的 _Tab 实例。
        """
        return self._tabs[self._active_tab]

    def _render_code(self) -> None:
        """按当前主题 / 换行 / 行号设置重绘代码区富文本。"""
        tab = self._active()
        html = build_code_html(
            tab.code,
            tab.language,
            self._theme,
            show_line_numbers=self._show_line_numbers,
            wrap=self._wrap,
            highlight_lines=tab.highlight_lines,
        )
        self._code_label.setWordWrap(self._wrap)
        self._code_label.setText(html)
        self._sync_scroll_height()

    def _sync_scroll_height(self) -> None:
        """把滚动区高度锁到 label 内容高度：纵向不滚动、整块全高。

        Note:
            非换行模式需预留一条横向滚动条高度，避免遮住最后一行。
        """
        h = self._code_label.sizeHint().height()
        # 横向滚动条会占一条高度，非换行模式预留，避免遮住最后一行
        if not self._wrap:
            h += self._scroll.horizontalScrollBar().sizeHint().height()
        self._scroll.setMinimumHeight(h)
        self._scroll.setMaximumHeight(h)

    # ------------------------------------------------------------
    # 交互回调
    # ------------------------------------------------------------
    def _on_tab(self, idx: int) -> None:
        """切换激活 tab 并重绘。

        Args:
            idx: 目标 tab 下标。
        """
        self._active_tab = idx
        self._render_code()

    def _on_wrap(self, wrap: bool) -> None:
        """切换自动换行并同步横向滚动策略。

        Args:
            wrap: True 时关闭横向滚动条并软换行。
        """
        self._wrap = wrap
        # 换行开启时禁横向滚动
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff if wrap else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._render_code()

    def _on_copy(self) -> None:
        """把当前 tab 的源码写入剪贴板并触发按钮反馈。"""
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._active().code)
            self._header.flash_copied()

    # ------------------------------------------------------------
    # 外观（外壳圆角 + 分层底色由 paintEvent 绘制）
    # ------------------------------------------------------------
    def _shell_bg(self) -> QColor:
        """外壳底色。

        Returns:
            按主题取 neutral 色阶的 QColor。
        """
        shade = (
            CODE_BLOCK_SPEC["shell_bg_shade_dark"]
            if self._theme == "dark"
            else CODE_BLOCK_SPEC["shell_bg_shade"]
        )
        return QColor(HEROUI_COLORS["default"][shade])

    def _header_bg(self) -> QColor:
        """标题栏底色。

        Returns:
            按主题取 CODE_BLOCK_SPEC 中标题栏色的 QColor。
        """
        return QColor(
            CODE_BLOCK_SPEC["header_bg_dark"]
            if self._theme == "dark"
            else CODE_BLOCK_SPEC["header_bg_light"]
        )

    def _code_bg(self) -> QColor:
        """代码区底色。

        Returns:
            按主题取 CODE_BLOCK_SPEC 中代码区色的 QColor。
        """
        return QColor(
            CODE_BLOCK_SPEC["code_bg_dark"]
            if self._theme == "dark"
            else CODE_BLOCK_SPEC["code_bg_light"]
        )

    def paintEvent(self, event):  # type: ignore[override]
        """自绘外壳圆角与标题栏 / 代码区分层底色。

        Args:
            event: Qt 绘制事件。

        Note:
            标题栏顶部圆角、底边直角；代码区底部圆角、顶边直角，
            靠补 drawRect 把各自朝向圆角的一侧填平。
        """
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = CODE_BLOCK_SPEC["radius"]
        rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        # 外壳圆角底
        painter.setBrush(self._shell_bg())
        painter.drawRoundedRect(rect, radius, radius)
        # 标题栏底色（顶部圆角，底边直角）
        hb = self._header.geometry()
        painter.setBrush(self._header_bg())
        painter.drawRoundedRect(hb.adjusted(0, 0, 0, radius), radius, radius)
        painter.drawRect(hb.left(), hb.bottom() - radius, hb.width(), radius)
        # 代码区底色（随主题；底部圆角，顶边直角）
        code_rect = self._scroll.geometry()
        painter.setBrush(self._code_bg())
        painter.drawRoundedRect(code_rect, radius, radius)
        painter.drawRect(code_rect.left(), code_rect.top(), code_rect.width(), radius)
        painter.end()

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_theme(self, theme: str) -> None:
        """切换主题并重建标题栏与代码配色。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._rebuild_theme()

    def _apply_provider_theme(self, theme: str) -> None:
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._rebuild_theme()

    def _rebuild_theme(self) -> None:
        """主题变更后重建标题栏、字体与代码富文本。

        Note:
            标题栏用 safe_delete 销毁后重建（按钮颜色需在构造时按
            新主题取色），再插回布局首位。
        """
        from ...utils import safe_delete

        self.layout().removeWidget(self._header)
        safe_delete(self._header)
        self._header = _CodeHeaderBar(
            filename=self._tabs[0].name or self._tabs[0].language,
            tabs=[t.name for t in self._tabs] if self._has_tabs else [],
            theme=self._theme,
            on_tab=self._on_tab,
            on_wrap=self._on_wrap,
            on_copy=self._on_copy,
            parent=self,
        )
        self.layout().insertWidget(0, self._header)
        self._header.show()
        self._code_label.set_theme(self._theme)
        self._code_label.setFont(mono_qfont(self._font_size, self._font_path))
        self._render_code()
        self.update()

    @property
    def theme(self) -> str:
        """当前实际生效的主题名。

        Returns:
            light 或 dark（auto 已解析为具体值）。
        """
        return self._theme


__all__ = ["CodeBlock"]
