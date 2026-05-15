"""Accordion — 手风琴容器组件。

基于 HeroUI v2 设计风格的手风琴折叠面板组件。

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/accordion.ts

结构::

    Accordion (QWidget 容器)
        └── AccordionItem (可折叠子项)
            ├── trigger (标题栏，可点击)
            │     ├── title 标题文字
            │     ├── subtitle 副标题（可选）
            │     └── indicator 展开/收起箭头
            └── content (折叠内容区)
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import ACCORDION_SIZES, HEROUI_COLORS, RADIUS

from .item import AccordionItem


class Accordion(QWidget):
    """手风琴容器组件

    参数:
        variant: 外观变体 ("light", "bordered", "splitted")
        allow_multiple: 是否允许同时展开多项
        size: 尺寸 ("sm", "md", "lg")
        theme: 主题 ("light", "dark")
        show_divider: 是否显示分割线
        parent: Qt 父对象
    """

    def __init__(
        self,
        variant: str = "light",
        allow_multiple: bool = False,
        size: str = "md",
        radius: str = "md",
        theme: str = "auto",
        show_divider: bool = True,
        parent: Optional[QWidget] = None,
    ):
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
        """应用容器级别样式

        四种变体对标 HeroUI v2:
        - light: 透明背景，无边框无阴影，项间分割线分隔
        - shadow: 白色背景 + 阴影 + 圆角，像一张 Card 垫底
        - bordered: 透明背景 + 边框 + 圆角，像一张只有边框的 Card
        - splitted: 透明容器，每项独立 Card（样式在 AccordionItem 上）
        """
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        r = RADIUS.get(self._radius, RADIUS["md"])

        if self._variant == "light":
            # light 无圆角
            self.setStyleSheet("#heroAccordion { background: transparent; border: none; border-radius: 0px; }")
            self._layout.setContentsMargins(8, 0, 8, 0)
            self._layout.setSpacing(0)

        elif self._variant == "shadow":
            bg = dc[900] if is_dark else "#ffffff"
            # Qt QSS 不支持 box-shadow，用浅色边框 + 背景模拟卡片感
            border_hint = f"border: 1px solid {dc[800]};" if is_dark else "border: 1px solid #f0f0f0;"
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
        """添加一个手风琴子项"""
        self._items.append(item)
        item._apply_styles(self._theme, self._variant, self._size, self._show_divider, self._radius)

        # 监听展开事件，实现单项展开逻辑
        item.expanded_changed.connect(
            lambda expanded, i=item: self._on_item_expanded(i, expanded)
        )

        self._layout.addWidget(item)

        # 最后一个元素不要分割线，前面的要
        self._update_dividers()

    def _update_dividers(self):
        """更新所有子项的分割线：最后一个隐藏"""
        for i, item in enumerate(self._items):
            is_last = (i == len(self._items) - 1)
            if is_last or self._variant == "splitted":
                item._divider.hide()
            elif self._show_divider:
                item._divider.show()
            else:
                item._divider.hide()

    def _on_item_expanded(self, item: AccordionItem, expanded: bool):
        """当某项展开时，如果不允许多项展开，则收起其他项"""
        if expanded and not self._allow_multiple:
            for other in self._items:
                if other is not item and other.is_expanded():
                    other.collapse()

    # ---- 公共 API ----

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
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(self._theme, self._variant, self._size, self._show_divider, self._radius)

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(theme, self._variant, self._size, self._show_divider, self._radius)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(self._theme, variant, self._size, self._show_divider, self._radius)

    def set_radius(self, radius: str):
        self._radius = radius
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(self._theme, self._variant, self._size, self._show_divider, radius)

    def set_size(self, size: str):
        self._size = size
        for item in self._items:
            item._apply_styles(self._theme, self._variant, size, self._show_divider, self._radius)

    def expand_all(self):
        for item in self._items:
            item.expand()

    def collapse_all(self):
        for item in self._items:
            item.collapse()
