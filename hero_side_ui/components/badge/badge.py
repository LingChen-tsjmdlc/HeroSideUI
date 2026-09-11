"""HeroSideUI Badge — 徽章 (HeroUI v2)。完整 API/示例见 docs/badge.md。

结构对照官方 badge.tsx：base（inline-flex 包裹 children）+ badge（absolute 角标）。
样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/badge.ts

isDot（content 为空）与 isOneChar（content 单字符）均由 content 自动判定，
与官方 String(content).length 逻辑一致。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import (
    BADGE_PLACEMENT_OFFSETS,
    BADGE_SIZES,
    VALID_BADGE_PLACEMENTS,
    VALID_BADGE_SHAPES,
    VALID_BADGE_SIZES,
    VALID_BADGE_VARIANTS,
)
from ..text import Text
from ._styling import build_badge_styles

# showOutline 描边色 = 官方 border-background（bg-background: light=#fff / dark=#000）
_OUTLINE_COLOR = {"light": "#ffffff", "dark": "#000000"}

# 官方 disableAnimation=false 时 !duration-300
ANIM_DURATION = 300


def _to_qcolor(css: str) -> QColor:
    """把 HEX 或 rgba() 字符串转 QColor（QColor 构造不吃 rgba() 函数式写法）。"""
    c = QColor(css)
    if c.isValid():
        return c
    if css.startswith("rgba"):
        nums = css[css.index("(") + 1 : css.rindex(")")].split(",")
        c = QColor(int(nums[0]), int(nums[1]), int(nums[2]))
        c.setAlphaF(float(nums[3]))
    return c


class _BadgeMark(QWidget):
    """角标容器：自绘圆角底色 + 描边。

    不用 QSS 的原因（对照实验实证）：容器 setStyleSheet 设背景后，样式链会把
    背景色染给内嵌 Text 子件的文字渲染（白字变底色 + 1px 重影），自绘绕开。

    set_mark_style(bg, border_color, border_width, radius) 四参全量下发。
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bg: Optional[QColor] = None
        self._border_color: Optional[QColor] = None
        self._border_width = 0
        self._radius = 0

    def set_mark_style(
        self, bg: QColor, border_color: Optional[QColor], border_width: int, radius: int
    ):
        # 形参：bg 底色；border_color 描边色（None 无边框）；border_width 描边宽；radius 圆角
        self._bg = bg
        self._border_color = border_color
        self._border_width = border_width
        self._radius = radius
        self.update()

    def paintEvent(self, event):
        if self._bg is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        if self._border_color is not None and self._border_width > 0:
            pen = QPen(self._border_color, float(self._border_width))
            p.setPen(pen)
            # 描边画在边缘线上，内缩半笔宽保证不溢出
            inset = self._border_width / 2.0
            rect = rect.adjusted(inset, inset, -inset, -inset)
        else:
            p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._bg)
        p.drawRoundedRect(rect, self._radius, self._radius)


