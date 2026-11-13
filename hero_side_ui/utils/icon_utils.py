"""旧静态快照兼容入口，转调 icons/ 资源边界；保留 DPR=1 契约。
新组件用 Icon；新渲染代码用 hero_side_ui.icons。
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPixmap

from ..icons import IconNotFoundError, get_icon, resolve_icon


def _resolve_theme_aware_color() -> str:
    """返回未指定颜色时的默认图标色。

    Note:
        旧 API 的兼容边界：ThemeProvider 已存在时跟随其主题，否则用浅色主题色，
        不会创建 Provider。
    """
    from ..core import ThemeProvider

    provider = ThemeProvider.peek()
    return "#fafafa" if provider is not None and provider.current_theme == "dark" else "#18181b"


def load_svg_icon(
    name_or_path: str,
    size: int = 24,
    color=None,
    stroke_width: int | float | None = None,
) -> QPixmap:
    """返回旧式静态快照；远程名需先预加载，新场景用 Icon。"""
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
