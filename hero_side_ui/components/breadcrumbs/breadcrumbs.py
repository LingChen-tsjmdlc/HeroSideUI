"""HeroSideUI Breadcrumbs — 面包屑导航 (HeroUI v2)。完整 API/示例见 docs/breadcrumbs.md。

结构对照官方 breadcrumbs.tsx + breadcrumb-item.tsx：nav > ol(list) >
li(base)[item(startContent+children+endContent), separator]。桌面端项为
自绘 _Crumb（hover 提亮/按下变淡/下划线模式），省略号折叠逻辑与官方
maxItems/itemsBeforeCollapse/itemsAfterCollapse 一致。

用法::

    crumbs = Breadcrumbs(items=[
        BreadcrumbItem("Home", key="home"),
        BreadcrumbItem("Music", key="music"),
        BreadcrumbItem("Current", key="now", is_current=True),
    ])
    crumbs.action_triggered.connect(lambda key: print(key))
"""

from __future__ import annotations

from typing import Callable, List, Optional, Union

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...utils import load_svg_icon
from ...themes import (
    HEROUI_COLORS,
    BREADCRUMBS_HOVER_OPACITY,
    BREADCRUMBS_ACTIVE_OPACITY,
    BREADCRUMBS_ITEMS_AFTER_COLLAPSE,
    BREADCRUMBS_ITEMS_BEFORE_COLLAPSE,
    BREADCRUMBS_MAX_ITEMS,
    BREADCRUMBS_SIZES,
    VALID_BREADCRUMBS_COLORS,
    VALID_BREADCRUMBS_RADII,
    VALID_BREADCRUMBS_SIZES,
    VALID_BREADCRUMBS_UNDERLINES,
    VALID_BREADCRUMBS_VARIANTS,
)
from ._styling import build_item_styles, build_list_styles, separator_color

# radius 档位（官方 default-layout：small 8 / medium 12 / large 14）
_RADIUS_PX = {"none": 0, "sm": 8, "md": 12, "lg": 14, "full": 9999}


class BreadcrumbItem:
    """面包屑项配置（声明式，由 Breadcrumbs 渲染）。

    start_content / end_content / separator 传 QWidget；separator 也可传
    str（渲染为文本分隔符）。is_last 由 Breadcrumbs 自动推断。
    """

    def __init__(
        self,
        label: str,
        *,
        key: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
        underline: Optional[str] = None,
        start_content: Optional[QWidget] = None,
        end_content: Optional[QWidget] = None,
        separator: Optional[Union[QWidget, str]] = None,
        is_current: Optional[bool] = None,
        hide_separator: bool = False,
        is_disabled: bool = False,
        bordered: bool = False,
        on_press: Optional[Callable[[], None]] = None,
    ):
        self.label = str(label)
        self.key = key
        self.color = color
        self.size = size
        self.underline = underline
        self.start_content = start_content
        self.end_content = end_content
        self.separator = separator
        # None=未设置（由 isLast 推断）；True/False=显式受控（优先于推断，
        # 对齐官方 cloneElement 中 ...child.props 覆盖默认 isCurrent 的顺序）
        self.is_current = is_current
        self.hide_separator = bool(hide_separator)
        self.is_disabled = bool(is_disabled)
        # 桌面扩展：胶囊边框项（官方 Menu Type 经 itemClasses 实现，桌面无
        # slot 机制，以项参数等价）
        self.bordered = bool(bordered)
        self.on_press = on_press


def _make_separator_widget(separator: str, theme: str) -> QWidget:
    """文本分隔符：官方无 str 分支，桌面扩展为文本分隔符。"""
    lbl = QLabel(separator)
    color = separator_color(theme)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    return lbl


