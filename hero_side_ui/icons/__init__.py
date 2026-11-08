"""Icon 资源边界：内置 SVG 唯一来源，渲染归 pyside-iconify；不改其网络策略。"""

from PySide6.QtGui import QIcon, QPixmap
from pyside_iconify import IconNotFoundError
from pyside_iconify import get_icon as _get_icon
from pyside_iconify import get_pixmap as _get_pixmap

from ._sources import IconSource, builtin_icon_names, resolve_icon

__all__ = [
    "IconNotFoundError",
    "IconSource",
    "builtin_icon_names",
    "get_icon",
    "get_pixmap",
    "resolve_icon",
]


def get_icon(icon: IconSource, *, size=None, stroke_width: float | None = None, **options) -> QIcon:
    """返回原生 QIcon，其余选项交由 pyside-iconify 校验。"""
    return _get_icon(resolve_icon(icon, stroke_width=stroke_width), size=size, **options)


def get_pixmap(
    icon: IconSource, *, size=None, stroke_width: float | None = None, **options
) -> QPixmap:
    """返回静态 QPixmap 快照，远程图标名需先预加载。"""
    return _get_pixmap(resolve_icon(icon, stroke_width=stroke_width), size=size, **options)
