"""
HeroSideUI Listbox Component
基于 HeroUI v2 设计风格 (listbox 复用 menu 样式)

样式来源：
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/menu.ts
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/listbox.ts
    https://github.com/heroui-inc/heroui/tree/main/packages/components/listbox

结构::

    Listbox (QWidget)
        ├── topContent     (可选)
        ├── _list_container (QWidget, list slot)
        │     ├── ListboxItem / ListboxSection ...
        │     └── _empty_label (默认隐藏)
        └── bottomContent  (可选)

    ListboxItem (QAbstractButton)
        自绘 base 背景/边框/分隔线
        水平内部 layout: [start_content] [wrapper(title + description)] [shortcut] [end_content / selectedIcon]
        状态: hover / focused / selected / disabled

    ListboxSection (QWidget)
        ├── heading  (Caption 字号 12)
        ├── group    QVBoxLayout 容纳 items
        └── divider  (可选)

特性对齐 HeroUI:
    - 6 variants: solid / shadow / bordered / flat / faded / light
    - 6 colors:   default / primary / secondary / success / warning / danger
    - 3 sizes:    sm / md / lg
    - selection_mode: none / single / multiple
    - showDivider / isDisabled / disable_animation
    - hide_selected_icon / should_highlight_on_focus
    - 信号: selection_changed(set[str]) / action(str)
    - 主题: light / dark / auto
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QAbstractButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QEvent
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPalette,
    QPainterPath,
    QFont,
    QFontMetrics,
    QPixmap,
)
from typing import Iterable, Optional, Union

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, LISTBOX_SIZES
from ..utils import load_svg_icon, aligned_color_pair
from ..animation import (
    tween_value,
    stop_tween,
    paint_animated_check,
    CheckDrawAnimation,
)
from ..core import ThemeProvider

# ============================================================
# 颜色解析（顶层函数，纯函数式）
# ============================================================


def _bg_role_color(theme: str) -> QColor:
    """list 默认底色（透明，跟随父）。"""
    return QColor(0, 0, 0, 0)


def _hover_bg(variant: str, color: str, theme: str) -> QColor:
    """item hover/focus 时的背景色。

    对应 HeroUI compoundVariants 中各 variant×color 的 data-[hover=true]:bg-...
    """
    palette = HEROUI_COLORS[color]
    default_pal = HEROUI_COLORS["default"]

    if variant in ("solid", "shadow"):
        # solid/shadow：default → default-100/dark-800；彩色 → {color}-500
        if color == "default":
            return (
                QColor(default_pal[100])
                if theme == "light"
                else QColor(default_pal[800])
            )
        return QColor(palette[500])

    if variant == "flat":
        # bg-{color}/20；default 用 default/40
        if color == "default":
            c = (
                QColor(default_pal[200])
                if theme == "light"
                else QColor(default_pal[700])
            )
            c.setAlphaF(0.40)
            return c
        c = QColor(palette[500])
        c.setAlphaF(0.20)
        return c

    if variant == "faded":
        # data-[hover=true]:bg-default-100（彩色 faded 也是 default-100 底，靠字色变色）
        return (
            QColor(default_pal[100]) if theme == "light" else QColor(default_pal[800])
        )

    # bordered / light：hover 不改 bg
    return QColor(0, 0, 0, 0)


def _hover_border(variant: str, color: str, theme: str) -> QColor:
    """item hover 时的边框色（仅 bordered / faded 使用）。"""
    palette = HEROUI_COLORS[color]
    if variant == "bordered":
        if color == "default":
            return QColor(palette[300]) if theme == "light" else QColor(palette[600])
        return QColor(palette[500])
    if variant == "faded":
        # hover:border-default
        return (
            QColor(HEROUI_COLORS["default"][200])
            if theme == "light"
            else QColor(HEROUI_COLORS["default"][700])
        )
    return QColor(0, 0, 0, 0)


def _faded_resting_bg(theme: str) -> QColor:
    """faded 变体未 hover 时的浅底（来自 menu faded 的 border-transparent + 视觉的 default-50）。

    HeroUI menu faded 默认其实是透明边框透明底，hover 时才出 default-100。这里我们对齐：
    resting 透明，hover 才有底。
    """
    return QColor(0, 0, 0, 0)


def _text_default(theme: str) -> QColor:
    """item 默认（未 hover/未 selected）字色。"""
    return (
        QColor(HEROUI_COLORS["default"][800])
        if theme == "light"
        else QColor(HEROUI_COLORS["default"][100])
    )


def _text_hover(variant: str, color: str, theme: str) -> QColor:
    """item hover/focused 时字色。"""
    palette = HEROUI_COLORS[color]
    if variant == "solid":
        if color == "default":
            # text-default-foreground = light:#000 dark:#fff
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        # 彩色 solid: text-{color}-foreground = 白
        return QColor("#FFFFFF")
    if variant == "shadow":
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor("#FFFFFF")
    if variant == "flat":
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(palette[500] if theme == "light" else palette[400])
    if variant == "faded":
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(palette[500] if theme == "light" else palette[400])
    if variant == "bordered":
        if color == "default":
            return _text_default(theme)
        return QColor(palette[500] if theme == "light" else palette[400])
    if variant == "light":
        if color == "default":
            return QColor(HEROUI_COLORS["default"][500])
        return QColor(palette[500] if theme == "light" else palette[400])
    return _text_default(theme)


def _desc_color(theme: str) -> QColor:
    """description 默认色 (text-foreground-500)。"""
    return QColor(HEROUI_COLORS["default"][500])


def _shortcut_border(theme: str) -> QColor:
    return (
        QColor(HEROUI_COLORS["default"][300])
        if theme == "light"
        else QColor(HEROUI_COLORS["default"][700])
    )


def _selected_indicator_color(variant: str, color: str, theme: str) -> QColor:
    """选中标记的颜色（v 形勾，对齐 selectedIcon 的 text-inherit -> 跟 hover 文字色一致）。"""
    return _text_hover(variant, color, theme)


def _divider_color(theme: str) -> QColor:
    return (
        QColor(HEROUI_COLORS["default"][200])
        if theme == "light"
        else QColor(HEROUI_COLORS["default"][700])
    )


# ============================================================
# ListboxItem
# ============================================================


class ListboxItem(QAbstractButton):
    """单个列表项。

    用法::

        item = ListboxItem("New file", key="new", description="Create a new file",
                           start_content=icon_widget, shortcut="Ctrl+N")
        listbox.add_item(item)

        # 或快捷创建：
        listbox.add_item("New file", key="new", description="Create a new file",
                         shortcut="Ctrl+N")

    交互::
        - 单击 → 触发 ``activated(key)`` 信号
        - 选中 (selection_mode != none) → 触发 ``selection_changed(bool)``

    样式属性由父 Listbox 通过 :py:meth:`apply_style` 注入；用户不要手动调。
    """

    HOVER_ANIM_DURATION = 150
    SELECT_ANIM_DURATION = 150

    activated = Signal(str)
    selected_changed = Signal(bool)

    def __init__(
        self,
        title: str = "",
        *,
        key: Optional[str] = None,
        description: str = "",
        start_content: Optional[Union[str, QWidget]] = None,
        end_content: Optional[Union[str, QWidget]] = None,
        shortcut: str = "",
        is_disabled: bool = False,
        show_divider: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCheckable(True)

        # 数据
        self._title = title
        self._key = key if key is not None else (title if title else f"item_{id(self)}")
        self._description = description
        self._shortcut = shortcut
        self._show_divider = show_divider
        self._is_disabled = is_disabled

        # 状态
        self._is_hover = False
        self._is_focused = False
        self._is_selected = False

        # 父 Listbox 注入的样式
        self._variant = "solid"
        self._color = "default"
        self._size = "md"
        self._radius = "sm"
        self._theme = "light"
        self._disable_animation = False
        self._hide_selected_icon = False  # 对齐 HeroUI 源码 hideSelectedIcon=false：默认显示对勾
        self._highlight_on_focus = False
        # selection 行为
        self._selectable = True

        # 当前过渡色（tween 改这两个，paintEvent / 字色直接读）
        self._cur_bg = QColor(0, 0, 0, 0)
        self._cur_border = QColor(0, 0, 0, 0)
        self._cur_text = _text_default("light")
        self._cur_indicator_alpha = (
            0.0  # 选中勾外层透明度（用于淡出，paint_animated_check 内部走 progress）
        )
        self._bg_anim_runner = None
        self._border_anim_runner = None
        self._text_anim_runner = None
        self._indicator_anim_runner = None

        # 选中勾的"按路径描出 / 反向擦除"动画
        # - 选中: progress 0 → 1（带 delay_in 让背景先铺开再描勾）
        # - 取消: progress 1 → 0（按原路径反向把勾擦掉，节奏要明显快于描出，
        #         避免"勾还在 hover 退出动画就开始消失"的体验拖沓）
        # 由 CheckDrawAnimation 的 draw_out=True 启用反向擦除；外层不再走 alpha 淡出。
        # easing_out 用 OutCubic（"快出慢收"），让擦除节奏与 in 段对称。
        from PySide6.QtCore import QEasingCurve

        self._check_anim = CheckDrawAnimation(
            self,
            on_step=lambda v: self.update(),
            duration_in=400,
            duration_out=120,
            delay_in=80,
            draw_out=True,
            easing_out=QEasingCurve.Type.OutCubic,
        )

        # 内部布局：HBox = [start_content] [wrapper(title/description)] [shortcut] [end_content / selectedIcon]
        self._h = QHBoxLayout(self)
        self._h.setContentsMargins(
            0, 0, 0, 0
        )  # padding 由 _content_margins 决定（见 _apply_size）
        self._h.setSpacing(0)

        # start_content 槽（QWidget 或 SVG 名/路径，str 时内部包成 QLabel + pixmap）
        self._start_label = QLabel(self)
        self._start_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._start_label.hide()
        self._h.addWidget(self._start_label, 0, Qt.AlignVCenter)
        self._start_widget: Optional[QWidget] = None
        self._start_src: Optional[str] = None

        # wrapper: title + description
        self._wrap = QWidget(self)
        self._wrap.setAttribute(Qt.WA_TranslucentBackground, True)
        self._wrap_v = QVBoxLayout(self._wrap)
        self._wrap_v.setContentsMargins(0, 0, 0, 0)
        self._wrap_v.setSpacing(0)
        self._title_label = QLabel(self._title, self._wrap)
        self._title_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._title_label.setForegroundRole(QPalette.WindowText)
        self._desc_label = QLabel(self._description, self._wrap)
        self._desc_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._desc_label.setForegroundRole(QPalette.WindowText)
        self._wrap_v.addWidget(self._title_label)
        self._wrap_v.addWidget(self._desc_label)
        if not self._description:
            self._desc_label.hide()
        self._h.addWidget(self._wrap, 1)

        # shortcut 标记
        self._shortcut_label = QLabel(self._shortcut, self)
        self._shortcut_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._shortcut_label.setForegroundRole(QPalette.WindowText)
        if not self._shortcut:
            self._shortcut_label.hide()
        self._h.addWidget(self._shortcut_label, 0, Qt.AlignVCenter)

        # end_content 槽
        self._end_label = QLabel(self)
        self._end_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._end_label.hide()
        self._h.addWidget(self._end_label, 0, Qt.AlignVCenter)
        self._end_widget: Optional[QWidget] = None
        self._end_src: Optional[str] = None

        # selectedIcon 占位槽 —— 用一个空 QWidget 占住对勾画的位置，
        # 让 wrapper / shortcut / end_content 的 layout 自动避开（不会重叠）。
        # 只在"会画对勾"的场景显示（selectable + hide_selected_icon=False + 没 end_content），
        # 其他时候 hide()。paintEvent 里 `_paint_check` 直接画到这个槽的 geometry。
        self._check_slot = QWidget(self)
        self._check_slot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._check_slot.setAttribute(Qt.WA_TranslucentBackground, True)
        self._check_slot.hide()
        self._h.addWidget(self._check_slot, 0, Qt.AlignVCenter)

        # 设置初始 content
        if start_content is not None:
            self.set_start_content(start_content)
        if end_content is not None:
            self.set_end_content(end_content)

        # 初次同步
        self._set_disabled(is_disabled)

        # 监听 toggled（Listbox 单/多选模式下 emit 选中切换）
        self.toggled.connect(self._on_toggled)

    # ------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------
    def key(self) -> str:
        return self._key

    def set_key(self, key: str):
        self._key = key

    def title(self) -> str:
        return self._title

    def set_title(self, t: str):
        self._title = t
        self._title_label.setText(t)

    def description(self) -> str:
        return self._description

    def set_description(self, d: str):
        self._description = d
        self._desc_label.setText(d)
        self._desc_label.setVisible(bool(d))

    def shortcut_text(self) -> str:
        return self._shortcut

    def set_shortcut(self, s: str):
        self._shortcut = s
        self._shortcut_label.setText(s)
        self._shortcut_label.setVisible(bool(s))

    def is_disabled(self) -> bool:
        return self._is_disabled

    def set_disabled(self, v: bool):
        self._set_disabled(v)

    def _set_disabled(self, v: bool):
        self._is_disabled = bool(v)
        self.setEnabled(not self._is_disabled)
        if self._is_disabled:
            self.setCursor(Qt.ForbiddenCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        self.update()

    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, v: bool):
        v = bool(v)
        if v == self._is_selected:
            return
        self._is_selected = v
        # 与 isChecked 保持一致（不发 toggled —— 由父 Listbox 控制）
        self.blockSignals(True)
        self.setChecked(v)
        self.blockSignals(False)
        # 选中态变化：驱动对勾描边动画
        if self._disable_animation:
            self._check_anim.set_immediate(v)
        else:
            self._check_anim.play(v)
        self._refresh_palette(animated=not self._disable_animation)
        self.selected_changed.emit(v)

    def show_divider(self) -> bool:
        return self._show_divider

    def set_show_divider(self, v: bool):
        self._show_divider = bool(v)
        self.update()
        # 高度需重算
        self.updateGeometry()

    def set_start_content(self, content: Optional[Union[str, QWidget]]):
        # 清旧
        if (
            self._start_widget is not None
            and self._start_widget is not self._start_label
        ):
            self._h.removeWidget(self._start_widget)
            self._start_widget.setParent(None)
            self._start_widget.deleteLater()
            self._start_widget = None
        self._start_src = None
        self._start_label.hide()

        if content is None:
            return
        if isinstance(content, str):
            self._start_src = content
            self._refresh_start_pixmap()
            self._start_label.show()
        elif isinstance(content, QWidget):
            self._start_widget = content
            self._h.insertWidget(0, content, 0, Qt.AlignVCenter)
        self._update_layout_spacing()

    def set_end_content(self, content: Optional[Union[str, QWidget]]):
        if self._end_widget is not None and self._end_widget is not self._end_label:
            self._h.removeWidget(self._end_widget)
            self._end_widget.setParent(None)
            self._end_widget.deleteLater()
            self._end_widget = None
        self._end_src = None
        self._end_label.hide()

        if content is None:
            self._update_layout_spacing()
            self._refresh_check_slot()
            return
        if isinstance(content, str):
            self._end_src = content
            self._refresh_end_pixmap()
            self._end_label.show()
        elif isinstance(content, QWidget):
            self._end_widget = content
            # 插在 _check_slot 之前（_check_slot 永远在最右），确保 end_content
            # 占据用户视觉关注的 endContent 槽位、selectedIcon 占位被 hide。
            slot_idx = self._h.indexOf(self._check_slot)
            insert_idx = slot_idx if slot_idx >= 0 else self._h.count()
            self._h.insertWidget(insert_idx, content, 0, Qt.AlignVCenter)
        self._update_layout_spacing()
        self._refresh_check_slot()

    # ------------------------------------------------------------
    # 父 Listbox 注入样式
    # ------------------------------------------------------------
    def apply_style(
        self,
        *,
        variant: str,
        color: str,
        size: str,
        radius: str,
        theme: str,
        disable_animation: bool,
        hide_selected_icon: bool,
        highlight_on_focus: bool,
        selectable: bool,
    ):
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._theme = theme
        self._disable_animation = disable_animation
        self._hide_selected_icon = hide_selected_icon
        self._highlight_on_focus = highlight_on_focus
        self._selectable = selectable

        self._apply_size()
        self._refresh_pixmap_color()
        self._refresh_palette(animated=False)
        self.update()

    # ------------------------------------------------------------
    # 尺寸与字体
    # ------------------------------------------------------------
    def _size_cfg(self) -> dict:
        return LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])

    def _apply_size(self):
        cfg = self._size_cfg()

        # 设置 layout margins
        self._h.setContentsMargins(
            cfg["item_padding_x"],
            cfg["item_padding_y"],
            cfg["item_padding_x"],
            cfg["item_padding_y"],
        )
        self._h.setSpacing(cfg["item_gap"])

        # 字体
        title_f = QFont(FONT_FAMILY)
        title_f.setPixelSize(cfg["title_font_size"])
        title_f.setWeight(QFont.Normal)
        self._title_label.setFont(title_f)

        desc_f = QFont(FONT_FAMILY)
        desc_f.setPixelSize(cfg["desc_font_size"])
        self._desc_label.setFont(desc_f)
        self._desc_label.setStyleSheet(
            f"color: {_desc_color(self._theme).name()}; background: transparent;"
        )

        sc_f = QFont(FONT_FAMILY)
        sc_f.setPixelSize(cfg["shortcut_font_size"])
        self._shortcut_label.setFont(sc_f)
        self._shortcut_label.setStyleSheet(
            f"color: {_desc_color(self._theme).name()};"
            f" border: 1px solid {_shortcut_border(self._theme).name()};"
            f" border-radius: 4px;"
            f" padding: 0 4px;"
            f" background: transparent;"
        )

        self._update_layout_spacing()
        self._refresh_check_slot()
        self.updateGeometry()

    def _refresh_check_slot(self):
        """根据当前状态决定是否在右侧预留 selectedIcon 占位。

        显示规则（和 ``_paint_check`` 必须保持一致）：
        - selectable（selection_mode != "none"）
        - hide_selected_icon=False（默认；为 True 时关闭对勾）
        - 没设 end_content（end_content 占同一槽位，让用户内容优先）

        宽度 = ``selected_icon_size * 1.6``（与 _paint_check 里的 box 一致）。
        """
        cfg = self._size_cfg()
        box = int(cfg["selected_icon_size"] * 1.6)
        will_show_check = (
            self._selectable
            and not self._hide_selected_icon
            and self._end_widget is None
            and self._end_src is None
        )
        if will_show_check:
            self._check_slot.setFixedSize(box, box)
            self._check_slot.show()
        else:
            self._check_slot.hide()

    def _update_layout_spacing(self):
        # 没有 description 时把 wrap 缩成单行高度
        self._desc_label.setVisible(bool(self._description))
        self._shortcut_label.setVisible(bool(self._shortcut))
        # 强制刷新尺寸
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        cfg = self._size_cfg()
        # 基础高度 = title font + 上下 padding；有 description 时再加 desc 行
        title_h = QFontMetrics(self._title_label.font()).height()
        h = title_h + cfg["item_padding_y"] * 2
        if self._description:
            desc_h = QFontMetrics(self._desc_label.font()).height()
            h += desc_h
        # 估算宽度（不强求精确，layout 会自己拉伸）
        w = self._title_label.sizeHint().width() + cfg["item_padding_x"] * 2 + 32
        if self._show_divider:
            h += cfg["divider_margin_bot"] + cfg["divider_height"]
        return QSize(max(w, 80), h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ------------------------------------------------------------
    # icon pixmap 着色
    # ------------------------------------------------------------
    def _refresh_pixmap_color(self):
        self._refresh_start_pixmap()
        self._refresh_end_pixmap()

    def _refresh_start_pixmap(self):
        if self._start_src is None:
            return
        cfg = self._size_cfg()
        size = cfg["title_font_size"] + 2
        c = self._cur_text if self._cur_text.isValid() else _text_default(self._theme)
        pix = load_svg_icon(self._start_src, size=size, color=c)
        self._start_label.setPixmap(pix)
        self._start_label.setFixedSize(size, size)

    def _refresh_end_pixmap(self):
        if self._end_src is None:
            return
        cfg = self._size_cfg()
        size = cfg["title_font_size"] + 2
        c = self._cur_text if self._cur_text.isValid() else _text_default(self._theme)
        pix = load_svg_icon(self._end_src, size=size, color=c)
        self._end_label.setPixmap(pix)
        self._end_label.setFixedSize(size, size)

    # ------------------------------------------------------------
    # 状态变化
    # ------------------------------------------------------------
    def enterEvent(self, e):
        super().enterEvent(e)
        if not self._is_disabled:
            self._is_hover = True
            self._refresh_palette(animated=not self._disable_animation)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._is_hover = False
        self._refresh_palette(animated=not self._disable_animation)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._is_focused = True
        if self._highlight_on_focus:
            self._refresh_palette(animated=not self._disable_animation)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._is_focused = False
        if self._highlight_on_focus:
            self._refresh_palette(animated=not self._disable_animation)

    def _on_toggled(self, checked: bool):
        # 只在 selectable 模式下当作选中态变化
        if not self._selectable:
            return
        self._is_selected = checked
        if self._disable_animation:
            self._check_anim.set_immediate(checked)
        else:
            self._check_anim.play(checked)
        self._refresh_palette(animated=not self._disable_animation)
        self.selected_changed.emit(checked)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if not self._is_disabled and self.rect().contains(
            e.position().toPoint() if hasattr(e, "position") else e.pos()
        ):
            self.activated.emit(self._key)

    # ------------------------------------------------------------
    # palette 计算（动画）
    # ------------------------------------------------------------
    def _is_active(self) -> bool:
        """是否处于"高亮"态（hover/focus(if highlight_on_focus)/selected）。"""
        if self._is_disabled:
            return False
        if self._is_hover:
            return True
        if self._highlight_on_focus and self._is_focused:
            return True
        if self._is_selected and self._selectable:
            return True
        return False

    def _refresh_palette(self, *, animated: bool):
        active = self._is_active()
        # 目标色
        if active:
            target_bg = _hover_bg(self._variant, self._color, self._theme)
            target_border = _hover_border(self._variant, self._color, self._theme)
            target_text = _text_hover(self._variant, self._color, self._theme)
        else:
            # 未激活：bg/border 透明（保留色相，避免插值经过黑色 → 见 _aligned_pair）
            target_bg = QColor(0, 0, 0, 0)
            target_border = QColor(0, 0, 0, 0)
            target_text = _text_default(self._theme)

        # 选中勾的"可见开关"alpha：只受 hide_selected_icon 影响。
        # 选中态本身的视觉过渡由 _check_anim.progress 负责（描出 / 反向擦除），
        # 不让 alpha 同步淡出 —— 否则会和 progress 1→0 重叠成"双重消失"。
        target_indicator = 0.0 if self._hide_selected_icon else 1.0

        if not animated:
            self._cur_bg = target_bg
            self._cur_border = target_border
            self._cur_text = target_text
            self._cur_indicator_alpha = target_indicator
            self._apply_text_color()
            self._refresh_pixmap_color()
            self.update()
            return

        # 关键：透明色没有"色相"，直接 lerp(QColor(0,0,0,0) → 实色) 在 alpha 升起的同时 RGB
        # 也从黑色拉过去，前半段会出现一抹深灰（用户截图里就是这个效果）。
        # 解决：用 aligned_color_pair 把"透明端"的 RGB 对齐到"非透明端"的 RGB，alpha 保持 0；
        # 这样插值就是纯粹的 alpha 起伏，色相全程稳定。
        bg_start, bg_end = aligned_color_pair(self._cur_bg, target_bg)
        bd_start, bd_end = aligned_color_pair(self._cur_border, target_border)

        # 文字色：RGB 一定有效，直接 tween；但若起点是默认色、终点是 hover 色（或反过来），
        # 中间也是同色域（灰 → 彩），不会经过黑/白，体感 OK，无需对齐。
        tween_value(
            self,
            "_bg_anim_runner",
            bg_start,
            bg_end,
            self._on_bg_step,
            duration=self.HOVER_ANIM_DURATION,
        )
        tween_value(
            self,
            "_border_anim_runner",
            bd_start,
            bd_end,
            self._on_border_step,
            duration=self.HOVER_ANIM_DURATION,
        )
        tween_value(
            self,
            "_text_anim_runner",
            QColor(self._cur_text),
            QColor(target_text),
            self._on_text_step,
            duration=self.HOVER_ANIM_DURATION,
        )
        tween_value(
            self,
            "_indicator_anim_runner",
            float(self._cur_indicator_alpha),
            float(target_indicator),
            self._on_indicator_step,
            duration=self.SELECT_ANIM_DURATION,
        )

    def _on_bg_step(self, c):
        self._cur_bg = QColor(c)
        self.update()

    def _on_border_step(self, c):
        self._cur_border = QColor(c)
        self.update()

    def _on_text_step(self, c):
        self._cur_text = QColor(c)
        self._apply_text_color()
        self._refresh_pixmap_color()
        self.update()

    def _on_indicator_step(self, v):
        self._cur_indicator_alpha = float(v)
        self.update()

    def _apply_text_color(self):
        # title 用当前过渡色，description 总是 default-500（HeroUI menu 行为）
        self._title_label.setStyleSheet(
            f"color: {self._cur_text.name()}; background: transparent;"
        )

    # ------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------
    def paintEvent(self, e):
        if self._is_disabled:
            opacity = 0.5
        else:
            opacity = 1.0

        cfg = self._size_cfg()
        item_radius = cfg["item_radius"]

        rect = self.rect()
        # 留出 divider 的位置
        body_rect = QRect(rect)
        if self._show_divider:
            body_rect.setHeight(
                rect.height() - cfg["divider_height"] - cfg["divider_margin_bot"]
            )

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(opacity)

        # 背景 (圆角)
        if self._cur_bg.alpha() > 0:
            path = QPainterPath()
            path.addRoundedRect(
                body_rect.adjusted(0, 0, 0, 0), item_radius, item_radius
            )
            p.fillPath(path, self._cur_bg)

        # 边框（仅当颜色非透明时）
        if self._cur_border.alpha() > 0:
            border_w = 2 if self._variant == "bordered" else 1
            p.setPen(self._cur_border)
            from PySide6.QtGui import QPen

            pen = QPen(self._cur_border)
            pen.setWidth(border_w)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            inset = border_w / 2
            p.drawRoundedRect(
                body_rect.adjusted(int(inset), int(inset), -int(inset), -int(inset)),
                item_radius - inset,
                item_radius - inset,
            )

        # 选中指示标记 (selectedIcon)：右侧画一个小勾
        if self._cur_indicator_alpha > 0.001 and not self._hide_selected_icon:
            self._paint_check(p, body_rect, cfg)

        # 分隔线
        if self._show_divider:
            divider_y = body_rect.bottom() + cfg["divider_margin_bot"]
            from PySide6.QtGui import QPen

            pen = QPen(_divider_color(self._theme))
            pen.setWidth(cfg["divider_height"])
            p.setPen(pen)
            p.setOpacity(opacity)
            p.drawLine(body_rect.left(), divider_y, body_rect.right(), divider_y)

        p.end()

    def _paint_check(self, p: QPainter, rect: QRect, cfg: dict):
        """画选中态对勾（按 path 描出）—— 复用 animation/check_draw.paint_animated_check。

        位置直接对齐 ``_check_slot.geometry()``。slot 由 ``_refresh_check_slot``
        负责显隐和宽度，layout 自动给它腾出位置 → 永远不会和 shortcut /
        end_content 重叠。

        end_content 已被设置时 slot 会被 hide，这里也直接 return（语义和 HeroUI
        selectedIcon 与 endContent 同槽位一致）。
        """
        if self._end_widget is not None or self._end_src is not None:
            return
        if not self._check_slot.isVisible():
            return

        slot = self._check_slot.geometry()
        c = QColor(_selected_indicator_color(self._variant, self._color, self._theme))
        paint_animated_check(
            p,
            slot,
            c,
            progress=self._check_anim.progress,
            opacity=self._cur_indicator_alpha,
        )


# ============================================================
# ListboxSection
# ============================================================


class ListboxSection(QWidget):
    """分组容器。

    用法::

        sec = ListboxSection("Actions", show_divider=True)
        sec.add_item("Copy", key="copy")
        sec.add_item("Paste", key="paste")
        listbox.add_section(sec)
    """

    def __init__(
        self,
        title: str = "",
        *,
        show_divider: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._title = title
        self._show_divider = show_divider

        self._theme = "light"
        self._size = "md"

        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(0, 0, 0, 0)
        self._v.setSpacing(0)

        # heading
        self._heading = QLabel(title, self)
        self._heading.setAttribute(Qt.WA_TranslucentBackground, True)
        self._heading.setForegroundRole(QPalette.WindowText)
        self._v.addWidget(self._heading)
        if not title:
            self._heading.hide()

        # group
        self._group = QWidget(self)
        self._group.setAttribute(Qt.WA_TranslucentBackground, True)
        self._group_v = QVBoxLayout(self._group)
        self._group_v.setContentsMargins(0, 0, 0, 0)
        self._v.addWidget(self._group)

        # divider 区域
        self._has_divider_painted = False

        self._items: list[ListboxItem] = []

    def title(self) -> str:
        return self._title

    def set_title(self, t: str):
        self._title = t
        self._heading.setText(t)
        self._heading.setVisible(bool(t))

    def show_divider(self) -> bool:
        return self._show_divider

    def set_show_divider(self, v: bool):
        self._show_divider = bool(v)
        self.update()

    def add_item(self, item_or_title, **kwargs) -> ListboxItem:
        """添加一项；可以传 ListboxItem 或 (title, **kwargs)"""
        if isinstance(item_or_title, ListboxItem):
            it = item_or_title
        else:
            it = ListboxItem(item_or_title, **kwargs)
        self._items.append(it)
        self._group_v.addWidget(it)
        # 父 Listbox 在 add_section 后会调 _propagate_style 注入样式
        return it

    def items(self) -> list[ListboxItem]:
        return list(self._items)

    def _apply_style(
        self,
        *,
        variant: str,
        color: str,
        size: str,
        radius: str,
        theme: str,
        disable_animation: bool,
        hide_selected_icon: bool,
        highlight_on_focus: bool,
        selectable: bool,
    ):
        self._theme = theme
        self._size = size

        cfg = LISTBOX_SIZES.get(size, LISTBOX_SIZES["md"])
        self._v.setSpacing(0)
        self._group_v.setSpacing(cfg["list_gap"])

        # heading 样式：text-tiny + text-foreground-500
        f = QFont(FONT_FAMILY)
        f.setPixelSize(cfg["desc_font_size"])
        self._heading.setFont(f)
        self._heading.setStyleSheet(
            f"color: {_desc_color(theme).name()};"
            f" padding: 0 {cfg['item_padding_x'] // 2}px;"
            f" background: transparent;"
        )
        # 顶部 padding：has-title=true:pt-1
        if self._title:
            self._group.setContentsMargins(0, 4, 0, 0)
        else:
            self._group.setContentsMargins(0, 0, 0, 0)

        # 底部 margin: mb-2 + divider mt-2 ≈ 8 + 8
        self._v.setContentsMargins(0, 0, 0, 8 if not self._show_divider else 16)

        # 把样式向下传给所有 item
        for it in self._items:
            it.apply_style(
                variant=variant,
                color=color,
                size=size,
                radius=radius,
                theme=theme,
                disable_animation=disable_animation,
                hide_selected_icon=hide_selected_icon,
                highlight_on_focus=highlight_on_focus,
                selectable=selectable,
            )

        self.update()

    def paintEvent(self, e):
        if not self._show_divider:
            return
        from PySide6.QtGui import QPen

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(_divider_color(self._theme))
        pen.setWidth(1)
        p.setPen(pen)
        # 在 section 底部一行
        y = self.height() - 8
        p.drawLine(0, y, self.width(), y)
        p.end()


# ============================================================
# Listbox
# ============================================================


class Listbox(QWidget):
    """HeroUI 风格列表框。

    用法::

        lb = Listbox(variant="flat", color="primary", selection_mode="single")
        lb.add_item("New", key="new", description="Create a new file", shortcut="Ctrl+N")
        lb.add_item("Copy", key="copy")
        lb.add_item("Paste", key="paste")
        lb.action.connect(lambda key: print("activated", key))
        lb.selection_changed.connect(lambda keys: print("selected", keys))

    分组::

        sec = ListboxSection("Actions", show_divider=True)
        sec.add_item("Copy", key="copy")
        lb.add_section(sec)
    """

    selection_changed = Signal(set)
    action = Signal(str)
    open_changed = Signal(bool)  # 预留

    VALID_VARIANTS = ("solid", "shadow", "bordered", "flat", "faded", "light")
    VALID_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
    VALID_SIZES = ("sm", "md", "lg")
    VALID_SELECTION_MODES = ("none", "single", "multiple")

    def __init__(
        self,
        *,
        variant: str = "solid",
        color: str = "default",
        size: str = "md",
        radius: str = "sm",
        selection_mode: str = "none",
        selected_keys: Optional[Iterable[str]] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        empty_content: Optional[str] = None,
        hide_selected_icon: bool = False,
        should_highlight_on_focus: bool = False,
        disable_animation: bool = False,
        is_disabled: bool = False,
        top_content: Optional[QWidget] = None,
        bottom_content: Optional[QWidget] = None,
        theme: str = "auto",
        parent=None,
    ):
        super().__init__(parent)

        if variant not in self.VALID_VARIANTS:
            variant = "solid"
        if color not in self.VALID_COLORS:
            color = "default"
        if size not in self.VALID_SIZES:
            size = "md"
        if selection_mode not in self.VALID_SELECTION_MODES:
            selection_mode = "none"

        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._selection_mode = selection_mode
        self._hide_selected_icon = hide_selected_icon
        self._highlight_on_focus = should_highlight_on_focus
        self._disable_animation = disable_animation
        self._is_disabled = is_disabled
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 选中/禁用 key 状态
        self._selected_keys: set[str] = set(selected_keys or [])
        self._disabled_keys: set[str] = set(disabled_keys or [])

        # 外层 layout = base slot (gap-1, p-1)
        self._outer = QVBoxLayout(self)
        cfg = LISTBOX_SIZES.get(size, LISTBOX_SIZES["md"])
        self._outer.setContentsMargins(
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
        )
        self._outer.setSpacing(cfg["group_gap"])

        # topContent
        self._top_content: Optional[QWidget] = None
        if top_content is not None:
            self.set_top_content(top_content)

        # list 容器（list slot）
        self._list = QWidget(self)
        self._list.setAttribute(Qt.WA_TranslucentBackground, True)
        self._list_v = QVBoxLayout(self._list)
        self._list_v.setContentsMargins(0, 0, 0, 0)
        self._list_v.setSpacing(cfg["list_gap"])
        self._outer.addWidget(self._list)

        # emptyContent
        # 用户传 str → 单行文字（兼容旧用法）
        # 用户传 None（默认）→ 居中 icon + 中英双语 ("Nothing to show / 暂无内容")
        self._empty_content_text = empty_content  # None / "" 都视为用默认 icon 模式
        self._empty_widget: QWidget = QWidget()  # 占位，立刻被 _rebuild_empty_widget 替换
        self._list_v.addWidget(self._empty_widget)
        self._empty_label: QLabel = QLabel()  # 占位，立刻被 _rebuild_empty_widget 替换
        self._rebuild_empty_widget()
        self._empty_widget.hide()

        # bottomContent
        self._bottom_content: Optional[QWidget] = None
        if bottom_content is not None:
            self.set_bottom_content(bottom_content)

        # 子项 / 分组
        self._items: list[ListboxItem] = []
        self._sections: list[ListboxSection] = []

        # 焦点项索引（键盘导航用）
        self._focused_index = -1

        self.setFocusPolicy(Qt.StrongFocus)

        # 注册主题
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._propagate_style()
        self._refresh_empty()

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------
    def _resolve_theme(self, mode: str) -> str:
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        if self._theme_mode != "auto":
            return
        self._theme = theme
        self._propagate_style()
        self.update()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            ThemeProvider.instance().register(self)
            self._theme = ThemeProvider.instance().current_theme
        elif theme in ("light", "dark"):
            self._theme_mode = theme
            self._theme = theme
        else:
            return
        self._propagate_style()
        self.update()

    # ------------------------------------------------------------
    # 公共 API：装配
    # ------------------------------------------------------------
    def set_top_content(self, w: Optional[QWidget]):
        if self._top_content is not None:
            self._outer.removeWidget(self._top_content)
            self._top_content.setParent(None)
            self._top_content.deleteLater()
            self._top_content = None
        if w is not None:
            self._top_content = w
            self._outer.insertWidget(0, w)

    def set_bottom_content(self, w: Optional[QWidget]):
        if self._bottom_content is not None:
            self._outer.removeWidget(self._bottom_content)
            self._bottom_content.setParent(None)
            self._bottom_content.deleteLater()
            self._bottom_content = None
        if w is not None:
            self._bottom_content = w
            self._outer.addWidget(w)

    def add_item(
        self,
        item_or_title,
        *,
        key: Optional[str] = None,
        description: str = "",
        start_content=None,
        end_content=None,
        shortcut: str = "",
        is_disabled: bool = False,
        show_divider: bool = False,
    ) -> ListboxItem:
        """追加一项。

        - 传 ``ListboxItem`` 实例 → 直接挂上
        - 传 ``str`` (title) + 关键字参数 → 内部构造 ``ListboxItem``
        """
        if isinstance(item_or_title, ListboxItem):
            it = item_or_title
        else:
            it = ListboxItem(
                item_or_title,
                key=key,
                description=description,
                start_content=start_content,
                end_content=end_content,
                shortcut=shortcut,
                is_disabled=is_disabled,
                show_divider=show_divider,
            )
        self._attach_item(it)
        # 插到 _empty_label 之前
        idx = self._list_v.indexOf(self._empty_label)
        if idx < 0:
            self._list_v.addWidget(it)
        else:
            self._list_v.insertWidget(idx, it)
        self._items.append(it)
        self._propagate_style()
        self._refresh_empty()
        return it

    def add_section(
        self, sec_or_title, *, show_divider: bool = False
    ) -> ListboxSection:
        if isinstance(sec_or_title, ListboxSection):
            sec = sec_or_title
        else:
            sec = ListboxSection(sec_or_title, show_divider=show_divider)
        # 把分组里现有 item 都注册到 _items 列表（用于键盘导航 / disabled 同步）
        for it in sec.items():
            self._attach_item(it)
            self._items.append(it)

        idx = self._list_v.indexOf(self._empty_label)
        if idx < 0:
            self._list_v.addWidget(sec)
        else:
            self._list_v.insertWidget(idx, sec)
        self._sections.append(sec)
        self._propagate_style()
        self._refresh_empty()
        return sec

    def clear(self):
        for it in list(self._items):
            it.setParent(None)
            it.deleteLater()
        self._items.clear()
        for sec in list(self._sections):
            sec.setParent(None)
            sec.deleteLater()
        self._sections.clear()
        self._selected_keys.clear()
        self._refresh_empty()

    def items(self) -> list[ListboxItem]:
        """所有可交互项（包含 section 内）"""
        return list(self._items)

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        for it in self._items:
            if it.key() == key:
                return it
        return None

    def _attach_item(self, it: ListboxItem):
        # 同步 disabled key
        if it.key() in self._disabled_keys:
            it.set_disabled(True)
        # 同步选中 key
        if it.key() in self._selected_keys and self._selection_mode != "none":
            it.set_selected(True)
        # 监听点击/选中
        it.activated.connect(self._on_item_activated)

    # ------------------------------------------------------------
    # 选中 / 禁用 API
    # ------------------------------------------------------------
    def selection_mode(self) -> str:
        return self._selection_mode

    def set_selection_mode(self, mode: str):
        if mode not in self.VALID_SELECTION_MODES:
            return
        self._selection_mode = mode
        if mode == "none":
            # 清空选中
            self._selected_keys.clear()
            for it in self._items:
                it.set_selected(False)
        self._propagate_style()

    def selected_keys(self) -> set[str]:
        return set(self._selected_keys)

    def set_selected_keys(self, keys: Iterable[str]):
        keys = set(keys)
        if self._selection_mode == "none":
            return
        if self._selection_mode == "single" and len(keys) > 1:
            keys = {next(iter(keys))}

        old = set(self._selected_keys)
        self._selected_keys = keys

        for it in self._items:
            want = it.key() in keys
            if it.is_selected() != want:
                it.set_selected(want)
        if old != keys:
            self.selection_changed.emit(set(self._selected_keys))

    def disabled_keys(self) -> set[str]:
        return set(self._disabled_keys)

    def set_disabled_keys(self, keys: Iterable[str]):
        self._disabled_keys = set(keys)
        for it in self._items:
            it.set_disabled(it.key() in self._disabled_keys)

    def is_disabled(self) -> bool:
        return self._is_disabled

    def set_is_disabled(self, v: bool):
        self._is_disabled = bool(v)
        # 通过 opacity effect 一刀切（不动 enabled，键盘焦点保留语义）
        if not hasattr(self, "_disabled_effect"):
            self._disabled_effect = QGraphicsOpacityEffect(self)
        self._disabled_effect.setOpacity(0.5 if self._is_disabled else 1.0)
        self.setGraphicsEffect(self._disabled_effect if self._is_disabled else None)
        for it in self._items:
            it.setEnabled(not self._is_disabled and it.key() not in self._disabled_keys)

    # ------------------------------------------------------------
    # 动态属性 setter
    # ------------------------------------------------------------
    def set_variant(self, v: str):
        if v not in self.VALID_VARIANTS:
            return
        self._variant = v
        self._propagate_style()

    def set_color(self, c: str):
        if c not in self.VALID_COLORS:
            return
        self._color = c
        self._propagate_style()

    def set_size(self, s: str):
        if s not in self.VALID_SIZES:
            return
        self._size = s
        cfg = LISTBOX_SIZES.get(s, LISTBOX_SIZES["md"])
        self._outer.setContentsMargins(
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
        )
        self._outer.setSpacing(cfg["group_gap"])
        self._list_v.setSpacing(cfg["list_gap"])
        self._empty_label.setMinimumHeight(cfg["empty_height"])
        self._propagate_style()

    def set_radius(self, r: str):
        if r not in RADIUS:
            return
        self._radius = r
        self._propagate_style()

    def set_empty_content(self, text: Optional[str]):
        """设置空状态文案。

        - 传 ``None`` / ``""``：恢复默认（icon + 中英双语）
        - 传非空 ``str``：单行文字
        """
        self._empty_content_text = text
        self._rebuild_empty_widget()

    def _rebuild_empty_widget(self):
        """重建 empty 占位 widget —— 在 set_empty_content / size / theme 变化时调用。"""
        idx = self._list_v.indexOf(self._empty_widget)
        was_visible = self._empty_widget.isVisible()
        self._list_v.removeWidget(self._empty_widget)
        self._empty_widget.setParent(None)
        self._empty_widget.deleteLater()
        self._empty_widget = self._build_empty_widget()
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        # 默认模式（icon + 双语）需要更高的占位空间；自定义文字保持原 empty_height
        if self._empty_content_text:
            self._empty_widget.setMinimumHeight(cfg["empty_height"])
        else:
            # icon (3×title) + 两行文字 + 上下 padding + spacing
            self._empty_widget.setMinimumHeight(
                cfg["title_font_size"] * 3
                + cfg["title_font_size"]
                + cfg["desc_font_size"]
                + cfg["item_padding_y"] * 4
                + 16
            )
        if idx < 0:
            self._list_v.addWidget(self._empty_widget)
        else:
            self._list_v.insertWidget(idx, self._empty_widget)
        self._empty_label = self._empty_widget.findChild(QLabel, "heroEmptyText") or QLabel()
        self._empty_widget.setVisible(was_visible)

    def set_hide_selected_icon(self, v: bool):
        self._hide_selected_icon = bool(v)
        self._propagate_style()

    def set_should_highlight_on_focus(self, v: bool):
        self._highlight_on_focus = bool(v)
        self._propagate_style()

    def set_disable_animation(self, v: bool):
        self._disable_animation = bool(v)
        self._propagate_style()

    # ------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------
    def _propagate_style(self):
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        self._list_v.setSpacing(cfg["list_gap"])
        self._outer.setSpacing(cfg["group_gap"])

        selectable = self._selection_mode != "none"
        for it in self._items:
            it.apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                radius=self._radius,
                theme=self._theme,
                disable_animation=self._disable_animation,
                hide_selected_icon=self._hide_selected_icon,
                highlight_on_focus=self._highlight_on_focus,
                selectable=selectable,
            )
        for sec in self._sections:
            sec._apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                radius=self._radius,
                theme=self._theme,
                disable_animation=self._disable_animation,
                hide_selected_icon=self._hide_selected_icon,
                highlight_on_focus=self._highlight_on_focus,
                selectable=selectable,
            )

        # empty 占位主题/尺寸跟随：直接重建 widget（icon 颜色 / 字号都依赖 theme + size）
        self._rebuild_empty_widget()

    def _refresh_empty(self):
        # 如果完全没 item（独立 + section 内部），显示 empty 占位（icon + 双语 / 自定义文字）
        empty = len(self._items) == 0
        self._empty_widget.setVisible(empty)

    def _build_empty_widget(self) -> QWidget:
        """构造空状态占位 widget。

        - ``_empty_content_text`` 为 None 或空：默认模式 → 居中 icon + 中英双语
        - 非空 str：单行文字（保持原行为兼容）
        """
        from PySide6.QtWidgets import QSizePolicy
        from PySide6.QtCore import Qt

        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        w = QWidget(self._list)
        w.setAttribute(Qt.WA_TranslucentBackground, True)

        if self._empty_content_text:
            # 兼容模式：单行文字
            v = QVBoxLayout(w)
            v.setContentsMargins(cfg["item_padding_x"], cfg["item_padding_y"],
                                  cfg["item_padding_x"], cfg["item_padding_y"])
            v.setSpacing(0)
            text_label = QLabel(self._empty_content_text, w)
            text_label.setObjectName("heroEmptyText")
            text_label.setAttribute(Qt.WA_TranslucentBackground, True)
            text_label.setForegroundRole(QPalette.WindowText)
            text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            v.addWidget(text_label)
            return w

        # 默认模式：icon + 中英双语
        v = QVBoxLayout(w)
        v.setContentsMargins(cfg["item_padding_x"], cfg["item_padding_y"] * 2,
                              cfg["item_padding_x"], cfg["item_padding_y"] * 2)
        v.setSpacing(8)
        v.setAlignment(Qt.AlignCenter)

        # icon
        icon_size = cfg["title_font_size"] * 3  # md=42, sm=36, lg=45 视觉适中
        icon_color = _desc_color(self._theme)
        icon_label = QLabel(w)
        icon_label.setObjectName("heroEmptyIcon")
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setAlignment(Qt.AlignCenter)
        pix = load_svg_icon("mingcute--empty-box-line", size=icon_size, color=icon_color)
        icon_label.setPixmap(pix)
        icon_label.setFixedSize(icon_size, icon_size)
        v.addWidget(icon_label, 0, Qt.AlignCenter)

        # 双语文字（en 在上，cn 在下，cn 字号略小）
        en_label = QLabel("Nothing to show", w)
        en_label.setObjectName("heroEmptyText")  # 主文本对外暴露给 _empty_label
        en_label.setAttribute(Qt.WA_TranslucentBackground, True)
        en_label.setAlignment(Qt.AlignCenter)
        en_f = QFont(FONT_FAMILY)
        en_f.setPixelSize(cfg["title_font_size"])
        en_label.setFont(en_f)
        en_label.setStyleSheet(
            f"color: {_desc_color(self._theme).name()}; background: transparent;"
        )
        v.addWidget(en_label, 0, Qt.AlignCenter)

        cn_label = QLabel("暂无内容", w)
        cn_label.setObjectName("heroEmptyTextCn")
        cn_label.setAttribute(Qt.WA_TranslucentBackground, True)
        cn_label.setAlignment(Qt.AlignCenter)
        cn_f = QFont(FONT_FAMILY)
        cn_f.setPixelSize(cfg["desc_font_size"])
        cn_label.setFont(cn_f)
        cn_label.setStyleSheet(
            f"color: {_desc_color(self._theme).name()}; background: transparent;"
        )
        v.addWidget(cn_label, 0, Qt.AlignCenter)

        return w

    def _on_item_activated(self, key: str):
        # 选中态切换
        if self._selection_mode == "single":
            old = set(self._selected_keys)
            if key in self._selected_keys:
                # 单选模式下点击已选项 —— HeroUI 默认仍保持选中（disallowEmptySelection），
                # 我们对齐：保持选中
                pass
            else:
                self._selected_keys = {key}
                for it in self._items:
                    it.set_selected(it.key() == key)
            if old != self._selected_keys:
                self.selection_changed.emit(set(self._selected_keys))
        elif self._selection_mode == "multiple":
            old = set(self._selected_keys)
            if key in self._selected_keys:
                self._selected_keys.remove(key)
                it = self.item_by_key(key)
                if it:
                    it.set_selected(False)
            else:
                self._selected_keys.add(key)
                it = self.item_by_key(key)
                if it:
                    it.set_selected(True)
            if old != self._selected_keys:
                self.selection_changed.emit(set(self._selected_keys))

        # action 总是在每次点击触发
        self.action.emit(key)

    # ------------------------------------------------------------
    # 键盘导航
    # ------------------------------------------------------------
    def keyPressEvent(self, e):
        key = e.key()
        if key in (Qt.Key_Down, Qt.Key_Up):
            step = 1 if key == Qt.Key_Down else -1
            self._move_focus(step)
            e.accept()
            return
        if key == Qt.Key_Home:
            self._set_focus_index(self._first_enabled_index())
            e.accept()
            return
        if key == Qt.Key_End:
            self._set_focus_index(self._last_enabled_index())
            e.accept()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self._focused_index < len(self._items):
                it = self._items[self._focused_index]
                if not it.is_disabled():
                    it.activated.emit(it.key())
                    self._on_item_activated(it.key())
            e.accept()
            return
        super().keyPressEvent(e)

    def _enabled_indices(self) -> list[int]:
        return [i for i, it in enumerate(self._items) if not it.is_disabled()]

    def _first_enabled_index(self) -> int:
        idxs = self._enabled_indices()
        return idxs[0] if idxs else -1

    def _last_enabled_index(self) -> int:
        idxs = self._enabled_indices()
        return idxs[-1] if idxs else -1

    def _move_focus(self, step: int):
        idxs = self._enabled_indices()
        if not idxs:
            return
        if self._focused_index < 0 or self._focused_index not in idxs:
            self._set_focus_index(idxs[0] if step > 0 else idxs[-1])
            return
        cur = idxs.index(self._focused_index)
        nxt = (cur + step) % len(idxs)
        self._set_focus_index(idxs[nxt])

    def _set_focus_index(self, idx: int):
        self._focused_index = idx
        if 0 <= idx < len(self._items):
            self._items[idx].setFocus(Qt.TabFocusReason)


__all__ = ["Listbox", "ListboxItem", "ListboxSection"]
