"""
HeroSideUIProvider —— 显式初始化门面（可选）

设计定位：
- 一行注册全套 core 全局基础设施的**显式入口**，用于：定制主题/字体、关闭某些全局开关、写大型项目时把"启动逻辑"集中在一处。
- **不强制使用**。HeroSideUI 的"开箱即用"铁律不变——任何组件 ``__init__`` 通过 ``ThemeProvider.instance()`` 触发 ``_boot`` 钩子也能得到完整就绪环境。

显式 vs 隐式：
- ``HeroSideUIProvider.setup(app, ...)`` → 显式路径，按用户参数初始化，**静默**。
- 用户没调 setup 直接构造组件 → 隐式路径，以**默认值**初始化，第一次降级会发一条
  双语 warning 提示存在显式入口（仅打一次，便于诊断/上线后可见）。

非门面：和 React 的 ``<HeroUIProvider>`` 不同——PySide 有 ``QApplication`` 单例 +
全局 ``QPalette``，不需要 children 包裹模式。本类是"统一启动入口"而非"作用域容器"。
"""

from __future__ import annotations

from typing import Literal, Optional

from PySide6.QtWidgets import QApplication


class HeroSideUIProvider:
    """HeroSideUI 全局基础设施的显式启动门面。

    用法（最小）::

        from PySide6.QtWidgets import QApplication
        from hero_side_ui import HeroSideUIProvider

        app = QApplication([])
        HeroSideUIProvider.setup(app)
        # ... 业务代码 ...
        app.exec()

    用法（带配置）::

        HeroSideUIProvider.setup(
            app,
            theme="light",
            font_family="Microsoft YaHei",
            font_base_size=14,
            smooth_scroll=False,   # 嵌入老项目时关掉
        )

    幂等：多次调用安全，**最后一次** family/base_size/theme 设置生效（覆盖语义）；
    smooth_scroll/scroll_style 仅以**第一次**为准（全局 filter 一旦装上不再撤销，
    需要禁用请用 ``SmoothScroll.disable_global()`` / ``ScrollStyle.remove_global()``）。
    """

    @classmethod
    def setup(
        cls,
        app: Optional[QApplication] = None,
        *,
        theme: Optional[Literal["auto", "light", "dark"]] = None,
        font_family: Optional[str] = None,
        font_base_size: Optional[int] = None,
        smooth_scroll: bool = True,
        scroll_style: bool = True,
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

        Raises:
            RuntimeError: 调用前 ``QApplication`` 还没创建。
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

        # 2) 触发 _boot 显式入口（按开关激活兄弟模块；置 _setup_done=True
        #    短路后续组件构造路径上的隐式钩子，让 False 开关真生效）
        from ._boot import setup_with_options

        setup_with_options(
            smooth_scroll=smooth_scroll,
            scroll_style=scroll_style,
        )

        # 3) 应用用户级配置（必须在 _boot 激活之后，确保各 Provider 单例已就绪）
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


__all__ = ["HeroSideUIProvider"]
