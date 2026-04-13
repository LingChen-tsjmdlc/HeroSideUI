"""
HeroSideUI Button Component
基于HeroUI v2设计风格，保持PySide原生API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/button.ts
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor
from typing import Optional

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, BUTTON_SIZES
from ..utils import hex_to_rgba
from ..animation import RippleOverlay, PressScaleEffect


class Button(QPushButton):
    """
    HeroUI 风格的按钮组件

    特性：
    - 保持 PySide 原生 API (继承 QPushButton)
    - 支持颜色 (default, primary, secondary, success, warning, danger)
    - 支持变体 (solid, bordered, flat, light, faded, ghost)
    - 支持尺寸 (sm, md, lg)
    - 支持圆角 (none, sm, md, lg, full)
    - 支持主题 (light, dark) — 暗色模式下自动调整文字和背景配色
    - 按压视觉反馈 (通过 QSS padding 模拟缩放)

    用法:
        btn = Button("Click me", color="primary", variant="solid", size="md")
        btn_dark = Button("Dark", color="primary", variant="flat", theme="dark")
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
        parent: Optional[QObject] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(text, parent)

        self._color = color
        self._variant = variant
        self._size = size
        self._radius = radius
        self._full_width = full_width
        self._theme = theme
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

        normal_colors, hover_colors, disabled_colors = \
            self._get_variant_styles(colors)

        return f"""
        QPushButton {{
            {normal_colors}
            border-radius: {radius};
            font-size: {size_config['font_size']};
            min-width: {size_config['min_width']};
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
                normal = f"background-color: transparent; color: {c_text}; border: none;"
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
    # 公共 API
    # ============================================================

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()
        self._update_ripple_color()

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_styles()
        self._update_ripple_color()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: str):
        self._radius = radius
        self._apply_styles()

    def set_theme(self, theme: str):
        self._theme = theme
        self._apply_styles()
        self._update_ripple_color()
