"""公共阴影：多层预合成、九宫格拉伸、按字节限额的 LRU 缓存，以及不占布局的 ShadowLayer。

模糊只在缓存未命中时发生；每次绘制只是贴图。模糊用 Qt 自带实现。
"""

from __future__ import annotations

import math
from collections import OrderedDict

import shiboken6
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QWidget,
)

from ..themes.shadow import Layer
from ..themes.theme_values import get_shadow_layers

# Qt 模糊半径换算为高斯 sigma 的系数（实测标定）
_QT_SIGMA_PER_RADIUS = 0.45
_CACHE_BYTES = 32 * 1024 * 1024

_cache: OrderedDict = OrderedDict()
_cache_bytes = 0


def clear_cache() -> None:
    """清空阴影缓存（配置变化后调用）。"""
    global _cache_bytes
    _cache.clear()
    _cache_bytes = 0


def _blur(src: QImage, radius_px: float) -> QImage:
    """用 Qt 内置模糊处理图像，仅在缓存未命中时调用。

    Args:
        src: 待模糊的 ARGB32 图。
        radius_px: Qt 模糊半径。
    """
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(src))
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius_px)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    out = QImage(src.size(), QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(0)
    painter = QPainter(out)
    scene.render(painter, QRectF(out.rect()), QRectF(src.rect()))
    painter.end()
    return out


def _compose(w_px: int, h_px: int, r_px: float, pad_px: int, layers: tuple, dpr: float) -> QPixmap:
    """把一档的外阴影层合成一张图，并挖掉本体区域（半透明本体下不透出阴影）。

    Args:
        w_px: 本体宽（物理像素）。
        h_px: 本体高（物理像素）。
        r_px: 圆角（物理像素）。
        pad_px: 四周留白（物理像素）。
        layers: 阴影层元组。
        dpr: 设备像素比。
    """
    size = (w_px + 2 * pad_px, h_px + 2 * pad_px)
    acc = QImage(*size, QImage.Format.Format_ARGB32_Premultiplied)
    acc.fill(0)
    for layer in layers:
        if layer.inset:
            continue
        src = QImage(*size, QImage.Format.Format_ARGB32_Premultiplied)
        src.fill(0)
        p = QPainter(src)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0))
        p.drawRoundedRect(QRectF(pad_px, pad_px + layer.y * dpr, w_px, h_px), r_px, r_px)
        p.end()

        img = _blur(src, layer.blur / 2 * dpr / _QT_SIGMA_PER_RADIUS)  # CSS：模糊半径 = 2σ
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        c = QColor(layer.color)
        c.setAlphaF(layer.opacity)
        p.fillRect(img.rect(), c)
        p.end()

        p = QPainter(acc)
        p.drawImage(0, 0, img)
        p.end()

    p = QPainter(acc)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0))
    p.drawRoundedRect(QRectF(pad_px, pad_px, w_px, h_px), r_px, r_px)
    p.end()

    pm = QPixmap.fromImage(acc)
    pm.setDevicePixelRatio(dpr)
    return pm


def _cached(key, build) -> QPixmap:
    """LRU 缓存取值；总字节超限时淘汰最久未用的。"""
    global _cache_bytes
    pm = _cache.get(key)
    if pm is not None:
        _cache.move_to_end(key)
        return pm
    pm = build()
    _cache[key] = pm
    _cache_bytes += pm.width() * pm.height() * 4
    while _cache_bytes > _CACHE_BYTES and len(_cache) > 1:
        _, old = _cache.popitem(last=False)
        _cache_bytes -= old.width() * old.height() * 4
    return pm


def _extent(layer: Layer) -> int:
    """单层阴影向外扩散的距离（逻辑像素，约 3σ）。"""
    return math.ceil(1.5 * layer.blur) + 1


def shadow_margin(layers: tuple) -> int:
    """整档阴影需要在本体四周预留的空间（含 y 偏移）。

    Args:
        layers: 阴影层元组；空元组返回 0。
    """
    return max((_extent(lay) + math.ceil(abs(lay.y)) for lay in layers if not lay.inset), default=0)


def _nine_size(layers: tuple, radius: float) -> int:
    """九宫格切片所需的最小本体边长。"""
    reach = max((lay.blur + abs(lay.y) for lay in layers if not lay.inset), default=0)
    return 2 * (math.ceil(max(radius, reach)) + 2)


