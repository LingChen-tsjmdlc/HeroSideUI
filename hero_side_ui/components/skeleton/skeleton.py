"""HeroSideUI Skeleton — 骨架屏占位组件 (HeroUI v2)

完全复刻 HeroUI Skeleton 的视觉行为：
- shimmer 扫光动画（before 伪元素 translateX(-100%)→200%, 3色标渐变）
- isLoaded 状态切换（骨架 ↔ 真实内容，300ms 交叉淡入淡出）
- disableAnimation 开关
- 支持 children（自动匹配子组件形状）和 standalone 模式
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ...core import ThemeProvider
from ...animation.skeleton_shimmer import SkeletonShimmerAnimation
from ._styling import build_skeleton_styles


class Skeleton(QWidget):
    """HeroUI 风格骨架屏。

    用法::

        skeleton = Skeleton(child=my_widget)
        skeleton.set_loaded(True)

        # 独立使用
        s = Skeleton()
        s.setFixedSize(200, 24)
    """

    def __init__(
        self,
        child: Optional[QWidget] = None,
        is_loaded: bool = False,
        disable_animation: bool = False,
        radius: str = "lg",
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroSkeleton")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._is_loaded = is_loaded
        self._disable_animation = disable_animation
        self._radius = radius
        self._theme_mode = theme
        self._theme = (
            ThemeProvider.instance().current_theme if theme == "auto" else theme
        )
        self._custom_styled = False

        # 官方: animate-shimmer 2s infinite
        self._shimmer = SkeletonShimmerAnimation(self, duration=2000)

        # 骨架层 opacity（paintEvent 绘制时使用）
        self._skeleton_opacity = 0.0 if is_loaded else 1.0
        self._skeleton_fade_anim: Optional[QPropertyAnimation] = None

        # 内容层 opacity
        self._content_opacity = 1.0 if is_loaded else 0.0
        self._content_fade_anim: Optional[QPropertyAnimation] = None

        self._styles: dict = {}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._content = QWidget(self)
        self._content.setObjectName("HeroSkeletonContent")
        self._content.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._layout.addWidget(self._content)

        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        if child is not None:
            self._content_layout.addWidget(child)

        self._apply_styles()

        if not is_loaded and not disable_animation:
            QTimer.singleShot(0, self._shimmer.start)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Qt Property — 骨架层 opacity（供 QPropertyAnimation 驱动）
    # ============================================================

    def _get_skeleton_opacity(self) -> float:
        return self._skeleton_opacity

    def _set_skeleton_opacity(self, v: float):
        self._skeleton_opacity = v
        self.update()

    skeletonOpacity = Property(float, _get_skeleton_opacity, _set_skeleton_opacity)

    # ============================================================
    # Paint — 自绘 shimmer 扫光（对齐 HeroUI before 伪元素）
    # ============================================================

    def paintEvent(self, event):
        # 骨架完全透明时不绘制
        if self._skeleton_opacity < 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._skeleton_opacity)

        w, h = self.width(), self.height()
        r_px = self._resolve_radius_px()
        s = self._styles

        # 1. 基底背景 (bg-content3 / dark:bg-content2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(s["base_bg"]))
        painter.drawRoundedRect(0, 0, w, h, r_px, r_px)

        # 2. Top border (before:border-content4/30)
        t = s["top_border"]
        t_color = (
            QColor(t[0], t[1], t[2], int(t[3] * 255))
            if isinstance(t, tuple)
            else QColor(t)
        )
        pen = QPen(t_color)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawLine(0, 0, w, 0)

        # 3. Shimmer 渐变条带
        # 官方: before:bg-gradient-to-r from-transparent via-content4 to-transparent
        #        before:-translate-x-full → translateX(200%)
        if not self._disable_animation:
            progress = self._shimmer.progress_value()
            via = s["shimmer_via"]
            c_via = QColor(via[0], via[1], via[2], int(via[3] * 255))

            band_w = float(w)
            offset = -band_w + progress * 3.0 * band_w

            grad = QLinearGradient(offset, 0, offset + band_w, 0)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.5, c_via)
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(0, 0, w, h, r_px, r_px)

        painter.end()

    # ============================================================
    # 公共 API
    # ============================================================

    def set_loaded(self, loaded: bool):
        if self._is_loaded == loaded:
            return
        self._is_loaded = loaded
        self._cancel_fade_anims()

        if loaded:
            # 关闭骨架：骨架层淡出 + 内容层淡入，同时进行 300ms
            self._animate_skeleton_to(0.0, on_done=self._shimmer.stop)
            self._fade_content_to(1.0)
        else:
            # 开启骨架：骨架层淡入 + 内容层淡出，同时进行 300ms
            if not self._disable_animation:
                self._shimmer.start()
            self._animate_skeleton_to(1.0)
            self._fade_content_to(0.0)

    def is_loaded(self) -> bool:
        return self._is_loaded

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable
        if disable:
            self._shimmer.stop()
        elif not self._is_loaded:
            self._shimmer.start()
        self.update()

    def set_radius(self, radius: str):
        self._radius = radius
        self.update()

    def set_child(self, child: QWidget):
        from ...utils import clear_layout
        clear_layout(self._content_layout)
        self._content_layout.addWidget(child)

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
        if not self._custom_styled:
            self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        self._theme = theme
        if not self._custom_styled:
            self._apply_styles()

    def set_stylesheet(self, qss: str):
        self._custom_styled = True
        super().setStyleSheet(qss)

    # ============================================================
    # 内部方法
    # ============================================================

    def _apply_styles(self):
        self._styles = build_skeleton_styles(self._theme)
        self._content_opacity = 1.0 if self._is_loaded else 0.0
        self._skeleton_opacity = 0.0 if self._is_loaded else 1.0
        self._update_content_opacity()
        self.update()

    def _resolve_radius_px(self) -> float:
        from ...themes import RADIUS

        r = self._radius
        if r == "full":
            return min(self.width(), self.height()) / 2.0
        if r == "none":
            return 0.0
        raw = RADIUS.get(r, RADIUS["lg"])
        return float(raw.replace("px", ""))

    # -- 骨架层 opacity 动画 --

    def _animate_skeleton_to(self, target: float, on_done=None):
        if abs(self._skeleton_opacity - target) < 0.01:
            if on_done:
                on_done()
            return

        self._skeleton_fade_anim = QPropertyAnimation(self, b"skeletonOpacity")
        self._skeleton_fade_anim.setDuration(300)
        self._skeleton_fade_anim.setStartValue(self._skeleton_opacity)
        self._skeleton_fade_anim.setEndValue(target)
        self._skeleton_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_finished():
            self._skeleton_fade_anim = None
            if on_done:
                on_done()

        self._skeleton_fade_anim.finished.connect(_on_finished)
        self._skeleton_fade_anim.start()

    # -- 内容层 opacity 动画 --

    def _update_content_opacity(self):
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        if not self._content.graphicsEffect():
            self._content.setGraphicsEffect(QGraphicsOpacityEffect(self._content))
        self._content.graphicsEffect().setOpacity(self._content_opacity)
        # NOTE: 不能 setVisible(False)，否则 layout 不为 child 分配空间，
        # 有 child 的 Skeleton 高度会坍缩为 0。靠 opacity=0 隐藏即可。

    def _fade_content_to(self, target: float):
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        if not self._content.graphicsEffect():
            self._content.setGraphicsEffect(QGraphicsOpacityEffect(self._content))

        if abs(self._content_opacity - target) < 0.01:
            self._content_opacity = target
            self._update_content_opacity()
            return

        self._content_fade_anim = QPropertyAnimation(
            self._content.graphicsEffect(), b"opacity"
        )
        self._content_fade_anim.setDuration(300)
        self._content_fade_anim.setStartValue(self._content_opacity)
        self._content_fade_anim.setEndValue(target)
        self._content_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_finished():
            self._content_opacity = target
            self._update_content_opacity()
            self._content_fade_anim = None

        self._content_fade_anim.finished.connect(_on_finished)
        self._content_fade_anim.start()

    def _cancel_fade_anims(self):
        if self._skeleton_fade_anim is not None:
            self._skeleton_fade_anim.stop()
            self._skeleton_fade_anim = None
        if self._content_fade_anim is not None:
            self._content_fade_anim.stop()
            self._content_fade_anim = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._is_loaded and not self._disable_animation:
            self._shimmer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._shimmer.stop()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()
