"""
HeroUI v2 字体系统 (Font)
==========================

全局共享的字体栈。

历史上 ``FONT_FAMILY`` 是一个静态字符串常量，被 18 个组件直接 ``from ...themes
import FONT_FAMILY`` 引用并拼进 QSS。现在改造为**模块级动态属性**：每次访问
``FONT_FAMILY`` 都会去查 :class:`hero_side_ui.core.font_provider.FontProvider`
当前的字体栈，从而：

- 内置思源黑体加载成功 → 自动得到 ``"Source Han Sans CN", "Inter", ...``。
- 加载失败或 FontProvider 未初始化（如 ``QApplication`` 还没建出来）→ 回退到
  原始 Inter/系统字体栈，与历史行为完全一致。

注意：``from ...themes import FONT_FAMILY`` 这种语句**只在 import 时取一次**，
之后即便 ``FontProvider.set_family()`` 切换了字体，也不会自动更新已经创建的
组件 QSS。如果需要"运行时切字体"，组件应该把 family 读取放到 ``_apply_font()``
之类的入口里、并向 ``FontProvider.register()`` 注册自己。
"""

from __future__ import annotations

# 与 FontProvider 内部 ``_FALLBACK_FAMILY_CSS`` 保持一致；
# 这一份独立常量用于 FontProvider 还没初始化（譬如还没 QApplication）的早期 import。
_FALLBACK_FONT_FAMILY = (
    '"Inter", "SF Pro Display", -apple-system, '
    '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
)


def __getattr__(name: str):
    """模块级动态属性：``FONT_FAMILY`` → FontProvider 当前字体栈。

    PEP 562 (Python 3.7+) 允许在模块级定义 ``__getattr__``，仅当通过属性访问
    （``themes.font.FONT_FAMILY`` 或 ``from .font import FONT_FAMILY``）找不到
    模块级名字时才会被触发。性能开销可忽略（一次属性查询）。
    """
    if name == "FONT_FAMILY":
        # 延迟 import：避免 themes 包在 QApplication 之前 import 时拉起 Qt
        try:
            from ..core.font_provider import FontProvider
        except Exception:
            return _FALLBACK_FONT_FAMILY
        try:
            return FontProvider.instance().font_family_css()
        except Exception:
            return _FALLBACK_FONT_FAMILY
    raise AttributeError(f"module 'hero_side_ui.themes.font' has no attribute {name!r}")


__all__ = ["FONT_FAMILY"]