def _paint_nine(p: QPainter, body: QRectF, radius: float, layers: tuple, dpr: float) -> bool:
    """九宫格贴图；本体不够大时返回 False。"""
    t = _nine_size(layers, radius)
    if body.width() < t or body.height() < t:
        return False
    e = shadow_margin(layers)
    sc = round((e + t / 2) * dpr)
    pad = round(e * dpr)

    def build():
        side = 2 * sc - 2 * pad
        return _compose(side, side, radius * dpr, pad, layers, dpr)

    pm = _cached(("n", layers, radius, dpr), build)
    ex, half, cw = pad / dpr, (sc - pad) / dpr, sc / dpr
    x, y, w, h = body.x(), body.y(), body.width(), body.height()
    mw, mh = w - 2 * half, h - 2 * half
    p.drawPixmap(QRectF(x - ex, y - ex, cw, cw), pm, QRectF(0, 0, sc, sc))
    p.drawPixmap(QRectF(x + w - half, y - ex, cw, cw), pm, QRectF(sc, 0, sc, sc))
    p.drawPixmap(QRectF(x - ex, y + h - half, cw, cw), pm, QRectF(0, sc, sc, sc))
    p.drawPixmap(QRectF(x + w - half, y + h - half, cw, cw), pm, QRectF(sc, sc, sc, sc))
    if mw > 0:
        p.drawPixmap(QRectF(x + half, y - ex, mw, cw), pm, QRectF(sc - 1, 0, 2, sc))
        p.drawPixmap(QRectF(x + half, y + h - half, mw, cw), pm, QRectF(sc - 1, sc, 2, sc))
    if mh > 0:
        p.drawPixmap(QRectF(x - ex, y + half, cw, mh), pm, QRectF(0, sc - 1, sc, 2))
        p.drawPixmap(QRectF(x + w - half, y + half, cw, mh), pm, QRectF(sc, sc - 1, sc, 2))
    return True


def _paint_direct(p: QPainter, body: QRectF, radius: float, layers: tuple, dpr: float) -> None:
    """小本体按实际尺寸整张合成并缓存。"""
    pad = round(shadow_margin(layers) * dpr)
    w_px, h_px = round(body.width() * dpr), round(body.height() * dpr)

    def build():
        return _compose(w_px, h_px, radius * dpr, pad, layers, dpr)

    pm = _cached(("d", layers, w_px, h_px, radius, dpr), build)
    p.drawPixmap(QPointF(body.x() - pad / dpr, body.y() - pad / dpr), pm)


def paint_shadow(p: QPainter, body: QRectF, radius: float, layers: tuple) -> None:
    """在 body 周围画外阴影；本体区域已在缓存图里挖空。

    Args:
        p: 画笔。
        body: 本体矩形（逻辑像素）。
        radius: 本体圆角（逻辑像素）。
        layers: 阴影层元组；无外阴影层时什么也不画。
    """
    if not any(not lay.inset for lay in layers):
        return
    dpr = p.device().devicePixelRatioF()
    if not _paint_nine(p, body, radius, layers, dpr):
        _paint_direct(p, body, radius, layers, dpr)


def paint_inset(p: QPainter, body: QRectF, radius: float, layers: tuple) -> None:
    """画内描边（暗色默认的 1px 近白细线）；须在背景填充之后调用。

    Args:
        p: 画笔。
        body: 本体矩形。
        radius: 本体圆角。
        layers: 阴影层元组。
    """
    insets = [lay for lay in layers if lay.inset]
    if not insets:
        return
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = max(radius - 0.5, 0)
    for lay in insets:
        c = QColor(lay.color)
        c.setAlphaF(lay.opacity)
        p.setPen(QPen(c, 1))
        p.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), r, r)
    p.restore()


def layers_for(tier: str, theme: str) -> tuple:
    """按档位与主题取当前阴影层。

    Args:
        tier: sm / md / lg；其他值（含 none）返回空元组。
        theme: "light" 或 "dark"。
    """
    return get_shadow_layers(tier, theme)


def tier_margin(tier: str) -> int:
    """某档阴影在独立浮窗内需要预留的留白（取亮暗两个主题中较大者，不随主题变）。

    Args:
        tier: sm / md / lg；其他值（含 none）返回 0。
    """
    return max(
        shadow_margin(get_shadow_layers(tier, "light")),
        shadow_margin(get_shadow_layers(tier, "dark")),
    )