class _Chevron(QWidget):
    """官方默认分隔符 chevron-right：QPainter 自绘（线条粗细/颜色完全可控）。"""

    def __init__(self, color, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = QColor(color) if isinstance(color, QColor) else QColor(color)
        self.setFixedSize(12, 12)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self._color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        # ">": (4,3) -> (8,6) -> (4,9)
        p.drawLine(4, 3, 8, 6)
        p.drawLine(8, 6, 4, 9)


class _EllipsisIcon(QLabel):
    """官方省略号图标（横向三点）。"""

    def __init__(self, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(load_svg_icon("heroicons--ellipsis-horizontal", size=18, color=color))


class _TextLabel(QWidget):
    """项文字绘制层：由 _Crumb 转发状态，本件不接收鼠标事件。"""

    def __init__(self, crumb: "_Crumb", width: int, parent: QWidget):
        super().__init__(parent)
        self._crumb = crumb
        self.setFixedSize(width, crumb.height())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event):
        crumb = self._crumb
        item = crumb._item
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        styles = build_item_styles(crumb._color_name, crumb._theme, item.is_current)
        # 状态色：常态 / hover 提亮 / 按下变淡（官方 hover:opacity-hover、
        # active:opacity-disabled）
        color = styles["text"]
        if not item.is_disabled and not item.is_current:
            if crumb._pressed:
                color = styles["text_pressed"]
            elif crumb._hover:
                color = styles["text_hover"]
        p.setOpacity(0.5 if item.is_disabled else 1.0)
        p.setFont(crumb._font)
        fm = QFontMetricsF(crumb._font)
        baseline = self.height() / 2 + (fm.ascent() - fm.descent()) / 2
        p.setPen(QPen(QColor(color), 0))
        p.drawText(QPointF(0, baseline), item.label)
        # 下划线（官方 underline 变体：hover/always/active/focus + offset-4；
        # focus 桌面语义=被点击后持久显示，直到点其它项转移）
        mode = crumb._underline
        show = (mode == "always"
                or (mode == "hover" and crumb._hover)
                or (mode == "active" and crumb._pressed)
                or (mode == "focus" and crumb._clicked))
        if show and not item.is_current and not item.is_disabled:
            w = fm.horizontalAdvance(item.label)
            y = baseline + 4
            p.drawLine(QPointF(0, y), QPointF(w, y))


class _Crumb(QWidget):
    """单个可点项：HBox（start_content | 自绘文字层 | end_content），
    鼠标/悬停状态在 _Crumb 层统一处理。"""

    pressed = Signal(object)  # BreadcrumbItem

    def __init__(self, item: BreadcrumbItem, base_color: str, size: str,
                 theme: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._item = item
        self._color_name = item.color or base_color
        self._theme = theme
        self._underline = item.underline or "hover"
        self._size = item.size or size
        self._hover = False
        self._pressed = False
        self._focused = False
        self._clicked = False  # underline="focus"：被点击后的持久标记
        self._font = QFont()
        self._font.setPixelSize(BREADCRUMBS_SIZES[self._size]["font"])
        self._font.setWeight(QFont.Weight.Medium)
        self.setCursor(Qt.CursorShape.PointingHandCursor
                       if not item.is_current else Qt.CursorShape.ArrowCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        fm = QFontMetricsF(self._font)
        self._bordered = getattr(item, "bordered", False)
        # 项高度 = max(文字行高, start/end content 高度)——内嵌 Button/Dropdown
        # 等交互组件时不能被文字行高压扁
        content_h = max(
            item.start_content.sizeHint().height() if item.start_content is not None else 0,
            item.end_content.sizeHint().height() if item.end_content is not None else 0,
        )
        if self._bordered:
            # 官方 Menu Type itemClasses：px-2 py-0.5 + 边框余量
            self.setFixedHeight(max(int(fm.height()) + 8, content_h + 4))
            margins = (8, 2, 8, 2)
        else:
            self.setFixedHeight(max(int(fm.height()) + 4, content_h))
            margins = (0, 0, 0, 0)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(4)

        self._label_w = fm.horizontalAdvance(item.label)
        label = _TextLabel(self, int(self._label_w) + 1, self)
        # 注意：start/end content 不设鼠标穿透——可能内嵌 Button/Dropdown
        # 等交互组件；纯装饰图标由调用方自行设置 WA_TransparentForMouseEvents
        if item.start_content is not None:
            self._layout.addWidget(item.start_content)
        if item.label:
            self._layout.addWidget(label)
        if item.end_content is not None:
            self._layout.addWidget(item.end_content)

    # ---- 状态 ----

    def paintEvent(self, event):
        """bordered 胶囊项（官方 Menu Type 的桌面等价）：
        - current：flat chip（default-100 浅底、无边框，文字全色）
        - 非 current：bordered chip（透明底、default-400 边框）
        - disabled：default-100 底 + default-400 边框、文字 50%"""
        if not self._bordered:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_dark = self._theme == "dark"
        d = HEROUI_COLORS["default"]
        # 暗色浅阶镜像（100↔800、400↔500）
        bg_100 = d[800] if is_dark else d[100]
        border_400 = d[500] if is_dark else d[400]

        item = self._item
        bg = None
        border = None
        if item.is_disabled:
            bg, border = QColor(bg_100), QColor(border_400)
        elif item.is_current:
            bg = QColor(bg_100)  # flat chip：浅底无边框
        else:
            border = QColor(border_400)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if bg is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(rect, 6, 6)
        if border is not None:
            p.setPen(QPen(border, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 6, 6)

    def set_hover(self, hover: bool):
        self._hover = hover
        self.update()

    def set_pressed(self, pressed: bool):
        self._pressed = pressed
        self.update()

    def set_clicked(self, clicked: bool):
        """underline="focus" 的持久标记（Breadcrumbs 层单选转移）。"""
        self._clicked = clicked
        self.update()

    def item(self) -> BreadcrumbItem:
        return self._item

    # ---- 事件 ----

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self._item.is_disabled and not self._item.is_current:
            self.set_hover(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.set_hover(False)
        self.set_pressed(False)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._item.is_disabled:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_pressed(True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._item.is_disabled:
            return
        was = self._pressed
        self.set_pressed(False)
        if was and self.rect().contains(event.position().toPoint()):
            if self._item.on_press is not None:
                self._item.on_press()
            self.pressed.emit(self._item)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focused = True
        self.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focused = False
        self.update()


class Breadcrumbs(QWidget):
    """HeroUI 风格面包屑导航。"""

    action_triggered = Signal(str)  # 对齐官方 onAction(key)
    item_pressed = Signal(object)   # BreadcrumbItem（对齐官方 onPress）

    def __init__(
        self,
        items: Optional[List[BreadcrumbItem]] = None,
        *,
        variant: str = "light",
        color: str = "foreground",
        size: str = "md",
        radius: str = "sm",
        underline: str = "hover",
        separator: Optional[Union[QWidget, str]] = None,
        max_items: int = BREADCRUMBS_MAX_ITEMS,
        items_before_collapse: int = BREADCRUMBS_ITEMS_BEFORE_COLLAPSE,
        items_after_collapse: int = BREADCRUMBS_ITEMS_AFTER_COLLAPSE,
        hide_separator: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        render_ellipsis: Optional[Callable[[], QWidget]] = None,
        on_action: Optional[Callable[[str], None]] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroBreadcrumbs")

        self._variant = variant if variant in VALID_BREADCRUMBS_VARIANTS else "light"
        self._color = color if color in VALID_BREADCRUMBS_COLORS else "foreground"
        self._size = size if size in VALID_BREADCRUMBS_SIZES else "md"
        self._radius = radius if radius in VALID_BREADCRUMBS_RADII else "sm"
        self._underline = underline if underline in VALID_BREADCRUMBS_UNDERLINES else "hover"
        self._separator = separator
        self._max_items = max(2, int(max_items))
        self._items_before = max(0, int(items_before_collapse))
        self._items_after = max(0, int(items_after_collapse))
        self._hide_separator = bool(hide_separator)
        self._is_disabled = bool(is_disabled)
        self._disable_animation = bool(disable_animation)
        self._render_ellipsis = render_ellipsis
        self._on_action = on_action
        self._items: List[BreadcrumbItem] = list(items or [])
        self._crumbs: List["_Crumb"] = []
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme

        self._list = QWidget(self)
        self._list_lay = QHBoxLayout(self._list)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(0)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._list)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._rebuild()

    # ---- 构建 ----

    def _separator_widget(self, item: BreadcrumbItem) -> Optional[QWidget]:
        """项分隔符：item 级 > 全局级 > 默认 chevron。"""
        if item.hide_separator:
            return None
        sep = item.separator if item.separator is not None else self._separator
        if isinstance(sep, str):
            return _make_separator_widget(sep, self._theme)
        if sep is not None:
            return sep
        color = build_item_styles(item.color or self._color, self._theme,
                                  item.is_current)["separator"]
        return _Chevron(color)

    def _crumb_for(self, item: BreadcrumbItem) -> _Crumb:
        # 项级 underline 缺省继承全局（官方 itemProps 下发 color/underline/size）
        if item.underline is None:
            item.underline = self._underline
        crumb = _Crumb(item, self._color, self._size, self._theme, self._list)
        crumb.pressed.connect(lambda it, c=crumb: self._on_item_pressed(it, c))
        self._crumbs.append(crumb)
        return crumb

    def _ellipsis_widget(self, collapsed_first: BreadcrumbItem,
                         collapsed_items: Optional[list] = None) -> QWidget:
        """省略号项：render_ellipsis(collapsed_items) 自定义 > 默认三点图标；
        点击触发第一个被折叠项。"""
        if self._render_ellipsis is not None:
            w = self._render_ellipsis(collapsed_items or [collapsed_first])
            if w is not None:
                return w
        color = build_item_styles(self._color, self._theme, False)["text"]
        wrap = QWidget(self._list)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_EllipsisIcon(color))
        wrap.setCursor(Qt.CursorShape.PointingHandCursor)

        def _pressed(item=collapsed_first):
            self._on_item_pressed(item)

        wrap.mousePressEvent = lambda e: _pressed()  # type: ignore[assignment]
        return wrap

    def _apply_list_style(self):
        """variant 容器样式：solid 底色 / bordered 边框 / light 无 + 内边距与圆角。"""
        styles = build_list_styles(self._variant, self._theme)
        pad = BREADCRUMBS_SIZES[self._size]
        if self._variant in ("solid", "bordered"):
            self._list_lay.setContentsMargins(pad["padding_x"], pad["padding_y"],
                                              pad["padding_x"], pad["padding_y"])
        else:
            self._list_lay.setContentsMargins(0, 0, 0, 0)
        # QWidget QSS 背景需要 WA_StyledBackground（项目铁律）
        self._list.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # full=胶囊：QSS 超大半径（9999px）在 Qt 中不绘制圆角，按内容高度取半
        radius = _RADIUS_PX[self._radius]
        if self._radius == "full":
            radius = (pad["padding_y"] * 2 + pad["font"] + 4) // 2 + 1
        qss = "background: transparent; border: none;"
        if styles["bg"] != "none":
            qss = f"background: {styles['bg'].name()}; border: none;"
        if styles["border"] != "none":
            qss = (f"background: none; border: {styles['border_w']}px solid "
                   f"{styles['border'].name()};")
        if radius:
            qss += f" border-radius: {radius}px;"
        self._list.setStyleSheet(qss)

    def _rebuild(self):
        """按官方逻辑重建整条链（含折叠）。"""
        self._crumbs = []
        while self._list_lay.count():
            w = self._list_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._apply_list_style()

        count = len(self._items)
        if count == 0:
            return

        # 官方：isLast 自动推断；isCurrent 显式值优先（cloneElement 中
        # ...child.props 覆盖默认推断），未设置才用 isLast 推断；
        # isDisabled 全局且非 last
        resolved: List[BreadcrumbItem] = []
        for i, item in enumerate(self._items):
            if item.key is None:
                item.key = str(i)
            item.is_last = i == count - 1
            if item.is_current is None:
                item.is_current = item.is_last
            if self._is_disabled and not item.is_last:
                item.is_disabled = True
            resolved.append(item)

        shown = resolved
        ellipsis_first: Optional[BreadcrumbItem] = None
        # 官方折叠：childCount >= maxItems 且 before+after < count
        if (count >= self._max_items
                and self._items_before + self._items_after < count):
            collapsed = resolved[self._items_before:count - self._items_after]
            if collapsed:
                ellipsis_first = collapsed[0]
                shown = (resolved[:self._items_before]
                         + [collapsed[0]]  # 省略号占位（渲染为图标）
                         + resolved[count - self._items_after:])

        for i, item in enumerate(shown):
            if i > 0:
                prev = shown[i - 1]
                sep = self._separator_widget(prev)
                if sep is not None:
                    self._list_lay.addWidget(sep)
            if item is ellipsis_first and ellipsis_first is not None:
                # 折叠占位：children 换成省略号图标（官方 cloneElement）
                self._list_lay.addWidget(self._ellipsis_widget(item, collapsed))
            else:
                self._list_lay.addWidget(self._crumb_for(item))

    def _on_item_pressed(self, item: BreadcrumbItem, crumb: Optional["_Crumb"] = None):
        # underline="focus"：点击转移持久下划线标记（单选）
        if crumb is not None:
            for c in self._crumbs:
                c.set_clicked(c is crumb)
        if item.on_press is not None:
            item.on_press()
        if item.key is not None:
            self.action_triggered.emit(item.key)
        if self._on_action is not None and item.key is not None:
            self._on_action(item.key)
        self.item_pressed.emit(item)

    # ---- 公共 API ----

    def set_items(self, items: List[BreadcrumbItem]):
        """替换整条面包屑。"""
        self._items = list(items)
        self._rebuild()

    def set_separator(self, separator: Optional[Union[QWidget, str]]):
        self._separator = separator
        self._rebuild()

    def set_variant(self, variant: str):
        self._variant = variant if variant in VALID_BREADCRUMBS_VARIANTS else "light"
        self._rebuild()

    def set_color(self, color: str):
        self._color = color if color in VALID_BREADCRUMBS_COLORS else "foreground"
        self._rebuild()

    def set_size(self, size: str):
        self._size = size if size in VALID_BREADCRUMBS_SIZES else "md"
        self._rebuild()

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self._rebuild()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._rebuild()

    def _apply_provider_theme(self, theme: str):
        self._theme = theme
        self._rebuild()

    def _apply_styles(self):
        self._rebuild()
