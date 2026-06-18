"""HeroSideUI Kbd 组件 —— 复刻 HeroUI v2 kbd 并按项目惯例扩展。

样式锚点：packages/core/theme/src/components/kbd.ts
组件锚点：packages/components/kbd/src/{kbd.tsx,use-kbd.ts,utils.ts}

视觉规格：bg-default-100 + text-foreground-600 + shadow-small + rounded-small
        + px-1.5 py-0.5 + space-x-0.5 + text-small + font-normal

扩展点（HeroUI 原版无）：
  - size:    sm / md / lg 三档
  - radius:  none / sm / md / lg / full 五档
  - platform: auto / mac / win / linux —— fn 与 alt 两键的 icon 平台敏感
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import (
    HEROUI_COLORS,
    KBD_SHADOW,
    KBD_SIZE_TABLE,
    VALID_KBD_RADII,
    VALID_KBD_SIZES,
)
from ...utils.icon_utils import load_svg_icon
from ..text import Text
from ._keys import (
    KBD_KEY_NAMES,
    KBD_KEYS_GLYPH_MAP,
    KBD_KEYS_LABEL_MAP,
    VALID_PLATFORMS,
    resolve_icon,
)

KbdKeysInput = Optional[Union[str, Sequence[str]]]

# size 未显式传 radius 时的推断表
# —— 统一默认 md：三档 size 各取所属规格的 md 像素值
DEFAULT_RADIUS_BY_SIZE = {
    "sm": "md",
    "md": "md",
    "lg": "md",
}


# ============================================================
# SVG icon 子控件：私有 QLabel + setPixmap（永不 setText）
# ============================================================


class _KbdIconLabel(QLabel):
    """SVG icon 渲染槽，跟主题着色，垂直居中对齐文字。"""

    def __init__(
        self,
        icon_name: str,
        title: str,
        size: int,
        color: QColor,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setToolTip(title)
        # 居中：pixmap 在 label 矩形内水平+垂直居中
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._icon_name = icon_name
        self._size = int(size)
        self.set_color(color)

    def set_color(self, color: QColor) -> None:
        pm = load_svg_icon(self._icon_name, size=self._size, color=color)
        self.setPixmap(pm)
        self.setFixedSize(pm.size())


# ============================================================
# Kbd 主组件
# ============================================================


class Kbd(QFrame):
    """HeroUI v2 风格的键盘按键组件。完整 API/示例见 ``docs/kbd.md``。"""

    def __init__(
        self,
        children: str = "",
        *,
        keys: KbdKeysInput = None,
        size: str = "md",
        radius: Optional[str] = None,
        platform: str = "auto",
        theme: str = "auto",
        use_unicode: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._children_text = str(children or "")
        self._keys: List[str] = self._normalize_keys(keys)
        self._use_unicode = bool(use_unicode)
        self._size = self._validate_size(size)
        # radius=None 哨兵：未显式传时跟随 size 推断
        self._radius_explicit = radius is not None
        self._radius = self._resolve_radius(radius, self._size)
        self._platform = self._validate_platform(platform)

        self.setObjectName("heroKbd")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        # shadow-small
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, KBD_SHADOW["offset_y"])
        self._shadow.setBlurRadius(KBD_SHADOW["blur"])
        self._shadow.setColor(QColor(0, 0, 0, int(KBD_SHADOW["opacity"] * 255)))
        self.setGraphicsEffect(self._shadow)

        self._layout = QHBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._slots: List[QWidget] = []
        self._rebuild_slots()
        self._apply_styles()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 工具
    # ============================================================
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    @staticmethod
    def _normalize_keys(keys: KbdKeysInput) -> List[str]:
        if keys is None:
            return []
        if isinstance(keys, str):
            return [keys]
        return [str(k) for k in keys]

    @staticmethod
    def _validate_size(size: str) -> str:
        if size not in VALID_KBD_SIZES:
            raise ValueError(f"Kbd: size 必须是 {VALID_KBD_SIZES}，传入 {size!r}")
        return size

    @staticmethod
    def _validate_radius(radius: str) -> str:
        if radius not in VALID_KBD_RADII:
            raise ValueError(f"Kbd: radius 必须是 {VALID_KBD_RADII}，传入 {radius!r}")
        return radius

    @classmethod
    def _resolve_radius(cls, radius: Optional[str], size: str) -> str:
        # None → 按 size 推荐默认；显式值→传验证
        if radius is None:
            return DEFAULT_RADIUS_BY_SIZE[size]
        return cls._validate_radius(radius)

    @staticmethod
    def _validate_platform(platform: str) -> str:
        if platform not in VALID_PLATFORMS:
            raise ValueError(
                f"Kbd: platform 必须是 {VALID_PLATFORMS}，传入 {platform!r}"
            )
        return platform

    def _spec(self) -> dict:
        """当前 size 的像素规格表。"""
        return KBD_SIZE_TABLE[self._size]

    # ============================================================
    # 主题色（对齐 default-100 / foreground-600）
    # ============================================================
    def _bg_color(self) -> str:
        if self._theme == "dark":
            return HEROUI_COLORS["default"][800]
        return HEROUI_COLORS["default"][100]

    def _fg_color(self) -> QColor:
        if self._theme == "dark":
            return QColor(HEROUI_COLORS["default"][300])
        return QColor(HEROUI_COLORS["default"][600])

    def _radius_px(self) -> str:
        # Kbd 自治圆角表（不走全局 RADIUS）：
        # —— Kbd 高度 18~28px，全局 token 会被 Qt 短边一半钳制，
        #    导致 lg 与 full 视觉重合，胶囊感丢失。
        # —— 每档 size 的 radius 表保证 lg 严格小于 full（差 2px）。
        spec = self._spec()
        if self._radius == "full":
            h = max(self.minimumHeight(), spec["min_height"])
            return f"{h // 2}px"
        return f"{spec['radius'][self._radius]}px"

    # ============================================================
    # 样式
    # ============================================================
    def _apply_styles(self) -> None:
        spec = self._spec()
        bg = self._bg_color()
        fg = self._fg_color()

        # layout 间距 / padding
        self._layout.setSpacing(spec["spacing"])
        self._layout.setContentsMargins(
            spec["padding_x"],
            spec["padding_y"],
            spec["padding_x"],
            spec["padding_y"],
        )

        # 壳：仅背景 + 圆角；文字 / icon 各自承担颜色
        self.setStyleSheet(
            f"#heroKbd {{ background-color: {bg}; "
            f"border: none; border-radius: {self._radius_px()}; }}"
        )
        # 推送色：Text 走 set_color；icon 走 set_color 重渲染
        for w in self._slots:
            if isinstance(w, _KbdIconLabel):
                w.set_color(fg)
            elif isinstance(w, Text):
                w.set_color(fg)
        self.setMinimumHeight(spec["min_height"])

    # ============================================================
    # slots 构建
    # ============================================================
    def _clear_slots(self) -> None:
        from ...utils import clear_layout
        clear_layout(self._layout)
        self._slots.clear()

    def _make_text(self, text: str, title: str = "") -> Text:
        """创建带 tooltip 的 Text 子控件（fg/theme 由父 Kbd 推，
        子 Text 用固定主题，避免双重注册到 ThemeProvider）。"""
        spec = self._spec()
        fg = self._fg_color()
        t = Text(
            text,
            size=spec["font_size"],
            weight="normal",
            color=fg,
            selectable=False,  # Kbd 内文字不参与选区
            theme=self._theme,  # 固定取父 Kbd 当前主题，不走 auto
            parent=self,
        )
        if title:
            t.setToolTip(title)
        return t

    def _add_slot(self, w: QWidget) -> None:
        # 关键：所有 slot 显式垂直居中——icon pixmap 与 Text baseline 对齐到 layout 中线
        self._layout.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        self._slots.append(w)

    def _rebuild_slots(self) -> None:
        self._clear_slots()
        spec = self._spec()
        fg = self._fg_color()

        # 1) keys → SVG (默认) / Text(unicode 字符) (use_unicode=True 或无 SVG)
        for key in self._keys:
            title = KBD_KEYS_LABEL_MAP.get(key, key)
            icon_name = None if self._use_unicode else resolve_icon(key, self._platform)
            if icon_name:
                w: QWidget = _KbdIconLabel(
                    icon_name, title, spec["icon_size"], fg, self
                )
            else:
                glyph = KBD_KEYS_GLYPH_MAP.get(key, key)
                w = self._make_text(glyph, title=title)
            self._add_slot(w)

        # 2) children 文本
        if self._children_text:
            self._add_slot(self._make_text(self._children_text))

    # ============================================================
    # 公共 API
    # ============================================================
    def set_keys(self, keys: KbdKeysInput) -> None:
        self._keys = self._normalize_keys(keys)
        self._rebuild_slots()
        self._apply_styles()

    def keys(self) -> List[str]:
        return list(self._keys)

    def set_children(self, text: str) -> None:
        self._children_text = str(text or "")
        self._rebuild_slots()
        self._apply_styles()

    def children_text(self) -> str:
        return self._children_text

    def set_use_unicode(self, use_unicode: bool) -> None:
        if bool(use_unicode) == self._use_unicode:
            return
        self._use_unicode = bool(use_unicode)
        self._rebuild_slots()
        self._apply_styles()

    def set_size(self, size: str) -> None:
        size = self._validate_size(size)
        if size == self._size:
            return
        self._size = size
        # 未显式传过 radius——跟随新 size 重推
        if not self._radius_explicit:
            self._radius = DEFAULT_RADIUS_BY_SIZE[size]
        self._rebuild_slots()
        self._apply_styles()

    def set_radius(self, radius: Optional[str]) -> None:
        # 传 None → 切回“跟随 size 推断”
        if radius is None:
            self._radius_explicit = False
            new_r = DEFAULT_RADIUS_BY_SIZE[self._size]
        else:
            new_r = self._validate_radius(radius)
            self._radius_explicit = True
        if new_r == self._radius:
            return
        self._radius = new_r
        self._apply_styles()

    def set_platform(self, platform: str) -> None:
        platform = self._validate_platform(platform)
        if platform == self._platform:
            return
        self._platform = platform
        # platform 影响 fn/alt icon —— 重建 slots
        self._rebuild_slots()
        self._apply_styles()

    def set_theme(self, theme: str) -> None:
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        # 同步子 Text 的着色 + 主题（子 Text 不注册到 Provider）
        for w in self._slots:
            if isinstance(w, Text):
                w.set_theme(self._theme)
        self._apply_styles()

    def _apply_provider_theme(self, theme: str) -> None:
        """ThemeProvider 广播专用入口。"""
        self._theme = theme
        # 子 Text 用固定主题，必须 Kbd 推送
        for w in self._slots:
            if isinstance(w, Text):
                w.set_theme(theme)
        self._apply_styles()

    # ============================================================
    # 元信息
    # ============================================================
    @staticmethod
    def valid_keys() -> tuple:
        """返回所有合法 KbdKey 名称。"""
        return KBD_KEY_NAMES

    @staticmethod
    def valid_sizes() -> tuple:
        return VALID_KBD_SIZES

    @staticmethod
    def valid_radii() -> tuple:
        return VALID_KBD_RADII

    @staticmethod
    def valid_platforms() -> tuple:
        return VALID_PLATFORMS


__all__ = ["Kbd"]