def prewarm(theme: str) -> None:
    """预热某主题三档的缓存，把冷启动成本移到启动阶段。

    Args:
        theme: "light" 或 "dark"。
    """
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        return
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    for tier in ("sm", "md", "lg"):
        layers = get_shadow_layers(tier, theme)
        t = _nine_size(layers, 14.0)
        e = shadow_margin(layers)
        sc = round((e + t / 2) * dpr)
        pad = round(e * dpr)
        _cached(("n", layers, 14.0, dpr), lambda: _compose(2 * sc - 2 * pad, 2 * sc - 2 * pad, 14.0 * dpr, pad, layers, dpr))


_WATCH_EVENTS = {
    QEvent.Type.Move,
    QEvent.Type.Resize,
    QEvent.Type.Show,
    QEvent.Type.Hide,
    QEvent.Type.ParentChange,
}


def clip_root(target: QWidget) -> QWidget | None:
    """阴影层的挂载点：目标最近的"裁剪边界"，与 CSS 的 overflow 一致。

    Args:
        target: 目标控件。

    Returns:
        最近的滚动区视口或顶层窗口；目标没有父控件时为 None。

    Note:
        普通容器（包着图片和说明文字的 QWidget 之类）不是裁剪边界，阴影可以越过它们；
        滚动区视口和窗口是，阴影到此为止。
    """
    w = target.parentWidget()
    while w is not None:
        if w.isWindow():
            return w
        parent = w.parentWidget()
        if isinstance(parent, QAbstractScrollArea) and parent.viewport() is w:
            return w
        w = parent
    return None


class ShadowLayer(QWidget):
    """目标控件的阴影层：叠在目标上方的透明覆盖层，不进布局、鼠标穿透。

    挂在目标最近的裁剪边界（滚动区视口或窗口）下，所以不会被包着目标的普通容器裁掉；
    本体区域在缓存图里已经挖空，所以盖在目标上方也不会遮住它。
    暗色主题的 1px 内描边同样画在这一层。
    """

    def __init__(self, target: QWidget, radius: float, layers: tuple, insets: tuple = (0, 0, 0, 0)):
        """创建阴影层并附着到目标。

        Args:
            target: 目标控件，须已有可用的裁剪边界（见 clip_root）。
            radius: 目标圆角（逻辑像素）。
            layers: 阴影层元组。
            insets: 本体相对目标矩形的内缩 (上, 右, 下, 左)；默认本体就是目标矩形。
        """
        super().__init__(clip_root(target))
        self._target = target
        self._radius = float(radius)
        self._layers = layers
        self._insets = tuple(insets)
        self._body_fn = None
        self._margin = shadow_margin(layers) + 2
        self._chain: list = []
        self._shown = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        target.destroyed.connect(self._on_target_destroyed)
        self._watch_chain()
        self.sync()

    def _on_target_destroyed(self, *_):
        """目标销毁后自毁。"""
        if shiboken6.isValid(self):
            self.deleteLater()

    def _unwatch_chain(self) -> None:
        """撤掉目标及其祖先上的事件监听。"""
        for w in self._chain:
            if shiboken6.isValid(w):
                w.removeEventFilter(self)
        self._chain = []

    def _watch_chain(self) -> None:
        """监听目标到裁剪边界之间每一层控件（含目标）的移动、缩放、显隐与换父。

        Note:
            滚动区滚动时，被移动的是内容控件而不是目标，所以祖先必须一起监听。
        """
        self._unwatch_chain()
        root = self.parentWidget()
        w = self._target
        while w is not None and w is not root:
            w.installEventFilter(self)
            self._chain.append(w)
            w = w.parentWidget()

    def set_style(self, radius: float, layers: tuple, insets: tuple = (0, 0, 0, 0)) -> None:
        """更新圆角与阴影层（主题或档位变化后调用）。

        Args:
            radius: 目标圆角。
            layers: 阴影层元组。
            insets: 本体内缩 (上, 右, 下, 左)。
        """
        self._radius = float(radius)
        self._layers = layers
        self._insets = tuple(insets)
        self._margin = shadow_margin(layers) + 2
        self.sync()

    def set_body_provider(self, fn) -> None:
        """指定本体矩形的提供者（目标坐标系内的 QRect/QRectF）；None 表示本体 = 目标矩形（扣除内缩）。

        Args:
            fn: 无参可调用，返回本体矩形；用于"外壳比可视卡片大"的组件。
        """
        self._body_fn = fn
        self.update()

    def sync(self) -> None:
        """几何、可见性与挂载点跟随目标。"""
        t = self._target
        if not shiboken6.isValid(t):
            return
        root = clip_root(t)
        if root is None:
            self._set_shown(False)
            return
        if self.parentWidget() is not root:
            self.setParent(root)
            self._shown = False  # setParent 会把控件藏起来
            self._watch_chain()
        m = self._margin
        origin = t.mapTo(root, QPoint(0, 0))
        self.setGeometry(QRect(origin, t.size()).adjusted(-m, -m, m, m))
        self._set_shown(t.isVisible() and bool(self._layers))
        self.update()

    def _set_shown(self, want: bool) -> None:
        """显隐切换；每次从隐藏变显示都置顶，保证盖在刚创建的兄弟控件上方。

        Args:
            want: True 显示，False 隐藏。
        """
        if want and not self._shown:
            self.show()
            self.raise_()
        elif not want and self._shown:
            self.hide()
        self._shown = want

    def eventFilter(self, obj, event):
        """目标或其祖先的几何、显隐、换父变化时同步。"""
        if event.type() in _WATCH_EVENTS and shiboken6.isValid(self):
            if event.type() == QEvent.Type.ParentChange and obj is self._target:
                self._watch_chain()
            self.sync()
        return False

    def _body_rect(self) -> QRectF:
        """本体矩形（本层坐标）。"""
        m = self._margin
        if self._body_fn is not None:
            r = QRectF(self._body_fn())
            return QRectF(m + r.x(), m + r.y(), r.width(), r.height())
        top, right, bottom, left = self._insets
        return QRectF(
            m + left,
            m + top,
            max(0, self._target.width() - left - right),
            max(0, self._target.height() - top - bottom),
        )

    def paintEvent(self, _event):
        """画阴影与暗色内描边；本体区域在缓存图里已挖空。"""
        p = QPainter(self)
        body = self._body_rect()
        paint_shadow(p, body, self._radius, self._layers)
        paint_inset(p, body, self._radius, self._layers)
        p.end()


