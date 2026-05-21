"""TabItem — Tabs 的单个标签按钮（用户可见 API）。

支持纯文本 / 文本+icon / 完全自定义 widget 三档模式。
"""

from typing import Optional, Union

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
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

from ...animation import paint_animated_check, tween_value, stop_tween
from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIUS, TABS_SIZES
from ...utils import load_svg_icon

from ._helpers import _resolve_selected_text, _resolve_unselected_text

# ============================================================
# TabItem: 单个 tab 按钮（QAbstractButton + 自绘文字）
# ============================================================


class TabItem(QAbstractButton):
    """单个 tab 标签 —— 三档插槽能力：

    1. **默认**：纯文本（与 HeroUI 默认一致）
       ``TabItem("Photos")``

    2. **icon + 文本**：左/右图标，颜色随选中态/主题自动着色
       ``TabItem("Photos", start_icon="heroicons--photo-solid", end_icon=...)``
       icon 支持内置 heroicons 名（不含 .svg 后缀）或外部 SVG 路径，
       由 ``hero_side_ui.utils.icon_utils.load_svg_icon`` 加载与着色。

    3. **完全自定义**：直接传 widget 作为标签内容
       ``TabItem(custom=my_widget)`` —— TabItem 把它作为子控件填满自己，
       不画文字/图标。hover-unselected/disabled 透明度仍然通过 QGraphicsOpacityEffect
       套在 custom widget 上。如果 custom widget 想跟随选中态，可监听
       ``TabItem.selected_changed(bool)`` 信号自行刷新。
    """

    HOVER_ANIM_DURATION = 150
    SELECT_ANIM_DURATION = 150

    # 选中态变化信号（暴露给 custom widget 监听）
    selected_changed = Signal(bool)

    def __init__(
        self,
        title: str = "",
        *,
        key: Optional[str] = None,
        start_icon=None,
        end_icon=None,
        custom: Optional[QWidget] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)
        # 让点击区域只覆盖文字 + padding，背景由 cursor 层负责
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._title = title
        self._key = key if key is not None else (title if title else f"tab_{id(self)}")
        self._is_hover = False
        self._is_disabled = False

        # ===== 插槽 =====
        # 档2：icon
        self._start_icon_src = start_icon
        self._end_icon_src = end_icon
        self._start_icon_pixmap: Optional[QPixmap] = None
        self._end_icon_pixmap: Optional[QPixmap] = None
        # 档3：custom widget
        self._custom: Optional[QWidget] = None
        self._custom_layout: Optional[QHBoxLayout] = None
        self._custom_opacity_effect = None

        # 由父 Tabs 注入
        self._variant = "solid"
        self._color = "default"
        self._size = "md"
        self._theme = "light"
        self._disable_animation = False

        self._unselected_color = QColor(HEROUI_COLORS["default"][500])
        self._selected_color = QColor("#000000")
        # 当前实际渲染色（动画驱动）—— 同时驱动 icon 着色
        self._current_text_color = QColor(self._unselected_color)
        # 透明度 0.0 ~ 1.0（hover-unselected -> 0.5）
        self._current_opacity = 1.0

        # 持有正在进行的动画实例，避免被 GC
        self._color_anim_runner = None
        self._opacity_anim_runner = None

        self._size_cfg = TABS_SIZES["md"]

        # 关键：监听 toggled 信号触发文字色动画。
        # 用 toggled 而非 override setChecked 的原因：QButtonGroup 在 exclusive 模式
        # 下会从 C++ 层直接调用 setChecked，跳过 Python 子类 override，导致动画不触发。
        # toggled 是 Qt 在 _checked 状态变化时无条件发出的信号，是唯一可靠的钩子。
        self.toggled.connect(self._on_toggled)
        self.toggled.connect(self.selected_changed)

        # 装载 custom widget（档3）
        if custom is not None:
            self.set_custom(custom)

        self._update_geometry()

    # -------------------- Public API --------------------

    def title(self) -> str:
        return self._title

    def set_title(self, title: str):
        self._title = title
        # custom 模式下 title 仅作为 key fallback，不影响视觉
        if self._custom is None:
            self._refresh_icons()
            self._update_geometry()
            self.update()

    def key(self) -> str:
        return self._key

    def set_key(self, key: str):
        self._key = key

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self.setEnabled(not self._is_disabled)
        if self._is_disabled:
            self.setCursor(Qt.ForbiddenCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        self._sync_custom_opacity()
        self.update()

    def is_disabled(self) -> bool:
        return self._is_disabled

    def set_start_icon(self, src):
        """设置起始图标。

        ``src`` 可以是 ``None`` / 内置图标名 / SVG 路径 / 已加载的 ``QPixmap``。
        """
        self._start_icon_src = src
        self._refresh_icons()
        self._update_geometry()
        self.update()

    def set_end_icon(self, src):
        """设置结束图标。"""
        self._end_icon_src = src
        self._refresh_icons()
        self._update_geometry()
        self.update()

    def has_icons(self) -> bool:
        return self._start_icon_src is not None or self._end_icon_src is not None

    # ----- 档3：custom widget 插槽 -----

    def set_custom(self, widget: Optional[QWidget]):
        """把自定义 widget 装进 TabItem，作为标签内容（档3）。

        传 ``None`` 取消 custom，回退到 text/icon 模式。
        """
        # 清掉旧的
        if self._custom is not None:
            self._custom.setParent(None)
            self._custom.deleteLater()
            self._custom = None
        if self._custom_layout is not None:
            # 清掉布局
            QWidget().setLayout(self._custom_layout)
            self._custom_layout = None
        self._custom_opacity_effect = None
        self.setGraphicsEffect(None)

        if widget is None:
            self._update_geometry()
            self.update()
            return

        self._custom = widget
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widget)
        self._custom_layout = layout

        # ---- palette 隔离 + 背景透明 ----
        # 1) palette: TabItem 是 QAbstractButton，子 QLabel 默认 foregroundRole=ButtonText，
        #    Qt Fusion 在按钮父链下会把 ButtonText 改成与按钮表面对比色（亮色按钮里=白）。
        #    递归把 custom widget 及其 QLabel 子代的 foregroundRole 切到 WindowText。
        # 2) 背景透明: TabItem 是 _TabList 的子 widget，cursor 也是 _TabList 的子 widget
        #    被 lower() 到底层。当 TabItem 装载子 widget 后，子 widget 的 native 渲染会
        #    盖住下方 cursor 区域（即使父 TabItem 自己 WA_TranslucentBackground=True）。
        #    必须给 widget 自身和无显式 background 的子 widget 设 WA_TranslucentBackground，
        #    让 native 渲染穿透到父级，cursor 才能透出（关键修复，否则暗色模式 cursor
        #    被 emoji/QLabel 等子 widget 区域整片盖住）。
        from PySide6.QtWidgets import QApplication, QLabel as _QLabel

        app_palette = QApplication.palette()
        widget.setPalette(app_palette)
        widget.setAttribute(Qt.WA_TranslucentBackground, True)
        widget.setAutoFillBackground(False)
        for child in widget.findChildren(QWidget):
            child.setPalette(app_palette)
            if isinstance(child, _QLabel):
                child.setForegroundRole(QPalette.WindowText)
            child.setAutoFillBackground(False)
            # 仅对"无显式 background stylesheet"的子 widget 设透明背景；
            # 设了 stylesheet background 的（如红点）保持原样让 stylesheet 渲染生效
            ss = child.styleSheet() or ""
            if "background" not in ss:
                child.setAttribute(Qt.WA_TranslucentBackground, True)

        # custom 模式不挂 QGraphicsOpacityEffect。
        # 原因：effect 会把整棵 widget 子树离屏渲染成位图，默认会用 palette.Window 色
        # 填充矩形 → 把下方 cursor 蓝底盖住（暗色模式下尤其明显）。
        # 折中：custom 模式下 hover-unselected 不做 50% 透明度变化（保持原样），
        # disabled 由 setEnabled(False) 让 Qt 自然变灰。这样跟"完全自定义"的语义
        # 也吻合 —— 用户想要 hover 反馈可监听 selected_changed 自管。
        self._custom_opacity_effect = None

        # 让 widget 不抢点击（点击仍然落到 TabItem 上）
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._update_geometry()
        self.update()

    def custom(self) -> Optional[QWidget]:
        return self._custom

    # -------------------- 由 Tabs 调用 --------------------

    def apply_style(
        self, *, variant, color, size, theme, disable_animation, full_width
    ):
        self._variant = variant
        self._color = color
        self._size = size
        self._theme = theme
        self._disable_animation = disable_animation
        self._size_cfg = TABS_SIZES[size]

        self._unselected_color = _resolve_unselected_text(theme)
        self._selected_color = _resolve_selected_text(variant, color, theme)

        # 立即跳转到目标颜色（apply_style 通常意味着批量样式变更，不打动画避免闪烁）
        target = self._selected_color if self.isChecked() else self._unselected_color
        stop_tween(self, "_color_anim_runner")
        self._current_text_color = QColor(target)

        # 颜色变了 → icon 也要重新着色
        self._refresh_icons()

        # full_width 时让按钮水平拉伸
        if full_width:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._update_geometry()
        self.update()

    # -------------------- 选中态切换（带动画） --------------------

    def set_checked_silent(self, checked: bool):
        """无动画地设置选中态（block toggled 信号 + 强制刷新色）。

        用于 Tabs 首次自动选中等场景，避免开屏闪一次淡入动画。
        """
        was = self.blockSignals(True)
        try:
            self.setChecked(checked)
        finally:
            self.blockSignals(was)
        # 同步颜色
        target = self._selected_color if checked else self._unselected_color
        stop_tween(self, "_color_anim_runner")
        self._current_text_color = QColor(target)
        self.update()

    def _on_toggled(self, checked: bool):
        """toggled 信号回调 —— 选中态变化时驱动文字色动画。

        这是处理选中态变化的**唯一**入口；无论是用户点击、QButtonGroup 排他切换、
        还是程序里 setChecked，都会经过此回调。
        """
        target = self._selected_color if checked else self._unselected_color
        if self._disable_animation:
            stop_tween(self, "_color_anim_runner")
            self._current_text_color = QColor(target)
            self._refresh_icons()
            self.update()
            return
        tween_value(
            self,
            "_color_anim_runner",
            QColor(self._current_text_color),
            QColor(target),
            self._on_color_step,
            duration=self.SELECT_ANIM_DURATION,
        )

    def _on_color_step(self, value):
        if isinstance(value, QColor):
            self._current_text_color = value
            # icon 跟随文字色
            self._refresh_icons()
            self.update()

    def _animate_opacity(self, target: float):
        if self._disable_animation:
            stop_tween(self, "_opacity_anim_runner")
            self._current_opacity = target
            self._sync_custom_opacity()
            self.update()
            return
        tween_value(
            self,
            "_opacity_anim_runner",
            float(self._current_opacity),
            float(target),
            self._on_opacity_step,
            duration=self.HOVER_ANIM_DURATION,
        )

    def _on_opacity_step(self, value):
        try:
            self._current_opacity = float(value)
        except Exception:
            return
        self._sync_custom_opacity()
        self.update()

    def _sync_custom_opacity(self):
        """custom 模式下，把 opacity 同步到 QGraphicsOpacityEffect 上。"""
        if self._custom_opacity_effect is None:
            return
        effective = self._current_opacity
        if self._is_disabled:
            effective = 0.3
        try:
            self._custom_opacity_effect.setOpacity(effective)
        except RuntimeError:
            self._custom_opacity_effect = None

    # -------------------- Hover --------------------

    def enterEvent(self, ev):
        self._is_hover = True
        if not self.isChecked() and not self._is_disabled:
            self._animate_opacity(0.5)
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._is_hover = False
        self._animate_opacity(1.0)
        super().leaveEvent(ev)

    # -------------------- Geometry --------------------

    def _icon_size_px(self) -> int:
        """icon 像素尺寸 = 文字行高 ≈ font_size + 2"""
        return self._size_cfg["tab_font_size"] + 2

    def _icon_gap(self) -> int:
        """icon 与文字之间间距。"""
        return 6

    def _refresh_icons(self):
        """根据当前文字色重新加载 + 着色 start/end icon。"""
        color = self._current_text_color
        size = self._icon_size_px()

        def _to_pixmap(src) -> Optional[QPixmap]:
            if src is None:
                return None
            if isinstance(src, QPixmap):
                return src
            if isinstance(src, str):
                return load_svg_icon(src, size=size, color=color)
            return None

        self._start_icon_pixmap = _to_pixmap(self._start_icon_src)
        self._end_icon_pixmap = _to_pixmap(self._end_icon_src)

    def _update_geometry(self):
        cfg = self._size_cfg
        from ...core import make_text_qfont

        font = make_text_qfont(cfg["tab_font_size"], "medium")
        self.setFont(font)

        h = cfg["tab_height"]
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)

        # custom 模式：宽度由 child widget sizeHint 决定
        if self._custom is not None:
            ch = self._custom.sizeHint()
            w = max(ch.width() + 2 * cfg["tab_padding_x"], cfg["tab_min_width"])
            self.setMinimumWidth(w)
            return

        # text + icon 模式
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._title) if self._title else 0
        icon_w = 0
        gap = self._icon_gap()
        icon_size = self._icon_size_px()
        if self._start_icon_pixmap is not None:
            icon_w += icon_size + (gap if self._title else 0)
        if self._end_icon_pixmap is not None:
            icon_w += icon_size + (
                gap if (self._title or self._start_icon_pixmap) else 0
            )
        w = max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"])
        self.setMinimumWidth(w)

    def sizeHint(self) -> QSize:
        cfg = self._size_cfg
        if self._custom is not None:
            ch = self._custom.sizeHint()
            return QSize(
                max(ch.width() + 2 * cfg["tab_padding_x"], cfg["tab_min_width"]),
                cfg["tab_height"],
            )
        from ...core import make_text_qfont

        font = make_text_qfont(cfg["tab_font_size"], "medium")
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._title) if self._title else 0
        icon_w = 0
        gap = self._icon_gap()
        icon_size = self._icon_size_px()
        if self._start_icon_pixmap is not None:
            icon_w += icon_size + (gap if self._title else 0)
        if self._end_icon_pixmap is not None:
            icon_w += icon_size + (
                gap if (self._title or self._start_icon_pixmap) else 0
            )
        return QSize(
            max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"]),
            cfg["tab_height"],
        )

    # -------------------- Paint --------------------

    def paintEvent(self, ev):
        # custom 模式：交给子 widget 自己渲染（QGraphicsOpacityEffect 套整体透明度）
        if self._custom is not None:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # 透明度 (hover-unselected 0.5; disabled 0.3)
        opacity = self._current_opacity
        if self._is_disabled:
            opacity = 0.3
        p.setOpacity(opacity)

        font = self.font()
        p.setFont(font)
        fm = QFontMetrics(font)

        gap = self._icon_gap()
        icon_size = self._icon_size_px()
        rect = self.rect()

        # 总内容宽度 → 水平居中起点
        text_w = fm.horizontalAdvance(self._title) if self._title else 0
        total_w = text_w
        if self._start_icon_pixmap is not None:
            total_w += icon_size + (gap if self._title else 0)
        if self._end_icon_pixmap is not None:
            total_w += icon_size + (
                gap if (self._title or self._start_icon_pixmap) else 0
            )

        # 严格垂直居中：所有元素都画在同一个高度为 rect.height() 的"行盒子"里，
        # 文字用 AlignVCenter，icon 用 (rect.height - icon_size)/2 的偏移。
        # 这样 icon 中心 == 行盒子中心 == 文字 bounding rect 中心，
        # 不会出现"看起来贴底"的问题。
        x = (rect.width() - total_w) / 2
        h = rect.height()

        # start icon
        if self._start_icon_pixmap is not None:
            iy = (h - icon_size) / 2
            p.drawPixmap(
                int(round(x)),
                int(round(iy)),
                icon_size,
                icon_size,
                self._start_icon_pixmap,
            )
            x += icon_size + (gap if self._title else 0)

        # text — 用 capHeight 做"光学居中"。
        # Qt 的 AlignVCenter 是按 ascent+descent 整高居中，但 ascent 包含了字符顶
        # 上方的空白，descent 仅含字符底下沿，二者不对称 → 文字看起来偏下。
        # 正确的视觉居中：让 cap-height 的中点对齐 rect 中心：
        #   baseline = (h + capHeight) / 2
        # 这样大写字母 / 中文字符的几何中心对齐 icon 几何中心，视觉一致。
        if self._title:
            p.setPen(QPen(self._current_text_color))
            cap = fm.capHeight() or fm.ascent() - fm.descent()
            baseline = (h + cap) / 2.0
            p.drawText(int(round(x)), int(round(baseline)), self._title)
            x += text_w + (gap if self._end_icon_pixmap is not None else 0)

        # end icon
        if self._end_icon_pixmap is not None:
            iy = (h - icon_size) / 2
            p.drawPixmap(
                int(round(x)),
                int(round(iy)),
                icon_size,
                icon_size,
                self._end_icon_pixmap,
            )

        p.end()
