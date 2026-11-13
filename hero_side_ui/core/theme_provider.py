"""全局主题管理器：auto/light/dark 三模式、一键切换与系统主题实时跟随。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from ._registry import WidgetRegistry

VALID_MODES = ("auto", "light", "dark")
VALID_THEMES = ("light", "dark")


class ThemeProvider(QObject):
    """全局主题管理器（单例）。

    Note:
        组件 theme="auto" 自动注册并跟随全局切换；"light"/"dark" 硬锁不注册。
        register 使用 weakref，组件销毁时自动清理。
    """

    # 当实际生效主题变化时发射 ("light" / "dark")
    theme_changed = Signal(str)

    # 当模式（用户设定）变化时发射 ("auto" / "light" / "dark")
    mode_changed = Signal(str)

    _instance: ThemeProvider | None = None

    def __init__(self):
        """初始化主题模式、系统检测结果与组件弱引用集合。"""
        super().__init__()

        self._mode: str = "auto"
        self._current_theme: str = self._detect_system_theme()

        # 弱引用登记簿：组件销毁后自动剔除，C++ 已删对象广播时自动注销
        self._widgets = WidgetRegistry("ThemeProvider")

        # 是否在主题变化时自动同步 QApplication 全局 palette
        # 默认开启 → 用户写普通 QWidget/QMainWindow 也能开箱即用
        self._auto_app_palette: bool = True
        # 首次改动前的 Window/WindowText 原色，release_app_palette 据此还原
        self._original_palette: tuple[QColor, QColor] | None = None

        # 监听系统主题变化（Qt 6.5+ 提供 colorSchemeChanged）
        self._connect_system_signals()

        # 立刻把当前主题同步到 app palette（让首屏背景就是对的）
        self._sync_app_palette()

    # ============================================================
    # 单例
    # ============================================================

    @classmethod
    def instance(cls) -> ThemeProvider:
        """获取全局单例，首次调用懒初始化并触发 core 基础设施启动。

        Returns:
            ThemeProvider 单例。

        Note:
            启动钩子见 core/_boot.py；钩子必须在 _instance 赋值后调用，
            避免兄弟模块初始化时的无限递归。
        """
        if cls._instance is None:
            cls._instance = ThemeProvider()
            from ._boot import ensure_core_ready

            ensure_core_ready()
        return cls._instance

    @classmethod
    def peek(cls) -> ThemeProvider | None:
        """返回已存在的单例；尚未创建时返回 None，不触发初始化。"""
        return cls._instance

    # ============================================================
    # 公共属性
    # ============================================================

    @property
    def mode(self) -> str:
        """当前模式：'auto' | 'light' | 'dark'"""
        return self._mode

    @property
    def current_theme(self) -> str:
        """返回当前实际生效的主题。

        Returns:
            "light" 或 "dark"；auto 模式时取系统检测结果。
        """
        return self._current_theme

    # ============================================================
    # 公共方法
    # ============================================================

    def set_mode(self, mode: str) -> None:
        """设置主题模式并广播给已注册组件。

        Args:
            mode: "auto"（跟随系统）、"light" 或 "dark"。
        """
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}, expected one of {VALID_MODES}")

        if mode == self._mode:
            return

        self._mode = mode
        self.mode_changed.emit(mode)
        self._refresh_theme()

    def toggle(self) -> None:
        """在 light 与 dark 间反转；切换后退出 auto 模式。"""
        new_mode = "dark" if self._current_theme == "light" else "light"
        self.set_mode(new_mode)

    def register(self, widget) -> None:
        """注册组件以跟随全局主题切换。

        Args:
            widget: 需提供 set_theme(theme) 方法；推荐同时实现
                _apply_provider_theme(theme) 供广播路径使用。
        """
        if not hasattr(widget, "set_theme"):
            raise TypeError(
                f"Widget {widget!r} has no set_theme() method, cannot register to ThemeProvider"
            )
        self._widgets.add(widget)
        # 注册时立即同步一次主题
        self._widgets.broadcast_to(
            widget, lambda w: self._push_theme_to_widget(w, self._current_theme)
        )

    def unregister(self, widget) -> None:
        """从主题管理器中移除组件"""
        self._widgets.discard(widget)

    def is_registered(self, widget) -> bool:
        """检查组件是否已注册"""
        return widget in self._widgets

    @property
    def registered_count(self) -> int:
        """当前已注册组件数量（活动引用）"""
        return len(self._widgets)

    # ============================================================
    # 系统检测
    # ============================================================

    def _detect_system_theme(self) -> str:
        """检测系统亮暗色：优先 Qt 6.5+ colorScheme()，回退 QPalette 亮度。"""
        app = QApplication.instance() or QGuiApplication.instance()
        if app is not None:
            # Qt 6.5+ 提供原生 colorScheme()
            style_hints = app.styleHints()
            if hasattr(style_hints, "colorScheme"):
                scheme = style_hints.colorScheme()
                if scheme == Qt.ColorScheme.Dark:
                    return "dark"
                if scheme == Qt.ColorScheme.Light:
                    return "light"
                # ColorScheme.Unknown → 退回 palette 判断

            # 回退方案：用 QPalette 亮度判断
            palette = app.palette()
            bg = palette.color(QPalette.ColorRole.Window)
            return "dark" if bg.lightness() < 128 else "light"

        return "light"

    def _connect_system_signals(self) -> None:
        """连接系统主题变化信号（Qt 6.5+）"""
        app = QApplication.instance() or QGuiApplication.instance()
        if app is None:
            return

        style_hints = app.styleHints()
        if hasattr(style_hints, "colorSchemeChanged"):
            try:
                style_hints.colorSchemeChanged.connect(self._on_system_theme_changed)
            except (AttributeError, TypeError):
                # 老版本 Qt 没有这个信号
                pass

    def _on_system_theme_changed(self, *args) -> None:
        """系统主题变化回调（仅在 auto 模式下生效）"""
        if self._mode == "auto":
            self._refresh_theme()

    # ============================================================
    # 内部：重新计算并广播主题
    # ============================================================

    def _resolve_current_theme(self) -> str:
        """根据 mode 计算实际主题"""
        if self._mode == "auto":
            return self._detect_system_theme()
        return self._mode  # "light" or "dark"

    def _refresh_theme(self) -> None:
        """重算 current_theme，如有变化则广播给所有已注册组件"""
        new_theme = self._resolve_current_theme()
        if new_theme == self._current_theme:
            return

        self._current_theme = new_theme

        # 先同步 QApplication 全局 palette,再广播给组件。
        # 原因: 部分组件(如 ScrollShadow 的 _fade_color)在 _apply_provider_theme
        # 里会读 self.palette().color(Window) —— 它会继承自 QApplication palette,
        # 必须先把 QApplication palette 设成新主题的值,组件读到才是正确的。
        # 顺序反了会导致组件读到旧主题色一帧。
        if self._auto_app_palette:
            self._sync_app_palette()

        # 广播给所有已注册组件
        self._widgets.broadcast(lambda w: self._push_theme_to_widget(w, new_theme))

        self.theme_changed.emit(new_theme)

    def _sync_app_palette(self) -> None:
        """把当前主题同步到 QApplication 全局 palette（仅 Window/WindowText）。

        Note:
            使未注册的原生窗口也跟随主题；不碰 Base/Text/Button 等 role，
            避免干预组件自绘与原生按钮。
        """
        app = QApplication.instance()
        if app is None:
            return

        theme = self._current_theme
        if theme == "dark":
            # HeroUI v2 dark：background 比 content1=#18181b（Card 底）暗一级，
            # 让 Card 在暗色模式靠"底色亮一级"浮起（shadow 在暗色下不可靠）。
            # 微调：纯黑 #000 太硬 → 偏冷一点 #0B0D12（R=11 G=13 B=18，蓝>红 7 点，冷感），
            # 既保留与 Card 的层级差，又不至于死黑。
            bg, fg = "#0B0D12", "#fafafa"
        else:
            # HeroUI v2 light：background=content1=#FFF（Card 靠 shadow 浮起）。
            # 微调：纯白 #FFF 太刺眼 + 暖白 #FBF9F5 偏暖太多 → 极淡冷白 #FAFBFD
            # （R=250 G=251 B=253，蓝>红 3 点，冷调克制）。Card 的纯白 #FFF
            # 仍能比窗口亮一丝浮出，色相统一冷调（不再有暖白 vs 纯白的色相分裂）。
            bg, fg = "#FAFBFD", "#18181b"

        pal = app.palette()
        if self._original_palette is None:
            self._original_palette = (
                pal.color(QPalette.ColorRole.Window),
                pal.color(QPalette.ColorRole.WindowText),
            )
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(fg))
        app.setPalette(pal)

    def release_app_palette(self) -> None:
        """停止同步并把 QApplication 的 Window/WindowText 还原为首次改动前的值。

        Note:
            未改动过调色板时只停止同步。
        """
        self._auto_app_palette = False
        app = QApplication.instance()
        if app is None or self._original_palette is None:
            return
        window, window_text = self._original_palette
        pal = app.palette()
        pal.setColor(QPalette.ColorRole.Window, window)
        pal.setColor(QPalette.ColorRole.WindowText, window_text)
        app.setPalette(pal)
        self._original_palette = None

    def set_auto_app_palette(self, enabled: bool) -> None:
        """开关"主题变化时自动同步 QApplication palette"。

        Args:
            enabled: False 时 ThemeProvider 不再改全局 palette。
        """
        self._auto_app_palette = bool(enabled)
        if self._auto_app_palette:
            self._sync_app_palette()

    @staticmethod
    def _push_theme_to_widget(widget, theme: str) -> None:
        """向组件推送主题——优先用内部方法，避免触发注册逻辑"""
        if hasattr(widget, "_apply_provider_theme"):
            widget._apply_provider_theme(theme)
        else:
            widget.set_theme(theme)

    # ============================================================
    # 测试用：重置单例（仅用于单元测试）
    # ============================================================

    @classmethod
    def _reset_for_test(cls) -> None:
        """重置单例。仅供测试使用。"""
        if cls._instance is not None:
            cls._instance._widgets.clear()
            cls._instance.deleteLater()
        cls._instance = None
