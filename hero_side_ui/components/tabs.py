"""
HeroSideUI Tabs Component
基于 HeroUI v2 设计风格 完整复刻

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/tabs.ts

结构:
    Tabs (QWidget)
        ├── _wrapper_layout: tabWrapper（top/bottom/start/end 四种布局方向）
        │   ├── TabList (QFrame, paintEvent 自绘背景/边框/圆角)
        │   │   ├── _CursorWidget (QPainter 自绘填充矩形 / 下划线)
        │   │   └── tab_layout (QHBoxLayout / QVBoxLayout)
        │   │       └── TabItem * N
        │   └── QStackedWidget (panels)

特性:
    - 4 种 variant: solid / light / underlined / bordered
    - 6 种 color: default / primary / secondary / success / warning / danger
    - 3 种 size: sm (h28) / md (h32) / lg (h36)
    - 5 种 radius: none / sm / md / lg / full
    - 4 种 placement: top / bottom / start / end
    - light/dark 双主题
    - full_width / is_disabled / disable_animation
    - cursor 250ms ease-out 几何动画（首次选中不动画）
    - tab 未选中 hover -> 50% 透明（HeroUI hover-unselected -> opacity-disabled）
    - selected 文字色 150ms 颜色平滑过渡
    - selection_changed(int, str) 信号: 触发参数 (index, key)
"""

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QBoxLayout,
    QStackedWidget,
    QSizePolicy,
    QButtonGroup,
    QAbstractButton,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QRect,
    QRectF,
    QSize,
    QPoint,
    Property,
    QEvent,
    QTimer,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QFontMetrics,
    QPainterPath,
    QBrush,
    QPixmap,
    QPalette,
)

from typing import Optional, List, Union

from ..themes import HEROUI_COLORS, RADIUS, TABS_SIZES, FONT_FAMILY
from ..utils import load_svg_icon
from ..animation import tween_value, stop_tween, tween_geometry
from ..core import ThemeProvider


VALID_VARIANTS = ("solid", "bordered", "light", "underlined")
VALID_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VALID_SIZES = ("sm", "md", "lg")
VALID_RADIUS = ("none", "sm", "md", "lg", "full")
VALID_PLACEMENTS = ("top", "bottom", "start", "end")
VALID_THEMES = ("light", "dark")


# ============================================================
# 工具：选中态文字色 / 未选中文字色 / cursor 填充色 解析
# ============================================================

def _opt(d: dict, *keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def _resolve_unselected_text(theme: str) -> QColor:
    """未选中 tab 文字色: HeroUI text-default-500"""
    return QColor(HEROUI_COLORS["default"][500])


def _resolve_selected_text(variant: str, color: str, theme: str) -> QColor:
    """选中态 tabContent 颜色:
    - solid/bordered/light: text-{color}-foreground 即对色的 contrast 文字色
        * default: light=#000 / dark=#fff
        * primary/secondary/success/danger: 对比白
        * warning: 对比黑
    - underlined: text-{color}（即色的主色 500）
        * default: light=#000 / dark=#fff（即 foreground）
    """
    if variant == "underlined":
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(HEROUI_COLORS[color][500])
    # solid/bordered/light: foreground 文字
    if color == "default":
        # default 选中态: foreground (light=黑, dark=白)
        return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
    if color == "warning":
        return QColor("#000000")
    return QColor("#FFFFFF")


def _resolve_cursor_fill(variant: str, color: str, theme: str) -> Optional[QColor]:
    """cursor 填充色（None 表示这个 variant 下不画填充 cursor）。"""
    if variant == "underlined":
        # underlined 下 cursor 是底边线条，不画矩形填充
        # 这里返回线条颜色
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(HEROUI_COLORS[color][500])
    # solid / bordered / light: 矩形填充 cursor
    if color == "default":
        # bg-background 亮色 = 白；dark:bg-default 暗色 = default-100/200
        return QColor("#FFFFFF") if theme == "light" else QColor(HEROUI_COLORS["default"][700])
    return QColor(HEROUI_COLORS[color][500])


def _resolve_list_bg(variant: str, theme: str) -> Optional[QColor]:
    """tabList 背景色。"""
    if variant in ("light", "underlined", "bordered"):
        return None  # 透明
    # solid: bg-default-100 / dark:bg-default-50
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][100])
    # 暗色 solid 背景：稍亮
    c = QColor(HEROUI_COLORS["default"][800])
    return c


