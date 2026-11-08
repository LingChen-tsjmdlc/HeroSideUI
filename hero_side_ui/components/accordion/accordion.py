"""Accordion 手风琴容器：AccordionItem 子项 = trigger（标题+副标题+箭头）
+ 折叠内容区。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIUS
from .item import AccordionItem


class Accordion(QWidget):
    """手风琴容器组件。

    Args:
        variant: light/shadow/bordered/splitted。
        allow_multiple: 是否允许多项同时展开。
        size: sm/md/lg。
        theme: light/dark/auto。
        show_divider: 子项间分割线。
    """

    def __init__(
        self,
        variant: str = "light",
        allow_multiple: bool = False,
        size: str = "md",
        radius: str = "md",
        theme: str = "auto",
        show_divider: bool = True,
        parent: QWidget | None = None,
    ):
        """创建手风琴容器并应用容器样式。

        Args:
            variant: light / shadow / bordered / splitted。
            allow_multiple: 是否允许多项同时展开。
            size: 尺寸档位 sm / md / lg。
            radius: 容器圆角档位。
            theme: light / dark / auto。
            show_divider: 子项之间是否显示分割线。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._variant = variant
        self._allow_multiple = allow_multiple
        self._size = size
        self._radius = radius
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._show_divider = show_divider
        self._items: list[AccordionItem] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 0, 8, 0)
        self._layout.setSpacing(0)

        self.setObjectName("heroAccordion")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._apply_container_styles()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    def _apply_container_styles(self):
        """应用容器级样式：light / shadow / bordered / splitted 四变体。

        四变体的内边距与间距不同：light 贴合列表、shadow 与 bordered 带
        16px 内边距、splitted 零边距加 8px 项间距。shadow 变体因 Qt QSS
        不支持 box-shadow，用浅色边框 + 背景模拟卡片感。
        """
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        r = RADIUS.get(self._radius, RADIUS["md"])

        if self._variant == "light":
            # light 无圆角
            self.setStyleSheet(
                "#heroAccordion { background: transparent; border: none; border-radius: 0px; }"
            )
            self._layout.setContentsMargins(8, 0, 8, 0)
            self._layout.setSpacing(0)

        elif self._variant == "shadow":
            bg = dc[900] if is_dark else "#ffffff"
            # Qt QSS 不支持 box-shadow，用浅色边框 + 背景模拟卡片感
            border_hint = (
                f"border: 1px solid {dc[800]};" if is_dark else "border: 1px solid #f0f0f0;"
            )
            self.setStyleSheet(f"""
                #heroAccordion {{
                    background-color: {bg};
                    {border_hint}
                    border-radius: {r};
                }}
            """)
            self._layout.setContentsMargins(16, 8, 16, 8)
            self._layout.setSpacing(0)

        elif self._variant == "bordered":
            border_color = dc[700] if is_dark else dc[300]
            self.setStyleSheet(f"""
                #heroAccordion {{
                    background-color: transparent;
                    border: 1.5px solid {border_color};
                    border-radius: {r};
                }}
            """)
            self._layout.setContentsMargins(16, 8, 16, 8)
            self._layout.setSpacing(0)

        elif self._variant == "splitted":
            self.setStyleSheet("#heroAccordion { background: transparent; border: none; }")
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._layout.setSpacing(8)

    def add_item(self, item: AccordionItem):
        """添加一个手风琴子项并接入互斥逻辑。

        Args:
            item: 要添加的 AccordionItem。

        Note:
            添加后监听其 expanded_changed 信号以实现「单项展开」约束；
            分割线由 _update_dividers 统一重算（最后一项隐藏）。
        """
        self._items.append(item)
        item._apply_styles(self._theme, self._variant, self._size, self._show_divider, self._radius)

        # 监听展开事件，实现单项展开逻辑
        item.expanded_changed.connect(lambda expanded, i=item: self._on_item_expanded(i, expanded))

        self._layout.addWidget(item)

        # 最后一个元素不要分割线，前面的要
        self._update_dividers()

    def _update_dividers(self):
        """重算所有子项分割线的可见性。

        规则：最后一项与 splitted 变体永远隐藏；其余按 show_divider 开关。
        """
        for i, item in enumerate(self._items):
            is_last = i == len(self._items) - 1
            if is_last or self._variant == "splitted":
                item._divider.hide()
            elif self._show_divider:
                item._divider.show()
            else:
                item._divider.hide()

    def _on_item_expanded(self, item: AccordionItem, expanded: bool):
        """处理子项展开事件，维持单项展开约束。

        Args:
            item: 状态变化的子项。
            expanded: True 表示刚展开。

        Note:
            仅当 allow_multiple 为 False 时才收起其他已展开项。
        """
        if expanded and not self._allow_multiple:
            for other in self._items:
                if other is not item and other.is_expanded():
                    other.collapse()

    # ---- 公共 API ----

    def set_theme(self, theme: str):
        """切换主题并联动刷新全部子项。

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
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(
                self._theme, self._variant, self._size, self._show_divider, self._radius
            )

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，只刷新容器与子项样式。
        """
        self._theme = theme
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(theme, self._variant, self._size, self._show_divider, self._radius)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark 或 auto 等其他值。

        Returns:
            light / dark 原样返回；其余返回 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_variant(self, variant: str):
        """切换容器变体并联动刷新子项。

        Args:
            variant: light / shadow / bordered / splitted。
        """
        self._variant = variant
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(self._theme, variant, self._size, self._show_divider, self._radius)

    def set_radius(self, radius: str):
        """切换圆角档位并联动刷新子项。

        Args:
            radius: 圆角档位名。
        """
        self._radius = radius
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(self._theme, self._variant, self._size, self._show_divider, radius)

    def set_size(self, size: str):
        """切换尺寸档位并联动刷新子项。

        Args:
            size: sm / md / lg。
        """
        self._size = size
        for item in self._items:
            item._apply_styles(self._theme, self._variant, size, self._show_divider, self._radius)

    def expand_all(self):
        """展开全部子项。

        Note:
            与 allow_multiple 无关，直接逐项调用 expand()。
        """
        for item in self._items:
            item.expand()

    def collapse_all(self):
        """收起全部子项。"""
        for item in self._items:
            item.collapse()
