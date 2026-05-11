"""
HeroSideUI Tooltip Component
基于 HeroUI v2 设计风格

样式来源: https://v2.heroui.com/docs/components/tooltip
设计意图: Tooltip = Popover 的 hover-only 简化版，不带 Backdrop

结构:
    Tooltip (顶层 QWidget, Qt.Tool; paintEvent 自绘背景 + 圆角 + 阴影 + 箭头)
        └── 内部 QLabel（纯文字内容）或自定义 QWidget

    Tooltip.attach(trigger_widget) 让任意 QWidget 当触发器，hover 自动显隐。
    支持 12 种 placement、auto flip。

特性:
    - 7 种颜色（default 即白底；其他色为 solid 主色背景）
    - 3 种尺寸（控制内容字号 / 默认 padding）
    - 5 种圆角（none/sm/md/lg/full）
    - 4 种阴影（none/sm/md/lg）
    - 12 种 placement
    - offset: 控制 tooltip 与 trigger 的距离（默认 7px）
    - open_delay / close_delay: 打开/关闭延迟（默认 0ms / 150ms）
    - show_arrow: 是否显示箭头（默认 False）
    - trigger_scale_on_open: 打开时给 trigger 设动态属性
    - 打开/关闭动画: windowOpacity 0 ↔ 1 + pixmap scale 0.9 ↔ 1 时长 in=200ms / out=150ms
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QApplication,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QRectF,
    QPoint,
    QEvent,
    QSize,
    QTimer,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPainterPath,
)
from typing import Optional, Union

from ..themes import HEROUI_COLORS, POPOVER_SHADOWS, TOOLTIP_SIZES
from ..animation import FadeScaleAnimation, PixmapScaleProxy
from ..core import ThemeProvider

ARROW_SIZE = 5  # 箭头一半边长
ARROW_INSET = 2  # 箭头底边相对 content_rect 向内偏移

# 合法 placement
VALID_PLACEMENTS = {
    "top",
    "top-start",
    "top-end",
    "bottom",
    "bottom-start",
    "bottom-end",
    "left",
    "left-start",
    "left-end",
    "right",
    "right-start",
    "right-end",
}


class Tooltip(QWidget):
    """HeroUI 风格 Tooltip — hover 触发的轻量信息提示。

    用法::

        tooltip = Tooltip(content="Hello tooltip", placement="top")
        tooltip.attach(my_button)

    或自定义内容::

        custom_widget = QWidget()
        # ... 配置 custom_widget ...
        tooltip = Tooltip(placement="bottom")
        tooltip.set_content(custom_widget)
        tooltip.attach(my_button)
    """

    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        content: Union[str, QWidget, None] = None,
        color: str = "default",
        size: str = "md",
        radius: str = "md",
        shadow: str = "sm",
        placement: str = "top",
        offset: int = 7,
        open_delay: int = 0,
        close_delay: int = 150,
        show_arrow: bool = False,
        trigger_scale_on_open: bool = True,
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if placement not in VALID_PLACEMENTS:
            placement = "top"

        self._color = color
        self._size = size
        self._radius = radius
        self._shadow = shadow
        self._placement = placement
        self._actual_placement = placement
        self._offset = offset
        self._open_delay = open_delay
        self._close_delay = close_delay
        self._show_arrow = show_arrow
        self._trigger_scale = trigger_scale_on_open
        self._is_disabled = is_disabled
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._trigger: Optional[QWidget] = None
        self._content: Optional[QWidget] = None
        self._is_open = False

        # 顶层窗口设置
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # Tooltip 不抢焦点
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # open_delay 计时器
        self._open_timer = QTimer(self)
        self._open_timer.setSingleShot(True)
        self._open_timer.timeout.connect(self._do_open)

        # close_delay 计时器
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._do_close)

        # 内层 layout
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(*self._frame_margins())
        self._outer.setSpacing(0)

        # 设置内容
        if content is not None:
            if isinstance(content, str):
                self._set_text_content(content)
            elif isinstance(content, QWidget):
                self._set_widget_content(content)
        else:
            self._set_empty_content()

        # 动画: opacity + pixmap scale
        self._fade = FadeScaleAnimation(
            target=self,
            scale_min=0.9,
            duration_in=200,
            duration_out=150,
            apply_opacity_via="window",
        )
        self._fade.finished_in.connect(self._on_anim_in_done)
        self._fade.finished_out.connect(self._finalize_close)

        # pixmap 缩放代理
        self._scale_proxy = PixmapScaleProxy(
            owner=self,
            content_widget_getter=lambda: self._content,
            scale_getter=self._fade.scale_value,
            enable_predicate=self._content_is_text_only,
        )

        # 默认隐藏
        self.hide()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 内容
    # ============================================================
    def _set_empty_content(self):
        empty = QWidget()
        empty.setLayout(QVBoxLayout())
        pad = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["padding"]
        empty.layout().setContentsMargins(pad, pad, pad, pad)
        self._content = empty
        self._outer.addWidget(empty)

    def _set_text_content(self, text: str):
        """设置纯文字内容。"""
        pad = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["padding"]
        font_size = TOOLTIP_SIZES.get(self._size, TOOLTIP_SIZES["md"])["font_size"]

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setStyleSheet(
            f"color: {self._text_color().name()}; "
            f"background: transparent; "
            f"font-size: {font_size}px;"
        )
        layout.addWidget(label)

        self._content = container
        self._outer.addWidget(container)

    def _set_widget_content(self, widget: QWidget):
        """设置自定义 widget 内容。"""
        self._content = widget
        self._outer.addWidget(widget)
        self._apply_content_text_color()

    def set_content(self, content: Union[str, QWidget]):
        """替换内容。如果 tooltip 正在显示，自动刷新尺寸和位置。"""
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.setParent(None)
            self._content.deleteLater()
        if isinstance(content, str):
            self._set_text_content(content)
        else:
            self._set_widget_content(content)
        # 如果正在显示，延迟到下一帧刷新（等 trigger 布局更新完）
        if self._is_open and self._trigger is not None:
            QTimer.singleShot(0, self._refresh_geometry)

    def _refresh_geometry(self):
        """刷新 tooltip 尺寸和位置（在下一帧调用，确保 trigger 布局已更新）。"""
        if not self._is_open or self._trigger is None:
            return
        self.adjustSize()
        self.resize(self.sizeHint())
        pos = self._calc_position(self._trigger)
        self.move(pos)

    def _apply_content_text_color(self):
        """给内容里的裸 QLabel 刷反色。"""
        if self._content is None:
            return
        text_hex = self._text_color().name()
        self._content.setStyleSheet("")
        layout = self._content.layout()
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if isinstance(w, QLabel):
                w.setStyleSheet(f"color: {text_hex}; background: transparent;")

    # ============================================================
    # 触发器
    # ============================================================
    def attach(self, trigger: QWidget):
        """把任意 widget 设为触发器（hover 自动触发）。"""
        if self._trigger is not None and self._trigger is not trigger:
            self._trigger.removeEventFilter(self)
        self._trigger = trigger
        trigger.installEventFilter(self)
        # 监听自己的 Enter/Leave
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # ---- trigger 的事件 ----
        if obj is self._trigger:
            if event.type() == QEvent.Type.Enter:
                if not self._is_disabled:
                    self._close_timer.stop()
                    self._schedule_open()
                return False
            if event.type() == QEvent.Type.Leave:
                self._open_timer.stop()
                self._schedule_close()
                return False

        # ---- tooltip 自己的 Enter/Leave ----
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self._close_timer.stop()
                self._open_timer.stop()
            elif event.type() == QEvent.Type.Leave:
                self._schedule_close()

        return super().eventFilter(obj, event)

    def _schedule_open(self):
        """根据 open_delay 决定是立即打开还是延迟打开。"""
        if self._is_open:
            return
        if self._open_delay <= 0:
            self._do_open()
        else:
            self._open_timer.setInterval(self._open_delay)
            self._open_timer.start()

    def _schedule_close(self):
        """根据 close_delay 决定是立即关闭还是延迟关闭。"""
        if not self._is_open:
            self._open_timer.stop()
            return
        if self._close_delay <= 0:
            self._do_close()
        else:
            self._close_timer.setInterval(self._close_delay)
            self._close_timer.start()

    # ============================================================
    # open / close 内部实现
    # ============================================================
    def _do_open(self):
        """实际执行打开逻辑。"""
        if self._is_open or self._is_disabled:
            return
        if self._trigger is None:
            return

        # 布局 + 位置
        self.adjustSize()
        self.resize(self.sizeHint())
        pos = self._calc_position(self._trigger)
        self.move(pos)

        # trigger 视觉反馈
        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(True)

        # 显示
        self.show()
        self.raise_()
        self._is_open = True
        self.opened.emit()

        if self._disable_animation:
            self._fade.play_in(instant=True)
        else:
            self._scale_proxy.begin()
            self._fade.play_in()

    def _do_close(self):
        """实际执行关闭逻辑。"""
        if not self._is_open:
            return

        if self._trigger_scale and self._trigger is not None:
            self._apply_trigger_open_state(False)

        if self._disable_animation:
            self._fade.play_out(instant=True)
            self._finalize_close()
        else:
            self._scale_proxy.begin()
            self._fade.play_out()

    def _finalize_close(self):
        if not self._is_open:
            return
        self.hide()
        self._is_open = False
        self._scale_proxy.end()
        self.closed.emit()

    # 公共 API
    def is_open(self) -> bool:
        return self._is_open

    def open(self):
        """手动打开 tooltip。"""
        self._close_timer.stop()
        self._do_open()

    def close(self):
        """手动关闭 tooltip。"""
        self._open_timer.stop()
        self._do_close()

    # ============================================================
    # 缩放动画辅助
    # ============================================================
    def _content_is_text_only(self) -> bool:
        if self._content is None:
            return True
        layout = self._content.layout()
        if layout is None:
            return True
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None:
                continue
            if not isinstance(w, QLabel):
                return False
        return True

    def _on_anim_in_done(self):
        self._scale_proxy.end()

    def hideEvent(self, event):
        if self._is_open:
            self._is_open = False
            self._scale_proxy.end()
            self.closed.emit()
        super().hideEvent(event)

    # ============================================================
    # 触发器视觉响应
    # ============================================================
    def _apply_trigger_open_state(self, opened: bool):
        if self._trigger is None:
            return
        self._trigger.setProperty("tooltipOpen", opened)
        style = self._trigger.style()
        if style is not None:
            style.unpolish(self._trigger)
            style.polish(self._trigger)

    # ============================================================
    # 几何
    # ============================================================
    def _frame_margins(self) -> tuple:
        """内 layout 四方向让出空间给 arrow 和阴影。"""
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["sm"])
        sm = cfg["blur"] + abs(cfg["offset_y"])
        arrow = ARROW_SIZE if self._show_arrow else 0
        place = self._actual_placement
        m = [sm, sm, sm, sm]  # left, top, right, bottom
        if place.startswith("top"):
            m[3] += arrow
        elif place.startswith("bottom"):
            m[1] += arrow
        elif place.startswith("left"):
            m[2] += arrow
        elif place.startswith("right"):
            m[0] += arrow
        return tuple(m)

    def _calc_position(self, trigger: QWidget) -> QPoint:
        """计算 tooltip 屏幕坐标位置（含 auto-flip）。"""
        tr_pos = trigger.mapToGlobal(QPoint(0, 0))
        tr_w = trigger.width()
        tr_h = trigger.height()

        screen = QApplication.primaryScreen().availableGeometry()

        place = self._placement
        pos = self._compute_pos_for(place, tr_pos, tr_w, tr_h)

        # 检查越界 → flip
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        rect = (pos.x(), pos.y(), my_w, my_h)
        if (
            rect[0] < screen.left()
            or rect[1] < screen.top()
            or rect[0] + rect[2] > screen.right()
            or rect[1] + rect[3] > screen.bottom()
        ):
            flipped = self._flip_placement(place)
            new_pos = self._compute_pos_for(flipped, tr_pos, tr_w, tr_h)
            self._actual_placement = flipped
            self._outer.setContentsMargins(*self._frame_margins())
            self.adjustSize()
            return new_pos

        self._actual_placement = place
        self._outer.setContentsMargins(*self._frame_margins())
        return pos

    def _compute_pos_for(
        self, place: str, tr_pos: QPoint, tr_w: int, tr_h: int
    ) -> QPoint:
        """根据 placement 计算 tooltip 左上角。"""
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        x, y = tr_pos.x(), tr_pos.y()

        ml, mt, mr, mb = self._frame_margins()
        # offset 替代 popover 里硬编码的 gap=6
        gap = self._offset

        if place == "top":
            return QPoint(x + (tr_w - my_w) // 2, y - my_h + mb - gap)
        if place == "top-start":
            return QPoint(x - ml, y - my_h + mb - gap)
        if place == "top-end":
            return QPoint(x + tr_w - my_w + mr, y - my_h + mb - gap)

        if place == "bottom":
            return QPoint(x + (tr_w - my_w) // 2, y + tr_h - mt + gap)
        if place == "bottom-start":
            return QPoint(x - ml, y + tr_h - mt + gap)
        if place == "bottom-end":
            return QPoint(x + tr_w - my_w + mr, y + tr_h - mt + gap)

        if place == "left":
            return QPoint(x - my_w + mr - gap, y + (tr_h - my_h) // 2)
        if place == "left-start":
            # content 顶部对齐 trigger 顶部
            return QPoint(x - my_w + mr - gap, y - mt)
        if place == "left-end":
            # content 底部对齐 trigger 底部
            return QPoint(x - my_w + mr - gap, y + tr_h - my_h + mb)

        if place == "right":
            return QPoint(x + tr_w - ml + gap, y + (tr_h - my_h) // 2)
        if place == "right-start":
            return QPoint(x + tr_w - ml + gap, y - mt)
        if place == "right-end":
            return QPoint(x + tr_w - ml + gap, y + tr_h - my_h + mb)

        return QPoint(x, y + tr_h)

    @staticmethod
    def _flip_placement(p: str) -> str:
        if p.startswith("top"):
            return p.replace("top", "bottom")
        if p.startswith("bottom"):
            return p.replace("bottom", "top")
        if p.startswith("left"):
            return p.replace("left", "right")
        if p.startswith("right"):
            return p.replace("right", "left")
        return p

    # ============================================================
    # 颜色
    # ============================================================
    def _bg_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#ffffff" if not is_dark else "#27272a")
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        return QColor(c[500])

    def _text_color(self) -> QColor:
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#11181c" if not is_dark else "#ecedee")
        if self._color == "warning":
            return QColor("#000000")
        return QColor("#ffffff")

    # ============================================================
    # 圆角
    # ============================================================
    def _resolve_radius(self) -> float:
        if self._radius == "none":
            return 0.0
        if self._radius == "full":
            return self._content_rect_size().height() / 2.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 8))

    def _content_rect_size(self) -> QSize:
        m = self._frame_margins()
        return QSize(
            max(0, self.width() - m[0] - m[2]), max(0, self.height() - m[1] - m[3])
        )

    # ============================================================
    # 绘制：阴影 + 圆角主体 + 箭头
    # ============================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 动画期间：只画缩放后的 pixmap
        if self._scale_proxy.is_active():
            w, h = self.width(), self.height()
            m = self._frame_margins()
            place = self._actual_placement
            content_rect = QRectF(m[0], m[1], w - m[0] - m[2], h - m[1] - m[3])
            if place.startswith("top"):
                cx, cy = content_rect.center().x(), content_rect.bottom()
            elif place.startswith("bottom"):
                cx, cy = content_rect.center().x(), content_rect.top()
            elif place.startswith("left"):
                cx, cy = content_rect.right(), content_rect.center().y()
            elif place.startswith("right"):
                cx, cy = content_rect.left(), content_rect.center().y()
            else:
                cx, cy = content_rect.center().x(), content_rect.center().y()
            self._scale_proxy.draw(painter, self.rect(), anchor=(cx, cy))
            return

        m = self._frame_margins()
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["sm"])
        bg = self._bg_color()
        radius = self._resolve_radius()

        # 内容矩形
        content_rect = QRectF(
            m[0], m[1], self.width() - m[0] - m[2], self.height() - m[1] - m[3]
        )

        # 阴影
        if cfg["layers"] > 0:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(cfg["layers"]):
                t = (i + 1) / cfg["layers"]
                grow = cfg["blur"] * (1 - t) + 1
                off = cfg["offset_y"] * (1 - t)
                rect = content_rect.adjusted(-grow, -grow + off, grow, grow + off)
                alpha = int(cfg["alpha"] * t)
                painter.setBrush(QColor(0, 0, 0, alpha))
                painter.drawRoundedRect(rect, radius, radius)
            painter.restore()

        # 主体背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(content_rect, radius, radius)

        # 箭头
        if self._show_arrow:
            self._draw_arrow(painter, content_rect, bg)

    def _draw_arrow(self, painter: QPainter, content_rect: QRectF, bg: QColor):
        """绘制箭头。

        箭头位置规则：
        - top/bottom 系列：箭头在底/顶边上。
          start → 靠左, end → 靠右, 无后缀 → 居中
        - left/right 系列：箭头在右/左边上。
          start → 靠上, end → 靠下, 无后缀 → 居中
        """
        place = self._actual_placement
        a = ARROW_SIZE
        path = QPainterPath()
        inset = ARROW_INSET
        # 箭头距离边缘的偏移：仅需避开圆角最小安全距离
        edge_offset = 10

        if place.startswith("top"):
            base_y = content_rect.bottom() - inset
            tip_y = content_rect.bottom() + a
            if "start" in place:
                cx = content_rect.left() + edge_offset
            elif "end" in place:
                cx = content_rect.right() - edge_offset
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("bottom"):
            base_y = content_rect.top() + inset
            tip_y = content_rect.top() - a
            if "start" in place:
                cx = content_rect.left() + edge_offset
            elif "end" in place:
                cx = content_rect.right() - edge_offset
            else:
                cx = content_rect.center().x()
            path.moveTo(cx - a, base_y)
            path.lineTo(cx + a, base_y)
            path.lineTo(cx, tip_y)
            path.closeSubpath()

        elif place.startswith("left"):
            # 箭头在 tooltip 右边
            base_x = content_rect.right() - inset
            tip_x = content_rect.right() + a
            if "start" in place:
                cy = content_rect.top() + edge_offset
            elif "end" in place:
                cy = content_rect.bottom() - edge_offset
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        elif place.startswith("right"):
            # 箭头在 tooltip 左边
            base_x = content_rect.left() + inset
            tip_x = content_rect.left() - a
            if "start" in place:
                cy = content_rect.top() + edge_offset
            elif "end" in place:
                cy = content_rect.bottom() - edge_offset
            else:
                cy = content_rect.center().y()
            path.moveTo(base_x, cy - a)
            path.lineTo(base_x, cy + a)
            path.lineTo(tip_x, cy)
            path.closeSubpath()

        else:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawPath(path)

    # ============================================================
    # 公共动态 API
    # ============================================================
    def set_color(self, color: str):
        self._color = color
        self.update()
        self._apply_content_text_color()

    def set_size(self, size: str):
        self._size = size
        self.update()

    def set_radius(self, radius: str):
        self._radius = radius
        self.update()

    def set_shadow(self, shadow: str):
        self._shadow = shadow
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

    def set_placement(self, placement: str):
        if placement in VALID_PLACEMENTS:
            self._placement = placement
            self._actual_placement = placement
            self._outer.setContentsMargins(*self._frame_margins())
            self.update()

    def set_offset(self, offset: int):
        """设置 tooltip 与 trigger 的距离（px）。"""
        self._offset = offset

    def set_open_delay(self, delay: int):
        """设置打开延迟（ms）。"""
        self._open_delay = delay

    def set_close_delay(self, delay: int):
        """设置关闭延迟（ms）。"""
        self._close_delay = delay

    def set_show_arrow(self, enabled: bool):
        self._show_arrow = enabled
        self._outer.setContentsMargins(*self._frame_margins())
        self.update()

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
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        if disabled and self._is_open:
            self.close()
