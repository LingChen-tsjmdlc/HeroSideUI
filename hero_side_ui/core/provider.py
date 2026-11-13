"""HeroSideUIProvider：core 全局基础设施的显式初始化门面（可选）。

setup() 显式按参数初始化；未调 setup 直接用组件则隐式以默认值初始化并
warning 提示一次。非 React 式作用域容器，仅统一启动入口。
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QApplication


class HeroSideUIProvider:
    """HeroSideUI 全局基础设施的显式启动门面。"""

    @classmethod
    def setup(
        cls,
        app: QApplication | None = None,
        *,
        theme: Literal["auto", "light", "dark"] | None = None,
        font_family: str | None = None,
        font_base_size: int | None = None,
        smooth_scroll: bool = True,
        scroll_style: bool = True,
        filter_libpng_warnings: bool = True,
    ) -> None:
        """显式初始化全套 HeroSideUI 基础设施。

        Args:
            app: ``QApplication`` 实例。不传则取 ``QApplication.instance()``。
                两者都没有时抛 ``RuntimeError``——必须先 ``QApplication([])``。
            theme: 锁定主题模式（``"auto"`` / ``"light"`` / ``"dark"``）。
                不传则保持 ThemeProvider 默认（auto，跟随系统）。
            font_family: 自定义全局字体 family。不传则使用内置思源黑体 VF
                （加载失败时 fallback Inter/系统栈）。
            font_base_size: 全局基准字号（px）。不传则保持 16。
            smooth_scroll: 是否启用全局平滑滚动。默认 True。
                为 False 时不装全局事件过滤器；后续可手动 ``SmoothScroll.apply_global()``。
            scroll_style: 是否注入全局细线滚动条 QSS。默认 True。
                为 False 时不修改 QApplication.styleSheet；用户可继续用系统原生滚动条。
            filter_libpng_warnings: 是否过滤 libpng 直接写到 fd=2 的
                ``"libpng warning: iCCP: known incorrect sRGB profile"`` 噪声。
                默认 True。这条警告来自 Qt 内置 PNG 资源，无害但会刷屏。

        Note:
            调用前 ``QApplication`` 还没创建时会抛 ``RuntimeError``。
        """
        # 1) 确认 app 存在
        if app is None:
            app = QApplication.instance()
        if app is None:
            raise RuntimeError(
                "HeroSideUIProvider.setup() requires a QApplication instance. "
                "Create one first:\n"
                "    app = QApplication(sys.argv)\n"
                "    HeroSideUIProvider.setup(app)\n"
                "\n"
                "调用 HeroSideUIProvider.setup() 前必须先创建 QApplication。"
                "请先创建 QApplication 实例：\n"
                "    app = QApplication(sys.argv)\n"
                "    HeroSideUIProvider.setup(app)"
            )

        # 2) 过滤 libpng iCCP 噪声（Qt 内置 PNG 资源已知问题，无害但刷屏）
        if filter_libpng_warnings:
            from . import _libpng_filter

            _libpng_filter.install()

        # 3) 触发 _boot 显式入口（按开关激活兄弟模块；置 _setup_done=True
        #    短路后续组件构造路径上的隐式钩子，让 False 开关真生效）
        from ._boot import setup_with_options

        setup_with_options(
            smooth_scroll=smooth_scroll,
            scroll_style=scroll_style,
        )

        # 4) 应用用户级配置（必须在 _boot 激活之后，确保各 Provider 单例已就绪）
        from .theme_provider import ThemeProvider

        # ThemeProvider.instance() 内部会再调一次 ensure_core_ready()，但此时
        # _setup_done=True 已短路，不会重复激活也不会发 warning——符合预期。
        provider = ThemeProvider.instance()
        if theme is not None:
            provider.set_mode(theme)

        if font_family is not None or font_base_size is not None:
            from .font_provider import FontProvider

            fp = FontProvider.instance()
            if font_family is not None:
                fp.set_family(font_family)
            if font_base_size is not None:
                fp.set_base_size_px(font_base_size)

    @classmethod
    def teardown(cls) -> None:
        """撤销 setup 安装的应用级设施，使宿主恢复到 setup 之前的状态。

        Note:
            还原 QApplication 的 Window/WindowText 调色板、移除滚动条样式与
            全局平滑滚动、停止 libpng 警告过滤并恢复 stderr 的文件描述符。
            已创建组件与已设置的字体不受影响。可重复调用，之后可再次 setup。
        """
        from . import _boot, _libpng_filter
        from .scroll_style import ScrollStyle
        from .smooth_scroll import SmoothScroll
        from .theme_provider import ThemeProvider

        peek = ThemeProvider.peek()
        if peek is not None:
            peek.release_app_palette()
        scroll_style = ScrollStyle.peek()
        if scroll_style is not None:
            scroll_style.remove_global()
        SmoothScroll.disable_global()
        _libpng_filter.uninstall()
        _boot.reset()


__all__ = ["HeroSideUIProvider"]
