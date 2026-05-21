"""
HeroSideUI - StatePalette
=========================

跨组件复用的"状态颜色解析器"：
给定 ``(variant, color, theme, state)``，返回该状态下应该用的 QColor。

设计目标
--------
原本 listbox / autocomplete / checkbox 等组件各自在文件顶部写了一堆
``_hover_bg``/``_text_hover``/``_hover_border`` 之类的私有函数，逻辑高度重叠
但拷贝散落，导致：

1. **巨头组件膨胀**（listbox 顶部光颜色函数就 13 个、~150 行）。
2. **复用反模式**：autocomplete 嵌入 listbox 时把这套逻辑抄了第二份。
3. **修一个色阶要改 N 个文件**，容易漏。

把它们集中到 ``core/state_palette.py``，对组件提供高层意图 API：

.. code-block:: python

    from hero_side_ui.core import StatePalette

    bg = StatePalette.bg("flat", "primary", "dark", "hover")
    fg = StatePalette.text("flat", "primary", "dark", "hover")
    bd = StatePalette.border("bordered", "primary", "light", "hover")

设计要点
--------
- **纯静态方法 + 纯函数**：无状态、无单例。完全无副作用，可被任何组件直接调。
- **返回 QColor**：组件自绘场景（``QPainter``）天然适用；走 QSS 的组件（如 button）自己 ``QColor.name(QColor.HexArgb)`` 转字符串。
- **覆盖 6 variants × 6 colors × 2 themes × 5 states**：和 HeroUI menu/listbox token 一致。

States
~~~~~~
- ``"resting"`` - 默认（未 hover、未 focused、未 selected）
- ``"hover"`` - 光标悬停
- ``"focus"`` - 键盘 focus（视觉上等同 hover，方便组件简化）
- ``"selected"`` - 选中态（在 listbox / autocomplete / checkbox 中表现不同）
- ``"disabled"`` - 禁用态

Variants
~~~~~~~~
``"solid"``, ``"shadow"``, ``"flat"``, ``"faded"``, ``"bordered"``, ``"light"``

Colors
~~~~~~
``"default"``, ``"primary"``, ``"secondary"``, ``"success"``, ``"warning"``, ``"danger"``

Themes
~~~~~~
``"light"`` / ``"dark"``（``"auto"`` 由组件层在订阅 ``ThemeProvider`` 时解析为具体值）。
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtGui import QColor

from ..themes import HEROUI_COLORS

__all__ = ["StatePalette", "Variant", "Color", "Theme", "State"]


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


# ============================================================
# StatePalette
# ============================================================


class StatePalette:
    """状态颜色解析器（无状态，纯静态方法）。

    组件用法::

        # 自绘背景
        bg = StatePalette.bg(self._variant, self._color, theme, "hover")
        painter.fillPath(path, bg)

        # 拼 QSS
        bg_hex = StatePalette.bg("flat", "primary", "dark", "hover").name(
            QColor.NameFormat.HexArgb
        )

    Notes:
        所有方法都是 ``@staticmethod``，没有实例化语义。这样做的好处：

        - 组件代码无需 import + 持有 palette 对象
        - 内部纯函数，性能等同于直接调全局函数
        - 命名空间清晰（``StatePalette.bg`` vs 一堆顶层 ``resolve_bg``）
    """

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

        if variant in ("solid", "shadow"):
            if color == "default":
                return (
                    QColor(default_pal[100])
                    if theme == "light"
                    else QColor(default_pal[800])
                )
            return QColor(palette[500])

        if variant == "flat":
            if color == "default":
                c = (
                    QColor(default_pal[200])
                    if theme == "light"
                    else QColor(default_pal[700])
                )
                c.setAlphaF(0.40)
                return c
            c = QColor(palette[500])
            c.setAlphaF(0.20)
            return c

        if variant == "faded":
            return (
                QColor(default_pal[100])
                if theme == "light"
                else QColor(default_pal[800])
            )

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
                return (
                    QColor(palette[300]) if theme == "light" else QColor(palette[600])
                )
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
        """item 主标题字色。

        - ``resting`` / ``disabled`` 返回中性默认色（``text_default``）。
        - ``hover`` / ``focus`` / ``selected`` 走"高亮态"逻辑，依赖 variant×color。
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
        """description / empty 占位的次级文字色。

        light: default-500（中性灰，白底清晰）
        dark:  default-400（提亮一档，深底才看得清；default-500 在 #0B0D12 上几乎不可见）
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
