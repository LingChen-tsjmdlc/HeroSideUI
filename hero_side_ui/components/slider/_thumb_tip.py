"""_SliderThumbTip：canvas 直系子 widget 的自绘 tooltip，防 Windows 原生装饰闪帧。"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import QWidget

from ...animation import tween_property
from ...core import ThemeProvider, make_text_qfont
from ...themes import HEROUI_COLORS, TOOLTIP_SIZES

# 箭头三角尺寸
_ARROW = 5
# tooltip 距 thumb 顶部的间距
_GAP = 6
# 手绘多层羽化阴影（不用 QGraphicsDropShadowEffect：在 Windows 上 effect 上报的 dirty
# rect 会超出 widget 边界 → UpdateLayeredWindowIndirect 参数错误警告）
_SHADOW_LAYERS = 4  # 层数，越多越柔和
_SHADOW_SPREAD = 6  # 最外层阴影距 body 的距离（也是上下左右预留 margin）
_SHADOW_OFFSET_Y = 1  # 阴影整体下偏量
_SHADOW_MARGIN = _SHADOW_SPREAD  # widget 四周预留


class _SliderThumbTip(QWidget):
    """单个 thumb 的轻量自绘 tooltip。"""

    def __init__(
        self,
        parent: QWidget,
        color: str = "default",
        size: str = "md",
        theme: str = "auto",
        disable_animation: bool = False,
    ):
        """构造顶层 tooltip 窗口并记录主题与动画配置。

        Args:
            parent: 作为坐标映射 anchor 的 canvas 控件。
            color: 语义色名。
            size: 尺寸档位。
            theme: 主题模式，auto 跟随 ThemeProvider。
            disable_animation: 是否关闭淡入淡出。

        Note:
            size 非法时回退到 md；parent 只用作 anchor，控件实际以 parent=None
            创建为独立窗口以免被 canvas 裁剪；淡入淡出走 windowOpacity。
        """
        # 顶层 widget：parent=None 让它独立窗口，不被 canvas 裁剪
        super().__init__(None)
        # 记录 anchor widget（canvas）做 mapToGlobal
        self._anchor: QWidget = parent

        self._color = color
        self._size = size if size in TOOLTIP_SIZES else "md"
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._disable_animation = disable_animation

        self._text = ""
        # 顶层无装饰 + 透明背景 + 不抢焦点
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # 淡入淡出 —— 顶层窗口用 windowOpacity
        self.setWindowOpacity(0.0)
        self._anim = None
        self._fade_done_cb = None  # 当前已连接的 finished 回调

        self.hide()

        if self._theme_mode == "auto":
            ThemeProvider.instance().theme_changed.connect(self._on_theme_changed)

    # ---- 主题 ----
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析为具体主题名。

        Args:
            mode: 主题模式，light / dark 直接生效。

        Returns:
            解析后的主题名；其它值跟随 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_theme(self, theme: str):
        """切换主题模式并重解析当前主题、触发重绘。"""
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self.update()

    def _on_theme_changed(self, theme: str):
        """auto 模式下响应主题广播并重绘。"""
        if self._theme_mode == "auto":
            self._theme = theme
            self.update()

    # ---- 颜色 ----
    def _bg_color(self) -> QColor:
        """返回 tooltip 主体背景色，default 随主题翻转。"""
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#ffffff" if not is_dark else "#27272a")
        c = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        return QColor(c[500])

    def _text_color(self) -> QColor:
        """返回 tooltip 文字颜色，warning 固定用黑字。"""
        is_dark = self._theme == "dark"
        if self._color == "default":
            return QColor("#11181c" if not is_dark else "#ecedee")
        if self._color == "warning":
            return QColor("#000000")
        return QColor("#ffffff")

    # ---- 内容 ----
    def set_text(self, text: str):
        """更新 tooltip 文字并重新排版，文本相同时忽略。"""
        if text == self._text:
            return
        self._text = text
        self._relayout()
        self.update()

    def _font(self):
        """按尺寸档位返回文字 QFont。"""
        cfg = TOOLTIP_SIZES[self._size]
        return make_text_qfont(size=cfg["font_size"], weight="medium")

    def _padding(self) -> int:
        """返回当前尺寸档位的内边距。"""
        return TOOLTIP_SIZES[self._size]["padding"]

    def _relayout(self):
        """按文字尺寸、箭头与阴影 margin 重算窗口大小。"""
        fm = QFontMetrics(self._font())
        pad = self._padding()
        text_w = fm.horizontalAdvance(self._text or " ")
        text_h = fm.height()
        body_w = text_w + pad * 2
        body_h = text_h + pad * 2
        # 总尺寸 = body + 底部箭头 + 阴影 margin（四周，底部另加 offset）
        self.resize(
            body_w + _SHADOW_MARGIN * 2,
            body_h + _ARROW + _SHADOW_MARGIN * 2 + _SHADOW_OFFSET_Y,
        )

    # ---- 阴影 ----
    def _draw_soft_shadow(self, p: QPainter, body_rect: QRectF, radius: float):
        """多层半透明圆角矩形模拟高斯柔化阴影。全部画在 widget 内部。"""
        # 阴影中心 = body 下偏 _SHADOW_OFFSET_Y
        for i in range(_SHADOW_LAYERS, 0, -1):
            grow = _SHADOW_SPREAD * i / _SHADOW_LAYERS
            # 外层 alpha 低，内层 alpha 高；整体强度比之前减半
            alpha = int(4 + 3 * (_SHADOW_LAYERS - i))  # 4, 7, 10, 13
            r = body_rect.adjusted(-grow, -grow + _SHADOW_OFFSET_Y, grow, grow + _SHADOW_OFFSET_Y)
            p.setBrush(QColor(0, 0, 0, alpha))
            p.drawRoundedRect(r, radius + grow, radius + grow)

    # ---- 位置 ----
    def show_at(self, thumb_top_center: QPointF):
        """thumb 顶部中心（canvas 局部坐标）→ 转全局，tip 箭头尖端对齐到该点上方 _GAP 处。"""
        self._relayout()
        w = self.width()
        h = self.height()
        gp = self._anchor.mapToGlobal(QPoint(int(thumb_top_center.x()), int(thumb_top_center.y())))
        # 箭头尖端在 widget 内部 y = _SHADOW_MARGIN + body_h + _ARROW；下方还有 _SHADOW_MARGIN + offset
        # 希望箭头尖端到 thumb_top 距离 = _GAP → widget.y = gp.y - _GAP - (箭头尖在 widget 内的 y)
        arrow_tip_in_widget = h - _SHADOW_MARGIN - _SHADOW_OFFSET_Y
        x = gp.x() - w // 2
        y = gp.y() - _GAP - arrow_tip_in_widget
        self.move(x, y)
        if not self.isVisible():
            self.show()
        self.raise_()
        self._fade(1.0)

    def fade_out(self):
        """淡出 tooltip，不可见时直接返回。"""
        if not self.isVisible():
            return
        self._fade(0.0, on_done=self.hide)

    def _fade(self, target: float, on_done=None):
        """把窗口透明度过渡到目标值。

        Args:
            target: 目标窗口透明度。
            on_done: 结束回调，淡出时用于隐藏窗口。
        """
        tween_property(
            self,
            "_anim",
            b"windowOpacity",
            target,
            duration=120,
            animated=not self._disable_animation and self.windowOpacity() != target,
            on_finished=on_done,
            easing=QEasingCurve.Type.Linear,
        )

    # ---- 绘制 ----
    def paintEvent(self, _event):
        """绘制阴影、主体、底部箭头与文字。"""
        if not self._text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg = self._bg_color()
        fg = self._text_color()
        # body 位于 widget 中部，四周预留 _SHADOW_MARGIN 供阴影层渲染
        body_x = float(_SHADOW_MARGIN)
        body_y = float(_SHADOW_MARGIN)
        body_w = self.width() - _SHADOW_MARGIN * 2
        body_h = self.height() - _ARROW - _SHADOW_MARGIN * 2 - _SHADOW_OFFSET_Y
        body_rect = QRectF(body_x, body_y, body_w, body_h)
        radius = 6.0

        # 柔和阴影（多层半透明圆角矩模拟高斯）
        p.setPen(Qt.PenStyle.NoPen)
        self._draw_soft_shadow(p, body_rect, radius)

        # 主体
        p.setBrush(bg)
        p.drawRoundedRect(body_rect, radius, radius)

        # 底部箭头（朝下）
        cx = body_x + body_w / 2.0
        arrow_top_y = body_y + body_h - 0.5
        path = QPainterPath()
        path.moveTo(cx - _ARROW, arrow_top_y)
        path.lineTo(cx + _ARROW, arrow_top_y)
        path.lineTo(cx, arrow_top_y + _ARROW + 0.5)
        path.closeSubpath()
        p.setBrush(bg)
        p.drawPath(path)

        # 文字
        p.setFont(self._font())
        p.setPen(fg)
        pad = self._padding()
        text_rect = body_rect.adjusted(pad, pad, -pad, -pad)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._text)


__all__ = ["_SliderThumbTip"]
