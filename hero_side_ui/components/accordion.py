"""
HeroSideUI Accordion Component
基于 HeroUI v2 设计风格的手风琴折叠面板组件

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/accordion.ts

结构:
    Accordion (QWidget 容器)
        └── AccordionItem (可折叠子项)
            ├── trigger (标题栏，可点击)
            │     ├── title 标题文字
            │     ├── subtitle 副标题（可选）
            │     └── indicator 展开/收起箭头
            └── content (折叠内容区)
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    Signal,
    Property,
)
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import QPointF
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, ACCORDION_SIZES
from ..utils import hex_to_rgba
from ..animation import CollapseAnimation


class AccordionItem(QWidget):
    """手风琴子项 — 包含可点击的标题栏和可折叠的内容区

    参数:
        title: 标题文字
        subtitle: 副标题文字（可选）
        content_widget: 折叠内容区的控件（可选，也可后续用 set_content 设置）
        content_text: 简单文本内容（与 content_widget 二选一）
        expanded: 初始是否展开
        is_disabled: 是否禁用
        start_icon: 标题左侧图标，支持内置图标名如 "heroicons--chevron-right-solid" 或 SVG 文件路径
        end_icon: 指示器左侧图标，同上
        parent: Qt 父对象
    """

    # 展开/收起状态变化信号
    expanded_changed = Signal(bool)

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        content_widget: Optional[QWidget] = None,
        content_text: str = "",
        expanded: bool = False,
        is_disabled: bool = False,
        start_icon: Optional[str] = None,
        end_icon: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title_text = title
        self._subtitle_text = subtitle
        self._expanded = expanded
        self._is_disabled = is_disabled
        self._start_icon_name = start_icon
        self._end_icon_name = end_icon
        self._indicator_rotation = 90.0 if expanded else 0.0
        self._content_height = 0
        self._animating = False

        # 从父级 Accordion 获取配置（后续由 Accordion 注入）
        self._theme = "light"
        self._variant = "light"
        self._size = "md"
        self._show_divider = True

        self._setup_ui(content_widget, content_text)

    def _setup_ui(self, content_widget: Optional[QWidget], content_text: str):
        """构建 UI 结构"""
        self.setObjectName("heroAccordionItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Trigger (标题栏) ----
        self._trigger = QWidget()
        self._trigger.setCursor(Qt.CursorShape.PointingHandCursor)
        trigger_layout = QHBoxLayout(self._trigger)
        trigger_layout.setContentsMargins(0, 8, 0, 8)
        trigger_layout.setSpacing(8)

        # start_icon（标题左侧图标）
        self._start_icon_label = QLabel()
        self._start_icon_label.setFixedSize(20, 20)
        if self._start_icon_name:
            self._start_icon_label.show()
        else:
            self._start_icon_label.hide()
        trigger_layout.addWidget(self._start_icon_label)

        # 标题区域
        title_wrapper = QVBoxLayout()
        title_wrapper.setSpacing(2)

        self._title_label = QLabel(self._title_text)
        self._title_label.setWordWrap(True)
        title_wrapper.addWidget(self._title_label)

        self._subtitle_label = QLabel(self._subtitle_text)
        self._subtitle_label.setWordWrap(True)
        if not self._subtitle_text:
            self._subtitle_label.hide()
        title_wrapper.addWidget(self._subtitle_label)

        trigger_layout.addLayout(title_wrapper, 1)

        # 指示器（默认 heroicons--chevron-right-solid 箭头，可通过 end_icon 替换）
        self._indicator = _IndicatorWidget(
            icon_name=self._end_icon_name or "heroicons--chevron-right-solid"
        )
        self._indicator.setFixedSize(18, 18)
        if self._expanded:
            self._indicator.set_rotation(90.0)
        trigger_layout.addWidget(self._indicator)

        layout.addWidget(self._trigger)

        # ---- Content (内容区) ----
        # clip_wrapper 负责 overflow 裁剪，内容区在里面
        self._clip_wrapper = QWidget()
        self._clip_wrapper.setStyleSheet("background: transparent;")

        self._content_container = QWidget()
        content_layout = QVBoxLayout(self._content_container)
        content_layout.setContentsMargins(0, 0, 0, 4)
        content_layout.setSpacing(0)

        if content_widget:
            content_layout.addWidget(content_widget)
        elif content_text:
            self._content_label = QLabel(content_text)
            self._content_label.setWordWrap(True)
            content_layout.addWidget(self._content_label)
        else:
            self._content_label = QLabel()
            self._content_label.setWordWrap(True)
            content_layout.addWidget(self._content_label)

        clip_layout = QVBoxLayout(self._clip_wrapper)
        clip_layout.setContentsMargins(0, 0, 0, 0)
        clip_layout.setSpacing(0)
        clip_layout.addWidget(self._content_container)

        layout.addWidget(self._clip_wrapper)

        # ---- 分割线（在条目最底部，各条目之间分隔） ----
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setFrameShadow(QFrame.Shadow.Plain)
        self._divider.setFixedHeight(1)
        layout.addWidget(self._divider)

        # ---- 折叠动画（由 animation/collapse.py 统一管理） ----
        self._collapse_anim = CollapseAnimation(
            content=self._content_container,
            wrapper=self._clip_wrapper,
            expanded=self._expanded,
        )

        # 箭头旋转动画（独立管理）
        self._rotation_anim = QPropertyAnimation(self._indicator, b"rotation")
        self._rotation_anim.setDuration(400)
        self._rotation_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # trigger 按压透明度反馈
        self._trigger_opacity = QGraphicsOpacityEffect(self._trigger)
        self._trigger.setGraphicsEffect(self._trigger_opacity)
        self._trigger_opacity.setOpacity(1.0)

        # 禁用状态
        if self._is_disabled:
            self.setEnabled(False)

    # ---- 样式应用（由 Accordion 调用） ----

    def _apply_styles(self, theme: str, variant: str, size: str, show_divider: bool, radius: str = "md"):
        """应用样式 — 由父级 Accordion 在添加时调用"""
        self._theme = theme
        self._variant = variant
        self._size = size
        self._show_divider = show_divider
        self._radius = radius

        is_dark = theme == "dark"
        dc = HEROUI_COLORS["default"]
        size_config = ACCORDION_SIZES.get(size, ACCORDION_SIZES["md"])

        # 标题字体
        title_color = dc[100] if is_dark else dc[900]
        subtitle_color = dc[400] if is_dark else dc[500]
        content_color = dc[300] if is_dark else dc[600]
        divider_color = dc[700] if is_dark else dc[200]
        indicator_color = dc[400]

        self._title_label.setStyleSheet(
            f"""
            color: {title_color};
            font-size: {size_config['title_font_size']};
            font-weight: 500;
            font-family: {FONT_FAMILY};
        """
        )

        self._subtitle_label.setStyleSheet(
            f"""
            color: {subtitle_color};
            font-size: {size_config['subtitle_font_size']};
            font-weight: 400;
            font-family: {FONT_FAMILY};
        """
        )

        if hasattr(self, "_content_label"):
            self._content_label.setStyleSheet(
                f"""
                color: {content_color};
                font-size: {size_config['content_font_size']};
                font-family: {FONT_FAMILY};
            """
            )

        # 分割线: light/shadow/bordered 有分割线，splitted 无
        if show_divider and variant != "splitted":
            self._divider.setStyleSheet(
                f"background-color: {divider_color}; border: none;"
            )
            self._divider.show()
        else:
            self._divider.hide()

        # start_icon / end_icon 渲染
        from ..utils import load_svg_icon
        icon_color = QColor(dc[400] if is_dark else dc[500])
        icon_size = size_config["indicator_size"]

        if self._start_icon_name:
            pixmap = load_svg_icon(self._start_icon_name, size=icon_size, color=icon_color)
            self._start_icon_label.setFixedSize(icon_size, icon_size)
            self._start_icon_label.setPixmap(pixmap)
            self._start_icon_label.show()

        # 指示器颜色（如果有自定义 end_icon 也会跟随着色）
        self._indicator.set_color(QColor(indicator_color))
        self._indicator.setFixedSize(
            size_config["indicator_size"], size_config["indicator_size"]
        )

        # Trigger / Content padding
        py = size_config["trigger_padding_y"]
        cy = size_config["content_padding_y"]

        # ---- 各变体子项样式 ----
        if variant == "splitted":
            # splitted: 每项独立 Card — 白底 + 圆角
            bg = dc[800] if is_dark else "#ffffff"
            border_hint = f"border: 1px solid {dc[700]};" if is_dark else "border: 1px solid #f0f0f0;"
            r = RADIUS.get(radius, RADIUS["md"])
            self.setStyleSheet(f"""
                #heroAccordionItem {{
                    background-color: {bg};
                    {border_hint}
                    border-radius: {r};
                }}
            """)
            self._trigger.layout().setContentsMargins(16, py, 16, py)
            self._content_container.layout().setContentsMargins(16, cy, 16, cy)

        elif variant == "shadow" or variant == "bordered":
            # shadow/bordered: 子项无独立样式，Card 样式在容器上
            self.setStyleSheet("#heroAccordionItem { background: transparent; border: none; border-radius: 0px; }")
            self._trigger.layout().setContentsMargins(0, py, 0, py)
            self._content_container.layout().setContentsMargins(0, cy, 0, cy)

        else:
            # light: 最简洁，无独立样式，无圆角
            self.setStyleSheet("#heroAccordionItem { background: transparent; border: none; border-radius: 0px; }")
            self._trigger.layout().setContentsMargins(0, py, 0, py)
            self._content_container.layout().setContentsMargins(0, cy, 0, cy)

        # 禁用态
        if self._is_disabled:
            self.setStyleSheet(self.styleSheet() + "QWidget { opacity: 0.5; }")

    # ---- 交互 ----

    def mousePressEvent(self, event):
        """点击标题栏切换展开/收起，带按压透明度反馈"""
        if not self._is_disabled and self._trigger.geometry().contains(event.pos()):
            self._trigger_opacity.setOpacity(0.7)
            self.toggle()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """松开时恢复 trigger 透明度"""
        self._trigger_opacity.setOpacity(1.0)
        super().mouseReleaseEvent(event)

    def toggle(self):
        """切换展开/收起状态"""
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """展开内容区"""
        if self._expanded and not self._collapse_anim.is_animating:
            return
        self._expanded = True

        # 折叠动画（高度+透明度）
        self._collapse_anim.expand()

        # 箭头旋转: → 90°
        self._rotation_anim.stop()
        self._rotation_anim.setStartValue(self._indicator.rotation)
        self._rotation_anim.setEndValue(90.0)
        self._rotation_anim.start()

        self.expanded_changed.emit(True)

    def collapse(self):
        """收起内容区"""
        if not self._expanded and not self._collapse_anim.is_animating:
            return
        self._expanded = False

        # 折叠动画（透明度先行 → 高度跟随）
        self._collapse_anim.collapse()

        # 箭头旋转: → 0°
        self._rotation_anim.stop()
        self._rotation_anim.setStartValue(self._indicator.rotation)
        self._rotation_anim.setEndValue(0.0)
        self._rotation_anim.start()

        self.expanded_changed.emit(False)

    # ---- 公共 API ----

    def set_title(self, text: str):
        self._title_text = text
        self._title_label.setText(text)

    def set_subtitle(self, text: str):
        self._subtitle_text = text
        self._subtitle_label.setText(text)
        self._subtitle_label.setVisible(bool(text))

    def set_content(self, widget: QWidget):
        """设置内容区控件"""
        content_layout = self._content_container.layout()
        # 清除旧内容
        while content_layout.count():
            item = content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        content_layout.addWidget(widget)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_start_icon(self, icon_name: str):
        """设置标题左侧图标（SVG 文件名，不含 .svg 后缀）"""
        self._start_icon_name = icon_name
        from ..utils import load_svg_icon
        size = self._start_icon_label.width() or 18
        pixmap = load_svg_icon(icon_name, size=size)
        self._start_icon_label.setPixmap(pixmap)
        self._start_icon_label.show()

    def set_end_icon(self, icon_name: str):
        """替换指示器图标（默认 heroicons--chevron-right-solid，传入内置图标名或 SVG 路径）"""
        self._end_icon_name = icon_name
        self._indicator.set_icon(icon_name)


class _IndicatorWidget(QWidget):
    """展开/收起箭头指示器 — 使用 SVG 图标渲染

    默认显示向右的 chevron，展开时顺时针旋转 90° 变成向下。
    """

    def __init__(self, icon_name: str = "heroicons--chevron-right-solid", parent=None):
        super().__init__(parent)
        self._rotation = 0.0
        self._color = QColor("#a1a1aa")
        self._icon_name = icon_name
        self._pixmap = None
        self._update_pixmap()

    # Qt Property: rotation（供 QPropertyAnimation 驱动）
    def _get_rotation(self) -> float:
        return self._rotation

    def _set_rotation(self, value: float):
        self._rotation = value
        self.update()

    def set_rotation(self, value: float):
        self._rotation = value
        self.update()

    rotation = Property(float, _get_rotation, _set_rotation)

    def set_color(self, color: QColor):
        self._color = color
        self._update_pixmap()
        self.update()

    def set_icon(self, icon_name: str):
        """替换图标"""
        self._icon_name = icon_name
        self._update_pixmap()
        self.update()

    def _update_pixmap(self):
        """重新渲染 SVG 图标"""
        from ..utils import load_svg_icon
        size = max(self.width(), self.height(), 18)
        self._pixmap = load_svg_icon(self._icon_name, size=size, color=self._color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # 居中旋转
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.translate(-cx, -cy)

        # 居中绘制 pixmap
        px = (w - self._pixmap.width()) / 2.0
        py = (h - self._pixmap.height()) / 2.0
        painter.drawPixmap(int(px), int(py), self._pixmap)

        painter.end()


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
        theme: str = "light",
        show_divider: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._variant = variant
        self._allow_multiple = allow_multiple
        self._size = size
        self._radius = radius
        self._theme = theme
        self._show_divider = show_divider
        self._items: list[AccordionItem] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 0, 8, 0)
        self._layout.setSpacing(0)

        self.setObjectName("heroAccordion")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._apply_container_styles()

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
        self._theme = theme
        self._apply_container_styles()
        for item in self._items:
            item._apply_styles(theme, self._variant, self._size, self._show_divider, self._radius)

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