class Badge(QWidget):
    """HeroUI 风格徽章 — 包裹一个 QWidget 并在其角上叠加角标。用法::

    Badge(Avatar(...), content="5", color="danger")
    Badge(Button("消息"), content="99+", placement="top-right", variant="flat")
    Badge(widget, content="", color="success")          # 空内容 → 圆点
    """

    def __init__(
        self,
        widget: Optional[QWidget] = None,
        content: str = "",
        color: str = "default",
        variant: str = "solid",
        size: str = "md",
        shape: str = "rectangle",
        placement: str = "top-right",
        show_outline: bool = True,
        is_invisible: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroBadge")

        self._widget: Optional[QWidget] = None
        self._content = str(content)
        self._color = color
        self._variant = variant if variant in VALID_BADGE_VARIANTS else "solid"
        self._size = size if size in BADGE_SIZES else "md"
        self._shape = shape if shape in VALID_BADGE_SHAPES else "rectangle"
        self._placement = (
            placement if placement in VALID_BADGE_PLACEMENTS else "top-right"
        )
        self._show_outline = bool(show_outline)
        self._is_invisible = bool(is_invisible)
        self._disable_animation = bool(disable_animation)
        self._theme_mode = theme
        self._theme = (
            ThemeProvider.instance().current_theme if theme == "auto" else theme
        )
        self._anim: Optional[QPropertyAnimation] = None
        self._styles: dict = {}

        self._build_ui()
        if widget is not None:
            self.set_widget(widget)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._apply_styles()
        # 构造期按需隐藏角标（无动画）
        self._badge.setVisible(not self._is_invisible)

    # ---- derived state ----

    @property
    def _is_dot(self) -> bool:
        # 官方 isDot: String(content)?.length === 0
        return len(self._content) == 0

    @property
    def _is_one_char(self) -> bool:
        # 官方 isOneChar: String(content)?.length === 1
        return len(self._content) == 1

    # ---- build ----

    def _build_ui(self):
        # 被包裹内容：布局零边距，Badge 尺寸完全跟随 children
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # 角标 = 自绘容器（底色/描边/圆角，绝对定位不走 layout）+ 内嵌 Text
        # 容器禁用 QSS：QSS 背景会经样式链染给 Text 子件（见 _BadgeMark 注释）
        self._badge = _BadgeMark(self)
        self._badge.setObjectName("HeroBadgeLabel")
        self._badge_lay = QVBoxLayout(self._badge)
        self._badge_lay.setContentsMargins(0, 0, 0, 0)
        self._badge_lay.setSpacing(0)

        cfg = BADGE_SIZES[self._size]
        self._label = Text(
            self._content,
            size=cfg["text_size"],
            weight="normal",
            theme=self._theme,
        )
        self._label.setContentsMargins(0, 0, 0, 0)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge_lay.addWidget(self._label)

    # ---- badge geometry ----

    def _update_badge_size(self):
        """按 content 形态固定角标尺寸：圆点/正方形/圆角矩形。"""
        cfg = BADGE_SIZES[self._size]
        if self._is_dot:
            side = cfg["dot"]
            self._badge.setFixedSize(side, side)
        elif self._is_one_char:
            side = cfg["one_char"]
            self._badge.setFixedSize(side, side)
        else:
            tw = self._label.fontMetrics().horizontalAdvance(self._content)
            h = cfg["multi_height"]
            self._badge.setFixedSize(max(tw + cfg["padding_x"] * 2, h), h)
        self._update_badge_margin()

    def _badge_margin(self) -> int:
        """四周预留边距 = 角标半径（中心悬边缘时最大悬出量），防被父裁剪。"""
        return (max(self._badge.width(), self._badge.height()) + 1) // 2

    def _update_badge_margin(self):
        """角标尺寸变化时同步预留边距；updateGeometry 通知父布局重排。"""
        m = self._badge_margin()
        cm = self._layout.contentsMargins()
        if cm.left() == m and cm.top() == m:
            return
        self._layout.setContentsMargins(m, m, m, m)
        self.updateGeometry()

    def _update_badge_geometry(self):
        """官方 placement×shape 定位。rectangle：角标中心悬在内容边缘的 5%
        锚点上（x/y 独立百分比）；circle：角标中心在 45° 对角线上、悬出内容
        外接圆边 0.65 倍角标半径（咬合恒为 0.35 倍角标半径，不随内容尺寸漂移；
        官方 10% 矩形锚点在大尺寸圆形内容上会脱离圆边）。
        基准是被包裹件的实际矩形；无被包裹件时退回预留边距内的矩形。"""
        if self._widget is not None and not self._widget.geometry().isNull():
            rect = self._widget.geometry()
        else:
            m = self._badge_margin()
            rect = self.rect().adjusted(m, m, -m, -m)
        w, h = rect.width(), rect.height()
        if w <= 0 or h <= 0:
            return
        bw, bh = self._badge.width(), self._badge.height()
        if self._shape == "circle":
            half = min(w, h) / 2
            d = half + 0.65 * bw / 2
            dx = d / 2**0.5
            cx0, cy0 = rect.x() + w / 2, rect.y() + h / 2
            cx = cx0 + (dx if "right" in self._placement else -dx)
            cy = cy0 + (-dx if self._placement.startswith("top") else dx)
        else:
            p = BADGE_PLACEMENT_OFFSETS.get(
                self._shape, BADGE_PLACEMENT_OFFSETS["rectangle"]
            )
            cx = rect.x() + (w * (1 - p) if "right" in self._placement else w * p)
            cy = rect.y() + (
                h * p if self._placement.startswith("top") else h * (1 - p)
            )
        # 防裁剪：钳制到容器内（预留边距只保证 hint 尺寸，父布局拉伸后锚点外移）
        x = min(max(round(cx - bw / 2), 0), self.width() - bw)
        y = min(max(round(cy - bh / 2), 0), self.height() - bh)
        self._badge.setGeometry(x, y, bw, bh)
        self._badge.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_badge_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        # 构造期 self.width() 是 640x480 垃圾值；若布局此后没再 resize 本组件
        # （尺寸恰与 hint 一致时），角标会停在陈旧位置，显示前再校正一次
        self._update_badge_geometry()

    # ---- styles ----

    def _apply_styles(self):
        self._styles = build_badge_styles(self._variant, self._color, self._theme)
        self._update_badge_size()

        # showOutline（官方默认 true）：2px 宿主背景色描边；False 时连 faded
        # 的边框也被官方 border-0 覆盖 → 无边框
        if self._show_outline:
            border_color = QColor(
                _OUTLINE_COLOR.get(self._theme, _OUTLINE_COLOR["light"])
            )
            border_width = 2
        else:
            border_color = None
            border_width = 0

        # 官方 badge 恒为 rounded-full → 圆角 = 短边一半
        r = self._badge.height() // 2
        self._badge.set_mark_style(
            bg=_to_qcolor(self._styles["bg"]),
            border_color=border_color,
            border_width=border_width,
            radius=r,
        )
        self._label.set_color(self._styles["fg"])
        self._apply_badge_effect()
        self._update_badge_geometry()

    def _apply_badge_effect(self):
        # 单效果约束：invisible 动画期间持有 opacity effect，结束后由
        # _on_anim_finished 恢复；稳定态下 shadow variant 用投影
        if self._anim is not None:
            return
        if self._styles.get("has_shadow") and self._styles.get("shadow_color"):
            eff = QGraphicsDropShadowEffect(self._badge)
            eff.setBlurRadius(12)
            eff.setOffset(0, 2)
            c = QColor(self._styles["shadow_color"])
            c.setAlphaF(0.45)
            eff.setColor(c)
            self._badge.setGraphicsEffect(eff)
        else:
            self._badge.setGraphicsEffect(None)

    # ---- visibility animation ----

    def _animate_visibility(self, show: bool):
        # 官方 isInvisible 切换 = scale-0 + opacity-0 过渡；桌面简化为
        # 300ms 透明度过渡（shadow 投影与 opacity effect 互斥，动画期间
        # 临时换成 opacity effect，结束后恢复）
        if self._anim is not None:
            self._anim.stop()
            self._anim.deleteLater()
            self._anim = None
        eff = QGraphicsOpacityEffect(self._badge)
        self._badge.setGraphicsEffect(eff)
        eff.setOpacity(0.0 if show else 1.0)
        self._badge.setVisible(True)
        self._anim = QPropertyAnimation(eff, b"opacity", self)
        self._anim.setDuration(ANIM_DURATION)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(0.0 if show else 1.0)
        self._anim.setEndValue(1.0 if show else 0.0)
        self._anim.finished.connect(lambda show=show: self._on_anim_finished(show))
        self._anim.start()

    def _on_anim_finished(self, show: bool):
        self._anim = None
        self._badge.setVisible(show)
        self._apply_badge_effect()

    # ---- wrapped widget ----

    def set_widget(self, widget: Optional[QWidget]):
        """替换被包裹的内容；旧 widget 从布局移除并脱离父级（不销毁）。"""
        old = self._widget
        if old is widget:
            return
        if old is not None:
            self._layout.removeWidget(old)
            old.setParent(None)
            old.hide()
        self._widget = widget
        if widget is not None:
            widget.setParent(self)
            self._layout.addWidget(widget)
            widget.show()
        self._update_badge_geometry()

    def widget(self) -> Optional[QWidget]:
        return self._widget

    # ---- setters ----

    def set_content(self, content: str):
        """更新角标内容；空串 → 圆点，单字符 → 正方形，多字符 → 圆角矩形。"""
        self._content = str(content)
        self._label.setText(self._content)
        self._apply_styles()

    def content(self) -> str:
        return self._content

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        if size not in BADGE_SIZES:
            return
        self._size = size
        self._label.set_size(BADGE_SIZES[size]["text_size"])
        self._apply_styles()

    def set_shape(self, shape: str):
        self._shape = shape
        self._update_badge_geometry()

    def set_placement(self, placement: str):
        self._placement = placement
        self._update_badge_geometry()

    def set_show_outline(self, show: bool):
        self._show_outline = bool(show)
        self._apply_styles()

    def set_invisible(self, invisible: bool):
        """切换角标可见性；默认带 300ms 淡入淡出（对齐官方 duration-300）。"""
        invisible = bool(invisible)
        if invisible == self._is_invisible:
            return
        self._is_invisible = invisible
        if self._disable_animation:
            if self._anim is not None:
                self._anim.stop()
                self._anim.deleteLater()
                self._anim = None
            self._badge.setVisible(not invisible)
            self._apply_badge_effect()
        else:
            self._animate_visibility(not invisible)

    def is_invisible(self) -> bool:
        return self._is_invisible

    def set_disable_animation(self, disabled: bool):
        self._disable_animation = bool(disabled)

    # ---- theme ----

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
        self._label.set_theme(self._theme)
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._label.set_theme(theme)
        self._apply_styles()