def _resolve_list_border(variant: str, theme: str) -> Optional[QColor]:
    """tabList 边框色（仅 bordered 变体）。"""
    if variant != "bordered":
        return None
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][200])
    return QColor(HEROUI_COLORS["default"][700])


def _resolve_radius_px(radius: str, size: str, height: int) -> tuple:
    """返回 (list_radius, tab_radius) 像素值。
    映射 HeroUI v2 tabs.ts:
        none -> (0, 0)
        sm   -> (medium=10, small=6)  我们项目 RADIUS sm=4 md=8 lg=14
        md   -> (medium, small)
        lg   -> (large, medium)
        full -> (height/2, height/2)
    我们映射:
        sm/md -> (8, 4)
        lg    -> (14, 8)
        none  -> (0, 0)
        full  -> (height/2, height/2)
    """
    if radius == "none":
        return (0, 0)
    if radius == "full":
        r = max(height // 2, 4)
        return (r, r)
    if radius == "sm":
        return (8, 4)
    if radius == "md":
        return (8, 4)
    if radius == "lg":
        return (14, 8)
    return (8, 4)


# ============================================================
# CursorWidget: 选中指示器（矩形填充 / 下划线）
# ============================================================


class _CursorWidget(QWidget):
    """绝对定位的指示器层。父是 TabList。

    根据 variant 绘制不同形态:
      - solid/bordered/light: 整块圆角矩形 + (color=default 时画 shadow-small)
      - underlined: 底部 2px 80% 宽度的水平线（垂直方向布局时改为右/左侧 2px 线）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._variant = "solid"
        self._color = "default"
        self._theme = "light"
        self._radius_px = 8
        self._placement = "top"
        self._underline_h = 2
        self._underline_ratio = 0.8

    def configure(self, *, variant=None, color=None, theme=None,
                  radius_px=None, placement=None,
                  underline_h=None, underline_ratio=None):
        if variant is not None: self._variant = variant
        if color is not None: self._color = color
        if theme is not None: self._theme = theme
        if radius_px is not None: self._radius_px = radius_px
        if placement is not None: self._placement = placement
        if underline_h is not None: self._underline_h = underline_h
        if underline_ratio is not None: self._underline_ratio = underline_ratio
        self.update()

    def paintEvent(self, ev):
        if self.width() <= 0 or self.height() <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self._variant == "underlined":
            self._paint_underline(p)
        else:
            self._paint_filled(p)
        p.end()

    def _paint_filled(self, p: QPainter):
        rect = QRectF(0, 0, self.width(), self.height())
        fill = _resolve_cursor_fill(self._variant, self._color, self._theme)
        if fill is None:
            return

        # default 色（亮色 = 白）画一个 shadow-small：底部一层柔和阴影
        if self._color == "default":
            shadow = QColor(0, 0, 0, 26 if self._theme == "light" else 0)
            if shadow.alpha() > 0:
                # 简化版 shadow-small: 向下 2px、blur 3px 的轻阴影
                for i in range(3):
                    a = int(shadow.alpha() * (1 - i / 3))
                    if a <= 0:
                        continue
                    sc = QColor(shadow.red(), shadow.green(), shadow.blue(), a)
                    sr = rect.adjusted(-i, -i + 1, i, i + 1)
                    path = QPainterPath()
                    path.addRoundedRect(sr, self._radius_px, self._radius_px)
                    p.fillPath(path, sc)

        path = QPainterPath()
        path.addRoundedRect(rect, self._radius_px, self._radius_px)
        p.fillPath(path, fill)

    def _paint_underline(self, p: QPainter):
        line_color = _resolve_cursor_fill(self._variant, self._color, self._theme)
        if line_color is None:
            return
        h = self._underline_h
        ratio = self._underline_ratio
        if self._placement in ("start", "end"):
            # 垂直方向：在 tab 的右边或左边画一条竖线
            line_w = h
            line_h = self.height() * ratio
            x = (self.width() - line_w) / 2 if self._placement == "top" else 0
            if self._placement == "start":
                # 列表在左，文本在右；下划线画在右边缘
                x = self.width() - line_w
            else:  # end
                x = 0
            y = (self.height() - line_h) / 2
            p.fillRect(QRectF(x, y, line_w, line_h), line_color)
        else:
            # 水平方向：底部
            line_w = self.width() * ratio
            x = (self.width() - line_w) / 2
            if self._placement == "bottom":
                # bottom 布局下 tabList 在 panel 下方，cursor 仍画在 tab 底部
                y = self.height() - h
            else:
                y = self.height() - h
            p.fillRect(QRectF(x, y, line_w, h), line_color)


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

    def apply_style(self, *, variant, color, size, theme,
                    disable_animation, full_width):
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
            self, "_color_anim_runner",
            QColor(self._current_text_color), QColor(target),
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
            self, "_opacity_anim_runner",
            float(self._current_opacity), float(target),
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
        font = QFont(FONT_FAMILY)
        font.setPixelSize(cfg["tab_font_size"])
        font.setWeight(QFont.Medium)
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
            icon_w += icon_size + (gap if (self._title or self._start_icon_pixmap) else 0)
        w = max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"])
        self.setMinimumWidth(w)

    def sizeHint(self) -> QSize:
        cfg = self._size_cfg
        if self._custom is not None:
            ch = self._custom.sizeHint()
            return QSize(
                max(ch.width() + 2 * cfg["tab_padding_x"], cfg["tab_min_width"]),
                cfg["tab_height"]
            )
        font = QFont(FONT_FAMILY)
        font.setPixelSize(cfg["tab_font_size"])
        font.setWeight(QFont.Medium)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._title) if self._title else 0
        icon_w = 0
        gap = self._icon_gap()
        icon_size = self._icon_size_px()
        if self._start_icon_pixmap is not None:
            icon_w += icon_size + (gap if self._title else 0)
        if self._end_icon_pixmap is not None:
            icon_w += icon_size + (gap if (self._title or self._start_icon_pixmap) else 0)
        return QSize(
            max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"]),
            cfg["tab_height"]
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
            total_w += icon_size + (gap if (self._title or self._start_icon_pixmap) else 0)

        # 严格垂直居中：所有元素都画在同一个高度为 rect.height() 的"行盒子"里，
        # 文字用 AlignVCenter，icon 用 (rect.height - icon_size)/2 的偏移。
        # 这样 icon 中心 == 行盒子中心 == 文字 bounding rect 中心，
        # 不会出现"看起来贴底"的问题。
        x = (rect.width() - total_w) / 2
        h = rect.height()

        # start icon
        if self._start_icon_pixmap is not None:
            iy = (h - icon_size) / 2
            p.drawPixmap(int(round(x)), int(round(iy)),
                         icon_size, icon_size, self._start_icon_pixmap)
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
            p.drawPixmap(int(round(x)), int(round(iy)),
                         icon_size, icon_size, self._end_icon_pixmap)

        p.end()


# ============================================================
# TabList: 容器（自绘背景 + 边框 + 圆角）
# ============================================================


class _TabList(QFrame):
    """tabList 容器，内部布局放 cursor + tabs。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._variant = "solid"
        self._theme = "light"
        self._radius_px = 8
        self._border_width = 0
        self._bg = None
        self._border = None
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def configure(self, *, variant=None, theme=None, radius_px=None, border_width=None):
        if variant is not None: self._variant = variant
        if theme is not None: self._theme = theme
        if radius_px is not None: self._radius_px = radius_px
        if border_width is not None: self._border_width = border_width
        self._bg = _resolve_list_bg(self._variant, self._theme)
        self._border = _resolve_list_border(self._variant, self._theme)
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        if self._radius_px > 0:
            path.addRoundedRect(rect, self._radius_px, self._radius_px)
        else:
            path.addRect(rect)

        if self._bg is not None:
            p.fillPath(path, self._bg)

        if self._border is not None and self._border_width > 0:
            pen = QPen(self._border)
            pen.setWidth(self._border_width)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

            # bordered 还有 shadow-xs；这里简化为不画
        p.end()


# ============================================================
# Tabs: 主组件
# ============================================================


class Tabs(QWidget):
    """HeroUI Tabs 组件 —— 完整复刻。

    选中变更信号: selection_changed(int index, str key)
    """

    CURSOR_ANIM_DURATION = 250

    selection_changed = Signal(int, str)

    def __init__(
        self,
        items: Optional[List[Union[str, tuple, dict]]] = None,
        *,
        variant: str = "solid",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
        placement: str = "top",
        theme: str = "auto",
        full_width: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # 校验
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        if placement not in VALID_PLACEMENTS:
            raise ValueError(f"placement must be one of {VALID_PLACEMENTS}")
        if theme not in ("auto", *VALID_THEMES):
            raise ValueError(f"theme must be one of ('auto', {VALID_THEMES})")

        self._variant = variant
        self._color = color
        self._size = size
        # underlined 强制 rounded-none（compoundSlots）
        if variant == "underlined":
            self._radius = "none"
        else:
            self._radius = radius if radius is not None else "md"
        self._placement = placement
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._full_width = bool(full_width)
        self._is_disabled = bool(is_disabled)
        self._disable_animation = bool(disable_animation)

        self._tabs: List[TabItem] = []
        self._panels: List[QWidget] = []
        self._current_index = -1
        self._cursor_initialized = False

        # ----- 构建 UI -----
        # 外层 wrapper (用 QBoxLayout, 方向由 placement 决定)
        self._wrapper_layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        self._wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._wrapper_layout.setSpacing(0)

        # tabList
        self._list = _TabList(self)
        self._list_layout = QHBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(TABS_SIZES[size]["list_gap"])

        # cursor 在 list 上层，但是 z 序在所有 tab 之下
        self._cursor = _CursorWidget(self._list)
        self._cursor.lower()

        # ButtonGroup 处理互斥
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self._on_id_clicked)

        # panels
        self._stack = QStackedWidget(self)

        # 装配
        self._wrapper_layout.addWidget(self._list)
        self._wrapper_layout.addWidget(self._stack)

        # 应用 placement
        self._apply_placement()
        self._apply_styles()
        self._apply_disabled_state()

        # 添加初始 items
        if items:
            for it in items:
                if isinstance(it, str):
                    self.add_tab(it)
                elif isinstance(it, tuple):
                    # (title, content) 或 (title, content, key)
                    if len(it) == 2:
                        self.add_tab(it[0], it[1])
                    elif len(it) == 3:
                        self.add_tab(it[0], it[1], key=it[2])
                elif isinstance(it, dict):
                    self.add_tab(
                        it.get("title", ""),
                        it.get("content"),
                        key=it.get("key"),
                        disabled=it.get("disabled", False),
                        start_icon=it.get("start_icon"),
                        end_icon=it.get("end_icon"),
                        custom=it.get("custom"),
                    )

        # 自动选中第一个可用 tab
        QTimer.singleShot(0, self._auto_select_first)

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Public API
    # ============================================================

    def add_tab(self, title: str = "", content: Optional[QWidget] = None,
                *, key: Optional[str] = None, disabled: bool = False,
                start_icon=None, end_icon=None,
                custom: Optional[QWidget] = None) -> TabItem:
        """添加一个 tab。

        三档插槽：
          1. 纯文本: ``add_tab("Photos")``
          2. icon + 文本: ``add_tab("Photos", start_icon="heroicons--photo-solid")``
          3. 完全自定义 tab 标签: ``add_tab(custom=my_widget)``（``title`` 仅作 key fallback）

        ``content`` 始终是 panel 内容（任意 QWidget），独立于 tab 标签外观。
        """
        tab = TabItem(
            title,
            key=key,
            start_icon=start_icon,
            end_icon=end_icon,
            custom=custom,
            parent=self._list,
        )
        if disabled:
            tab.set_disabled(True)
        # 加入 group + layout
        idx = len(self._tabs)
        self._group.addButton(tab, idx)
        self._list_layout.addWidget(tab)
        self._tabs.append(tab)

        # 内容面板：用户没传则给一个空 QWidget
        panel = content if content is not None else QWidget()
        self._panels.append(panel)
        self._stack.addWidget(panel)

        tab.apply_style(
            variant=self._variant,
            color=self._color,
            size=self._size,
            theme=self._theme,
            disable_animation=self._disable_animation,
            full_width=self._full_width,
        )
        return tab

    def remove_tab(self, index: int):
        if not 0 <= index < len(self._tabs):
            return
        tab = self._tabs.pop(index)
        panel = self._panels.pop(index)
        self._group.removeButton(tab)
        self._list_layout.removeWidget(tab)
        tab.setParent(None)
        tab.deleteLater()
        self._stack.removeWidget(panel)
        # 重新映射 button id
        for i, t in enumerate(self._tabs):
            self._group.setId(t, i)
        if self._current_index >= len(self._tabs):
            self._current_index = len(self._tabs) - 1
        if self._current_index >= 0:
            self.set_selected(self._current_index, animate=False)

    def clear(self):
        while self._tabs:
            self.remove_tab(0)
        self._current_index = -1

    def count(self) -> int:
        return len(self._tabs)

    def tab_at(self, index: int) -> Optional[TabItem]:
        if 0 <= index < len(self._tabs):
            return self._tabs[index]
        return None

    def panel_at(self, index: int) -> Optional[QWidget]:
        if 0 <= index < len(self._panels):
            return self._panels[index]
        return None

    def current_index(self) -> int:
        return self._current_index

    def current_key(self) -> Optional[str]:
        if 0 <= self._current_index < len(self._tabs):
            return self._tabs[self._current_index].key()
        return None

    def set_selected(self, index_or_key: Union[int, str], *, animate: bool = True):
        """切换到指定 tab。"""
        if isinstance(index_or_key, str):
            index = next((i for i, t in enumerate(self._tabs) if t.key() == index_or_key), -1)
        else:
            index = int(index_or_key)
        if not 0 <= index < len(self._tabs):
            return
        target = self._tabs[index]
        if target.is_disabled():
            return
        prev = self._current_index
        self._current_index = index

        do_animate = animate and not self._disable_animation

        # 更新所有 tab 的选中态。两种路径：
        # - 带动画：用 setChecked，QButtonGroup 排他自动反选其他 tab，toggled 信号驱动文字色动画
        # - 不带动画：用 set_checked_silent，block toggled 信号 + 直接刷颜色，避免开屏闪
        if do_animate:
            for i, t in enumerate(self._tabs):
                checked = (i == index)
                if t.isChecked() != checked:
                    t.setChecked(checked)
        else:
            for i, t in enumerate(self._tabs):
                checked = (i == index)
                if t.isChecked() != checked:
                    t.set_checked_silent(checked)

        self._stack.setCurrentIndex(index)
        # 移动 cursor
        self._move_cursor_to(index, animate=animate and self._cursor_initialized)
        if not self._cursor_initialized:
            self._cursor_initialized = True
        if prev != index:
            self.selection_changed.emit(index, target.key())

    # -------- 动态 setter --------

    # -------- 动态 setter --------

    def _validate(self, name: str, value: str, valid):
        if value not in valid:
            raise ValueError(f"{name} must be one of {tuple(valid)}")

    def _reposition_cursor_async(self):
        QTimer.singleShot(
            0, lambda: self._move_cursor_to(self._current_index, animate=False)
        )

    def set_variant(self, variant: str):
        self._validate("variant", variant, VALID_VARIANTS)
        self._variant = variant
        if variant == "underlined":
            self._radius = "none"
        self._apply_styles()
        self._move_cursor_to(self._current_index, animate=False)

    def set_color(self, color: str):
        self._validate("color", color, VALID_COLORS)
        self._color = color
        self._apply_styles()

    def set_size(self, size: str):
        self._validate("size", size, VALID_SIZES)
        self._size = size
        self._list_layout.setSpacing(TABS_SIZES[size]["list_gap"])
        self._apply_styles()
        self._reposition_cursor_async()

    def set_radius(self, radius: str):
        self._validate("radius", radius, VALID_RADIUS)
        if self._variant == "underlined":
            radius = "none"
        self._radius = radius
        self._apply_styles()
        self._reposition_cursor_async()

    def set_placement(self, placement: str):
        self._validate("placement", placement, VALID_PLACEMENTS)
        self._placement = placement
        self._apply_placement()
        self._apply_styles()
        self._reposition_cursor_async()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            self._validate("theme", theme, VALID_THEMES)
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_full_width(self, full: bool):
        self._full_width = bool(full)
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self._apply_disabled_state()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = bool(disable)
        for t in self._tabs:
            t._disable_animation = self._disable_animation

    def _apply_placement(self):
        """根据 placement 重新组合 wrapper layout 方向。"""
        # tabList 内部方向
        # top/bottom -> 水平 list；start/end -> 垂直 list
        self._list_layout.setDirection(
            QBoxLayout.LeftToRight if self._placement in ("top", "bottom")
            else QBoxLayout.TopToBottom
        )
        # wrapper 方向：top -> TopToBottom; bottom -> BottomToTop
        # start -> LeftToRight; end -> RightToLeft
        mapping = {
            "top": QBoxLayout.TopToBottom,
            "bottom": QBoxLayout.BottomToTop,
            "start": QBoxLayout.LeftToRight,
            "end": QBoxLayout.RightToLeft,
        }
        self._wrapper_layout.setDirection(mapping[self._placement])

        # cursor 重新刷
        self._cursor.configure(placement=self._placement)

    def _apply_styles(self):
        """根据当前所有属性应用样式。"""
        cfg = TABS_SIZES[self._size]

        # 估算 tabList 高度，用于 full radius
        if self._placement in ("top", "bottom"):
            est_h = cfg["tab_height"] + 2 * cfg["list_padding"]
        else:
            est_h = cfg["tab_height"]

        list_radius_px, tab_radius_px = _resolve_radius_px(
            self._radius, self._size, est_h
        )
        # underlined 强制无圆角（compoundSlots）
        if self._variant == "underlined":
            list_radius_px = 0
            tab_radius_px = 0

        # 配置 list
        border_w = cfg["border_width"] if self._variant == "bordered" else 0
        self._list.configure(
            variant=self._variant,
            theme=self._theme,
            radius_px=list_radius_px,
            border_width=border_w,
        )
        list_pad = cfg["list_padding"]
        # underlined / light / bordered 不需要 padding（保持紧凑）
        # solid 才需要内 padding 露出底色
        if self._variant in ("solid",):
            self._list_layout.setContentsMargins(list_pad, list_pad, list_pad, list_pad)
        elif self._variant == "bordered":
            self._list_layout.setContentsMargins(list_pad, list_pad, list_pad, list_pad)
        else:
            self._list_layout.setContentsMargins(0, 0, 0, 0)

        # 配置 cursor
        self._cursor.configure(
            variant=self._variant,
            color=self._color,
            theme=self._theme,
            radius_px=tab_radius_px,
            placement=self._placement,
            underline_h=cfg["underline_h"],
            underline_ratio=cfg["underline_ratio"],
        )

        # 应用到每个 tab
        for t in self._tabs:
            t.apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                theme=self._theme,
                disable_animation=self._disable_animation,
                full_width=self._full_width,
            )

        # full_width
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            if self._placement in ("top", "bottom"):
                self._list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                self._list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self._list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # panel padding
        if self._placement in ("start", "end"):
            self._stack.setContentsMargins(
                cfg["panel_padding_h_side"], cfg["panel_padding_v_side"],
                cfg["panel_padding_h_side"], cfg["panel_padding_v_side"]
            )
        else:
            self._stack.setContentsMargins(
                cfg["panel_padding_h"], cfg["panel_padding_v"],
                cfg["panel_padding_h"], cfg["panel_padding_v"]
            )

        # underlined 时 list_layout spacing 略增
        self._list_layout.setSpacing(cfg["list_gap"])

        self._list.update()

    def _apply_disabled_state(self):
        """tabList 整体禁用 -> 50% 透明 + 屏蔽点击。"""
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        if self._is_disabled:
            eff = QGraphicsOpacityEffect(self._list)
            eff.setOpacity(0.5)
            self._list.setGraphicsEffect(eff)
            self._list.setEnabled(False)
        else:
            self._list.setGraphicsEffect(None)
            self._list.setEnabled(True)

    def _on_id_clicked(self, idx: int):
        if not 0 <= idx < len(self._tabs):
            return
        if self._tabs[idx].is_disabled():
            return
        if idx == self._current_index:
            return
        self.set_selected(idx)

    def _auto_select_first(self):
        if self._current_index == -1 and self._tabs:
            for i, t in enumerate(self._tabs):
                if not t.is_disabled():
                    self.set_selected(i, animate=False)
                    break

    def _move_cursor_to(self, index: int, *, animate: bool):
        if not 0 <= index < len(self._tabs):
            self._cursor.hide()
            return
        target_geom = QRect(self._tabs[index].geometry())

        # 首次 / disable_animation / cursor 还没显示过 —— 直接到位
        if not animate or self._disable_animation or not self._cursor.isVisible():
            stop_tween(self._cursor, "_cursor_anim_runner")
            self._cursor.setGeometry(target_geom)
            self._cursor.show()
            self._cursor.lower()
            return

        tween_geometry(
            self._cursor, "_cursor_anim_runner", target_geom,
            duration=self.CURSOR_ANIM_DURATION,
        )
        self._cursor.lower()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # 让 cursor 紧跟当前 tab 的几何
        self._reposition_cursor_async()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._reposition_cursor_async()


__all__ = ["Tabs", "TabItem"]
