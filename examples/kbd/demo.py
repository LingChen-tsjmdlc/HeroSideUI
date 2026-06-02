"""Kbd 组件示例 — 对齐 HeroUI v2 + 项目扩展（size/radius/platform/新增 SVG）。

覆盖：默认/全 Key/Glyph/复合键/children/纯文字/三档 size/五档 radius/
平台敏感 fn|alt/24 个新增 SVG 总览。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hero_side_ui import Body, Caption, Kbd
from hero_side_ui.core import ThemeProvider
from hero_side_ui.themes import HEROUI_COLORS
from hero_side_ui.utils.icon_utils import load_svg_icon
from _base import DemoBase


# ============================================================
# 布局工具
# ============================================================
def _row(*widgets: QWidget, spacing: int = 12) -> QWidget:
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for w in widgets:
        lay.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    box.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    return box


def _column(*widgets: QWidget, spacing: int = 8) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
    for w in widgets:
        lay.addWidget(w)
    return box


def _labeled(label: str, widget: QWidget) -> QWidget:
    return _row(Caption(label), widget, spacing=10)


# ============================================================
# 1. Default
# ============================================================
def _make_default() -> list[QWidget]:
    return [
        Kbd(keys="command"),
        Kbd(keys="shift"),
        Kbd(keys="enter"),
    ]


# ============================================================
# 2. 全部 KbdKey
# ============================================================
_ALL_KEYS = list(Kbd.valid_keys())


def _make_all_keys() -> QWidget:
    rows: list[QWidget] = []
    cols = 6
    for i in range(0, len(_ALL_KEYS), cols):
        chunk = _ALL_KEYS[i : i + cols]
        items = [_labeled(k, Kbd(keys=k)) for k in chunk]
        rows.append(_row(*items, spacing=20))
    return _column(*rows, spacing=10)


# ============================================================
# 3. Glyph 模式
# ============================================================
def _make_glyph_mode() -> list[QWidget]:
    keys = [
        "command",
        "shift",
        "option",
        "ctrl",
        "enter",
        "backspace",
        "escape",
        "space",
        "delete",
    ]
    return [Kbd(keys=k, use_unicode=True) for k in keys]


# ============================================================
# 4. 复合按键
# ============================================================
def _make_combinations() -> QWidget:
    return _column(
        _labeled("New file (macOS)", Kbd(keys=["command", "shift"], children="N")),
        _labeled("Quit application", Kbd(keys=["command"], children="Q")),
        _labeled("Run command", Kbd(keys=["ctrl"], children="K")),
        _labeled("Force quit", Kbd(keys=["command", "option", "escape"])),
        _labeled("Switch app", Kbd(keys=["command", "tab"])),
        _labeled("Windows lock", Kbd(keys=["win"], children="L")),
        _labeled("Move to Trash", Kbd(keys=["command"], children="⌫")),
        spacing=10,
    )


# ============================================================
# 5. keys + children 自定义文字
# ============================================================
def _make_with_children() -> list[QWidget]:
    return [
        Kbd(keys="command", children="K"),
        Kbd(keys=["command", "shift"], children="P"),
        Kbd(keys="ctrl", children="/"),
        Kbd(keys="alt", children="F4"),
    ]


# ============================================================
# 6. 纯文字 Kbd
# ============================================================
def _make_plain_text() -> list[QWidget]:
    return [
        Kbd(children="Esc"),
        Kbd(children="Enter"),
        Kbd(children="Space"),
        Kbd(children="Click"),
    ]


# ============================================================
# 7. Sizes
# ============================================================
def _make_sizes() -> QWidget:
    return _row(
        _labeled("sm", Kbd(keys=["command", "shift"], children="N", size="sm")),
        _labeled("md", Kbd(keys=["command", "shift"], children="N", size="md")),
        _labeled("lg", Kbd(keys=["command", "shift"], children="N", size="lg")),
        spacing=24,
    )


# ============================================================
# 8. Radii
# ============================================================
# 三档 size × 五档 radius 矩阵：体现 Qt「border-radius 钳制到短边一半」规律——
# sm/md 高度容不下 lg(14px)，lg 与 full 视觉趋同；lg size(28px) 五档差异最清晰。
def _radius_row(size: str) -> QWidget:
    return _row(
        Caption(f"size={size}"),
        _labeled("none", Kbd(keys="command", children="K", size=size, radius="none")),
        _labeled("sm", Kbd(keys="command", children="K", size=size, radius="sm")),
        _labeled("md", Kbd(keys="command", children="K", size=size, radius="md")),
        _labeled("lg", Kbd(keys="command", children="K", size=size, radius="lg")),
        _labeled("full", Kbd(keys="command", children="K", size=size, radius="full")),
        spacing=18,
    )


def _make_radii() -> QWidget:
    return _column(
        _radius_row("sm"),
        _radius_row("md"),
        _radius_row("lg"),
        spacing=12,
    )


# ============================================================
# 9. Platform
# ============================================================
def _make_platform() -> QWidget:
    return _column(
        Caption("fn 键 / alt 键的 icon 跟平台走（auto 由 sys.platform 决定）："),
        _row(
            _labeled("fn auto", Kbd(keys="fn")),
            _labeled("fn mac", Kbd(keys="fn", platform="mac")),
            _labeled("fn win", Kbd(keys="fn", platform="win")),
            spacing=24,
        ),
        _row(
            _labeled("alt auto", Kbd(keys="alt")),
            _labeled("alt mac", Kbd(keys="alt", platform="mac")),
            _labeled("alt win", Kbd(keys="alt", platform="win")),
            spacing=24,
        ),
        spacing=10,
    )


# ============================================================
# 10. 24 个新增 SVG 总览（主题感知 + Grid 整齐排列）
# ============================================================
# 24 个全部用上：22 个对应 KbdKey + fn/alt 的另一个平台变体
_NEW_ICONS: list[tuple[str, str]] = [
    ("carbon--mac-command", "command"),
    ("carbon--mac-shift", "shift"),
    ("qlementine-icons--key-ctrl", "ctrl"),
    ("carbon--mac-option", "option / alt(mac)"),
    ("tabler--alt", "alt (win)"),
    ("boxicons--enter", "enter"),
    ("material-symbols--backspace-outline", "backspace ⌫"),
    ("material-symbols--delete-outline", "delete (Forward)"),
    ("bi--escape", "escape"),
    ("octicon--tab-24", "tab"),
    ("bi--capslock", "capslock"),
    ("teenyicons--up-solid", "up"),
    ("teenyicons--right-solid", "right"),
    ("teenyicons--down-solid", "down"),
    ("teenyicons--left-solid", "left"),
    ("iconoir--page-up", "pageup"),
    ("iconoir--page-down", "pagedown"),
    ("mdi--arrow-top-left", "home"),
    ("mdi--arrow-bottom-right", "end"),
    ("material-symbols--help-outline", "help"),
    ("tabler--space", "space"),
    ("ion--globe-outline", "fn (mac)"),
    ("tabler--function", "fn (win)"),
    ("mingcute--windows-line", "win"),
]


class _IconCell(QWidget):
    """单个 icon 展示格子：图标 + 标签 + 文件名，主题感知自动重染色。"""

    def __init__(self, icon_name: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._theme = ThemeProvider.instance().current_theme

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 自绘 icon QLabel：主题感知染色（demo 内部 helper，不污染组件公共 API）
        self._icon = QLabel(self)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._icon.setAutoFillBackground(False)
        self._icon.setToolTip(label)
        v.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self._label = Caption(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._sub = Caption(icon_name)
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._sub, 0, Qt.AlignmentFlag.AlignHCenter)

        self.setObjectName("kbdIconCell")
        self._apply_styles()
        ThemeProvider.instance().register(self)

    def _fg(self) -> QColor:
        if self._theme == "dark":
            return QColor(HEROUI_COLORS["default"][300])
        return QColor(HEROUI_COLORS["default"][600])

    def _bg(self) -> str:
        if self._theme == "dark":
            return HEROUI_COLORS["default"][800]
        return HEROUI_COLORS["default"][100]

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"#kbdIconCell {{ background-color: {self._bg()}; "
            f"border-radius: 8px; }}"
        )
        pm = load_svg_icon(self._icon_name, size=22, color=self._fg())
        self._icon.setPixmap(pm)
        self._icon.setFixedSize(pm.size())

    # ThemeProvider.register 契约要求
    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str) -> None:
        self._theme = theme
        self._apply_styles()


def _make_new_icons() -> QWidget:
    """4 列 Grid 整齐排列；cell 自带圆角浅底，跟随主题。"""
    box = QWidget()
    grid = QGridLayout(box)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(12)
    cols = 4
    for idx, (icon_name, label) in enumerate(_NEW_ICONS):
        r, c = divmod(idx, cols)
        grid.addWidget(_IconCell(icon_name, label), r, c)
    # 列等宽
    for c in range(cols):
        grid.setColumnStretch(c, 1)
    return box


# ============================================================
# Demo 主类
# ============================================================
class KbdDemo(DemoBase):
    component_name = "Kbd"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 纯横排的章节走基类 add_section（支持 widget 列表）
        self.add_section(layout, "Default", _make_default(), spacing=12)

        # 全 Key Grid 是 "caption + Kbd" 嵌套结构，基类 helper 不覆盖，保留自绘
        layout.addWidget(self._section_title("All Keys (内置 KbdKey 全集, SVG 模式)"))
        layout.addWidget(_make_all_keys())

        self.add_section(
            layout,
            "Glyph Mode (use_unicode=True, unicode 字符)",
            _make_glyph_mode(),
            spacing=12,
        )

        # 多组 "caption + Kbd" 竖排，结构特殊保留自绘
        layout.addWidget(self._section_title("Combinations (复合按键)"))
        layout.addWidget(_make_combinations())

        self.add_section(
            layout,
            "With Children (keys + 自定义文字)",
            _make_with_children(),
            spacing=12,
        )

        self.add_section(
            layout,
            "Plain Text (纯文字 Kbd, 无 keys)",
            _make_plain_text(),
            spacing=12,
        )

        # Sizes / Radii / Platform 内部带 "caption + Kbd" 标签，保留自绘
        layout.addWidget(self._section_title("Sizes (sm / md / lg)"))
        layout.addWidget(_make_sizes())

        layout.addWidget(self._section_title("Radii (none / sm / md / lg / full)"))
        layout.addWidget(_make_radii())

        layout.addWidget(self._section_title("Platform (fn / alt 平台敏感)"))
        layout.addWidget(_make_platform())

        # 24 icon 总览：自定义 4 列 Grid + 主题感知 cell，基类 helper 不覆盖
        layout.addWidget(self._section_title("24 个新增 SVG 总览"))
        layout.addWidget(
            Body(
                "全部 24 个 SVG 都已用上：22 个对应 KbdKey + 2 个平台变体（"
                "fn 的 win 字样、alt 的 win 字样）。fn/alt 在 mac 与 win 下走"
                "不同 icon，由 platform 参数控制。"
            )
        )
        layout.addWidget(_make_new_icons())


if __name__ == "__main__":
    KbdDemo.run()
