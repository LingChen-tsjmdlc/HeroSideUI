"""HeroSideUI icon resource boundary; rendering is owned by pyside-iconify.

Bundled SVGs are the only source of built-in data. Neither this module nor its
consumers change the dependency's network policy or global defaults.
"""

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
    """Return a native QIcon; other options are validated by pyside-iconify."""
    return _get_icon(resolve_icon(icon, stroke_width=stroke_width), size=size, **options)


def get_pixmap(
    icon: IconSource, *, size=None, stroke_width: float | None = None, **options
) -> QPixmap:
    """Return a static snapshot. Preload remote names or use Icon for live loading."""
    return _get_pixmap(resolve_icon(icon, stroke_width=stroke_width), size=size, **options)
