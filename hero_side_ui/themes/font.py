"""HeroUI 字体系统：FONT_FAMILY 为 PEP 562 动态属性，每次访问查 FontProvider
当前字体栈（失败回退 Inter/系统栈）。运行时切字体需组件注册 FontProvider。
"""

from __future__ import annotations

# 与 FontProvider 内部 ``_FALLBACK_FAMILY_CSS`` 保持一致；
# 这一份独立常量用于 FontProvider 还没初始化（譬如还没 QApplication）的早期 import。
_FALLBACK_FONT_FAMILY = (
    '"Inter", "SF Pro Display", -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif'
)


def __getattr__(name: str):
    """按 PEP 562 解析动态属性 FONT_FAMILY，返回 FontProvider 当前字体栈。

    Args:
        name: 待解析的模块属性名。

    Returns:
        当前字体栈 CSS 字符串；FontProvider 不可用时返回回退字体栈。

    Note:
        延迟 import 以免 themes 包在 QApplication 之前导入时拉起 Qt；
        非 FONT_FAMILY 的属性名会抛 AttributeError。
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


__all__ = ["FONT_FAMILY"]  # noqa: F822  # PEP 562 动态属性，见上方 __getattr__
