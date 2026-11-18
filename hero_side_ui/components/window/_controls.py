"""窗口控制按钮：三种风格（windows / linux / mac）的自绘按钮与按钮组。

按钮底色、圆点、悬停态都是自绘；里面的符号统一用内置的 Fluent SVG 图标，按主题与按钮状态着色。
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton, QWidget

from ...icons import get_icon
from ...themes import WINDOW_SPEC
from ._style import WindowColors, button_size, controls_width, window_colors

# 显示顺序：mac 为 关闭 / 最小化 / 缩放，其余为 最小化 / 最大化 / 关闭
_ORDER_DEFAULT = ("minimize", "maximize", "close")
_ORDER_MAC = ("close", "minimize", "maximize")

# 符号用的内置图标（hero_side_ui/resources/icons）
_ICON_CLOSE = "fluent--dismiss-24-filled"
_ICON_MINIMIZE = "fluent--subtract-24-filled"
_ICON_MAXIMIZE = "fluent--maximize-24-filled"
_ICON_RESTORE = "fluent--square-multiple-24-regular"
_ICON_FULLSCREEN_ENTER = "fluent--arrow-maximize-top-left-bottom-right-24-filled"
_ICON_FULLSCREEN_EXIT = "fluent--arrow-minimize-top-left-bottom-right-24-filled"


@lru_cache(maxsize=256)
def _glyph(name: str, size: int, color: str, opacity: float, dpr: float) -> QPixmap:
    """渲染一枚符号图标（带缓存）。

    Args:
        name: 内置图标名。
        size: 边长，逻辑像素。
        color: 图标色，十六进制。
        opacity: 0~1。
        dpr: 设备像素比，保证高分屏上清晰。
    """
    icon = get_icon(
        name,
        size=size,
        color=color,
        color_light_theme=color,
        color_dark_theme=color,
        opacity=opacity,
    )
    return icon.pixmap(QSize(size, size), dpr)


class _CtrlButton(QAbstractButton):
    """单个控制按钮：kind 为 minimize / maximize / close，外观随 style 切换。"""

    def __init__(self, kind: str, parent: QWidget | None = None):
        """创建按钮。

        Args:
            kind: minimize / maximize / close。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._kind = kind
        self._style = "windows"
        self._colors: WindowColors = window_colors("light")
        self._theme = "light"
        self._maximized = False
        self._fullscreen = False
        self._group_hover = False
        self._active = True
        self._native_hover = False
        self._native_down = False
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    # ---- 状态 ----
    def configure(self, style: str, theme: str):
        """切换外观风格与主题。

        Args:
            style: windows / linux / mac。
            theme: light / dark。
        """
        self._style = style
        self._theme = theme
        self._colors = window_colors(theme)
        self.update()

    def set_window_state(self, maximized: bool, fullscreen: bool):
        """同步窗口状态，决定最大化按钮显示"最大化"还是"还原"。

        Args:
            maximized: 窗口是否最大化。
            fullscreen: 窗口是否全屏（mac 绿色按钮用）。
        """
        self._maximized = maximized
        self._fullscreen = fullscreen
        self.update()

    def set_group_hover(self, hovering: bool):
        """mac：整组悬停时三个圆点同时显示符号。

        Args:
            hovering: 鼠标是否在按钮组内。
        """
        self._group_hover = hovering
        self.update()

    def set_window_active(self, active: bool):
        """mac：窗口失去焦点时圆点变灰。

        Args:
            active: 窗口是否处于激活状态。
        """
        self._active = active
        self.update()

    def set_native_state(self, hover: bool, down: bool):
        """Windows 原生命中（HTMAXBUTTON）下，由窗口消息驱动的悬停 / 按下态。

        Args:
            hover: 是否悬停。
            down: 是否按下。
        """
        if (hover, down) != (self._native_hover, self._native_down):
            self._native_hover, self._native_down = hover, down
            self.update()

    def kind(self) -> str:
        """返回按钮种类。"""
        return self._kind

    def _hovered(self) -> bool:
        return self.underMouse() or self._native_hover

    def _pressed(self) -> bool:
        return self.isDown() or self._native_down

    def enterEvent(self, event):
        """进入时重绘悬停态。"""
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        """离开时重绘。"""
        super().leaveEvent(event)
        self.update()

    # ---- 绘制 ----
    def paintEvent(self, _event):
        """按风格分派绘制。"""
        p = QPainter(self)
        if self._style == "windows":
            self._paint_windows(p)
        elif self._style == "linux":
            self._paint_linux(p)
        else:
            self._paint_mac(p)

    def _glyph_name(self, alt: bool = False) -> str:
        """当前按钮要画的 SVG 图标名（全部是 hero_side_ui/resources/icons 里的内置图标）。

        Args:
            alt: mac 绿色按钮在按住 Alt 时，改画最大化 / 还原而不是全屏箭头。
        """
        if self._kind == "close":
            return _ICON_CLOSE
        if self._kind == "minimize":
            return _ICON_MINIMIZE
        if self._style == "mac" and not alt:
            return _ICON_FULLSCREEN_EXIT if self._fullscreen else _ICON_FULLSCREEN_ENTER
        return _ICON_RESTORE if self._maximized else _ICON_MAXIMIZE

    def _draw_glyph(self, p: QPainter, name: str, size: int, color: QColor, opacity: float = 1.0):
        """把图标居中画在按钮中央。

        Args:
            p: 画笔。
            name: 内置图标名。
            size: 图标边长，逻辑像素。
            color: 图标色，透明度通过 opacity 单独传。
            opacity: 0~1。
        """
        pm = _glyph(name, size, color.name(), opacity, self.devicePixelRatioF())
        x = (self.width() - size) / 2
        y = (self.height() - size) / 2
        p.drawPixmap(QPointF(x, y), pm)

    def _paint_windows(self, p: QPainter):
        """windows：方块悬停底 + 图标。关闭悬停整块变红、图标变白。"""
        c = self._colors
        hovered, pressed = self._hovered(), self._pressed()
        icon = c.foreground
        if self._kind == "close" and (hovered or pressed):
            bg = QColor(WINDOW_SPEC["windows_close_press" if pressed else "windows_close_hover"])
            p.fillRect(self.rect(), bg)
            icon = QColor("#ffffff")
        elif pressed:
            p.fillRect(self.rect(), c.press)
        elif hovered:
            p.fillRect(self.rect(), c.hover)
        self._draw_glyph(p, self._glyph_name(), WINDOW_SPEC["windows_icon_size"], icon)

    def _paint_linux(self, p: QPainter):
        """linux (GNOME)：常驻浅灰圆底，悬停加深，关闭不变红。"""
        c = self._colors
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        d = min(self.width(), self.height())
        circle = QRectF((self.width() - d) / 2, (self.height() - d) / 2, d, d)
        base = QColor(c.foreground)
        base.setAlphaF(0.16 if self._pressed() else 0.12 if self._hovered() else 0.07)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawEllipse(circle)
        size = max(WINDOW_SPEC["linux_min_icon"], round(d * WINDOW_SPEC["linux_icon_ratio"]))
        self._draw_glyph(p, self._glyph_name(), size, c.foreground)

    def _paint_mac(self, p: QPainter):
        """mac：红黄绿圆点，整组悬停显示符号；窗口失焦变灰；全屏时绿色按钮画向内箭头。"""
        c = self._colors
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        d = min(self.width(), self.height())
        circle = QRectF((self.width() - d) / 2, (self.height() - d) / 2, d, d)
        show_symbol = self._group_hover or self._hovered()
        if self._active or show_symbol:
            color = QColor(WINDOW_SPEC[f"mac_{self._kind}"])
        else:
            color = QColor(c.mac_inactive)
        if self._pressed():
            color = color.darker(125)
        p.setBrush(color)
        ring = QPen(QColor(0, 0, 0, 38), 0.6)
        p.setPen(ring)
        p.drawEllipse(circle.adjusted(0.3, 0.3, -0.3, -0.3))
        if not show_symbol:
            return
        alt = bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        size = max(WINDOW_SPEC["mac_min_icon"], round(d * WINDOW_SPEC["mac_icon_ratio"]))
        self._draw_glyph(
            p, self._glyph_name(alt), size, QColor(0, 0, 0), WINDOW_SPEC["mac_symbol_opacity"]
        )


