"""
HeroSideUI ThemeSwitcher Component
亮暗色主题切换按钮 — 一键切换全局主题

使用 HeroSideUI 自己的 Button 组件，内嵌太阳/月亮 icon，
点击后调用 ThemeProvider.toggle() 切换全局主题。

用法:
    from hero_side_ui import ThemeSwitcher

    # 默认: 亮色显示太阳（金黄），暗色显示月亮（蓝色）
    switcher = ThemeSwitcher()

    # 自定义颜色
    switcher = ThemeSwitcher(
        sun_color="#FF8800",
        moon_color="#88CCFF",
    )

    # 自定义 icon（传内置图标名或 SVG 路径）
    switcher = ThemeSwitcher(
        sun_icon="heroicons--sun-solid",
        moon_icon="C:/my/moon.svg",
    )

    # 自定义 Button 外观
    switcher = ThemeSwitcher(
        variant="flat",
        color="default",
        size="md",
        radius="full",
    )
"""

from typing import Optional

from PySide6.QtCore import QSize, QObject
from PySide6.QtGui import QIcon, QColor

from ..button import Button
from ...core import ThemeProvider
from ...utils import load_svg_icon


# 默认 icon（内置）
DEFAULT_SUN_ICON = "flowbite--sun-solid"
DEFAULT_MOON_ICON = "ri--moon-clear-fill"

# 默认颜色
DEFAULT_SUN_COLOR = "#F5A524"   # 金黄色（warning-500）
DEFAULT_MOON_COLOR = "#7DD3FC"  # 蓝色（sky-300，柔和的月光蓝）


class ThemeSwitcher(Button):
    """主题切换按钮

    继承自 HeroSideUI 的 Button，点击后自动调用
    ``ThemeProvider.instance().toggle()`` 切换全局亮暗色。

    会根据 ThemeProvider 当前主题自动切换显示的 icon：
    - 亮色模式 → 显示太阳 icon（默认金黄色）
    - 暗色模式 → 显示月亮 icon（默认蓝色）

    Args:
        sun_icon: 亮色模式的 icon — 内置图标名或 SVG 路径。默认 sun-solid。
        moon_icon: 暗色模式的 icon — 内置图标名或 SVG 路径。默认 moon-clear-fill。
        sun_color: 太阳 icon 颜色（HEX 字符串或 QColor）。默认金黄 `#F5A524`。
        moon_color: 月亮 icon 颜色（HEX 字符串或 QColor）。默认蓝 `#7DD3FC`。
        icon_size: icon 像素尺寸。默认根据 Button size 自动选择（sm=14/md=16/lg=18）。
        variant: Button 样式变体。默认 `"flat"`（柔和的半透明底色）。
        color: Button 颜色（影响 hover 等）。默认 `"default"`。
        size: Button 尺寸 (`"sm"`/`"md"`/`"lg"`)。默认 `"md"`。
        radius: Button 圆角。默认 `"full"`（圆形按钮，最适合图标按钮）。
        其余参数透传给 Button（icon_only 被强制为 True）。
    """

    # 不同 size 的默认 icon 像素尺寸（约占按钮 50%）
    _ICON_SIZE_MAP = {"sm": 16, "md": 24, "lg": 32}

    def __init__(
        self,
        sun_icon: str = DEFAULT_SUN_ICON,
        moon_icon: str = DEFAULT_MOON_ICON,
        sun_color: "str | QColor" = DEFAULT_SUN_COLOR,
        moon_color: "str | QColor" = DEFAULT_MOON_COLOR,
        icon_size: Optional[int] = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = "full",
        parent: Optional[QObject] = None,
        **kwargs,
    ):
        # ThemeSwitcher 自身始终跟随全局（auto），不需要用户改 theme
        kwargs.pop("theme", None)
        # icon_only 由 ThemeSwitcher 强制开启，不允许用户覆盖
        kwargs.pop("icon_only", None)

        super().__init__(
            text="",
            color=color,
            variant=variant,
            size=size,
            radius=radius,
            icon_only=True,
            parent=parent,
            theme="auto",
            **kwargs,
        )

        self._sun_icon_src = sun_icon
        self._moon_icon_src = moon_icon
        self._sun_color = QColor(sun_color) if not isinstance(sun_color, QColor) else sun_color
        self._moon_color = QColor(moon_color) if not isinstance(moon_color, QColor) else moon_color
        self._icon_size = icon_size or self._ICON_SIZE_MAP.get(size, 16)

        # Button.setIconSize 需要 QSize
        self.setIconSize(QSize(self._icon_size, self._icon_size))

        # 初始 icon 同步
        self._refresh_icon()

        # 绑定点击 → 切换主题
        self.clicked.connect(self._on_clicked)

    # ============================================================
    # 主题切换
    # ============================================================
    def _on_clicked(self):
        ThemeProvider.instance().toggle()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播主题时被调用 —— 同时刷新 icon"""
        # 调父类的 provider 主题应用（更新 Button 自身 light/dark 样式）
        super()._apply_provider_theme(theme)
        # 再刷新 icon（基于 theme 决定显示太阳还是月亮）
        self._refresh_icon()

    def _refresh_icon(self):
        """根据当前实际主题刷新 icon"""
        theme = self._theme
        if theme == "dark":
            pixmap = load_svg_icon(
                self._moon_icon_src,
                size=self._icon_size,
                color=self._moon_color,
            )
        else:
            pixmap = load_svg_icon(
                self._sun_icon_src,
                size=self._icon_size,
                color=self._sun_color,
            )
        self.setIcon(QIcon(pixmap))

    # ============================================================
    # 公共 API
    # ============================================================
    def set_sun_icon(self, name_or_path: str):
        """设置亮色模式的 icon（内置图标名或 SVG 路径）"""
        self._sun_icon_src = name_or_path
        self._refresh_icon()

    def set_moon_icon(self, name_or_path: str):
        """设置暗色模式的 icon"""
        self._moon_icon_src = name_or_path
        self._refresh_icon()

    def set_sun_color(self, color: "str | QColor"):
        """设置太阳 icon 颜色"""
        self._sun_color = QColor(color) if not isinstance(color, QColor) else color
        self._refresh_icon()

    def set_moon_color(self, color: "str | QColor"):
        """设置月亮 icon 颜色"""
        self._moon_color = QColor(color) if not isinstance(color, QColor) else color
        self._refresh_icon()

    def set_icon_size(self, size_px: int):
        """设置 icon 像素尺寸"""
        self._icon_size = int(size_px)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self._refresh_icon()

    # 重写 set_theme：ThemeSwitcher 始终是 auto，不允许硬锁
    def set_theme(self, theme: str):
        # 始终走 auto 路径，并刷新 icon
        super().set_theme("auto")
        self._refresh_icon()
