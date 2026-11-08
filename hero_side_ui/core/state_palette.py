"""StatePalette：按 (variant, color, theme, state) 解析状态颜色的纯静态工具。

states: resting/hover/focus/selected/disabled；variants: solid/shadow/flat/
faded/bordered/light；暗色 hover 比 HeroUI 提一档以适配 Popover 底色。
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtGui import QColor

from ..themes import HEROUI_COLORS

__all__ = ["Color", "State", "StatePalette", "Theme", "Variant"]


# ---- Type aliases (仅用于类型提示，运行期是普通 str) ---------------------------

Variant = Literal["solid", "shadow", "flat", "faded", "bordered", "light"]
Color = Literal["default", "primary", "secondary", "success", "warning", "danger"]
Theme = Literal["light", "dark"]
State = Literal["resting", "hover", "focus", "selected", "disabled"]

# 透明 QColor，复用避免重复构造
_TRANSPARENT = QColor(0, 0, 0, 0)


def _pal(color: str) -> dict:
    """安全取色板，未知 color 退回到 ``default`` 避免 KeyError。"""
    return HEROUI_COLORS.get(color, HEROUI_COLORS["default"])


# HeroUI 语义色 ``default.DEFAULT``（``bg-default`` 用的那一档）不是 500：
# semantic.ts 里 light=zinc-300 / dark=zinc-700；其余 color 的 DEFAULT 是 500。
_DEFAULT_SHADE = {"light": 300, "dark": 700}


def _pal_default(color: str, theme: str) -> QColor:
    """HeroUI ``default.DEFAULT`` 档；非 default 色一律 500。"""
    pal = _pal(color)
    if color == "default":
        return QColor(pal[_DEFAULT_SHADE.get(theme, "300")])
    return QColor(pal[500])


# 菜单容器的暗色底是 Popover 的 #27272a (= default-800)，比 HeroUI 的
# content1(#18181b) 亮一档。HeroUI 的 hover 色是按 content1 容器标定的，
# 直接用会与容器同色（solid/faded 恰好都是 #27272a）→ 整体再提一档。
# 中性灰靠色相拉不开差距，flat 额外加 alpha 补足。
_STEP_UP = {"light": {"solid": 300, "faded": 100}, "dark": {"solid": 600, "faded": 700}}
_FLAT_ALPHA = {"light": 0.40, "dark": 0.70}


# ============================================================
# StatePalette
# ============================================================


class StatePalette:
    """状态颜色解析器（无状态，纯静态方法）。"""

    # --------------------------------------------------------
    # 背景色
    # --------------------------------------------------------

    @staticmethod
    def bg(variant: str, color: str, theme: str, state: str = "resting") -> QColor:
        """item 背景色。

        Args:
            variant: solid / shadow / flat / faded / bordered / light
            color:   default / primary / ... / danger
            theme:   light / dark
            state:   resting / hover / focus / selected / disabled

        Returns:
            QColor。``resting`` 状态在所有 variant 下默认透明（让父背景透出来）。
            ``focus`` 视觉等同 ``hover``。``selected`` 视觉等同 ``hover``
            （listbox/menu 标准行为：选中即"持续 hover"态）。
        """
        # resting / disabled / light variant 默认透明
        if state in ("resting", "disabled"):
            return QColor(_TRANSPARENT)

        # focus / selected 视觉等同 hover（listbox/menu 标准）
        # (此处不区分，调用方如需特殊化 selected，可外层叠加)
        palette = _pal(color)
        default_pal = HEROUI_COLORS["default"]

        step = _STEP_UP.get(theme, _STEP_UP["light"])

        if variant in ("solid", "shadow"):
            if color == "default":
                return QColor(default_pal[step["solid"]])
            return QColor(palette[500])

        if variant == "flat":
            if color == "default":
                c = _pal_default("default", theme)
                c.setAlphaF(_FLAT_ALPHA.get(theme, 0.40))
                return c
            # 彩色靠色相就能和中性容器拉开，维持 HeroUI 的 /20
            c = QColor(palette[500])
            c.setAlphaF(0.20)
            return c

        if variant == "faded":
            # HeroUI faded 恒用 bg-default-100，不跟 color 变
            return QColor(default_pal[step["faded"]])

        # bordered / light: hover 不改 bg
        return QColor(_TRANSPARENT)

    # --------------------------------------------------------
    # 边框色
    # --------------------------------------------------------

    @staticmethod
    def border(variant: str, color: str, theme: str, state: str = "resting") -> QColor:
        """item 边框色。

        仅 ``bordered`` / ``faded`` 在 hover 时有边框变化；其他 variant 返回透明。
        """
        if state in ("resting", "disabled"):
            return QColor(_TRANSPARENT)

        palette = _pal(color)
        if variant == "bordered":
            if color == "default":
                return QColor(palette[300]) if theme == "light" else QColor(palette[600])
            return QColor(palette[500])

        if variant == "faded":
            # hover:border-default
            return (
                QColor(HEROUI_COLORS["default"][200])
                if theme == "light"
                else QColor(HEROUI_COLORS["default"][700])
            )
        return QColor(_TRANSPARENT)

    # --------------------------------------------------------
    # 文字色
    # --------------------------------------------------------

    @staticmethod
    def text(variant: str, color: str, theme: str, state: str = "resting") -> QColor:
        """取 item 主标题字色。

        Args:
            variant: 样式变体。
            color: 语义色。
            theme: "light" 或 "dark"。
            state: resting/hover/focus/selected/disabled。

        Returns:
            resting/disabled 返回中性默认色；高亮态依赖 variant×color。
        """
        if state in ("resting", "disabled"):
            return StatePalette.text_default(theme)

        palette = _pal(color)

        if variant == "solid":
            if color == "default":
                return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
            return QColor("#FFFFFF")

        if variant == "shadow":
            if color == "default":
                return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
            return QColor("#FFFFFF")

        if variant == "flat":
            if color == "default":
                return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
            return QColor(palette[500] if theme == "light" else palette[400])

        if variant == "faded":
            if color == "default":
                return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
            return QColor(palette[500] if theme == "light" else palette[400])

        if variant == "bordered":
            if color == "default":
                return StatePalette.text_default(theme)
            return QColor(palette[500] if theme == "light" else palette[400])

        if variant == "light":
            if color == "default":
                return QColor(HEROUI_COLORS["default"][500])
            return QColor(palette[500] if theme == "light" else palette[400])

        return StatePalette.text_default(theme)

    # --------------------------------------------------------
    # 中性辅助色（与 variant/color 无关，只看 theme）
    # --------------------------------------------------------

    @staticmethod
    def text_default(theme: str) -> QColor:
        """item 默认（resting）字色。light: default-800；dark: default-100。"""
        return (
            QColor(HEROUI_COLORS["default"][800])
            if theme == "light"
            else QColor(HEROUI_COLORS["default"][100])
        )

    @staticmethod
    def text_description(theme: str) -> QColor:
        """取次级文字色（description/empty 占位）。

        Args:
            theme: "light" 或 "dark"。

        Returns:
            light 为 default-500；dark 提亮为 default-400。
        """
        if theme == "dark":
            return QColor(HEROUI_COLORS["default"][400])
        return QColor(HEROUI_COLORS["default"][500])

    @staticmethod
    def shortcut_border(theme: str) -> QColor:
        """快捷键标签的边框色（细灰线）。"""
        return (
            QColor(HEROUI_COLORS["default"][300])
            if theme == "light"
            else QColor(HEROUI_COLORS["default"][700])
        )

    @staticmethod
    def divider(theme: str) -> QColor:
        """分隔线颜色（item 之间或 section 内部）。"""
        return (
            QColor(HEROUI_COLORS["default"][200])
            if theme == "light"
            else QColor(HEROUI_COLORS["default"][700])
        )

    # --------------------------------------------------------
    # 复合便捷方法
    # --------------------------------------------------------

    @staticmethod
    def selected_indicator(variant: str, color: str, theme: str) -> QColor:
        """选中标记（v 形勾等）的颜色。

        HeroUI 中 ``selectedIcon`` 走 ``text-inherit``，即跟随 hover/selected 态文字色。
        """
        return StatePalette.text(variant, color, theme, "hover")
