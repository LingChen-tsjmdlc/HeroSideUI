"""默认字体栈常量。运行时字体由 core.FontProvider 管理。"""

from __future__ import annotations

import warnings

DEFAULT_FONT_FAMILY = (
    '"Inter", "SF Pro Display", -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif'
)


def __getattr__(name: str):
    """兼容旧属性 FONT_FAMILY，返回静态默认字体栈。

    Args:
        name: 被访问的模块属性名。

    Returns:
        默认字体栈；它不再跟随 FontProvider 切换。

    Raises:
        AttributeError: 名称不是 FONT_FAMILY。
    """
    if name == "FONT_FAMILY":
        warnings.warn(
            "FONT_FAMILY is deprecated and no longer follows the active font; "
            "use FontProvider.instance().font_family_css() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DEFAULT_FONT_FAMILY
    raise AttributeError(f"module 'hero_side_ui.themes.font' has no attribute {name!r}")


__all__ = ["DEFAULT_FONT_FAMILY"]
