"""Compatibility import for the former component-local trigger.

该模块只保留转发：SelectorButton 已上移到 _shared/selection，
旧 import 路径（autocomplete._selector_button）靠它兼容存量代码。
"""

from ..._shared.selection import SelectorButton as _SelectorButton

__all__ = ["_SelectorButton"]
