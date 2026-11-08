"""TabItem — Tabs 的单个标签按钮（用户可见 API）。

支持纯文本 / 文本+icon / 完全自定义 widget 三档模式。
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from ...animation import stop_tween, tween_value
from ...themes import HEROUI_COLORS, TABS_SIZES
from ...utils import load_svg_icon
from ._helpers import _resolve_selected_text, _resolve_unselected_text

# ============================================================
# TabItem: 单个 tab 按钮（QAbstractButton + 自绘文字）
# ============================================================


class TabItem(QAbstractButton):
    """单个 tab 标签，三档插槽：纯文本 / icon+文本 / custom widget。

    Note:
        custom 模式不画文字图标，选中态由 selected_changed 信号自理。
    """

    HOVER_ANIM_DURATION = 150
    SELECT_ANIM_DURATION = 150

    # 选中态变化信号（暴露给 custom widget 监听）
    selected_changed = Signal(bool)

    def __init__(
        self,
        title: str = "",
        *,
        key: str | None = None,
        start_icon=None,
        end_icon=None,
        custom: QWidget | None = None,
        parent=None,
    ):
        """创建标签按钮并初始化三档插槽与默认样式。

        Args:
            title: 标签标题；custom 模式下仅作为 key 的回退值。
            key: 唯一标识；未传时回退到 title。
            start_icon: 起始图标来源。
            end_icon: 结束图标来源。
            custom: 自定义内容 widget，传入即进入 custom 模式。
            parent: Qt 父对象。

        Note:
            QButtonGroup 的 exclusive 模式会从 C++ 层直接调用 setChecked，
            Python 子类 override 无法拦截，故用 toggled 信号驱动选中动画。
        """
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
        self._start_icon_pixmap: QPixmap | None = None
        self._end_icon_pixmap: QPixmap | None = None
        # 档3：custom widget
        self._custom: QWidget | None = None
        self._custom_layout: QHBoxLayout | None = None
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
        """返回当前标签标题。"""
        return self._title

    def set_title(self, title: str):
        """设置标签标题，custom 模式下不影响视觉。"""
        self._title = title
        # custom 模式下 title 仅作为 key fallback，不影响视觉
        if self._custom is None:
            self._refresh_icons()
            self._update_geometry()
            self.update()

    def key(self) -> str:
        """返回标签的唯一标识。"""
        return self._key

    def set_key(self, key: str):
        """设置标签的唯一标识。"""
        self._key = key

    def set_disabled(self, disabled: bool):
        """设置禁用态并同步鼠标样式与 custom 透明度。"""
        self._is_disabled = bool(disabled)
        self.setEnabled(not self._is_disabled)
        if self._is_disabled:
            self.setCursor(Qt.ForbiddenCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        self._sync_custom_opacity()
        self.update()

    def is_disabled(self) -> bool:
        """返回是否处于禁用态。"""
        return self._is_disabled

    def set_start_icon(self, src):
        """设置起始图标。

        Args:
            src: 图标来源，可为 None / 内置图标名 / SVG 路径 / QPixmap。
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
        """返回是否存在起始或结束图标。"""
        return self._start_icon_src is not None or self._end_icon_src is not None

    # ----- 档3：custom widget 插槽 -----

    def set_custom(self, widget: QWidget | None):
        """把自定义 widget 装进标签作为内容（档3）。

        Args:
            widget: 自定义内容；传 None 取消 custom 并回退到 text/icon 模式。

        Note:
            custom 模式不挂 QGraphicsOpacityEffect，因其离屏渲染会用
            palette.Window 填色盖住下层 cursor；hover 透明度变化由此不生效。
        """
        # 清掉旧的
        if self._custom is not None:
            from ...utils import safe_delete

            safe_delete(self._custom)
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
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWidgets import QLabel as _QLabel

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

    def custom(self) -> QWidget | None:
        """返回当前 custom widget，未启用时返回 None。"""
        return self._custom

    # -------------------- 由 Tabs 调用 --------------------

    def apply_style(self, *, variant, color, size, theme, disable_animation, full_width):
        """批量应用由 Tabs 注入的样式并立即刷新文字色与几何。

        Args:
            variant: 变体名。
            color: 主题色名。
            size: 尺寸名。
            theme: 明暗主题名。
            disable_animation: 是否禁用动画。
            full_width: 是否让按钮水平拉伸。
        """
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
        """无动画地设置选中态并强制刷新文字色。

        Note:
            用于首次自动选中等场景，避免开屏闪一次淡入动画；通过
            blockSignals 屏蔽 toggled 以跳过颜色过渡。
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
        """选中态变化时把文字色过渡到目标色。"""
        target = self._selected_color if checked else self._unselected_color
        tween_value(
            self,
            "_color_anim_runner",
            QColor(self._current_text_color),
            QColor(target),
            self._on_color_step,
            duration=self.SELECT_ANIM_DURATION,
            animated=not self._disable_animation,
        )

    def _on_color_step(self, value):
        """动画帧回调：更新当前文字色并重绘图标。"""
        if isinstance(value, QColor):
            self._current_text_color = value
            # icon 跟随文字色
            self._refresh_icons()
            self.update()

    def _animate_opacity(self, target: float):
        """把整体透明度过渡到 target。"""
        tween_value(
            self,
            "_opacity_anim_runner",
            float(self._current_opacity),
            float(target),
            self._on_opacity_step,
            duration=self.HOVER_ANIM_DURATION,
            animated=not self._disable_animation,
        )

    def _on_opacity_step(self, value):
        """动画帧回调：更新透明度并同步 custom 效果。"""
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
        """鼠标进入时记录 hover 态并降低未选中项透明度。"""
        self._is_hover = True
        if not self.isChecked() and not self._is_disabled:
            self._animate_opacity(0.5)
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        """鼠标离开时清除 hover 态并恢复透明度。"""
        self._is_hover = False
        self._animate_opacity(1.0)
        super().leaveEvent(ev)

    # -------------------- Geometry --------------------

    def _icon_size_px(self) -> int:
        """返回 icon 像素尺寸，约等于文字行高。"""
        return self._size_cfg["tab_font_size"] + 2

    def _icon_gap(self) -> int:
        """icon 与文字之间间距。"""
        return 6

    def _refresh_icons(self):
        """根据当前文字色重新加载 + 着色 start/end icon。"""
        color = self._current_text_color
        size = self._icon_size_px()

        def _to_pixmap(src) -> QPixmap | None:
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
        """按尺寸配置与内容计算并应用最小宽高。"""
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
            icon_w += icon_size + (gap if (self._title or self._start_icon_pixmap) else 0)
        w = max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"])
        self.setMinimumWidth(w)

    def sizeHint(self) -> QSize:
        """返回按内容与尺寸配置计算的建议尺寸。"""
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
            icon_w += icon_size + (gap if (self._title or self._start_icon_pixmap) else 0)
        return QSize(
            max(text_w + icon_w + 2 * cfg["tab_padding_x"], cfg["tab_min_width"]),
            cfg["tab_height"],
        )

    # -------------------- Paint --------------------

    def paintEvent(self, ev):
        """自绘标题文字与起止图标，custom 模式交给子 widget 渲染。

        Note:
            文字基线按 capHeight 对齐行盒中心，避免 Qt 按 ascent/descent
            整高居中导致的视觉偏下。
        """
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
            p.drawPixmap(
                round(x),
                round(iy),
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
            p.drawText(round(x), round(baseline), self._title)
            x += text_w + (gap if self._end_icon_pixmap is not None else 0)

        # end icon
        if self._end_icon_pixmap is not None:
            iy = (h - icon_size) / 2
            p.drawPixmap(
                round(x),
                round(iy),
                icon_size,
                icon_size,
                self._end_icon_pixmap,
            )

        p.end()