class ShadowController(QObject):
    """为任意控件挂载公共阴影：有了裁剪边界才创建阴影层，档位/圆角/主题变化时同步。

    阴影层不占布局；目标没有父控件时不创建，避免产生顶层窗口。
    """

    def __init__(self, target: QWidget):
        """绑定目标控件。

        Args:
            target: 需要阴影的控件。
        """
        super().__init__(target)
        self._target = target
        self._layer: ShadowLayer | None = None
        self._tier = "none"
        self._radius = 0.0
        self._theme = "light"
        self._insets = (0, 0, 0, 0)
        self._body_fn = None
        target.installEventFilter(self)

    def set_body_provider(self, fn) -> None:
        """指定本体矩形的提供者（目标坐标系）；阴影只包目标的一部分时使用。

        Args:
            fn: 无参可调用，返回本体矩形；None 恢复为目标矩形。
        """
        self._body_fn = fn
        if self._layer is not None and shiboken6.isValid(self._layer):
            self._layer.set_body_provider(fn)

    def set_style(self, tier: str, radius: float, theme: str, insets: tuple = (0, 0, 0, 0)) -> None:
        """设置档位、圆角与主题，并同步阴影层。

        Args:
            tier: none / sm / md / lg。
            radius: 目标圆角（逻辑像素）。
            theme: "light" 或 "dark"。
            insets: 本体相对目标矩形的内缩 (上, 右, 下, 左)。
        """
        self._tier, self._radius, self._theme = tier, float(radius), theme
        self._insets = tuple(insets)
        self._refresh()

    def _refresh(self) -> None:
        """按当前样式创建或更新阴影层。"""
        layers = layers_for(self._tier, self._theme)
        if self._layer is not None and shiboken6.isValid(self._layer):
            self._layer.set_style(self._radius, layers, self._insets)
            self._layer.set_body_provider(self._body_fn)
            return
        self._layer = None
        if clip_root(self._target) is None or not layers:
            return
        self._layer = ShadowLayer(self._target, self._radius, layers, self._insets)
        self._layer.set_body_provider(self._body_fn)

    def eventFilter(self, obj, event):
        """目标换父控件或首次显示时补建阴影层。"""
        if obj is self._target and self._layer is None and event.type() in (
            QEvent.Type.ParentChange,
            QEvent.Type.Show,
        ):
            self._refresh()
        return False


__all__ = [
    "ShadowController",
    "ShadowLayer",
    "clear_cache",
    "clip_root",
    "layers_for",
    "paint_inset",
    "paint_shadow",
    "prewarm",
    "shadow_margin",
    "tier_margin",
]
