"""Skeleton 骨架屏：shimmer 扫光 + isLoaded 交叉淡入淡出 + 动画开关。"""

from __future__ import annotations

from PySide6.QtCore import Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...animation import stop_tween, tween_property, tween_value
from ...animation.skeleton_shimmer import SkeletonShimmerAnimation
from ...core import ThemeProvider
from ._styling import build_skeleton_styles


class Skeleton(QWidget):
    """HeroUI 风格骨架屏；child 自动匹配形状，也可独立 setFixedSize 用。"""

    def __init__(
        self,
        child: QWidget | None = None,
        is_loaded: bool = False,
        disable_animation: bool = False,
        radius: str = "lg",
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构造骨架屏并记录初始状态，按 is_loaded 决定初始透明度。

        Args:
            child: 内容层承载的子控件。
            is_loaded: 初始是否已完成加载。
            disable_animation: 是否关闭 shimmer 与淡入淡出动画。
            radius: 圆角档位。
            theme: 主题模式，auto 跟随 ThemeProvider。
            parent: 作为 Qt 父对象的 QWidget。

        Note:
            is_loaded 为真时骨架层初始透明度为 0、内容层为 1；未加载且未禁用
            动画时启动 shimmer；theme=auto 时向 ThemeProvider 注册。
        """
        super().__init__(parent)
        self.setObjectName("HeroSkeleton")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._is_loaded = is_loaded
        self._disable_animation = disable_animation
        self._radius = radius
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme
        self._custom_styled = False

        # 官方: animate-shimmer 2s infinite
        self._shimmer = SkeletonShimmerAnimation(self, duration=2000)

        # 骨架层 opacity（paintEvent 绘制时使用）
        self._skeleton_opacity = 0.0 if is_loaded else 1.0
        self._skeleton_fade_anim: QPropertyAnimation | None = None

        # 内容层 opacity
        self._content_opacity = 1.0 if is_loaded else 0.0
        self._content_fade_anim: QPropertyAnimation | None = None

        self._styles: dict = {}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._content = QWidget(self)
        self._content.setObjectName("HeroSkeletonContent")
        self._content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._layout.addWidget(self._content)

        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        if child is not None:
            self._content_layout.addWidget(child)

        self._apply_styles()

        if not is_loaded and not disable_animation:
            self._shimmer.start()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Qt Property — 骨架层 opacity（供 QPropertyAnimation 驱动）
    # ============================================================

    def _get_skeleton_opacity(self) -> float:
        """返回骨架层当前透明度。"""
        return self._skeleton_opacity

    def _set_skeleton_opacity(self, v: float):
        """设置骨架层透明度并触发重绘。"""
        self._skeleton_opacity = v
        self.update()

    skeletonOpacity = Property(float, _get_skeleton_opacity, _set_skeleton_opacity)

    # ============================================================
    # Paint — 自绘 shimmer 扫光（对齐 HeroUI before 伪元素）
    # ============================================================

    def paintEvent(self, event):
        """绘制骨架背景、顶部描边与 shimmer 渐变条带。

        Note:
            骨架透明度低于 0.01 时直接返回；禁用动画时不绘制 shimmer 条带。
        """
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
        t_color = QColor(t[0], t[1], t[2], int(t[3] * 255)) if isinstance(t, tuple) else QColor(t)
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
        """切换加载态，在骨架层与内容层之间做交叉淡入淡出。

        Args:
            loaded: 是否标记为已加载。

        Note:
            与当前状态相同则直接返回；加载时停 shimmer，卸载时按需重启。
        """
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
        """返回当前是否已加载。"""
        return self._is_loaded

    def set_disable_animation(self, disable: bool):
        """切换动画开关并同步两层透明度与 shimmer 状态。

        Args:
            disable: 是否禁用动画。
        """
        self._disable_animation = disable
        if disable:
            self._cancel_fade_anims()
            self._shimmer.stop()
            self._skeleton_opacity = 0.0 if self._is_loaded else 1.0
            self._content_opacity = 1.0 if self._is_loaded else 0.0
            self._update_content_opacity()
        elif not self._is_loaded:
            self._shimmer.start()
        self.update()

    def set_radius(self, radius: str):
        """设置圆角档位并触发重绘。"""
        self._radius = radius
        self.update()

    def set_child(self, child: QWidget):
        """清空内容层并挂入新的子控件。"""
        from ...utils import clear_layout

        clear_layout(self._content_layout)
        self._content_layout.addWidget(child)

    def set_theme(self, theme: str):
        """切换主题模式并按需刷新内置样式。

        Args:
            theme: 目标模式；auto 重新注册 ThemeProvider，其他值注销注册。

        Note:
            _custom_styled 为真时（已 set_stylesheet）不重算内置样式。
        """
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
        """在 auto 模式下应用 provider 主题并按需刷新内置样式。

        Args:
            theme: ThemeProvider 下发的当前主题名。
        """
        self._theme = theme
        if not self._custom_styled:
            self._apply_styles()

    def set_stylesheet(self, qss: str):
        """应用自定义 QSS 并标记样式由用户接管。

        Note:
            标记 _custom_styled 后，主题刷新不再重算内置样式。
        """
        self._custom_styled = True
        super().setStyleSheet(qss)

    # ============================================================
    # 内部方法
    # ============================================================

    def _apply_styles(self):
        """重建颜色 token 并按加载态复位两层透明度。"""
        self._styles = build_skeleton_styles(self._theme)
        self._content_opacity = 1.0 if self._is_loaded else 0.0
        self._skeleton_opacity = 0.0 if self._is_loaded else 1.0
        self._update_content_opacity()
        self.update()

    def _resolve_radius_px(self) -> float:
        """把圆角档位解析为像素半径。

        Returns:
            full 返回短边一半，none 返回 0，其余取 RADIUS 表数值。
        """
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
        """把骨架层透明度过渡到目标值。

        Args:
            target: 目标透明度。
            on_done: 动画结束回调，加载完成时用于停 shimmer。
        """
        tween_property(
            self,
            "_skeleton_fade_anim",
            b"skeletonOpacity",
            target,
            duration=300,
            animated=not self._disable_animation and abs(self._skeleton_opacity - target) >= 0.01,
            on_finished=on_done,
        )

    # -- 内容层 opacity 动画 --

    def _update_content_opacity(self):
        """把内容层透明度写入其 QGraphicsOpacityEffect。

        Note:
            不能用 setVisible(False) 隐藏内容层，否则 layout 不为 child 分配
            空间，有 child 时骨架高度会坍缩为 0，只能靠 opacity=0 隐藏。
        """
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        if not self._content.graphicsEffect():
            self._content.setGraphicsEffect(QGraphicsOpacityEffect(self._content))
        self._content.graphicsEffect().setOpacity(self._content_opacity)
        # NOTE: 不能 setVisible(False)，否则 layout 不为 child 分配空间，
        # 有 child 的 Skeleton 高度会坍缩为 0。靠 opacity=0 隐藏即可。

    def _fade_content_to(self, target: float):
        """把内容层透明度过渡到目标值。

        Args:
            target: 目标透明度。
        """

        def apply(value):
            self._content_opacity = float(value)
            self._update_content_opacity()

        tween_value(
            self,
            "_content_fade_anim",
            self._content_opacity,
            target,
            apply,
            duration=300,
            animated=not self._disable_animation,
        )

    def _cancel_fade_anims(self):
        """取消骨架层与内容层进行中的淡入淡出动画。"""
        stop_tween(self, "_skeleton_fade_anim")
        stop_tween(self, "_content_fade_anim")

    def resizeEvent(self, event):
        """尺寸变化时触发重绘，并交给父类处理事件。"""
        super().resizeEvent(event)
        self.update()
