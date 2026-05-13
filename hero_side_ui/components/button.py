"""
HeroSideUI Button Component
基于HeroUI v2设计风格，保持PySide原生API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/button.ts
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QObject, Qt, QSize, QEvent
from PySide6.QtGui import QColor, QIcon, QPixmap
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, BUTTON_SIZES
from ..utils import hex_to_rgba, load_svg_icon
from ..animation import RippleOverlay, PressScaleEffect
from ..core import ThemeProvider


class Button(QPushButton):
    """
    HeroUI 风格的按钮组件

    特性：
    - 保持 PySide 原生 API (继承 QPushButton)
    - 支持颜色 (default, primary, secondary, success, warning, danger)
    - 支持变体 (solid, bordered, flat, light, faded, ghost)
    - 支持尺寸 (sm, md, lg)
    - 支持圆角 (none, sm, md, lg, full)
    - 支持主题 (light, dark, auto) — auto 跟随 ThemeProvider 全局切换
    - 支持 icon_only 模式（锁成正方形，适合纯图标按钮）
    - 支持 icon 参数（内置图标名或 SVG 路径）——icon 颜色自动根据 variant/color/theme
      和 hover 状态切换，用户不用关心配色
    - 按压视觉反馈 (通过 QSS padding 模拟缩放)

    用法:
        btn = Button("Click me", color="primary", variant="solid", size="md")
        btn_dark = Button("Dark", color="primary", variant="flat", theme="dark")
        btn_auto = Button("Auto", theme="auto")  # 跟随系统/全局主题
        btn_icon = Button(icon_only=True, icon="heroicons--eye-solid", variant="flat")
        btn_with_icon = Button("搜索", icon="heroicons--magnifying-glass-solid")
    """

    def __init__(
        self,
        text: str = "",
        color: str = "primary",
        variant: str = "solid",
        size: str = "md",
        radius: Optional[str] = None,
        is_disabled: bool = False,
        full_width: bool = False,
        icon_only: bool = False,
        icon: Optional[str] = None,
        icon_size: Optional[int] = None,
        icon_color=None,
        parent: Optional[QObject] = None,
        theme: str = "auto",
        **kwargs,
    ):
        super().__init__(text, parent)

        self._color = color
        self._variant = variant
        self._size = size
        self._radius = radius
        self._full_width = full_width
        self._icon_only = icon_only
        self._icon_src = icon
        self._icon_size_override = icon_size
        self._icon_color_override = icon_color  # 用户显式指定则覆盖自动配色
        self._icon_only_side_override: Optional[int] = None  # 外部锁 icon_only 边长(px)
        self._is_hovered = False
        self._theme_mode = theme  # 用户设定的模式: "auto"/"light"/"dark"
        self._theme = self._resolve_theme(theme)  # 实际生效: "light"/"dark"
        self._disable_ripple = kwargs.get("disable_ripple", False)

        # 应用样式
        self._apply_styles()

        # 水波纹覆盖层
        self._ripple_overlay = None
        if not self._disable_ripple:
            ripple_color = self._get_ripple_color()
            self._ripple_overlay = RippleOverlay(
                parent=self, color=ripple_color, ripple_enabled=True
            )

        # 按压缩放效果 (HeroUI: scale-[0.97])
        self._press_scale = PressScaleEffect(target=self)

        # 禁用状态
        if is_disabled:
            self.setEnabled(False)

        # icon: 初始渲染
        if self._icon_src:
            self._refresh_icon()

        # 开启 hover 事件追踪（用于动态切换 icon 颜色）
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 样式系统
    # ============================================================

    def _apply_styles(self):
        """生成并应用完整的 QSS 样式"""
        qss = self._build_qss()
        self.setStyleSheet(qss)

        if self._full_width:
            from PySide6.QtWidgets import QSizePolicy

            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # icon_only: 把按钮锁成正方形（边长 = 高度，或外部 override）
        if self._icon_only:
            if self._icon_only_side_override is not None:
                # 外部容器(如 Autocomplete 把 button 嵌进 input row)需要精确控制
                # 边长来贴合行高 —— 用 override,不走 size_config 自动算的 30/40/...
                side = int(self._icon_only_side_override)
            else:
                size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
                h = int(size_config["height"].replace("px", ""))
                padding_y = size_config["padding_y"]
                side = h + 2 * padding_y  # 总高 = 内容高 + 上下 padding
            from PySide6.QtWidgets import QSizePolicy

            self.setFixedSize(side, side)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setMouseTracking(True)
        from PySide6.QtCore import Qt

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _build_qss(self) -> str:
        """构建完整的 QSS 样式表"""
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        radius = self._resolve_radius(size_config)

        padding_x = size_config["padding_x"]
        padding_y = size_config["padding_y"]
        if self._radius == "full":
            padding_x += 8

        # icon_only: padding 对称 + 清空 min-width，避免压扁 icon
        if self._icon_only:
            padding_x = padding_y  # 左右 padding 等于上下
            min_width = "0"
        else:
            min_width = size_config["min_width"]

        normal_colors, hover_colors, disabled_colors = self._get_variant_styles(colors)

        return f"""
        QPushButton {{
            {normal_colors}
            border-radius: {radius};
            font-size: {size_config['font_size']};
            min-width: {min_width};
            padding: {padding_y}px {padding_x}px;
            font-weight: {size_config['font_weight']};
            outline: none;
            font-family: {FONT_FAMILY};
        }}
        QPushButton:hover {{
            {hover_colors}
        }}
        QPushButton:disabled {{
            {disabled_colors}
        }}
        """

    def _resolve_radius(self, size_config: dict) -> str:
        """解析圆角值 — 优先用户指定，否则跟随尺寸默认值"""
        radius_key = self._radius or size_config.get("default_radius", "md")

        # full 圆角需要根据组件高度动态计算
        if radius_key == "full":
            h = int(size_config["height"].replace("px", ""))
            return f"{h // 2}px"

        # 从全局 token 中取值
        return RADIUS.get(radius_key, RADIUS["md"])

    def _get_variant_styles(self, colors: dict) -> tuple:
        """根据变体类型生成 (normal, hover, disabled) 样式

        暗色模式下：文字更亮（用 300-400 色阶），背景透明度更低
        """
        is_dark = self._theme == "dark"

        c500 = colors[500]
        c600 = colors[600]
        # 暗色模式文字用浅色阶
        c_text = colors[300] if is_dark else c600
        c_text_hover = colors[200] if is_dark else colors[700]

        fg_on_solid = "#FFFFFF"
        if self._color == "warning":
            fg_on_solid = "#000000"
        if self._color == "default":
            if is_dark:
                # 暗色模式: solid 底色用深灰，文字用中灰（不要纯白）
                fg_on_solid = "#d4d4d8"
                c500 = colors[700]
                c600 = colors[600]
                c_text = colors[400]
                c_text_hover = colors[300]
            else:
                # 亮色模式: solid 底色用更深的灰（不要太浅）
                fg_on_solid = "#FFFFFF"
                c500 = colors[500]
                c600 = colors[600]
                c_text = colors[700]
                c_text_hover = colors[800]

        variant = self._variant

        if is_dark:
            disabled_style = f"""
                background-color: {hex_to_rgba(colors[800], 0.6)};
                color: {hex_to_rgba(colors[500], 0.4)};
                border: none;
            """
        else:
            disabled_style = f"""
                background-color: {colors[200]};
                color: {hex_to_rgba(colors[500], 0.5)};
                border: none;
            """

        if variant == "solid":
            normal = f"background-color: {c500}; color: {fg_on_solid}; border: none;"
            hover = f"background-color: {c600}; color: {fg_on_solid};"

        elif variant == "bordered":
            if is_dark:
                normal = f"background-color: transparent; color: {c_text}; border: 1px solid {c500};"
                hover = f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c_text_hover}; border: 1px solid {colors[400]};"
            else:
                normal = f"background-color: transparent; color: {c500}; border: 1px solid {c500};"
                hover = f"background-color: {hex_to_rgba(c500, 0.1)}; color: {c600}; border: 1px solid {c600};"

        elif variant == "flat":
            if is_dark:
                normal = f"background-color: {hex_to_rgba(c500, 0.2)}; color: {c_text}; border: none;"
                hover = f"background-color: {hex_to_rgba(c500, 0.3)}; color: {c_text_hover};"
            else:
                normal = f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c600}; border: none;"
                hover = f"background-color: {hex_to_rgba(c500, 0.25)}; color: {colors[700]};"

        elif variant == "light":
            if is_dark:
                normal = (
                    f"background-color: transparent; color: {c_text}; border: none;"
                )
                hover = f"background-color: {hex_to_rgba(c500, 0.2)}; color: {c_text_hover};"
            else:
                normal = f"background-color: transparent; color: {c500}; border: none;"
                hover = f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c600};"

        elif variant == "faded":
            dc = HEROUI_COLORS["default"]
            if is_dark:
                normal = f"background-color: {dc[800]}; color: {c_text}; border: 1px solid {dc[700]};"
                hover = f"background-color: {dc[700]}; color: {c_text_hover}; border: 1px solid {dc[600]};"
            else:
                normal = f"background-color: {dc[100]}; color: {c500}; border: 1px solid {dc[300]};"
                hover = f"background-color: {dc[200]}; color: {c600}; border: 1px solid {dc[400]};"

        elif variant == "ghost":
            if is_dark:
                normal = f"background-color: transparent; color: {c_text}; border: 1px solid {c500};"
                hover = f"background-color: {c500}; color: {fg_on_solid}; border: 1px solid {c500};"
            else:
                normal = f"background-color: transparent; color: {c500}; border: 1px solid {c500};"
                hover = f"background-color: {c500}; color: {fg_on_solid}; border: 1px solid {c500};"

        else:
            normal = f"background-color: {c500}; color: {fg_on_solid}; border: none;"
            hover = f"background-color: {c600};"

        return normal, hover, disabled_style

    # ============================================================
    # 水波纹
    # ============================================================

    def mousePressEvent(self, event):
        """鼠标按下: 触发水波纹 + 按压缩小"""
        if self.isEnabled():
            if self._ripple_overlay:
                self._ripple_overlay.add_ripple(event.position().toPoint())
            self._press_scale.press()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标松开: 恢复缩放"""
        if self.isEnabled():
            self._press_scale.release()
        super().mouseReleaseEvent(event)

    def _get_ripple_color(self) -> QColor:
        """根据变体决定水波纹颜色

        - solid/ghost: 白色水波纹（底色深，需要浅色水波纹）
        - 其他变体: 使用按钮主色
        """
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])

        if self._variant in ("solid", "ghost"):
            # solid/ghost 按钮底色深，用白色水波纹
            if self._color == "warning":
                return QColor(0, 0, 0)  # warning 底色浅，用黑色
            if self._color == "default" and self._theme == "light":
                return QColor(0, 0, 0)  # 亮色 default 底色也算浅
            return QColor(255, 255, 255)
        else:
            # 其他变体: 用主色
            hex_color = colors[500].lstrip("#")
            r = int(hex_color[:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return QColor(r, g, b)

    def _update_ripple_color(self):
        """颜色/变体/主题切换后更新水波纹颜色"""
        if self._ripple_overlay:
            self._ripple_overlay.set_color(self._get_ripple_color())

    # ============================================================
    # Icon 系统 —— 根据 variant/color/theme/hover 自动选对比色
    # ============================================================

    def _resolve_icon_color(self) -> str:
        """计算 icon 应该用的颜色（HEX 字符串）

        规则（与 _get_variant_styles 的 foreground color 对齐）：
        - 用户显式传 icon_color → 用它
        - solid 变体: 底色是 color-500，icon 用 fg_on_solid（白色/黑色）
        - ghost 变体:
            * normal（未 hover）→ 底色透明，icon 用 color-500（和边框色一致）
            * hover → 底色变 color-500，icon 用 fg_on_solid 对比色
        - 其他变体（bordered/flat/light/faded）→ 透明/浅底，icon 用 color-500
          （和 _get_variant_styles 的 c_text 对齐：dark 用 color-300，light 用 color-600）
        """
        # 用户显式指定 → 直接用
        if self._icon_color_override is not None:
            c = self._icon_color_override
            if isinstance(c, QColor):
                return c.name()
            return c

        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        is_dark = self._theme == "dark"

        # fg_on_solid: 和 _get_variant_styles 保持一致
        if self._color == "warning":
            fg_on_solid = "#000000"
        elif self._color == "default":
            fg_on_solid = "#d4d4d8" if is_dark else "#FFFFFF"
        else:
            fg_on_solid = "#FFFFFF"

        variant = self._variant

        if variant == "solid":
            return fg_on_solid
        if variant == "ghost":
            # hover 时底色变深，用对比色；normal 用彩色
            if self._is_hovered:
                return fg_on_solid
            # normal 状态用 color-500
            if self._color == "default":
                return colors[700] if not is_dark else colors[400]
            return colors[500]

        # bordered / flat / light / faded / underlined：和文字色对齐
        if self._color == "default":
            return colors[700] if not is_dark else colors[400]
        # 与 _get_variant_styles 里 c_text 一致: dark 用 300，light 用 600
        return colors[300] if is_dark else colors[600]

    def _refresh_icon(self):
        """重新渲染 icon pixmap（根据当前 variant/color/theme/hover 状态）"""
        if not self._icon_src:
            return

        # 计算 icon 尺寸
        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        if self._icon_size_override is not None:
            icon_size = self._icon_size_override
        elif self._icon_only:
            # icon_only: icon 占按钮约 50%
            h = int(size_config["height"].replace("px", ""))
            padding_y = size_config["padding_y"]
            side = h + 2 * padding_y
            icon_size = int(side * 0.5)
        else:
            # 带文字的按钮：icon 大小跟 font_size 对齐 + 微增
            font_size = int(size_config["font_size"].replace("px", ""))
            icon_size = font_size + 2

        color_str = self._resolve_icon_color()
        pixmap = load_svg_icon(self._icon_src, size=icon_size, color=color_str)
        # 直接调 QPushButton 原生 setIcon，避开我们重写的 setIcon（会把 _icon_src 清空）
        QPushButton.setIcon(self, QIcon(pixmap))
        self.setIconSize(QSize(icon_size, icon_size))

    def enterEvent(self, event):
        """hover 进入 → 刷新 icon（ghost variant 需要换色）"""
        self._is_hovered = True
        if self._icon_src:
            self._refresh_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """hover 离开 → 刷新 icon"""
        self._is_hovered = False
        if self._icon_src:
            self._refresh_icon()
        super().leaveEvent(event)

    # ============================================================
    # 公共 API
    # ============================================================

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()
        self._refresh_icon()

    def set_radius(self, radius: str):
        self._radius = radius
        self._apply_styles()

    def set_icon(self, icon):
        """设置图标（snake_case 版本）—— 等同于 setIcon

        支持两种形式：
        - 字符串（内置图标名或 SVG 路径）→ Button 会自动根据 variant/color/theme/hover 着色
        - QIcon 对象 → 直接调用 QPushButton.setIcon（用户自己负责颜色）
        """
        self.setIcon(icon)

    def setIcon(self, icon):  # noqa: N802 —— 重写 Qt 原生 setIcon
        """重写 QPushButton.setIcon 支持字符串（内置图标名或 SVG 路径）

        传字符串 → Button 自动 render（根据 variant/color/theme/hover 动态着色）
        传 QIcon / QPixmap → 退回原生行为，用户自己管颜色
        """
        if isinstance(icon, str):
            self._icon_src = icon
            self._refresh_icon()
        else:
            # QIcon/QPixmap —— 用户自己管色
            self._icon_src = None
            super().setIcon(icon)

    def set_icon_color(self, color):
        """显式指定 icon 颜色（覆盖自动配色）。传 None 恢复自动配色。"""
        self._icon_color_override = color
        self._refresh_icon()

    def set_icon_size(self, size: Optional[int]):
        """显式指定 icon 渲染尺寸（px）。传 None 恢复"按按钮尺寸自动算"模式。

        默认行为（None）下,Button 会根据自身 size 自动选 icon_size:
            - icon_only: side * 0.5
            - 普通带文字: font_size + 2
        当外部容器（如 Autocomplete）想精确控制 icon size 与 input row 高度
        匹配时,可以显式传入。
        """
        self._icon_size_override = size
        self._refresh_icon()

    def set_icon_only_side(self, side: Optional[int]):
        """显式锁定 icon_only 模式下按钮的边长（px）。传 None 恢复自动算。

        默认行为（None）：side = height + 2*padding_y(由 BUTTON_SIZES 决定,
        sm 是 30,md 40 等)。在像 Autocomplete 这种"按钮嵌入 input row"的场景,
        autocomplete 的 end_btn_size 是 18/20/22 远小于 Button 自动算的 side,
        外部 setFixedSize 又会被 _apply_styles(主题切换/setter 触发)冲掉。
        改用这个 setter 把 override 持久化,_apply_styles 永远尊重它。
        """
        self._icon_only_side_override = side
        self._apply_styles()

    def set_icon_only(self, icon_only: bool):
        """切换 icon_only 模式（True 时按钮锁成正方形）"""
        self._icon_only = bool(icon_only)
        if not self._icon_only:
            # 解除固定尺寸
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            from PySide6.QtWidgets import QSizePolicy

            self.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
            )
        self._apply_styles()
        self._refresh_icon()

    def set_theme(self, theme: str):
        """设置主题

        - "auto": 跟随 ThemeProvider 全局切换（并注册）
        - "light"/"dark": 强制固定（并取消注册）
        """
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            # 如果从 auto 切到固定模式，取消注册
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()

    # ============================================================
    # 内部：解析主题模式
    # ============================================================

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """将模式解析为实际的 'light' 或 'dark'"""
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用——只更新实际主题，不改 _theme_mode"""
        self._theme = theme
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()
