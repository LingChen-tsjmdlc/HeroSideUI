"""Kbd 键盘按键组件：bg-default-100 + shadow-small；扩展 size/radius/platform 三档。"""

from __future__ import annotations

from collections.abc import Sequence

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

KbdKeysInput = str | Sequence[str] | None

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
        parent: QWidget | None = None,
    ):
        """创建 SVG icon 子控件。

        Args:
            icon_name: SVG icon 名。
            title: tooltip 文本。
            size: 图标边长（像素）。
            color: 图标颜色。
            parent: Qt 父对象。
        """
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
        """按主题色重渲染图标并固定尺寸。

        Args:
            color: 新图标颜色。
        """
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
        radius: str | None = None,
        platform: str = "auto",
        theme: str = "auto",
        use_unicode: bool = False,
        parent: QWidget | None = None,
    ):
        """创建键盘按键组件。

        Args:
            children: 直接文本子内容。
            keys: 按键序列（str / 列表 / None）。
            size: 尺寸档位。
            radius: 圆角档位；None 跟随 size 推断。
            platform: 图标平台（auto / mac / win / linux）。
            theme: auto / light / dark。
            use_unicode: 是否用 Unicode 字形替代 SVG。
            parent: Qt 父对象。
        """
        super().__init__(parent)

        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._children_text = str(children or "")
        self._keys: list[str] = self._normalize_keys(keys)
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

        self._slots: list[QWidget] = []
        self._rebuild_slots()
        self._apply_styles()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 工具
    # ============================================================
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """将主题模式解析为实际 light / dark。

        Args:
            mode: 主题模式字符串。

        Returns:
            str: "light" 或 "dark"。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    @staticmethod
    def _normalize_keys(keys: KbdKeysInput) -> list[str]:
        """把 keys 输入统一成字符串列表。

        Args:
            keys: str / 序列 / None。

        Returns:
            list[str]: 归一化后的按键列表。
        """
        if keys is None:
            return []
        if isinstance(keys, str):
            return [keys]
        return [str(k) for k in keys]

    @staticmethod
    def _validate_size(size: str) -> str:
        """校验尺寸档位，非法值抛 ValueError。

        Args:
            size: 待校验尺寸。

        Returns:
            str: 合法尺寸。
        """
        if size not in VALID_KBD_SIZES:
            raise ValueError(f"Kbd: size 必须是 {VALID_KBD_SIZES}，传入 {size!r}")
        return size

    @staticmethod
    def _validate_radius(radius: str) -> str:
        """校验圆角档位，非法值抛 ValueError。

        Args:
            radius: 待校验圆角。

        Returns:
            str: 合法圆角。
        """
        if radius not in VALID_KBD_RADII:
            raise ValueError(f"Kbd: radius 必须是 {VALID_KBD_RADII}，传入 {radius!r}")
        return radius

    @classmethod
    def _resolve_radius(cls, radius: str | None, size: str) -> str:
        """解析最终圆角：None 按 size 推荐默认，显式值走校验。

        Args:
            radius: 圆角档位或 None。
            size: 当前尺寸档位。

        Returns:
            str: 最终生效的圆角档位。
        """
        if radius is None:
            return DEFAULT_RADIUS_BY_SIZE[size]
        return cls._validate_radius(radius)

    @staticmethod
    def _validate_platform(platform: str) -> str:
        """校验平台 token，非法值抛 ValueError。

        Args:
            platform: 待校验平台。

        Returns:
            str: 合法平台 token。
        """
        if platform not in VALID_PLATFORMS:
            raise ValueError(f"Kbd: platform 必须是 {VALID_PLATFORMS}，传入 {platform!r}")
        return platform

    def _spec(self) -> dict:
        """当前 size 的像素规格表。

        Returns:
            dict: 含 padding / spacing / font_size / icon_size / radius 等规格。
        """
        return KBD_SIZE_TABLE[self._size]

    # ============================================================
    # 主题色（对齐 default-100 / foreground-600）
    # ============================================================
    def _bg_color(self) -> str:
        """背景色（对齐 default-100 / dark-default-800）。

        Returns:
            str: 十六进制背景色串。
        """
        if self._theme == "dark":
            return HEROUI_COLORS["default"][800]
        return HEROUI_COLORS["default"][100]

    def _fg_color(self) -> QColor:
        """前景文字色（对齐 foreground-600 / dark-300）。

        Returns:
            QColor: 文字颜色。
        """
        if self._theme == "dark":
            return QColor(HEROUI_COLORS["default"][300])
        return QColor(HEROUI_COLORS["default"][600])

    def _radius_px(self) -> str:
        """计算实际圆角像素值字符串。

        Returns:
            str: 形如 "8px" 的圆角值。

        Note:
            Kbd 自治圆角表（不走全局 RADIUS）：Kbd 高度 18~28px，
            全局 token 会被 Qt 短边一半钳制导致 lg 与 full 重合；
            每档 size 的 radius 表保证 lg 严格小于 full（差 2px）。
        """
        spec = self._spec()
        if self._radius == "full":
            h = max(self.minimumHeight(), spec["min_height"])
            return f"{h // 2}px"
        return f"{spec['radius'][self._radius]}px"

    # ============================================================
    # 样式
    # ============================================================
    def _apply_styles(self) -> None:
        """套用背景、圆角、padding 与子控件配色。"""
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
            if isinstance(w, (_KbdIconLabel, Text)):
                w.set_color(fg)
        self.setMinimumHeight(spec["min_height"])

    # ============================================================
    # slots 构建
    # ============================================================
    def _clear_slots(self) -> None:
        """清空 layout 与 slots 记录，供重建前使用。"""
        from ...utils import clear_layout

        clear_layout(self._layout)
        self._slots.clear()

    def _make_text(self, text: str, title: str = "") -> Text:
        """创建带 tooltip 的 Text 子控件。

        Args:
            text: 文本内容。
            title: tooltip 文本（可空）。

        Returns:
            Text: 配置好主题与颜色的子控件。

        Note:
            fg/theme 由父 Kbd 推，子 Text 用固定主题，避免双重注册到
            ThemeProvider。
        """
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
        """把子控件加入布局并登记到 slots（强制垂直居中）。

        Args:
            w: 待加入的子控件（icon 或 Text）。
        """
        # 关键：所有 slot 显式垂直居中——icon pixmap 与 Text baseline 对齐到 layout 中线
        self._layout.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        self._slots.append(w)

    def _rebuild_slots(self) -> None:
        """依据 keys 与 children 重建全部子控件（icon / 文字）。"""
        self._clear_slots()
        spec = self._spec()
        fg = self._fg_color()

        # 1) keys → SVG (默认) / Text(unicode 字符) (use_unicode=True 或无 SVG)
        for key in self._keys:
            title = KBD_KEYS_LABEL_MAP.get(key, key)
            icon_name = None if self._use_unicode else resolve_icon(key, self._platform)
            if icon_name:
                w: QWidget = _KbdIconLabel(icon_name, title, spec["icon_size"], fg, self)
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
        """设置按键序列并重建显示。

        Args:
            keys: str / 列表 / None。
        """
        self._keys = self._normalize_keys(keys)
        self._rebuild_slots()
        self._apply_styles()

    def keys(self) -> list[str]:
        """返回当前按键列表副本。

        Returns:
            list[str]: 当前按键序列。
        """
        return list(self._keys)

    def set_children(self, text: str) -> None:
        """设置直接文本子内容并重建显示。

        Args:
            text: 文本内容。
        """
        self._children_text = str(text or "")
        self._rebuild_slots()
        self._apply_styles()

    def children_text(self) -> str:
        """返回当前文本子内容。

        Returns:
            str: 当前 children 文本。
        """
        return self._children_text

    def set_use_unicode(self, use_unicode: bool) -> None:
        """切换 Unicode 字形 / SVG 渲染。

        Args:
            use_unicode: True 用 Unicode 字形，False 用 SVG。
        """
        if bool(use_unicode) == self._use_unicode:
            return
        self._use_unicode = bool(use_unicode)
        self._rebuild_slots()
        self._apply_styles()

    def set_size(self, size: str) -> None:
        """设置尺寸档位。

        Args:
            size: 尺寸名（非法值抛 ValueError）。

        Note:
            未显式传过 radius 时，新 size 会重推默认 radius。
        """
        size = self._validate_size(size)
        if size == self._size:
            return
        self._size = size
        # 未显式传过 radius——跟随新 size 重推
        if not self._radius_explicit:
            self._radius = DEFAULT_RADIUS_BY_SIZE[size]
        self._rebuild_slots()
        self._apply_styles()

    def set_radius(self, radius: str | None) -> None:
        """设置圆角档位；传 None 切回「跟随 size 推断」。

        Args:
            radius: 圆角档位或 None。
        """
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
        """设置图标平台（影响 fn/alt 图标）。

        Args:
            platform: 平台 token（非法值抛 ValueError）。
        """
        platform = self._validate_platform(platform)
        if platform == self._platform:
            return
        self._platform = platform
        # platform 影响 fn/alt icon —— 重建 slots
        self._rebuild_slots()
        self._apply_styles()

    def set_theme(self, theme: str) -> None:
        """设置主题。

        Args:
            theme: auto / light / dark。auto 注册 ThemeProvider 跟随全局。

        Note:
            会同步子 Text 的着色与主题（子 Text 不注册到 Provider）。
        """
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
        """ThemeProvider 广播回调：更新主题并推送子 Text。

        Args:
            theme: 广播下发的实际主题（light/dark）。
        """
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
        """返回所有合法 KbdKey 名称。

        Returns:
            tuple: 合法 key 名称集合。
        """
        return KBD_KEY_NAMES

    @staticmethod
    def valid_sizes() -> tuple:
        """返回所有合法尺寸档位。

        Returns:
            tuple: 合法 size 集合。
        """
        return VALID_KBD_SIZES

    @staticmethod
    def valid_radii() -> tuple:
        """返回所有合法圆角档位。

        Returns:
            tuple: 合法 radius 集合。
        """
        return VALID_KBD_RADII

    @staticmethod
    def valid_platforms() -> tuple:
        """返回所有合法平台 token。

        Returns:
            tuple: 合法 platform 集合。
        """
        return VALID_PLATFORMS


__all__ = ["Kbd"]
