"""
HeroSideUI core 全局基础设施启动钩子（内部模块，不对外）

本模块的职责：作为"中性触发点"统一激活所有 core 全局设施。

两条触发路径：
1. **显式**：用户调 ``HeroSideUIProvider.setup(app, ...)`` → ``setup_with_options(...)``
   按用户参数激活，置 ``_setup_done = True``。
2. **隐式（友好降级）**：用户没调 setup() 直接构造组件 → ``ThemeProvider.instance()``
   首次创建触发 ``ensure_core_ready()`` → 一次性双语 warning + 用默认值激活。

幂等保证：
- 各模块自身的 ensure_*() / instance() 都是幂等的（QApplication 不在则跳过等下次）。
- 本钩子用 ``_booted`` 标志再加一层短路，重复调用零开销。
- ``_setup_done`` 优先级最高：用户显式 setup 后，隐式钩子永不再激活，让用户的开关
  （比如 smooth_scroll=False）真生效，不被组件构造时的二次触发覆盖。
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
    """隐式激活全部 core 全局基础设施（友好降级路径）。

    调用时机：``ThemeProvider`` 单例首次创建后由其内部触发。
    用户层永远不需要直接调本函数——这是内部钩子。

    行为：
    - 如果用户已显式 ``setup()``：直接 return（不重复激活，让 setup 的开关生效）。
    - 否则：第一次触发时打双语 warning + 全套默认激活。

    QApplication 未起来时各模块各自跳过；下次任意组件构造再次触发
    ``ThemeProvider.instance()`` → 本钩子 → 各模块再尝试一次，直至成功。
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
    """显式激活入口（被 ``HeroSideUIProvider.setup()`` 调用，不对用户暴露）。

    与 ``ensure_core_ready`` 的差异：
    - 不打 warning（用户主动调，不是降级）。
    - 接受 smooth_scroll / scroll_style 开关，False 时跳过对应模块。
    - 设 ``_setup_done = True``，后续隐式钩子永不再触发，开关真生效。

    幂等：多次调用安全（_booted 短路），但参数仅以**第一次**为准；如需变更
    具体配置，请直接调对应模块（FontProvider / ScrollStyle / SmoothScroll）的 setter。
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
