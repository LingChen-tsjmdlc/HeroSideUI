"""Markdown 组件：解析树 → 块级 widget 纵向堆叠；行内拼富文本不拆 widget。
主题切换整树重建。API 见 docs/markdown.md。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import MARKDOWN_SPACING
from ...utils import clear_layout
from ._inline import InlineOverride
from ._inline_flow import InlineWidget
from ._parser import parse
from ._renderer import BlockRenderer, MarkdownRenderer


class Markdown(QWidget):
    """Markdown 渲染组件。

    用法::

        md = Markdown("# 标题\\n\\n正文 **粗体** 与 [链接](https://x.com)")
        md.set_markdown("...")   # 动态替换内容

    自定义渲染（类似 react-markdown 的 components）::

        # 行内样式（声明式，一次配置到处套用，全程连续框选）——推荐主入口
        md = Markdown(text, inline_styles={
            "strong": {"color": "danger"},
            "em":     {"color": "secondary"},
            "code":   {"bg": "default-100", "fg": "default-700"},
            "link":   {"color": "primary", "underline": "always"},
        })

        # 行内样式的底层入口：返回原始 HTML 片段（inline_styles 表达不了时用）
        md = Markdown(text, inline_overrides={
            "strong": lambda c: f"<span style='color:#f31260'>{c.children}</span>",
        })

        # 块级：返回你自己的 QWidget（块级元素独占整行，可整块替换，不碍行内框选）
        md = Markdown(text, block_renderers={
            "fence":      lambda c: MyCodeSnippet(c.node.content, parent=c.parent),
            "blockquote": lambda c: MyCard(c.render_children(c.parent)),
        })

    Args:
        text:             初始 Markdown 文本
        theme:            "auto" / "light" / "dark"
        inline_styles:    {type: {样式属性}} 声明式配置行内 strong/em/s/code/link 的样式，
                          编译成富文本 → 默认全程连续框选。**推荐主入口。**
        inline_overrides: {type: callable(InlineContext)->str} 覆盖行内默认 HTML（底层入口）
        block_renderers:  {type: callable(BlockContext)->QWidget} 覆盖块级默认 widget，
                          可用 key: paragraph / heading / blockquote / bullet_list /
                          ordered_list / table / hr / fence
        inline_widgets:   {type: callable(InlineWidgetContext)->QWidget} 逃生舱：把行内元素
                          渲染成独立 QWidget。**默认为空**——绝大多数需求用 inline_styles。
                          仅极少数需交互的行内角标才用，该处会打断连续选区。
    """

    def __init__(
        self,
        text: str = "",
        *,
        theme: str = "auto",
        inline_styles: dict[str, dict] | None = None,
        inline_overrides: dict[str, InlineOverride] | None = None,
        block_renderers: dict[str, BlockRenderer] | None = None,
        inline_widgets: dict[str, InlineWidget] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._text = str(text or "")
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._inline_styles = dict(inline_styles) if inline_styles else {}
        self._inline_overrides = dict(inline_overrides) if inline_overrides else {}
        self._block_renderers = dict(block_renderers) if block_renderers else {}
        self._inline_widgets = dict(inline_widgets) if inline_widgets else {}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(MARKDOWN_SPACING["block_gap"])
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._rebuild()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析为具体 light/dark。

        Args:
            mode: auto / light / dark。

        Returns:
            str: 解析后的实际主题；auto 回落当前 ThemeProvider 主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ------------------------------------------------------------
    # 重建
    # ------------------------------------------------------------
    def _rebuild(self) -> None:
        """整树重建：清空布局、重新解析文本并渲染所有块级 widget。"""
        self.setUpdatesEnabled(False)
        clear_layout(self._layout)
        root = parse(self._text)
        renderer = MarkdownRenderer(
            self._theme,
            inline_overrides=self._inline_overrides,
            block_renderers=self._block_renderers,
            inline_widgets=self._inline_widgets,
            inline_styles=self._inline_styles,
        )
        for w in renderer.render(root, self):
            self._layout.addWidget(w)
            w.show()
        self.setUpdatesEnabled(True)

    # ------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------
    def set_markdown(self, text: str) -> None:
        """动态替换 Markdown 内容并重建渲染。

        Args:
            text: 新的 Markdown 文本。
        """
        self._text = str(text or "")
        self._rebuild()

    def markdown(self) -> str:
        """返回当前 Markdown 源文本。

        Returns:
            str: 当前文本。
        """
        return self._text

    def set_inline_overrides(self, overrides: dict[str, InlineOverride]) -> None:
        """设置行内 HTML override（重建渲染）。

        Args:
            overrides: {type: callable(InlineContext)->str}。
        """
        self._inline_overrides = dict(overrides) if overrides else {}
        self._rebuild()

    def set_inline_styles(self, styles: dict[str, dict]) -> None:
        """设置声明的行内样式（重建渲染）。

        Args:
            styles: {type: {样式属性}}。
        """
        self._inline_styles = dict(styles) if styles else {}
        self._rebuild()

    def set_block_renderers(self, renderers: dict[str, BlockRenderer]) -> None:
        """设置块级覆盖渲染器（重建渲染）。

        Args:
            renderers: {type: callable(BlockContext)->QWidget}。
        """
        self._block_renderers = dict(renderers) if renderers else {}
        self._rebuild()

    def set_inline_widgets(self, widgets: dict[str, InlineWidget]) -> None:
        """设置行内 widget 工厂（重建渲染）。

        Args:
            widgets: {type: callable(InlineWidgetContext)->QWidget}。
        """
        self._inline_widgets = dict(widgets) if widgets else {}
        self._rebuild()

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------
    def set_theme(self, theme: str) -> None:
        """设置主题（auto/light/dark），auto 时注册 ThemeProvider（重建渲染）。

        Args:
            theme: auto 跟随全局；light/dark 硬锁主题。
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
        self._rebuild()

    def _apply_provider_theme(self, theme: str) -> None:
        """ThemeProvider 回调：auto 模式下跟随全局主题切换并重建。"""
        self._theme = theme
        self._rebuild()

    @property
    def theme(self) -> str:
        """当前实际主题（light/dark）。

        Returns:
            str: 当前主题。
        """
        return self._theme


__all__ = ["Markdown"]
