"""ListboxItem — 列表项（可选中、可禁用、可带 icon/快捷键）。"""

from __future__ import annotations

from typing import Optional, Union

from PySide6.QtCore import QEvent, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import (
    CheckDrawAnimation,
    paint_animated_check,
    stop_tween,
    tween_value,
)
from ...core import StatePalette, ThemeProvider
from ...themes import FONT_FAMILY, HEROUI_COLORS, LISTBOX_SIZES, RADIUS
from ...utils import aligned_color_pair, load_svg_icon



# ============================================================
# 颜色解析
# ============================================================
#
# 历史上此处定义了 13 个 ``_hover_bg / _text_hover / _desc_color / ...``
# 私有函数。重构后统一迁到 ``core/state_palette.py``，组件只用 ``StatePalette``
# 高层 API，不再重复这套 variant × color × theme × state 查找表。
#
# 迁移映射（保留备忘，代码中无直接调用）：
#   _bg_role_color(theme)                    → StatePalette.bg(v, c, theme, "resting")
#   _faded_resting_bg(theme)                 → StatePalette.bg("faded", c, theme, "resting")
#   _hover_bg(variant, color, theme)         → StatePalette.bg(variant, color, theme, "hover")
#   _hover_border(variant, color, theme)     → StatePalette.border(variant, color, theme, "hover")
#   _text_default(theme)                     → StatePalette.text_default(theme)
#   _text_hover(variant, color, theme)       → StatePalette.text(variant, color, theme, "hover")
#   _desc_color(theme)                       → StatePalette.text_description(theme)
#   _shortcut_border(theme)                  → StatePalette.shortcut_border(theme)
#   _selected_indicator_color(v, c, theme)   → StatePalette.selected_indicator(v, c, theme)
#   _divider_color(theme)                    → StatePalette.divider(theme)


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
        self._hide_selected_icon = (
            False  # 对齐 HeroUI 源码 hideSelectedIcon=false：默认显示对勾
        )
        self._highlight_on_focus = False
        # selection 行为
        self._selectable = True

        # 当前过渡色（tween 改这两个，paintEvent / 字色直接读）
        self._cur_bg = QColor(0, 0, 0, 0)
        self._cur_border = QColor(0, 0, 0, 0)
        self._cur_text = StatePalette.text_default("light")
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
            f"color: {StatePalette.text_description(self._theme).name()}; background: transparent;"
        )

        sc_f = QFont(FONT_FAMILY)
        sc_f.setPixelSize(cfg["shortcut_font_size"])
        self._shortcut_label.setFont(sc_f)
        self._shortcut_label.setStyleSheet(
            f"color: {StatePalette.text_description(self._theme).name()};"
            f" border: 1px solid {StatePalette.shortcut_border(self._theme).name()};"
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
        c = self._cur_text if self._cur_text.isValid() else StatePalette.text_default(self._theme)
        pix = load_svg_icon(self._start_src, size=size, color=c)
        self._start_label.setPixmap(pix)
        self._start_label.setFixedSize(size, size)

    def _refresh_end_pixmap(self):
        if self._end_src is None:
            return
        cfg = self._size_cfg()
        size = cfg["title_font_size"] + 2
        c = self._cur_text if self._cur_text.isValid() else StatePalette.text_default(self._theme)
        pix = load_svg_icon(self._end_src, size=size, color=c)
        self._end_label.setPixmap(pix)
        self._end_label.setFixedSize(size, size)

    # ------------------------------------------------------------
    # 状态变化
    # ------------------------------------------------------------
    def enterEvent(self, e):
        super().enterEvent(e)
        # disabled 也记录 hover —— _refresh_palette 会用一个"减弱版"hover bg
        # 给视觉反馈("我知道你在 hover 我,但我点不动"),观感比完全不响应好。
        # 字色/对勾仍走 disabled 默认(由 _is_active 拦截)。
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
            target_bg = StatePalette.bg(self._variant, self._color, self._theme, "hover")
            target_border = StatePalette.border(self._variant, self._color, self._theme, "hover")
            target_text = StatePalette.text(self._variant, self._color, self._theme, "hover")
        elif self._is_disabled and self._is_hover:
            # disabled 但鼠标在上面:给一个"减弱版"hover 背景作为视觉反馈
            # ——告诉用户"我知道你 hover 我,但我点不动",观感比完全无反应好。
            # 字色保持 disabled 默认(不染深),对勾不显示(由 _is_active=False 决定)。
            # alpha 系数 0.75:既明显感知到 hover,又区别于正常 hover 的"可点击"暗示。
            base = StatePalette.bg(self._variant, self._color, self._theme, "hover")
            target_bg = QColor(base)
            target_bg.setAlpha(int(base.alpha() * 0.75))
            target_border = QColor(0, 0, 0, 0)
            target_text = StatePalette.text_default(self._theme)
        else:
            # 未激活：bg/border 透明（保留色相，避免插值经过黑色 → 见 _aligned_pair）
            target_bg = QColor(0, 0, 0, 0)
            target_border = QColor(0, 0, 0, 0)
            target_text = StatePalette.text_default(self._theme)

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

            pen = QPen(StatePalette.divider(self._theme))
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
        c = QColor(StatePalette.selected_indicator(self._variant, self._color, self._theme))
        paint_animated_check(
            p,
            slot,
            c,
            progress=self._check_anim.progress,
            opacity=self._cur_indicator_alpha,
        )
