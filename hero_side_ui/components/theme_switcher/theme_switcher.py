"""ThemeSwitcher 主题切换按钮：内嵌太阳/月亮 icon，点击 toggle 全局主题。

基于 Button 实现，支持自定义 icon/颜色/尺寸/圆角。
"""

from typing import ClassVar

from PySide6.QtCore import QObject, QSize
from PySide6.QtGui import QColor, QIcon

from ...core import ThemeProvider
from ...utils import load_svg_icon
from ..button import Button

# 默认 icon（内置）
DEFAULT_SUN_ICON = "flowbite--sun-solid"
DEFAULT_MOON_ICON = "ri--moon-clear-fill"

# 默认颜色
DEFAULT_SUN_COLOR = "#F5A524"  # 金黄色（warning-500）
DEFAULT_MOON_COLOR = "#7DD3FC"  # 蓝色（sky-300，柔和的月光蓝）


class ThemeSwitcher(Button):
    """主题切换按钮，点击切换全局亮暗主题并同步太阳/月亮 icon。

    Note:
        始终以 auto 主题运行，set_theme 被覆写为不锁死主题；点击通过
        ThemeProvider.instance().toggle() 切换，icon 随主题广播刷新。
    """

    # 不同 size 的默认 icon 像素尺寸（约占按钮 50%）
    _ICON_SIZE_MAP: ClassVar[dict[str, int]] = {"sm": 16, "md": 24, "lg": 32}

    def __init__(
        self,
        sun_icon: str = DEFAULT_SUN_ICON,
        moon_icon: str = DEFAULT_MOON_ICON,
        sun_color: "str | QColor" = DEFAULT_SUN_COLOR,
        moon_color: "str | QColor" = DEFAULT_MOON_COLOR,
        icon_size: int | None = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str | None = "full",
        parent: QObject | None = None,
    ):
        """创建主题切换按钮，强制以 icon_only 圆形按钮承载主题 icon。

        Args:
            sun_icon: 亮色模式 icon，内置图标名或 SVG 路径。
            moon_icon: 暗色模式 icon，内置图标名或 SVG 路径。
            sun_color: 太阳 icon 颜色，HEX 字符串或 QColor。
            moon_color: 月亮 icon 颜色，HEX 字符串或 QColor。
            icon_size: icon 像素尺寸；未传时按 Button size 选默认值。
            variant: Button 样式变体。
            color: Button 颜色。
            size: Button 尺寸，sm / md / lg。
            radius: Button 圆角。
            parent: Qt 父对象。

        Note:
            icon_only 被强制为 True，theme 固定为 auto；icon 依当前主题
            在太阳/月亮间切换。
        """
        super().__init__(
            text="",
            color=color,
            variant=variant,
            size=size,
            radius=radius,
            icon_only=True,
            parent=parent,
            theme="auto",
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
        """调用 ThemeProvider 切换全局亮暗主题。"""
        ThemeProvider.instance().toggle()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播主题时被调用 —— 同时刷新 icon。"""
        # 调父类的 provider 主题应用（更新 Button 自身 light/dark 样式）
        super()._apply_provider_theme(theme)
        # 再刷新 icon（基于 theme 决定显示太阳还是月亮）
        self._refresh_icon()

    def _refresh_icon(self):
        """根据当前实际主题刷新 icon。"""
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
        """设置亮色模式的 icon（内置图标名或 SVG 路径）。"""
        self._sun_icon_src = name_or_path
        self._refresh_icon()

    def set_moon_icon(self, name_or_path: str):
        """设置暗色模式的 icon。"""
        self._moon_icon_src = name_or_path
        self._refresh_icon()

    def set_sun_color(self, color: "str | QColor"):
        """设置太阳 icon 颜色。"""
        self._sun_color = QColor(color) if not isinstance(color, QColor) else color
        self._refresh_icon()

    def set_moon_color(self, color: "str | QColor"):
        """设置月亮 icon 颜色。"""
        self._moon_color = QColor(color) if not isinstance(color, QColor) else color
        self._refresh_icon()

    def set_icon_size(self, size_px: int):
        """设置 icon 像素尺寸。"""
        self._icon_size = int(size_px)
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self._refresh_icon()

    # 重写 set_theme：ThemeSwitcher 始终是 auto，不允许硬锁
    def set_theme(self, theme: str):
        """强制按 auto 主题运行并刷新 icon。

        Note:
            ThemeSwitcher 不允许硬锁主题，忽略传入的 theme 走 auto 路径。
        """
        # 始终走 auto 路径，并刷新 icon
        super().set_theme("auto")
        self._refresh_icon()
