"""
HeroSideUI ScrollShadow 组件

对标 HeroUI v2:
    https://v2.heroui.com/docs/components/scroll-shadow
    源码: https://github.com/heroui-inc/heroui/tree/main/packages/components/scroll-shadow

行为对齐:
    在可滚动容器的起/止端，绘制一条与"容器父层背景"同色的渐变蒙版，
    让内容看起来"淡出"在边缘——暗示"还有更多内容可滚"。
    - vertical 方向: 顶部 / 底部各一条阴影
    - horizontal 方向: 左端 / 右端各一条阴影
    阴影自动根据滚动位置显隐:
        - 容器没到顶 → 显示顶部淡出
        - 没到底 → 显示底部淡出
        - 不可滚动 → 全部隐藏

Qt 实现:
    Web 端 HeroUI 用 CSS `mask-image: linear-gradient(...)` 把容器自身
    的边缘做 alpha 渐变;Qt 里没有 CSS mask——改为 viewport 上叠一个
    透明覆盖层 `_ShadowOverlay`,用 `QLinearGradient` 画一条
    "背景色→透明" 的渐变,视觉效果与 mask-image 完全等价。

    阴影的"淡出目标色"取自 ThemeProvider 的窗口背景色
    (light=#FAFBFD / dark=#0B0D12),确保渐变终点和父容器融为一体。

结构:
    ScrollShadow (QScrollArea)
        └── viewport (QWidget, QScrollArea 内置)
                ├── 用户通过 setWidget() 设置的内容
                └── _ShadowOverlay (QWidget, 覆盖在内容之上,鼠标穿透)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QEvent, QObject, Signal, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLayout

from ..core import ThemeProvider

# visibility 合法值
_VISIBILITY = ("auto", "both", "top", "bottom", "left", "right", "none")
# orientation 合法值
_ORIENTATION = ("vertical", "horizontal")


class _ShadowOverlay(QWidget):
    """覆盖在 viewport 上的透明层,负责绘制两端渐变。"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 绘制状态由外部 ScrollShadow 注入
        self._orientation: str = "vertical"
        self._size: int = 40
        self._show_start: bool = False  # 顶/左
        self._show_end: bool = False    # 底/右
        self._fade_color: QColor = QColor("#FAFBFD")

    def configure(
        self,
        orientation: str,
        size: int,
        show_start: bool,
        show_end: bool,
        fade_color: QColor,
    ) -> None:
        """由 ScrollShadow 调用,设置本帧要画什么。"""
        self._orientation = orientation
        self._size = max(0, size)
        self._show_start = show_start
        self._show_end = show_end
        self._fade_color = fade_color
        self.update()

    def paintEvent(self, event):
        if self._size <= 0:
            return
        if not (self._show_start or self._show_end):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(Qt.PenStyle.NoPen)

        w, h = self.width(), self.height()
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

    用法:
        sa = ScrollShadow(orientation="vertical", size=40)
        sa.setWidget(my_long_content)   # 和 QScrollArea 完全一样

        # 水平方向
        sa = ScrollShadow(orientation="horizontal", hide_scrollbar=True)

        # 强制两端始终显示
        sa = ScrollShadow(visibility="both")

    参数:
        orientation     : "vertical" | "horizontal"   默认 "vertical"
        size            : 阴影渐变宽度 (px)           默认 40
        offset          : 进入"到顶/到底"判定的容差 (px) 默认 0
        visibility      : "auto"|"both"|"top"|"bottom"|"left"|"right"|"none"
                          默认 "auto" —— 按滚动位置自动显隐
        is_enabled      : 是否启用阴影                 默认 True
        hide_scrollbar  : 是否隐藏原生滚动条           默认 False
        theme           : "auto"|"light"|"dark"       默认 "auto"

    信号:
        visibility_changed(str)  : 当前显隐组合变化时发射
                                    值为 "top"/"bottom"/"both"/"none"/"left"/"right"
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
        fade_color: Optional[str] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if orientation not in _ORIENTATION:
            raise ValueError(
                f"orientation must be one of {_ORIENTATION}, got {orientation!r}"
            )
        if visibility not in _VISIBILITY:
            raise ValueError(
                f"visibility must be one of {_VISIBILITY}, got {visibility!r}"
            )

        self._orientation = orientation
        self._size = int(size)
        self._offset = int(offset)
        self._visibility = visibility
        self._is_enabled = bool(is_enabled)
        self._hide_scrollbar = bool(hide_scrollbar)
        self._fade_color_user: Optional[str] = fade_color
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
        """往 ScrollShadow 内部追加一个子 widget。

        内部容器是 QVBoxLayout (vertical 方向) 或 QHBoxLayout (horizontal 方向),
        按调用顺序堆叠。完全等价 `self.layout().addWidget(widget)`。
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
        """返回内置的内容容器 widget(已挂好 layout)。

        高级用法: 需要直接操作这个 QWidget 时用(如 setContentsMargins
        做边距、或把现有 layout 替换成自定义 GridLayout)。
        """
        return self._content

    def layout(self) -> QLayout:  # type: ignore[override]
        """返回内置的内容 layout。

        用户可以 `sc.layout().addWidget(...)` / `sc.layout().addLayout(...)`
        像普通容器一样装配内容。
        """
        return self._content_layout

    # ============================================================
    # QScrollArea 原生 setWidget(高级用法,替换整个内容容器)
    # ============================================================
    def setWidget(self, widget):  # type: ignore[override]
        """替换整个内容容器。

        调用后,插槽 API (add_widget / layout / content) 不再有效 ——
        因为它们指向的内容 widget 被替换掉了。只推荐需要完全自定义内容
        容器的高级场景使用。
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
        if obj is self.viewport() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self._sync_overlay_geometry()
            self._refresh_shadow()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_overlay_geometry()
        self._refresh_shadow()

    def showEvent(self, event):
        # 首次 show 时 parent 链已经挂好,重算一次 fade_color
        # (处理"addWidget 之后才有 heroCard 祖先"的场景)
        super().showEvent(event)
        self._refresh_shadow()

    # ============================================================
    # 内部: overlay 几何 & 阴影计算
    # ============================================================
    def _sync_overlay_geometry(self) -> None:
        vp = self.viewport()
        self._overlay.setGeometry(0, 0, vp.width(), vp.height())
        self._overlay.raise_()

    def _compute_effective_visibility(self) -> tuple[bool, bool, str]:
        """计算 (show_start, show_end, label) —— label 用于信号广播。

        返回的 label 对应原版 HeroUI 的 data-* 属性语义:
            vertical: "top" / "bottom" / "both" / "none"
            horizontal: "left" / "right" / "both" / "none"
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
        """淡出的目标色 —— 实时跟随"容器所处背景"。

        决策顺序:
            1. 用户显式传了 `fade_color` → 直接用(最高优先级,手动覆盖)
            2. 沿 parent 链向上找第一个提供 `current_bg_color()` API 的
               祖先容器(如 Card),读其返回值。这是 duck typing,不耦合
               具体类名或 objectName——任何"自知底色且愿意暴露"的容器都能
               被命中。
            3. 回退读自身 palette.Window —— Qt palette 沿 parent 链继承,
               ThemeProvider 已把 QApplication.palette.Window 同步为当前
               主题窗口色。

        配合:
            - ThemeProvider `_refresh_theme` 先 _sync_app_palette 再广播
            - changeEvent 监听 PaletteChange 实时重绘
            - _apply_provider_theme 用 QTimer.singleShot(0) 推迟到事件循环
              末尾(保证所有级联 setPalette 跑完)
            - Card 等容器的 theme_changed 会触发自己 _apply_styles ->
              子树 palette 变更 -> ScrollShadow 收到 PaletteChange -> 重绘
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
        start, end, label = self._compute_effective_visibility()
        self._overlay.configure(
            orientation=self._orientation,
            size=self._size,
            show_start=start,
            show_end=end,
            fade_color=self._fade_color(),
        )
        if label != self._last_effective_vis:
            self._last_effective_vis = label
            self.visibility_changed.emit(label)

    def _apply_scrollbar_policy(self) -> None:
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
        if o not in _ORIENTATION:
            raise ValueError(f"orientation must be one of {_ORIENTATION}")
        self._orientation = o
        self._apply_scrollbar_policy()
        self._refresh_shadow()

    def set_size(self, s: int) -> None:
        self._size = max(0, int(s))
        self._refresh_shadow()

    def set_offset(self, o: int) -> None:
        self._offset = int(o)
        self._refresh_shadow()

    def set_visibility(self, v: str) -> None:
        if v not in _VISIBILITY:
            raise ValueError(f"visibility must be one of {_VISIBILITY}")
        self._visibility = v
        self._refresh_shadow()

    def set_is_enabled(self, v: bool) -> None:
        self._is_enabled = bool(v)
        self._refresh_shadow()

    def set_hide_scrollbar(self, v: bool) -> None:
        self._hide_scrollbar = bool(v)
        self._apply_scrollbar_policy()
        self._sync_overlay_geometry()
        self._refresh_shadow()

    def set_fade_color(self, c: Optional[str]) -> None:
        """设置淡出渐变的目标色 —— **同时**把 ScrollShadow 自身+viewport 的
        背景也填成这个色,保证阴影与底色严丝合缝。

        传 None 恢复"跟随 palette 自动决策"模式(自身/viewport 背景回到透明,
        让父容器的背景/palette 透过来画)。

        场景: 嵌在非默认背景容器里(比如主题不一致的区域、自定义色彩面板),
        一行传背景色即可,无需关心 palette 推断。
        """
        self._fade_color_user = c
        self._apply_user_bg()
        self._refresh_shadow()

    def _apply_user_bg(self) -> None:
        """用户传了 fade_color 时,把 self + viewport 背景也涂成该色。

        通过 palette.Window + setAutoFillBackground 实现(不用 QSS,避免
        QSS 向内部 widget 传染——MEMORY 23 条的经验教训)。
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
        self._theme = theme
        # 推迟到事件循环末尾再重绘: 保证此时其他组件(如父级 Card)也已经
        # 完成 palette 同步,我们读 self.palette().Window 能拿到最新色。
        QTimer.singleShot(0, self._refresh_shadow)

    # --- 响应 palette 变化 (覆盖 QWidget.changeEvent) ---
    def changeEvent(self, event):
        # 当 QApplication.setPalette 或 parent.setPalette 触发子树 palette 变更,
        # Qt 会给每个子 widget 发 PaletteChange 事件。在这里重绘以保证阴影色
        # 即时跟随 Card / 窗口的 palette 变化。
        if event.type() == QEvent.Type.PaletteChange:
            self._refresh_shadow()
        super().changeEvent(event)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # Getter (便于外部查询)
    # ============================================================
    @property
    def orientation(self) -> str:
        return self._orientation

    @property
    def size_px(self) -> int:
        return self._size

    @property
    def effective_visibility(self) -> str:
        return self._last_effective_vis
