"""HeroSideUI theme and resource adapter for pyside-iconify's IconWidget."""

from PySide6.QtGui import QPalette
from pyside_iconify import IconWidget, get_icon_data

from ...core import ThemeProvider, resolve_text_color
from ...icons import IconSource, resolve_icon
from ...icons._sources import ensure_local_icon
from ...themes import HEROUI_COLORS, ICON_SIZES

_UNSET = object()


def _size(value):
    return ICON_SIZES.get(value, value) if isinstance(value, str) else value


def _color(value):
    if isinstance(value, str):
        name, separator, shade = value.partition("-")
        if name in HEROUI_COLORS and (not separator or shade.isdigit()):
            palette = HEROUI_COLORS[name]
            level = int(shade) if separator else 500
            if level not in palette:
                raise ValueError(f"unknown icon color token: {value}")
            return palette[level]
    return value


class Icon(IconWidget):
    """An IconWidget with bundled resources, HeroUI tokens and local theme.

    Native rendering, loading signals, hover and animation methods are inherited.
    Iconify names not bundled locally use the dependency's normal loading path.
    """

    def __init__(
        self,
        icon: IconSource,
        *,
        size="md",
        color=None,
        color_light_theme=None,
        color_dark_theme=None,
        hover_color=None,
        hover_color_light_theme=None,
        hover_color_dark_theme=None,
        opacity=None,
        width=None,
        height=None,
        rotate=0,
        rotate_overflow=False,
        spin=False,
        spin_period=None,
        animation=None,
        animation_period=None,
        animation_depth=None,
        autoplay=True,
        speed=1.0,
        h_flip=False,
        v_flip=False,
        qss=None,
        fallback=_UNSET,
        is_disabled=False,
        theme="auto",
        parent=None,
    ):
        if theme not in ("auto", "light", "dark"):
            raise ValueError("theme must be 'auto', 'light' or 'dark'")
        self._hero_theme_mode = theme
        self._remember_source(icon)
        fallback_options = {}
        self._hero_local_fallback = None
        if fallback is not _UNSET:
            fallback_name = resolve_icon(fallback) if fallback is not None else None
            fallback_options["fallback"] = fallback_name
            if fallback_name is not None and fallback_name.startswith("herosideui:"):
                self._hero_local_fallback = (fallback_name, get_icon_data(fallback_name))
        self._restore_local_data()
        super().__init__(
            self._hero_resolved,
            size=_size(size),
            color=_color(color),
            color_light_theme=_color(color_light_theme),
            color_dark_theme=_color(color_dark_theme),
            hover_color=_color(hover_color),
            hover_color_light_theme=_color(hover_color_light_theme),
            hover_color_dark_theme=_color(hover_color_dark_theme),
            opacity=opacity,
            width=width,
            height=height,
            rotate=rotate,
            rotate_overflow=rotate_overflow,
            spin=spin,
            spin_period=spin_period,
            animation=animation,
            animation_period=animation_period,
            animation_depth=animation_depth,
            autoplay=autoplay,
            speed=speed,
            h_flip=h_flip,
            v_flip=v_flip,
            qss=qss,
            parent=parent,
            **fallback_options,
        )
        self.setEnabled(not is_disabled)
        if theme == "auto":
            ThemeProvider.instance().register(self)
        else:
            self._apply_provider_theme(theme)

    def _remember_source(self, icon):
        resolved = resolve_icon(icon)
        self._hero_resolved = resolved
        self._hero_local_data = get_icon_data(resolved) if resolved.startswith("herosideui:") else None

    def setIcon(self, icon):
        self._remember_source(icon)
        super().setIcon(self._hero_resolved)

    def set_icon(self, icon):
        self.setIcon(icon)

    def setSize(self, size):
        super().setSize(_size(size))

    def set_size(self, size):
        self.setSize(size)

    def setColor(self, color):
        super().setColor(_color(color))

    def set_color(self, color):
        self.setColor(color)

    def setColorLightTheme(self, color):
        super().setColorLightTheme(_color(color))

    def setColorDarkTheme(self, color):
        super().setColorDarkTheme(_color(color))

    def set_theme(self, theme):
        if theme not in ("auto", "light", "dark"):
            raise ValueError("theme must be 'auto', 'light' or 'dark'")
        if self._hero_theme_mode == "auto":
            ThemeProvider.instance().unregister(self)
        self._hero_theme_mode = theme
        if theme == "auto":
            ThemeProvider.instance().register(self)
        else:
            self._apply_provider_theme(theme)

    def _apply_provider_theme(self, theme):
        palette = QPalette(self.palette())
        background = "default-900" if theme == "dark" else "default-50"
        palette.setColor(QPalette.ColorRole.Window, resolve_text_color(background, theme))
        palette.setColor(QPalette.ColorRole.WindowText, resolve_text_color(None, theme))
        # Clear Qt's stylesheet palette snapshot before replacing local colors.
        # Otherwise IconWidget's repolish can restore the previous theme palette.
        style = self.style()
        style.unpolish(self)
        self.setPalette(palette)
        style.polish(self)
        self.update()

    def _restore_local_data(self):
        if self._hero_local_fallback is not None:
            ensure_local_icon(*self._hero_local_fallback)
        # Keep the primary icon last when the shared data cache is very small.
        if self._hero_local_data is not None:
            ensure_local_icon(self._hero_resolved, self._hero_local_data)

    def paintEvent(self, event):
        # Restoring owned data prevents shared registry eviction from turning a
        # bundled widget into an unintended network lookup. No client is changed.
        self._restore_local_data()
        super().paintEvent(event)
