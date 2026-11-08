"""Compatibility entry for static SVG snapshots, rendered by pyside-iconify.

The legacy API deliberately retains size-by-size, DPR=1 snapshots, transparent
missing icons, original SVG colors and the Provider-aware default contrast.
New widgets use hero_side_ui.Icon; new rendering code uses hero_side_ui.icons.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPixmap

from ..icons import IconNotFoundError, get_icon, resolve_icon


def _resolve_theme_aware_color() -> str:
    # Retained at the compatibility boundary; resource/rendering modules do not
    # query Providers or install global facilities.
    from ..core import ThemeProvider

    return "#fafafa" if ThemeProvider.instance().current_theme == "dark" else "#18181b"


def load_svg_icon(
    name_or_path: str,
    size: int = 24,
    color=None,
    stroke_width: int | float | None = None,
) -> QPixmap:
    """Return the legacy static snapshot; remote names should be preloaded.

    Bundled names, Iconify names already available locally and external SVG paths
    all use the shared icon resource boundary. Use Icon for live asynchronous icons.
    """
    try:
        resolved = resolve_icon(name_or_path, stroke_width=stroke_width)
    except (FileNotFoundError, IconNotFoundError):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        return pixmap
    if color is None:
        tint = _resolve_theme_aware_color()
    elif isinstance(color, str) and color == "original":
        tint = {}  # Explicit empty mapping preserves SVG colors, ignoring defaults.
    elif isinstance(color, QColor):
        tint = color.name()
    else:
        tint = color
    try:
        icon = get_icon(
            resolved,
            size=size,
            color=tint,
            color_light_theme=tint,
            color_dark_theme=tint,
            opacity=1.0,
        )
    except (FileNotFoundError, IconNotFoundError):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        return pixmap
    return icon.pixmap(QSize(size, size), 1.0)
