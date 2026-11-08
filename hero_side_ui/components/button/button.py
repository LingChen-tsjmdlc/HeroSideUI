"""Button 组件：HeroUI v2 风格按钮，保持 PySide 原生 API。"""

from PySide6.QtCore import QObject, QSize, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QPushButton

from ...animation import PressScaleEffect, RippleOverlay
from ...core import ThemeProvider
from ...themes import (
    BUTTON_SIZES,
    HEROUI_COLORS,
    RADIUS,
    VALID_BUTTON_VARIANTS,
)
from ...utils import hex_to_rgba, load_svg_icon


class Button(QPushButton):
    """HeroUI 风格按钮，继承 QPushButton。

    支持 color/variant/size/radius/theme、icon_only 方形模式与 icon 自动配色；
    theme="auto" 跟随 ThemeProvider 全局切换。
    """

    VALID_VARIANTS = VALID_BUTTON_VARIANTS

    def __init__(
        self,
        text: str = "",
        color: str = "primary",
        variant: str = "solid",
        size: str = "md",
        radius: str | None = None,
        is_disabled: bool = False,
        full_width: bool = False,
        icon_only: bool = False,
        icon: str | None = None,
        icon_size: int | None = None,
        icon_color=None,
        parent: QObject | None = None,
        theme: str = "auto",
        disable_ripple: bool = False,
    ):
        """创建按钮并装配样式、几何、水波纹与按压缩放。

        Args:
            text: 按钮文字。
            color: 语义色，未命中回退 primary。
            variant: solid / bordered / flat / light / faded / ghost。
            size: 尺寸档位。
            radius: 圆角档位；None 跟随尺寸默认，full 按高度折算。
            is_disabled: 是否禁用。
            full_width: 是否横向撑满。
            icon_only: 方形纯图标模式。
            icon: 图标名或 SVG 路径。
            icon_size: 图标渲染尺寸；None 自动计算。
            icon_color: 显式图标色；None 走自动对比色。
            parent: Qt 父对象。
            theme: 主题名；auto 时跟随 ThemeProvider。
            disable_ripple: 是否关闭水波纹。

        Note:
            样式与几何拆分应用：_apply_styles 只管 QSS，
            _apply_geometry 只管尺寸策略，互不覆盖外部定制。
        """
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
        self._icon_only_side_override: int | None = None  # 外部锁 icon_only 边长(px)
        self._is_hovered = False
        self._theme_mode = theme  # 用户设定的模式: "auto"/"light"/"dark"
        self._theme = self._resolve_theme(theme)  # 实际生效: "light"/"dark"
        self._disable_ripple = disable_ripple

        # 样式与几何拆分：样式 setter 只重跑 _apply_styles，不冲外部几何定制
        self._apply_styles()
        self._apply_geometry()

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
        """应用视觉样式：QSS + 字体 + 光标；不碰几何。

        Note:
            字体走 Text/FontProvider 同源，QSS 不写 font-family，
            避免与 setFont() 形成二元源。
        """
        qss = self._build_qss()
        self.setStyleSheet(qss)

        # 字体走 Text/FontProvider 同源：QSS 里不再写 font-family，
        # 避免与 setFont() 产生二元源。
        from ...core import make_text_qfont

        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        try:
            fs = int(str(size_config["font_size"]).rstrip("px"))
        except Exception:
            fs = 14
        try:
            fw = int(size_config["font_weight"])
            # QSS font_weight 表达为 100~900，Text 映射为 6 档：取近陫到支持的 token。
            if fw <= 250:
                weight_token = "extralight"
            elif fw <= 350:
                weight_token = "light"
            elif fw <= 450:
                weight_token = "normal"
            elif fw <= 550:
                weight_token = "medium"
            elif fw <= 800:
                weight_token = "bold"
            else:
                weight_token = "black"
        except Exception:
            weight_token = "medium"
        self.setFont(make_text_qfont(fs, weight_token))

        self.setMouseTracking(True)
        from PySide6.QtCore import Qt

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_geometry(self):
        """应用几何策略：sizePolicy 与固定尺寸。

        仅在 icon_only / side / size / full_width 变化时需要调用；
        普通按钮宽度按内容自适应，绝不允许弹性缩小。
        """
        from PySide6.QtWidgets import QSizePolicy

        if self._icon_only:
            side = self._resolve_icon_only_side()
            self.setFixedSize(side, side)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        elif self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            # 普通按钮：宽度按内容自适应，绝不允许弹性缩小，允许弹性增大
            self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def _resolve_icon_only_side(self) -> int:
        """解析 icon_only 模式的正方形边长。

        Returns:
            外部 override 优先；否则按高度 + 两侧 padding 自动计算。
        """
        if self._icon_only_side_override is not None:
            return int(self._icon_only_side_override)
        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        h = int(size_config["height"].replace("px", ""))
        return h + 2 * size_config["padding_y"]

    def _build_qss(self) -> str:
        """构建完整的 QSS 样式表。

        Returns:
            含 normal / hover / disabled 三态的 QPushButton QSS。

        Note:
            icon_only 时 QSS 的 min/max 四向锁死与 setFixedSize 同步给出——
            QSS 盒模型属性会覆盖 setFixedSize 的显式最小值。
        """
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])
        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        radius = self._resolve_radius(size_config)

        padding_x = size_config["padding_x"]
        padding_y = size_config["padding_y"]
        if self._radius == "full":
            padding_x += 8

        # icon_only: padding 对称 + QSS 四向 min/max 锁死正方形
        # （QSS 盒模型属性会覆盖 setFixedSize 的显式最小值，必须同步给出）
        if self._icon_only:
            padding_x = padding_y  # 左右 padding 等于上下
            border = 1 if self._variant in ("bordered", "ghost", "faded") else 0
            content = self._resolve_icon_only_side() - 2 * padding_y - 2 * border
            box_constraints = (
                f"min-width: {content}px; max-width: {content}px; "
                f"min-height: {content}px; max-height: {content}px;"
            )
        else:
            box_constraints = f"min-width: {size_config['min_width']};"

        normal_colors, hover_colors, disabled_colors = self._get_variant_styles(colors)

        return f"""
        QPushButton {{
            {normal_colors}
            border-radius: {radius};
            font-size: {size_config["font_size"]};
            {box_constraints}
            padding: {padding_y}px {padding_x}px;
            font-weight: {size_config["font_weight"]};
            outline: none;
        }}
        QPushButton:hover {{
            {hover_colors}
        }}
        QPushButton:disabled {{
            {disabled_colors}
        }}
        """

    def _resolve_radius(self, size_config: dict) -> str:
        """解析圆角值。

        Args:
            size_config: 当前尺寸 token。

        Returns:
            用户指定档位优先；full 按按钮高度折算；其余取全局 token。
        """
        radius_key = self._radius or size_config.get("default_radius", "md")

        # full 圆角需要根据组件高度动态计算
        if radius_key == "full":
            h = int(size_config["height"].replace("px", ""))
            return f"{h // 2}px"

        # 从全局 token 中取值
        return RADIUS.get(radius_key, RADIUS["md"])

    def _get_variant_styles(self, colors: dict) -> tuple:
        """根据变体生成 (normal, hover, disabled) 三态样式。

        Args:
            colors: 当前语义色阶字典。

        Returns:
            三段 QSS 片段的元组。

        Note:
            暗色下文字用更浅色阶（200-400），避免 flat/light/bordered
            在暗背景上发灰；透明底变体禁用态保持透明仅文字变淡。
        """
        is_dark = self._theme == "dark"

        c500 = colors[500]
        c600 = colors[600]
        # 暗色模式文字用更浅色阶，避免 flat/light/bordered 在暗背景上发灰看不清
        c_text = colors[200] if is_dark else c600
        c_text_hover = colors[100] if is_dark else colors[700]

        fg_on_solid = "#FFFFFF"
        if self._color == "warning":
            fg_on_solid = "#000000"
        if self._color == "default":
            if is_dark:
                # 暗色模式: solid 底色用深灰，文字用中灰（不要纯白）
                fg_on_solid = "#d4d4d8"
                c500 = colors[700]
                c600 = colors[600]
                c_text = colors[300]
                c_text_hover = colors[200]
            else:
                # 亮色模式: solid 底色用更深的灰（不要太浅）
                fg_on_solid = "#FFFFFF"
                c500 = colors[500]
                c600 = colors[600]
                c_text = colors[700]
                c_text_hover = colors[800]

        variant = self._variant

        # 透明底变体（light/ghost/bordered）禁用态保持透明，仅文字变淡；
        # 其余（solid/flat/faded）用浅底表示禁用。
        transparent_variants = ("light", "ghost", "bordered")
        if variant in transparent_variants:
            disabled_style = f"""
                background-color: transparent;
                color: {hex_to_rgba(colors[500], 0.4 if is_dark else 0.5)};
                border: none;
            """
        elif is_dark:
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
                normal = (
                    f"background-color: transparent; color: {c_text}; border: 1px solid {c500};"
                )
                hover = f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c_text_hover}; border: 1px solid {colors[400]};"
            else:
                normal = f"background-color: transparent; color: {c500}; border: 1px solid {c500};"
                hover = f"background-color: {hex_to_rgba(c500, 0.1)}; color: {c600}; border: 1px solid {c600};"

        elif variant == "flat":
            if is_dark:
                normal = (
                    f"background-color: {hex_to_rgba(c500, 0.2)}; color: {c_text}; border: none;"
                )
                hover = f"background-color: {hex_to_rgba(c500, 0.3)}; color: {c_text_hover};"
            else:
                normal = (
                    f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c600}; border: none;"
                )
                hover = f"background-color: {hex_to_rgba(c500, 0.25)}; color: {colors[700]};"

        elif variant == "light":
            if is_dark:
                normal = f"background-color: transparent; color: {c_text}; border: none;"
                hover = f"background-color: {hex_to_rgba(c500, 0.2)}; color: {c_text_hover};"
            else:
                normal = f"background-color: transparent; color: {c500}; border: none;"
                hover = f"background-color: {hex_to_rgba(c500, 0.15)}; color: {c600};"

        elif variant == "faded":
            dc = HEROUI_COLORS["default"]
            if is_dark:
                normal = (
                    f"background-color: {dc[800]}; color: {c_text}; border: 1px solid {dc[700]};"
                )
                hover = f"background-color: {dc[700]}; color: {c_text_hover}; border: 1px solid {dc[600]};"
            else:
                normal = f"background-color: {dc[100]}; color: {c500}; border: 1px solid {dc[300]};"
                hover = f"background-color: {dc[200]}; color: {c600}; border: 1px solid {dc[400]};"

        elif variant == "ghost":
            if is_dark:
                normal = (
                    f"background-color: transparent; color: {c_text}; border: 1px solid {c500};"
                )
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
        """鼠标按下：触发水波纹与按压缩放。

        Args:
            event: Qt 鼠标按下事件。
        """
        if self.isEnabled():
            if self._ripple_overlay:
                self._ripple_overlay.add_ripple(event.position().toPoint())
            self._press_scale.press()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标松开：恢复缩放。

        Args:
            event: Qt 鼠标释放事件。
        """
        if self.isEnabled():
            self._press_scale.release()
        super().mouseReleaseEvent(event)

    def _get_ripple_color(self) -> QColor:
        """按变体取水波纹颜色。

        Returns:
            solid / ghost 底色深用白色（warning 与亮色 default 例外用黑）；
            其余变体用主色 500。
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
        """颜色 / 变体 / 主题切换后同步水波纹颜色。"""
        if self._ripple_overlay:
            self._ripple_overlay.set_color(self._get_ripple_color())

    # ============================================================
    # Icon 系统 —— 根据 variant/color/theme/hover 自动选对比色
    # ============================================================

    def _resolve_icon_color(self) -> str:
        """计算 icon 颜色（HEX），与变体前景色对齐。

        规则：显式 icon_color 优先；solid 用实底对比色；ghost 未 hover 用
        主色、hover 用对比色；其余变体与文字色一致。
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
            return colors[700] if not is_dark else colors[300]
        # 与 _get_variant_styles 里 c_text 一致: dark 用 200，light 用 600
        return colors[200] if is_dark else colors[600]

    def _refresh_icon(self):
        """按当前状态重渲染 icon pixmap。

        Note:
            尺寸来源：显式 override > icon_only 按边长 50% > 字号 +2；
            直接调 QPushButton 原生 setIcon，避开本类重写的 setIcon
            （它会清空 _icon_src）。
        """
        if not self._icon_src:
            return

        # 计算 icon 尺寸
        size_config = BUTTON_SIZES.get(self._size, BUTTON_SIZES["md"])
        if self._icon_size_override is not None:
            icon_size = self._icon_size_override
        elif self._icon_only:
            # icon_only: icon 占按钮约 50%（边长与 _apply_geometry/_build_qss 同源）
            icon_size = int(self._resolve_icon_only_side() * 0.5)
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
        """hover 进入：置位并刷新 icon（ghost 变体需换色）。

        Args:
            event: Qt 进入事件。
        """
        self._is_hovered = True
        if self._icon_src:
            self._refresh_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """hover 离开：复位并刷新 icon。

        Args:
            event: Qt 离开事件。
        """
        self._is_hovered = False
        if self._icon_src:
            self._refresh_icon()
        super().leaveEvent(event)

    # ============================================================
    # 公共 API
    # ============================================================

    def set_color(self, color: str):
        """切换语义色并联动样式、水波纹与图标。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()

    def set_variant(self, variant: str):
        """切换视觉变体并联动样式、水波纹与图标。

        Args:
            variant: 变体名。
        """
        self._variant = variant
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()

    def set_size(self, size: str):
        """切换尺寸档位并联动几何与图标。

        Args:
            size: 尺寸档位名。

        Note:
            size 影响 icon_only 边长，几何必须同步重算。
        """
        self._size = size
        self._apply_styles()
        self._apply_geometry()  # size 影响 icon_only 边长，几何需同步
        self._refresh_icon()

    def set_radius(self, radius: str):
        """切换圆角档位并重算 QSS。

        Args:
            radius: 圆角档位名。
        """
        self._radius = radius
        self._apply_styles()

    def set_icon(self, icon):
        """设置图标，等同于 setIcon。"""
        self.setIcon(icon)

    def setIcon(self, icon):
        """重写 setIcon 以支持字符串图标名/SVG 路径。

        Args:
            icon: 字符串时自动着色渲染；QIcon/QPixmap 走原生行为。
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

    def set_icon_size(self, size: int | None):
        """显式指定 icon 渲染尺寸（px）；None 恢复自动计算。"""
        self._icon_size_override = size
        self._refresh_icon()

    def set_icon_only_side(self, side: int | None):
        """锁定 icon_only 模式边长（px）；None 恢复按尺寸自动计算。

        Note:
            override 持久化，样式重建永远尊重它，不会被主题切换冲掉。
        """
        self._icon_only_side_override = side
        self._apply_styles()
        self._apply_geometry()

    def set_icon_only(self, icon_only: bool):
        """切换 icon_only 模式（True 时按钮锁成正方形）"""
        self._icon_only = bool(icon_only)
        if not self._icon_only:
            # 解除固定尺寸
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
        self._apply_geometry()
        self._apply_styles()
        self._refresh_icon()

    def set_theme(self, theme: str):
        """设置主题：auto 注册跟随全局；light / dark 硬锁并取消注册。

        Args:
            theme: auto / light / dark。
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
        """将主题模式解析为实际 light / dark。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不改 _theme_mode、不触碰注册状态。
        """
        self._theme = theme
        self._apply_styles()
        self._update_ripple_color()
        self._refresh_icon()
