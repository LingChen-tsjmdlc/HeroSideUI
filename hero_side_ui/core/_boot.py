"""core 全局基础设施启动钩子（内部模块）。

显式路径 setup_with_options 按用户参数激活；隐式路径 ensure_core_ready
在首次组件构造时以默认值降级激活并 warning 一次。各 ensure 幂等。
"""

from __future__ import annotations

import warnings

_booted: bool = False
_setup_done: bool = False
_warned: bool = False

# 双语 friendly-fallback warning（仅打一次）
_FALLBACK_WARNING = (
    "\n⚠️  HeroSideUI components were created before HeroSideUIProvider.setup().\n"
    "Auto-initializing with defaults. For explicit control, recommended:\n"
    "    from hero_side_ui import HeroSideUIProvider\n"
    "    HeroSideUIProvider.setup(app)\n"
    "at the start of your application.\n"
    "\n"
    "⚠️  HeroSideUI 组件在 HeroSideUIProvider.setup() 之前被创建。\n"
    "已自动以默认配置初始化。推荐显式调用：\n"
    "    from hero_side_ui import HeroSideUIProvider\n"
    "    HeroSideUIProvider.setup(app)"
)


def ensure_core_ready() -> None:
    """隐式激活全部 core 设施（友好降级路径，由 ThemeProvider 单例触发）。

    用户已显式 setup 时直接返回；首次触发打双语 warning。
    """
    global _booted, _warned
    if _setup_done or _booted:
        return

    # 友好降级提示（一次性）
    if not _warned:
        warnings.warn(_FALLBACK_WARNING, stacklevel=3)
        _warned = True

    _activate_defaults()


def setup_with_options(
    *,
    smooth_scroll: bool = True,
    scroll_style: bool = True,
) -> None:
    """显式激活入口（HeroSideUIProvider.setup 调用，不对用户暴露）。

    Args:
        smooth_scroll: False 时跳过平滑滚动模块。
        scroll_style: False 时跳过滚动条样式模块。

    Note:
        多次调用安全但参数以第一次为准；变更配置请直调各模块 setter。
    """
    global _booted, _setup_done
    _setup_done = True
    if _booted:
        return

    try:
        from .font_provider import FontProvider

        FontProvider.instance()  # 内部 ensure_loaded()

        if scroll_style:
            from .scroll_style import ScrollStyle

            ScrollStyle.instance()  # 内部 ensure_applied()

        if smooth_scroll:
            from .smooth_scroll import SmoothScroll

            SmoothScroll.ensure_applied()
    except Exception:
        # 兜底：兄弟模块若挂了不影响 ThemeProvider 主线可用
        return

    _booted = True


def _activate_defaults() -> None:
    """全套默认激活（友好降级走这里）。"""
    global _booted
    try:
        from .font_provider import FontProvider
        from .scroll_style import ScrollStyle
        from .smooth_scroll import SmoothScroll

        FontProvider.instance()
        ScrollStyle.instance()
        SmoothScroll.ensure_applied()
    except Exception:
        return

    _booted = True


def _reset_for_test() -> None:
    """仅供单元测试：复位启动标志，让钩子可重新触发。"""
    global _booted, _setup_done, _warned
    _booted = False
    _setup_done = False
    _warned = False
