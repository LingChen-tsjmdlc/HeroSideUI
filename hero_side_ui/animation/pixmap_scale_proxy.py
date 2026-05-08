"""
PixmapScaleProxy —— 用 pixmap 代理实现"顶层窗口内容整体缩放"的动画辅助类

背景:
    顶层 QWidget（尤其是 `Qt.Tool` / `Qt.Popup`）的 paintEvent 里做
    `painter.scale()` 只影响 owner 自己绘制的背景/装饰，**不影响子控件**
    （子控件独立走自己的 paintEvent）。所以普通做法看起来是"壳子缩了，
    里面内容没缩"。

    其它方案的坑:
    - resize-based scale（改 setFixedSize）：子控件 minimumSize 卡住下限
    - QGraphicsScale on Qt.Tool：顶层窗口效果不可靠
    - 给 owner 挂 QGraphicsEffect：和子控件自己的 effect（例如 Button 的
      PressScaleEffect）互相覆盖冲突

做法:
    1. 动画前：`begin()` 里把整个 owner（含子控件）render 到一张 QPixmap，
       然后把真实的"内容控件"（content_widget）hide，让 owner 只剩一张图
    2. 动画期间：owner 的 paintEvent 里检查 `is_active()`，如果是就跳过
       正常绘制，改用 `draw(painter, owner_rect, anchor)` 把缩放后的
       pixmap 画到窗口上
    3. 动画后：`end()` 清 pixmap + 恢复 content_widget.show()

典型用法::

    class MyPopover(QWidget):
        def __init__(self, ...):
            ...
            self._scale_proxy = PixmapScaleProxy(
                owner=self,
                content_widget_getter=lambda: self._content,
                scale_getter=lambda: self._fade.scale_value(),
            )

        def open(self):
            ...
            self._scale_proxy.begin()  # 抓快照 + 隐藏内容
            self._fade.play_in()

        def _on_fade_in_done(self):
            self._scale_proxy.end()  # 恢复真实内容

        def paintEvent(self, event):
            p = QPainter(self)
            if self._scale_proxy.is_active():
                self._scale_proxy.draw(p, self.rect(), anchor=(cx, cy))
                return
            # 正常绘制 ...
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPixmap
from typing import Callable, Optional, Tuple


class PixmapScaleProxy:
    """整窗 pixmap 缩放代理。

    参数:
        owner: 承载动画的顶层 widget
        content_widget_getter: 返回"真实内容控件"的可调用对象；动画期间
            这个控件会被 hide，避免在 pixmap 底下抢绘制。允许返回 None
            （表示没有可隐藏的内容，仅做整窗快照）。
        scale_getter: 返回当前缩放系数（动画每帧调用）的可调用对象
        enable_predicate: 可选。返回 False 时 `begin()` 变成空操作
            （用来支持"只对某些内容类型启用 scale"的场景）
    """

    def __init__(
        self,
        owner: QWidget,
        content_widget_getter: Callable[[], Optional[QWidget]],
        scale_getter: Callable[[], float],
        enable_predicate: Optional[Callable[[], bool]] = None,
    ):
        self._owner = owner
        self._get_content = content_widget_getter
        self._get_scale = scale_getter
        self._enable_predicate = enable_predicate
        self._pixmap: Optional[QPixmap] = None

    # ---- 状态 ----
    def is_active(self) -> bool:
        return self._pixmap is not None

    def pixmap(self) -> Optional[QPixmap]:
        return self._pixmap

    # ---- 生命周期 ----
    def begin(self):
        """启动代理：截图 → 隐藏真实内容。

        若 `enable_predicate` 返回 False 或 owner 尺寸非法，直接空操作。
        """
        if self._enable_predicate is not None and not self._enable_predicate():
            return

        w, h = self._owner.width(), self._owner.height()
        if w <= 0 or h <= 0:
            return

        pm = QPixmap(w, h)
        pm.fill(Qt.GlobalColor.transparent)
        # render 前确保 _pixmap=None，让 owner.paintEvent 走常规绘制
        self._pixmap = None
        self._owner.render(pm)

        self._pixmap = pm
        content = self._get_content()
        if content is not None:
            content.hide()
        self._owner.update()

    def end(self):
        """结束代理：清 pixmap + 恢复真实内容。"""
        self._pixmap = None
        content = self._get_content()
        if content is not None:
            content.show()
        self._owner.update()

    # ---- 绘制 ----
    def draw(self, painter: QPainter, owner_rect: QRect, anchor: Tuple[float, float]):
        """在 owner 的 paintEvent 中调用：把 pixmap 按当前 scale 绘制到 owner 上。

        `anchor` 为缩放锚点（owner 坐标系）。视觉上会以 anchor 为中心缩放。
        """
        if self._pixmap is None:
            return
        s = self._get_scale()
        cx, cy = anchor
        painter.save()
        painter.translate(cx, cy)
        painter.scale(s, s)
        painter.translate(-cx, -cy)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.restore()
