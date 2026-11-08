"""ScrollShadow 组件：可滚动容器两端的背景色渐变蒙版，暗示可滚动方向。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QHBoxLayout, QLayout, QScrollArea, QVBoxLayout, QWidget

from ...core import ThemeProvider

# visibility 合法值
_VISIBILITY = ("auto", "both", "top", "bottom", "left", "right", "none")
# orientation 合法值
_ORIENTATION = ("vertical", "horizontal")


class _ShadowOverlay(QWidget):
    """覆盖在 viewport 上的透明层,负责绘制两端渐变。"""

    def __init__(self, parent: QWidget):
        """初始化透明叠加层并设默认绘制状态。

        Args:
            parent: 承载叠加层的父 widget。

        Note:
            设置鼠标事件穿透与半透明背景，使叠加层只绘制渐变而不拦截交互。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 绘制状态由外部 ScrollShadow 注入
        self._orientation: str = "vertical"
        self._size: int = 40
        self._show_start: bool = False  # 顶/左
        self._show_end: bool = False  # 底/右
        self._fade_color: QColor = QColor("#FAFBFD")
        # 裁剪圆角(px)。>0 时 paintEvent 用 QPainterPath 把渐变裁到圆角矩形内,
        # 让阴影跟随父级 popover/card 的圆角内收,避免"中间滚动时四角变直角"。
        self._clip_radius: float = 0.0

    def configure(
        self,
        orientation: str,
        size: int,
        show_start: bool,
        show_end: bool,
        fade_color: QColor,
        clip_radius: float = 0.0,
    ) -> None:
        """由 ScrollShadow 调用，设置本帧的渐变绘制参数。

        Args:
            orientation: 渐变方向，vertical 或 horizontal。
            size: 渐变长度（像素）。
            show_start: 是否绘制起始端阴影。
            show_end: 是否绘制末端阴影。
            fade_color: 渐变淡出目标色。
            clip_radius: 圆角裁剪半径，为 0 时不裁剪。
        """
        self._orientation = orientation
        self._size = max(0, size)
        self._show_start = show_start
        self._show_end = show_end
        self._fade_color = fade_color
        self._clip_radius = max(0.0, float(clip_radius))
        self.update()

    def paintEvent(self, event):
        """按配置在两端绘制渐变蒙版。

        Args:
            event: Qt 绘制事件。

        Note:
            clip_radius 大于 0 时用 QPainterPath 裁剪到圆角矩形，
            避免 setMask 的 1bit 锯齿；两端同显时渐变长度取半，防止重叠。
        """
        if self._size <= 0:
            return
        if not (self._show_start or self._show_end):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        w, h = self.width(), self.height()

        # 裁剪到圆角矩形(若 clip_radius>0):让阴影跟随父级容器圆角内收。
        # 用 QPainterPath 而非 setMask —— mask 是 1bit 没抗锯齿,圆角会有锯齿;
        # path clip 走 QPainter 抗锯齿,边缘平滑。
        if self._clip_radius > 0.0:
            path = QPainterPath()
            path.addRoundedRect(0.0, 0.0, float(w), float(h), self._clip_radius, self._clip_radius)
            painter.setClipPath(path)

        c_solid = QColor(self._fade_color)
        c_solid.setAlpha(255)
        c_trans = QColor(self._fade_color)
        c_trans.setAlpha(0)

        if self._orientation == "vertical":
            s = min(self._size, h // 2 if (self._show_start and self._show_end) else h)
            if self._show_start and s > 0:
                # 顶部: 从 y=0 (不透明) 渐变到 y=s (透明)
                g = QLinearGradient(0, 0, 0, s)
                g.setColorAt(0.0, c_solid)
                g.setColorAt(1.0, c_trans)
                painter.fillRect(0, 0, w, s, g)
            if self._show_end and s > 0:
                # 底部: 从 y=h-s (透明) 渐变到 y=h (不透明)
                g = QLinearGradient(0, h - s, 0, h)
                g.setColorAt(0.0, c_trans)
                g.setColorAt(1.0, c_solid)
                painter.fillRect(0, h - s, w, s, g)
        else:
            s = min(self._size, w // 2 if (self._show_start and self._show_end) else w)
            if self._show_start and s > 0:
                g = QLinearGradient(0, 0, s, 0)
                g.setColorAt(0.0, c_solid)
                g.setColorAt(1.0, c_trans)
                painter.fillRect(0, 0, s, h, g)
            if self._show_end and s > 0:
                g = QLinearGradient(w - s, 0, w, 0)
                g.setColorAt(0.0, c_trans)
                g.setColorAt(1.0, c_solid)
                painter.fillRect(w - s, 0, s, h, g)

        painter.end()


class ScrollShadow(QScrollArea):
    """HeroUI 风格的滚动阴影容器。

    Note:
        orientation 决定纵向(顶/底)或横向(左/右)两端渐变；visibility="auto"
        时按滚动位置自动显隐，不可滚动则全部隐藏。
    """

    visibility_changed = Signal(str)

    def __init__(
        self,
        orientation: str = "vertical",
        size: int = 40,
        offset: int = 0,
        visibility: str = "auto",
        is_enabled: bool = True,
        hide_scrollbar: bool = False,
        fade_color: str | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """初始化滚动阴影容器并校验方向、可见性参数。

        Args:
            orientation: 滚动方向，vertical 或 horizontal。
            size: 渐变长度（像素）。
            offset: 判定可滚动时使用的边界偏移。
            visibility: 显隐策略，auto/both/top/bottom/left/right/none。
            is_enabled: 是否启用阴影。
            hide_scrollbar: 是否隐藏滚动条。
            fade_color: 显式淡出目标色；None 表示跟随容器背景。
            theme: 主题模式，auto/light/dark。
            parent: Qt 父对象。

        Note:
            orientation、visibility 非法值抛 ValueError；
            theme 为 auto 时注册到 ThemeProvider；
            viewport 与内容容器关闭自动填背景，让父容器底色透上来。
        """
        super().__init__(parent)

        if orientation not in _ORIENTATION:
            raise ValueError(f"orientation must be one of {_ORIENTATION}, got {orientation!r}")
        if visibility not in _VISIBILITY:
            raise ValueError(f"visibility must be one of {_VISIBILITY}, got {visibility!r}")

        self._orientation = orientation
        self._size = int(size)
        self._offset = int(offset)
        self._visibility = visibility
        self._is_enabled = bool(is_enabled)
        self._hide_scrollbar = bool(hide_scrollbar)
        self._fade_color_user: str | None = fade_color
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 上一次广播的 visibility 字符串,用于去抖
        self._last_effective_vis: str = "none"

        # --- QScrollArea 基础配置 ---
        # 去掉默认 frame,避免 1px 边框干扰阴影
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setWidgetResizable(True)

        # 按 orientation 决定滚动条策略
        self._apply_scrollbar_policy()

        # --- 插槽容器(内置,用户直接往里塞内容) ---
        # 让 ScrollShadow 像 Card 一样是"可装配"的容器,而不是只能
        # setWidget 一次的包装器。vertical 时用 QVBoxLayout,horizontal
        # 时用 QHBoxLayout —— 滚动方向决定内容堆叠方向。
        self._content = QWidget()
        self._content.setObjectName("heroScrollShadowContent")
        if self._orientation == "vertical":
            self._content_layout: QLayout = QVBoxLayout(self._content)
        else:
            self._content_layout = QHBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        super().setWidget(self._content)  # 注意:用 super 避免走自己的 setWidget override

        # QScrollArea 的 viewport 默认有 palette.Base=白 + autoFillBackground=True,
        # 会把父容器的底色遮住(dark Card 内出现白色矩形 bug)。让 viewport
        # 和 _content 都不自动填背景、并且 WA_TranslucentBackground,
        # 让 parent 容器的底色透上来。用户传 fade_color 时 _apply_user_bg 会
        # 重新打开 autoFillBackground + 设 palette.Window,覆盖这里的默认。
        self.viewport().setAutoFillBackground(False)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._content.setAutoFillBackground(False)
        self._content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # --- 叠加层 ---
        self._overlay = _ShadowOverlay(self.viewport())
        self._overlay.show()
        self._sync_overlay_geometry()

        # viewport 大小变化时同步 overlay
        self.viewport().installEventFilter(self)

        # 滚动位置变化时刷新
        self.verticalScrollBar().valueChanged.connect(self._refresh_shadow)
        self.verticalScrollBar().rangeChanged.connect(lambda *_: self._refresh_shadow())
        self.horizontalScrollBar().valueChanged.connect(self._refresh_shadow)
        self.horizontalScrollBar().rangeChanged.connect(lambda *_: self._refresh_shadow())

        # auto 主题: 注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        # 如果用户显式传了 fade_color,把 ScrollShadow 自身 + viewport 的背景
        # 也填成同色 —— 保证阴影淡出端与底色严丝合缝、不依赖 palette 推断。
        self._apply_user_bg()

        self._refresh_shadow()

    # ============================================================
    # 插槽 API (推荐用法,像 Card 一样可装配)
    # ============================================================
    def add_widget(self, widget: QWidget) -> None:
        """向内部容器追加一个子 widget。

        Args:
            widget: 要追加的子控件。
        """
        self._content_layout.addWidget(widget)

    def insert_widget(self, index: int, widget: QWidget) -> None:
        """在指定位置插入子 widget。"""
        if isinstance(self._content_layout, (QVBoxLayout, QHBoxLayout)):
            self._content_layout.insertWidget(index, widget)
        else:
            self._content_layout.addWidget(widget)

    def add_stretch(self, stretch: int = 1) -> None:
        """往内容末尾追加一个弹性空间(对 QBoxLayout 有效)。"""
        if isinstance(self._content_layout, (QVBoxLayout, QHBoxLayout)):
            self._content_layout.addStretch(stretch)

    def content(self) -> QWidget:
        """返回内置内容容器，供直接操作（如设边距或替换 layout）。"""
        return self._content

    def layout(self) -> QLayout:  # type: ignore[override]
        """返回内置内容 layout，可像普通容器一样装配。

        Returns:
            内部 QLayout。
        """
        return self._content_layout

    # ============================================================
    # QScrollArea 原生 setWidget(高级用法,替换整个内容容器)
    # ============================================================
    def setWidget(self, widget):  # type: ignore[override]
        """替换整个内容容器，替换后插槽 API 失效。

        Args:
            widget: 新的内容控件；调用后 add_widget/layout/content 不再指向原容器。
        """
        super().setWidget(widget)
        self._content = widget
        # 传入 widget 如果自带 layout,继续暴露;否则保持原引用
        lay = widget.layout() if widget is not None else None
        if lay is not None:
            self._content_layout = lay
        self._refresh_shadow()

    # ============================================================
    # 事件
    # ============================================================
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """在 viewport 尺寸或显示变化时同步几何并刷新阴影。

        Args:
            obj: 事件来源对象。
            event: 待过滤的 Qt 事件。

        Returns:
            交由父类 eventFilter 的返回值。
        """
        if obj is self.viewport() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self._sync_overlay_geometry()
            self._refresh_shadow()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """尺寸变化时同步叠加层几何并刷新阴影。

        Args:
            event: Qt 尺寸事件。
        """
        super().resizeEvent(event)
        self._sync_overlay_geometry()
        self._refresh_shadow()

    def showEvent(self, event):
        """首次显示后重算一次淡出目标色。

        Args:
            event: Qt 显示事件。

        Note:
            推迟到 parent 链挂好后计算，以读到祖先容器提供的背景色。
        """
        # 首次 show 时 parent 链已经挂好,重算一次 fade_color
        # (处理"addWidget 之后才有 heroCard 祖先"的场景)
        super().showEvent(event)
        self._refresh_shadow()

    # ============================================================
    # 内部: overlay 几何 & 阴影计算
    # ============================================================
    def _sync_overlay_geometry(self) -> None:
        """把叠加层几何对齐到 viewport 并置顶。"""
        vp = self.viewport()
        self._overlay.setGeometry(0, 0, vp.width(), vp.height())
        self._overlay.raise_()

    def _compute_effective_visibility(self) -> tuple[bool, bool, str]:
        """计算两端显隐状态与广播标签。

        Returns:
            (show_start, show_end, label)；label 为 "top"/"bottom"/"both"/
            "none"/"left"/"right"，语义对齐 HeroUI data-* 属性。
        """
        if not self._is_enabled:
            return False, False, "none"

        # 手动强制模式
        v = self._visibility
        if v == "none":
            return False, False, "none"

        is_v = self._orientation == "vertical"

        if v == "both":
            return True, True, "both"
        if v == "top":
            return (True, False, "top") if is_v else (False, False, "none")
        if v == "bottom":
            return (False, True, "bottom") if is_v else (False, False, "none")
        if v == "left":
            return (True, False, "left") if (not is_v) else (False, False, "none")
        if v == "right":
            return (False, True, "right") if (not is_v) else (False, False, "none")

        # auto: 按滚动位置
        if is_v:
            sb = self.verticalScrollBar()
        else:
            sb = self.horizontalScrollBar()

        # 不可滚动
        if sb.maximum() <= sb.minimum():
            return False, False, "none"

        val = sb.value()
        # can_back: 可以向回滚(还能往上/往左拉),说明起始端(顶/左)内容没全显示
        #           → 在"起始端"画阴影,提示"上面/左边还有内容"
        # can_fwd : 可以向前滚(还能往下/往右拉),说明末端(底/右)内容没全显示
        #           → 在"末端"画阴影,提示"下面/右边还有内容"
        can_back = val > sb.minimum() + self._offset
        can_fwd = val < sb.maximum() - self._offset

        if is_v:
            if can_back and can_fwd:
                return True, True, "both"
            if can_back:
                # 已离顶 → 需要顶部阴影告诉用户"上面还有内容"
                return True, False, "top"
            if can_fwd:
                # 未到底 → 需要底部阴影告诉用户"下面还有内容"
                return False, True, "bottom"
            return False, False, "none"
        else:
            if can_back and can_fwd:
                return True, True, "both"
            if can_back:
                return True, False, "left"
            if can_fwd:
                return False, True, "right"
            return False, False, "none"

    def _fade_color(self) -> QColor:
        """取淡出目标色，实时跟随容器所处背景。

        Note:
            优先级依次为显式 fade_color、父链上 current_bg_color()、palette.Window；
            父链通过 duck typing 查找提供该方法的祖先。
        """
        if self._fade_color_user is not None:
            return QColor(self._fade_color_user)

        # Duck typing: 任何提供 current_bg_color() 的祖先都被命中
        p = self.parentWidget()
        while p is not None:
            getter = getattr(p, "current_bg_color", None)
            if callable(getter):
                try:
                    c = getter()
                    if isinstance(c, QColor) and c.isValid():
                        return QColor(c)
                except Exception:
                    pass
            p = p.parentWidget()

        return self.palette().color(QPalette.ColorRole.Window)

    def _refresh_shadow(self) -> None:
        """按当前状态重配叠加层，并在标签变化时广播 visibility_changed。

        Note:
            用 _last_effective_vis 去重，避免同一显隐状态重复广播。
        """
        start, end, label = self._compute_effective_visibility()
        self._overlay.configure(
            orientation=self._orientation,
            size=self._size,
            show_start=start,
            show_end=end,
            fade_color=self._fade_color(),
            clip_radius=self._clip_radius(),
        )
        if label != self._last_effective_vis:
            self._last_effective_vis = label
            self.visibility_changed.emit(label)

    def _clip_radius(self) -> float:
        """取裁剪圆角半径，沿父链 duck-typing 找 current_corner_radius()。

        Returns:
            圆角像素值；父链无提供者时返回 0（不裁剪）。
        """
        p = self.parentWidget()
        while p is not None:
            getter = getattr(p, "current_corner_radius", None)
            if callable(getter):
                try:
                    r = getter()
                    if isinstance(r, (int, float)) and r > 0:
                        return float(r)
                except Exception:
                    pass
            p = p.parentWidget()
        return 0.0

    def _apply_scrollbar_policy(self) -> None:
        """按方向与隐藏设置配置横纵滚动条策略。

        Note:
            hide_scrollbar 为真时两轴都强制关闭；否则仅保留滚动方向对应的滚动条。
        """
        if self._hide_scrollbar:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            return

        if self._orientation == "vertical":
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # ============================================================
    # 公共 setter
    # ============================================================
    def set_orientation(self, o: str) -> None:
        """切换滚动方向并重配滚动条策略。

        Args:
            o: vertical 或 horizontal。

        Note:
            非法值抛 ValueError。
        """
        if o not in _ORIENTATION:
            raise ValueError(f"orientation must be one of {_ORIENTATION}")
        self._orientation = o
        self._apply_scrollbar_policy()
        self._refresh_shadow()

    def set_size(self, s: int) -> None:
        """设置渐变长度并刷新阴影。"""
        self._size = max(0, int(s))
        self._refresh_shadow()

    def set_offset(self, o: int) -> None:
        """设置可滚动判定的边界偏移并刷新阴影。"""
        self._offset = int(o)
        self._refresh_shadow()

    def set_visibility(self, v: str) -> None:
        """切换显隐策略并刷新阴影。

        Args:
            v: 显隐策略，须为 _VISIBILITY 中的值。

        Note:
            非法值抛 ValueError。
        """
        if v not in _VISIBILITY:
            raise ValueError(f"visibility must be one of {_VISIBILITY}")
        self._visibility = v
        self._refresh_shadow()

    def set_is_enabled(self, v: bool) -> None:
        """设置是否启用阴影并刷新。"""
        self._is_enabled = bool(v)
        self._refresh_shadow()

    def set_hide_scrollbar(self, v: bool) -> None:
        """设置是否隐藏滚动条并刷新阴影。"""
        self._hide_scrollbar = bool(v)
        self._apply_scrollbar_policy()
        self._sync_overlay_geometry()
        self._refresh_shadow()

    def set_fade_color(self, c: str | None) -> None:
        """设置淡出目标色，并同步自身与 viewport 背景。

        Args:
            c: 目标色；传 None 恢复跟随 palette 自动决策。
        """
        self._fade_color_user = c
        self._apply_user_bg()
        self._refresh_shadow()

    def _apply_user_bg(self) -> None:
        """把自身与 viewport 背景涂成用户指定的 fade_color。

        Note:
            通过 palette.Window 实现而非 QSS，避免样式向内部 widget 传染。
        """
        vp = self.viewport()
        if self._fade_color_user is None:
            # 恢复默认: 不自动填背景,让父/palette 穿透
            self.setAutoFillBackground(False)
            vp.setAutoFillBackground(False)
            return

        color = QColor(self._fade_color_user)
        for w in (self, vp):
            pal = w.palette()
            pal.setColor(QPalette.ColorRole.Window, color)
            w.setPalette(pal)
            w.setAutoFillBackground(True)

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, t: str) -> None:
        """切换主题模式并刷新阴影。

        Args:
            t: auto 时注册到 ThemeProvider，其余值作为固定主题。

        Note:
            由 auto 切到固定主题时会从 ThemeProvider 注销。
        """
        if t == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = t
            self._theme = t
        self._refresh_shadow()

    def _apply_provider_theme(self, theme: str) -> None:
        """响应 ThemeProvider 广播，延迟到事件循环末尾再重绘。

        Note:
            用 QTimer.singleShot(0) 推迟，确保此时父级组件已完成 palette 同步。
        """
        self._theme = theme
        # 推迟到事件循环末尾再重绘: 保证此时其他组件(如父级 Card)也已经
        # 完成 palette 同步,我们读 self.palette().Window 能拿到最新色。
        QTimer.singleShot(0, self._refresh_shadow)

    # --- 响应 palette 变化 (覆盖 QWidget.changeEvent) ---
    def changeEvent(self, event):
        """在 palette 变更时重绘阴影。

        Args:
            event: Qt 事件。

        Note:
            仅 QEvent.Type.PaletteChange 触发刷新，其余事件交回父类处理。
        """
        # 当 QApplication.setPalette 或 parent.setPalette 触发子树 palette 变更,
        # Qt 会给每个子 widget 发 PaletteChange 事件。在这里重绘以保证阴影色
        # 即时跟随 Card / 窗口的 palette 变化。
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh_shadow()
        super().changeEvent(event)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析为具体的 light 或 dark。

        Args:
            mode: 主题模式。

        Returns:
            light/dark 原样返回；其余返回 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # Getter (便于外部查询)
    # ============================================================
    @property
    def orientation(self) -> str:
        """返回当前滚动方向。"""
        return self._orientation

    @property
    def size_px(self) -> int:
        """返回当前渐变长度（像素）。"""
        return self._size

    @property
    def effective_visibility(self) -> str:
        """返回上一次广播的显隐标签。"""
        return self._last_effective_vis
