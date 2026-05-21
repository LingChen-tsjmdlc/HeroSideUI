"""
HeroSideUI 全局主题管理器 (ThemeProvider)

负责管理整个应用的亮暗色模式，支持：
- auto 模式（跟随系统）
- light / dark 强制模式
- 一键切换 (toggle)
- 系统主题变化实时响应（Qt 6.5+ colorSchemeChanged）
- 通过 weakref 避免组件内存泄漏
"""

from __future__ import annotations

import weakref
from typing import Optional

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QPalette, QGuiApplication
from PySide6.QtWidgets import QApplication

VALID_MODES = ("auto", "light", "dark")
VALID_THEMES = ("light", "dark")


class ThemeProvider(QObject):
    """
    全局主题管理器（单例）

    用法：
        # 获取单例
        provider = ThemeProvider.instance()

        # 一键切换
        provider.toggle()

        # 设置模式
        provider.set_mode("auto")    # 跟随系统
        provider.set_mode("light")   # 强制亮色
        provider.set_mode("dark")    # 强制暗色

        # 监听变化
        provider.theme_changed.connect(lambda t: print("now:", t))

        # 当前实际生效的主题
        print(provider.current_theme)  # "light" 或 "dark"

    注册策略：
        - 组件 theme="auto" 时会自动注册到 provider，跟随全局切换
        - 组件 theme="light"/"dark" 时是硬锁，不参与全局切换
        - register() 用 weakref，组件销毁时自动清理
    """

    # 当实际生效主题变化时发射 ("light" / "dark")
    theme_changed = Signal(str)

    # 当模式（用户设定）变化时发射 ("auto" / "light" / "dark")
    mode_changed = Signal(str)

    _instance: Optional["ThemeProvider"] = None

    def __init__(self):
        super().__init__()

        self._mode: str = "auto"
        self._current_theme: str = self._detect_system_theme()

        # 用 WeakSet 存储已注册组件，组件销毁后自动剔除
        self._widgets: "weakref.WeakSet" = weakref.WeakSet()

        # 是否在主题变化时自动同步 QApplication 全局 palette
        # 默认开启 → 用户写普通 QWidget/QMainWindow 也能开箱即用
        self._auto_app_palette: bool = True

        # 监听系统主题变化（Qt 6.5+ 提供 colorSchemeChanged）
        self._connect_system_signals()

        # 立刻把当前主题同步到 app palette（让首屏背景就是对的）
        self._sync_app_palette()

    # ============================================================
    # 单例
    # ============================================================

    @classmethod
    def instance(cls) -> "ThemeProvider":
        """获取全局单例。第一次调用时懒初始化。

        单例首次创建后会触发 core 全局基础设施启动钩子（``_boot.ensure_core_ready``），
        它统一激活 FontProvider / ScrollStyle / SmoothScroll 等兄弟模块——
        组件 ``__init__`` 注册到 ``ThemeProvider.instance()`` 即获全套就绪，零样板。

        ThemeProvider 自身只管主题，不直接知道兄弟模块名字（职责单一）。
        激活顺序与具体模块名集中在 ``core/_boot.py``，新增 core 模块时改那里即可。

        注意：钩子必须在 ``cls._instance`` 赋值**之后**调用——兄弟模块的
        ``__init__`` 可能反过来调 ``ThemeProvider.instance()``，赋值早一步
        才能直接命中已 cache 的单例，避免无限递归。
        """
        if cls._instance is None:
            cls._instance = ThemeProvider()
            from ._boot import ensure_core_ready

            ensure_core_ready()
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
        """当前实际生效的主题：'light' | 'dark'

        - mode == "auto"  → 系统检测结果
        - mode == "light" → "light"
        - mode == "dark"  → "dark"
        """
        return self._current_theme

    # ============================================================
    # 公共方法
    # ============================================================

    def set_mode(self, mode: str) -> None:
        """设置主题模式

        - "auto" : 跟随系统
        - "light": 强制亮色
        - "dark" : 强制暗色

        模式变化后，自动广播给所有已注册组件。
        """
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}, expected one of {VALID_MODES}")

        if mode == self._mode:
            return

        self._mode = mode
        self.mode_changed.emit(mode)
        self._refresh_theme()

    def toggle(self) -> None:
        """一键切换：在 light 和 dark 之间反转

        切换后会进入手动模式（light/dark），不再跟随系统。
        如果当前是 auto 模式，会基于当前实际主题反转。
        """
        new_mode = "dark" if self._current_theme == "light" else "light"
        self.set_mode(new_mode)

    def register(self, widget) -> None:
        """注册组件到主题管理器

        组件需要有 set_theme(theme: str) 方法。
        推荐组件同时实现 _apply_provider_theme(theme: str) 用于 provider 广播，
        避免触发 set_theme 中的注册/取消注册逻辑。

        使用 weakref，组件销毁时自动剔除，无需手动 unregister。
        """
        if not hasattr(widget, "set_theme"):
            raise TypeError(
                f"Widget {widget!r} has no set_theme() method, "
                "cannot register to ThemeProvider"
            )
        self._widgets.add(widget)
        # 注册时立即同步一次主题
        self._push_theme_to_widget(widget, self._current_theme)

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
        """检测当前系统的亮暗色模式

        优先用 Qt 6.5+ 的 styleHints().colorScheme()，
        回退用 QPalette 亮度判断。
        """
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
        for widget in list(self._widgets):
            self._push_theme_to_widget(widget, new_theme)

        self.theme_changed.emit(new_theme)

    def _sync_app_palette(self) -> None:
        """把当前主题同步到 QApplication 全局 palette

        这是"开箱即用"的关键：用户写 QMainWindow/QWidget 不需要注册到
        ThemeProvider，因为 Qt 默认 palette 机制会让所有子 widget 的
        背景/文字色跟随 QApplication.palette()。

        只改 Window/WindowText 两个 role，不碰其他：
        - Base/Text：Input `_LineEdit` palette.Base 挖空 bug（见 MEMORY.md 22/23/24）
        - Button/ButtonText：HeroSideUI 的 Button/Checkbox/TabItem 都自绘不读 palette
            Button role，写它属于越权干预 Qt 原生按钮——不是组件库的职责。
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

        from PySide6.QtGui import QColor

        pal = app.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(fg))
        app.setPalette(pal)

    def set_auto_app_palette(self, enabled: bool) -> None:
        """开关"主题变化时自动同步 QApplication palette"

        默认 True（开箱即用）。关闭后 ThemeProvider 仅管注册组件，
        不改全局 palette，由用户自己负责。
        """
        self._auto_app_palette = bool(enabled)
        if self._auto_app_palette:
            self._sync_app_palette()

    @staticmethod
    def _push_theme_to_widget(widget, theme: str) -> None:
        """向组件推送主题——优先用内部方法，避免触发注册逻辑"""
        try:
            if hasattr(widget, "_apply_provider_theme"):
                widget._apply_provider_theme(theme)
            else:
                widget.set_theme(theme)
        except Exception:
            pass

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
