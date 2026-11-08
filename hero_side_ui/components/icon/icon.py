"""HeroSideUI theme and resource adapter for pyside-iconify's IconWidget."""

from PySide6.QtGui import QPalette
from pyside_iconify import IconWidget, get_icon_data

from ...core import ThemeProvider, resolve_text_color
from ...icons import IconSource, resolve_icon
from ...icons._sources import ensure_local_icon
from ...themes import HEROUI_COLORS, ICON_SIZES

_UNSET = object()


def _size(value):
    """把尺寸档位 token 解析成实际像素值。

    Args:
        value: 尺寸档位名或原始数值。

    Returns:
        ICON_SIZES 中对应值；非字符串原样返回。
    """
    return ICON_SIZES.get(value, value) if isinstance(value, str) else value


def _color(value):
    """把语义色 token（如 danger-500）解析成十六进制色。

    Args:
        value: 颜色 token 或原始颜色值。

    Returns:
        对应色阶的十六进制字符串；非 token 原样返回。

    Raises:
        ValueError: token 的色阶不在调色板中时抛出。
    """
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
    """带内置资源、HeroUI token 与局部主题的 IconWidget 子类。

    渲染、加载信号、hover 与动画继承自依赖库；未内置的 Iconify 名走
    依赖库正常加载路径。
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
        """创建带内置资源与 HeroUI token 支持的图标。

        Args:
            icon: 图标来源（内置名 / Iconify 名 / 本地路径）。
            size: 尺寸档位或像素值。
            color: 主色（可为 HeroUI token）。
            color_light_theme: 亮色主题专用主色。
            color_dark_theme: 暗色主题专用主色。
            hover_color: hover 主色。
            hover_color_light_theme: hover 亮色主题色。
            hover_color_dark_theme: hover 暗色主题色。
            opacity: 不透明度。
            width: 显式宽度。
            height: 显式高度。
            rotate: 旋转角度。
            rotate_overflow: 允许旋转溢出边界。
            spin: 是否持续旋转。
            spin_period: 旋转周期。
            animation: 动画类型。
            animation_period: 动画周期。
            animation_depth: 动画幅度。
            autoplay: 是否自动播放。
            speed: 动画速度倍率。
            h_flip: 水平翻转。
            v_flip: 垂直翻转。
            qss: 附加样式表。
            fallback: 加载失败时的备用图标；默认哨兵表示未指定。
            is_disabled: 禁用。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Raises:
            ValueError: theme 非法或颜色 token 色阶不存在时抛出。

        Note:
            渲染、加载信号、hover 与动画继承自 pyside-iconify；
            未内置的 Iconify 名走依赖库正常加载路径。
        """
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
        """解析并记录图标来源，内置资源顺带取回 SVG 数据。

        Args:
            icon: 原始图标来源。
        """
        resolved = resolve_icon(icon)
        self._hero_resolved = resolved
        self._hero_local_data = (
            get_icon_data(resolved) if resolved.startswith("herosideui:") else None
        )

    def setIcon(self, icon):
        """覆写 setIcon：先按 HeroSideUI 规则解析来源。

        Args:
            icon: 新图标来源。
        """
        self._remember_source(icon)
        super().setIcon(self._hero_resolved)

    def set_icon(self, icon):
        """setIcon 的别名。

        Args:
            icon: 新图标来源。
        """
        self.setIcon(icon)

    def setSize(self, size):
        """覆写 setSize：支持尺寸 token。

        Args:
            size: 尺寸档位名或像素值。
        """
        super().setSize(_size(size))

    def set_size(self, size):
        """setSize 的别名。

        Args:
            size: 尺寸档位名或像素值。
        """
        self.setSize(size)

    def setColor(self, color):
        """覆写 setColor：支持 HeroUI 颜色 token。

        Args:
            color: 颜色 token 或原始颜色值。
        """
        super().setColor(_color(color))

    def set_color(self, color):
        """setColor 的别名。

        Args:
            color: 颜色 token 或原始颜色值。
        """
        self.setColor(color)

    def setColorLightTheme(self, color):
        """覆写亮色主题专用色设置，支持颜色 token。

        Args:
            color: 颜色 token 或原始颜色值。
        """
        super().setColorLightTheme(_color(color))

    def setColorDarkTheme(self, color):
        """覆写暗色主题专用色设置，支持颜色 token。

        Args:
            color: 颜色 token 或原始颜色值。
        """
        super().setColorDarkTheme(_color(color))

    def set_theme(self, theme):
        """切换主题并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Raises:
            ValueError: theme 非法时抛出。
        """
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
        """按主题重设局部 palette 让 IconWidget 正确取色。

        Args:
            theme: light / dark。

        Note:
            替换本地颜色前必须先 unpolish，否则 IconWidget 的 repolish
            会用样式表快照恢复回旧主题 palette。
        """
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
        """把内置图标数据重新登记进共享缓存。

        Note:
            防止共享 registry 容量淘汰后把内置图标误判为需要网络加载；
            主图标最后登记，保证极小缓存下优先保留。
        """
        if self._hero_local_fallback is not None:
            ensure_local_icon(*self._hero_local_fallback)
        # Keep the primary icon last when the shared data cache is very small.
        if self._hero_local_data is not None:
            ensure_local_icon(self._hero_resolved, self._hero_local_data)

    def paintEvent(self, event):
        """绘制前恢复内置资源登记，再交给父类绘制。

        Args:
            event: Qt 绘制事件。
        """
        # Restoring owned data prevents shared registry eviction from turning a
        # bundled widget into an unintended network lookup. No client is changed.
        self._restore_local_data()
        super().paintEvent(event)