class _Controls(QWidget):
    """窗口控制按钮组：按风格排布，管理显隐与组宽。"""

    def __init__(self, parent: QWidget | None = None):
        """创建三个按钮并默认全部可见。

        Args:
            parent: Qt 父对象（标题栏）。
        """
        super().__init__(parent)
        self._buttons = {k: _CtrlButton(k, self) for k in _ORDER_DEFAULT}
        self._system = "windows"
        self._height = 32
        self._visible = {k: True for k in _ORDER_DEFAULT}
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def button(self, kind: str) -> _CtrlButton:
        """按种类取按钮。

        Args:
            kind: minimize / maximize / close。
        """
        return self._buttons[kind]

    def configure(self, system: str, theme: str, title_bar_height: int, visible: dict[str, bool]):
        """应用风格、主题、栏高与按钮显隐，并重排。

        Args:
            system: windows / mac / linux（已解析）。
            theme: light / dark。
            title_bar_height: 标题栏高度。
            visible: 三个按钮是否可见。
        """
        self._system = system
        self._height = title_bar_height
        self._visible = dict(visible)
        for b in self._buttons.values():
            b.configure(system, theme)
        self._layout_buttons()

    def visible_count(self) -> int:
        """可见按钮个数。"""
        return sum(1 for v in self._visible.values() if v)

    def preferred_width(self) -> int:
        """按钮组需要的总宽度；没有可见按钮时为 0。"""
        return controls_width(self._system, self._height, self.visible_count())

    def _layout_buttons(self):
        """按风格排布按钮几何。"""
        order = _ORDER_MAC if self._system == "mac" else _ORDER_DEFAULT
        bw, bh = button_size(self._system, self._height)
        if self._system == "windows":
            x, gap = 0, 0
        elif self._system == "linux":
            x, gap = WINDOW_SPEC["linux_side_padding"], WINDOW_SPEC["linux_button_gap"]
        else:
            x, gap = WINDOW_SPEC["mac_side_padding"], WINDOW_SPEC["mac_gap"]
        y = (self._height - bh) // 2
        for kind in order:
            b = self._buttons[kind]
            if not self._visible[kind]:
                b.hide()
                continue
            b.setGeometry(x, y, bw, bh)
            b.show()
            x += bw + gap

    def button_rect(self, kind: str) -> QRect:
        """按钮在本组坐标系下的矩形；不可见时返回空矩形。

        Args:
            kind: minimize / maximize / close。
        """
        b = self._buttons[kind]
        return b.geometry() if not b.isHidden() else QRect()

    def set_window_state(self, maximized: bool, fullscreen: bool):
        """把窗口状态同步给所有按钮。"""
        for b in self._buttons.values():
            b.set_window_state(maximized, fullscreen)

    def set_window_active(self, active: bool):
        """把窗口激活状态同步给所有按钮。"""
        for b in self._buttons.values():
            b.set_window_active(active)

    def _set_group_hover(self, hovering: bool):
        for b in self._buttons.values():
            b.set_group_hover(hovering)

    def enterEvent(self, event):
        """mac：鼠标进组，三个圆点同时亮符号。"""
        super().enterEvent(event)
        self._set_group_hover(True)

    def leaveEvent(self, event):
        """鼠标离组，符号收起。"""
        super().leaveEvent(event)
        self._set_group_hover(False)

    def paintEvent(self, _event):
        """组本身不画任何东西。"""


__all__ = ["_Controls", "_CtrlButton"]
