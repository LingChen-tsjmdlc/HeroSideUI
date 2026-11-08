"""Badge 徽章：包裹 QWidget 并叠角标；isDot/isOneChar 由 content 自动判定。"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...animation import stop_tween, tween_property
from ...core import ThemeProvider
from ...themes import (
    BADGE_PLACEMENT_OFFSETS,
    BADGE_SIZES,
    VALID_BADGE_PLACEMENTS,
    VALID_BADGE_SHAPES,
    VALID_BADGE_VARIANTS,
)
from ..text import Text
from ._styling import build_badge_styles

# showOutline 描边色 = 官方 border-background（bg-background: light=#fff / dark=#000）
_OUTLINE_COLOR = {"light": "#ffffff", "dark": "#000000"}

# 官方 disableAnimation=false 时 !duration-300
ANIM_DURATION = 300


def _to_qcolor(css: str) -> QColor:
    """把 HEX 或 rgba() 字符串转成 QColor。

    Args:
        css: HEX 或 rgba(r,g,b,a) 形式的颜色字符串。

    Returns:
        对应的 QColor；rgba 写法需手工解析，因为 QColor 构造不认函数式写法。
    """
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

    Note:
        不用 QSS——样式链会把背景染给内嵌 Text 文字（白字变底色+重影）。
    """

    def __init__(self, parent: QWidget | None = None):
        """初始化自绘参数，全部样式等 set_mark_style 写入。

        Args:
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._bg: QColor | None = None
        self._border_color: QColor | None = None
        self._border_width = 0
        self._radius = 0

    def set_mark_style(
        self, bg: QColor, border_color: QColor | None, border_width: int, radius: int
    ):
        """写入角标自绘参数并触发重绘。

        Args:
            bg: 底色。
            border_color: 描边色；None 表示无边框。
            border_width: 描边宽度，单位像素。
            radius: 圆角半径，单位像素。
        """
        # 形参：bg 底色；border_color 描边色（None 无边框）；border_width 描边宽；radius 圆角
        self._bg = bg
        self._border_color = border_color
        self._border_width = border_width
        self._radius = radius
        self.update()

    def paintEvent(self, event):
        """自绘圆角底色与描边。

        Args:
            event: Qt 绘制事件。

        Note:
            有描边时把矩形内缩半笔宽，避免线条画到边界外被裁剪；
            _bg 未设置（构造后尚未 set_mark_style）时直接返回。
        """
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
    """HeroUI 风格徽章：包裹一个 QWidget 并在其角上叠加角标。"""

    def __init__(
        self,
        widget: QWidget | None = None,
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
        parent: QWidget | None = None,
    ):
        """创建徽章容器并装配角标。

        Args:
            widget: 被包裹的内容 widget，可为 None 后续用 set_widget 设置。
            content: 角标文本；空串为圆点、单字符为正方形。
            color: 语义色。
            variant: 视觉变体，非法值回退 solid。
            size: 尺寸档位，非法值回退 md。
            shape: 角标形状，非法值回退 rectangle。
            placement: 角标位置，非法值回退 top-right。
            show_outline: 是否画 2px 宿主背景色描边。
            is_invisible: 构造时是否隐藏角标。
            disable_animation: 是否关闭显隐过渡。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("HeroBadge")

        self._widget: QWidget | None = None
        self._content = str(content)
        self._color = color
        self._variant = variant if variant in VALID_BADGE_VARIANTS else "solid"
        self._size = size if size in BADGE_SIZES else "md"
        self._shape = shape if shape in VALID_BADGE_SHAPES else "rectangle"
        self._placement = placement if placement in VALID_BADGE_PLACEMENTS else "top-right"
        self._show_outline = bool(show_outline)
        self._is_invisible = bool(is_invisible)
        self._disable_animation = bool(disable_animation)
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme
        self._anim: QPropertyAnimation | None = None
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
        """角标是否为圆点形态。

        Returns:
            content 为空串时为 True，对齐 HeroUI 的 isDot 判定。
        """
        # 官方 isDot: String(content)?.length === 0
        return len(self._content) == 0

    @property
    def _is_one_char(self) -> bool:
        """角标是否为单字符正方形形态。

        Returns:
            content 长度为 1 时为 True，对齐 HeroUI 的 isOneChar 判定。
        """
        # 官方 isOneChar: String(content)?.length === 1
        return len(self._content) == 1

    # ---- build ----

    def _build_ui(self):
        """装配零边距主布局与绝对定位的角标容器。

        角标用 _BadgeMark 自绘而不是 QSS，避免样式链把背景染给内嵌的
        Text 子件造成白字重影；它不走布局，几何由 _update_badge_geometry 算。
        """
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
        """按 content 形态固定角标尺寸：圆点 / 正方形 / 圆角矩形。

        多字符时用字宽加两侧 padding 估算宽度，并以 multi_height 兜底，
        保证短文本也是胶囊形。尺寸变化后同步刷新预留边距。
        """
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
        """计算四周预留边距。

        Returns:
            角标半径（中心悬在内容边缘时的最大悬出量），用于防止被父裁剪。
        """
        return (max(self._badge.width(), self._badge.height()) + 1) // 2

    def _update_badge_margin(self):
        """角标尺寸变化时同步预留边距，并通知父布局重排。

        Note:
            新旧边距相同就直接返回，避免 updateGeometry 触发无意义的重排循环。
        """
        m = self._badge_margin()
        cm = self._layout.contentsMargins()
        if cm.left() == m and cm.top() == m:
            return
        self._layout.setContentsMargins(m, m, m, m)
        self.updateGeometry()

    def _update_badge_geometry(self):
        """按 placement × shape 定位角标并钳制在容器内。

        rectangle 用内容边缘百分比锚点；circle 用 45° 对角线圆贴合模型，
        咬合恒为 0.35 倍角标半径，不随内容尺寸漂移。

        Note:
            预留边距只保证 sizeHint，父布局拉伸后锚点会外移，所以最后
            必须把坐标钳到 [0, width/height - 角标尺寸] 区间并 raise_() 置顶。
        """
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
            p = BADGE_PLACEMENT_OFFSETS.get(self._shape, BADGE_PLACEMENT_OFFSETS["rectangle"])
            cx = rect.x() + (w * (1 - p) if "right" in self._placement else w * p)
            cy = rect.y() + (h * p if self._placement.startswith("top") else h * (1 - p))
        # 防裁剪：钳制到容器内（预留边距只保证 hint 尺寸，父布局拉伸后锚点外移）
        x = min(max(round(cx - bw / 2), 0), self.width() - bw)
        y = min(max(round(cy - bh / 2), 0), self.height() - bh)
        self._badge.setGeometry(x, y, bw, bh)
        self._badge.raise_()

    def resizeEvent(self, event):
        """尺寸变化后重算角标几何。

        Args:
            event: Qt 尺寸变化事件。
        """
        super().resizeEvent(event)
        self._update_badge_geometry()

    def showEvent(self, event):
        """显示前再校正一次角标几何。

        Args:
            event: Qt 显示事件。

        Note:
            构造期 width() 是 640×480 的垃圾值；若布局此后没再 resize
            （尺寸恰与 hint 一致），角标会停在陈旧位置。
        """
        super().showEvent(event)
        # 构造期 self.width() 是 640x480 垃圾值；若布局此后没再 resize 本组件
        # （尺寸恰与 hint 一致时），角标会停在陈旧位置，显示前再校正一次
        self._update_badge_geometry()

    # ---- styles ----

    def _apply_styles(self):
        """重算配色、角标尺寸、描边与图形效果，并刷新几何。

        show_outline 为 True 时用宿主背景色画 2px 描边；为 False 时连
        faded 变体的边框也一并去掉。圆角恒取角标短边一半（rounded-full）。
        """
        self._styles = build_badge_styles(self._variant, self._color, self._theme)
        self._update_badge_size()

        # showOutline（官方默认 true）：2px 宿主背景色描边；False 时连 faded
        # 的边框也被官方 border-0 覆盖 → 无边框
        if self._show_outline:
            border_color = QColor(_OUTLINE_COLOR.get(self._theme, _OUTLINE_COLOR["light"]))
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
        """稳定态下按 has_shadow 应用投影，否则清掉旧效果。

        Note:
            显隐动画期间 _anim 非空，此时 opacity effect 归动画持有，
            本方法直接返回；动画结束后由 _on_anim_finished 回调恢复。
        """
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
        """用 opacity 过渡播放角标显隐。

        Args:
            show: True 为淡入、False 为淡出。

        Note:
            先 stop_tween 抢占 _anim 通道，避免连续切换时旧动画回调
            把可见性写回旧值；全程保持 setVisible(True)，结束后才定稿。
        """
        stop_tween(self, "_anim")
        effect = QGraphicsOpacityEffect(self._badge)
        self._badge.setGraphicsEffect(effect)
        effect.setOpacity(0.0 if show else 1.0)
        self._badge.setVisible(True)
        tween_property(
            effect,
            "_anim",
            b"opacity",
            1.0 if show else 0.0,
            owner=self,
            duration=ANIM_DURATION,
            on_finished=lambda: self._on_anim_finished(show),
        )

    def _on_anim_finished(self, show: bool):
        """显隐动画收尾：定稿可见性并恢复稳定态效果。

        Args:
            show: 本次动画的目标可见状态。
        """
        self._anim = None
        self._badge.setVisible(show)
        self._apply_badge_effect()

    # ---- wrapped widget ----

    def set_widget(self, widget: QWidget | None):
        """替换被包裹的内容 widget。

        Args:
            widget: 新的内容 widget；None 表示只移除旧内容。

        Note:
            旧 widget 从布局移除并脱离父级但不销毁，交由调用方管理生命周期；
            传入同一对象时直接返回，避免无意义的重排。
        """
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

    def widget(self) -> QWidget | None:
        """返回当前被包裹的内容 widget。

        Returns:
            当前内容 widget；未设置时为 None。
        """
        return self._widget

    # ---- setters ----

    def set_content(self, content: str):
        """更新角标文本并重算形态。

        Args:
            content: 新文本；空串 → 圆点，单字符 → 正方形，多字符 → 圆角矩形。
        """
        self._content = str(content)
        self._label.setText(self._content)
        self._apply_styles()

    def content(self) -> str:
        """返回当前角标文本。

        Returns:
            当前文本；构造时已统一转成 str。
        """
        return self._content

    def set_color(self, color: str):
        """切换语义色并重算配色。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        """切换视觉变体并重算配色。

        Args:
            variant: 变体名。
        """
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        """切换尺寸档位并同步角标字号。

        Args:
            size: 档位名；不在 BADGE_SIZES 中时直接忽略本次调用。
        """
        if size not in BADGE_SIZES:
            return
        self._size = size
        self._label.set_size(BADGE_SIZES[size]["text_size"])
        self._apply_styles()

    def set_shape(self, shape: str):
        """切换角标形状并重算几何。

        Args:
            shape: 形状名；circle 走 45° 对角线贴合，rectangle 走边缘锚点。
        """
        self._shape = shape
        self._update_badge_geometry()

    def set_placement(self, placement: str):
        """切换角标位置并重算几何。

        Args:
            placement: 位置名，如 top-right / bottom-left。
        """
        self._placement = placement
        self._update_badge_geometry()

    def set_show_outline(self, show: bool):
        """切换是否绘制宿主背景色描边。

        Args:
            show: False 时连 faded 变体的边框也一并去掉。
        """
        self._show_outline = bool(show)
        self._apply_styles()

    def set_invisible(self, invisible: bool):
        """切换角标显隐，按配置决定直接切换还是播动画。

        Args:
            invisible: True 表示隐藏角标。

        Note:
            状态未变时直接返回；禁用动画时先抢占 _anim 通道再直接 setVisible，
            避免残留动画回调把可见性写回旧值。
        """
        invisible = bool(invisible)
        if invisible == self._is_invisible:
            return
        self._is_invisible = invisible
        if self._disable_animation:
            stop_tween(self, "_anim")
            self._badge.setVisible(not invisible)
            self._apply_badge_effect()
        else:
            self._animate_visibility(not invisible)

    def is_invisible(self) -> bool:
        """返回角标当前是否处于隐藏状态。

        Returns:
            _is_invisible 的当前值。
        """
        return self._is_invisible

    def set_disable_animation(self, disabled: bool):
        """切换显隐过渡开关。

        Args:
            disabled: True 表示后续显隐直接切换、不播 opacity 动画。
        """
        self._disable_animation = bool(disabled)

    # ---- theme ----

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 的注册状态。

        Args:
            theme: 主题名，或 auto 表示跟随全局主题。

        Note:
            从 auto 切回固定主题时先 unregister，避免后续广播覆盖设定。
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
        self._label.set_theme(self._theme)
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._label.set_theme(theme)
        self._apply_styles()
