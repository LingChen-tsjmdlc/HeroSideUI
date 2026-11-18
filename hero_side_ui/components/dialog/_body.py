"""Dialog 的内置内容：图标 + 小标题 + 正文，另含图标渲染。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...themes import DIALOG_ICONS, DIALOG_SPEC, HEROUI_COLORS
from ...utils import load_svg_icon, safe_delete
from ..text import Text


def semantic_hex(color: str) -> str:
    """语义色的 DEFAULT 档（500）十六进制；未知色名回退 primary。"""
    return HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])[500]


def default_icon_color(icon) -> str:
    """图标对应的默认语义色：预设图标取表里的色，其余用 primary。"""
    if isinstance(icon, str) and icon in DIALOG_ICONS:
        return DIALOG_ICONS[icon][1]
    return "primary"


def _success_pixmap(size: int, hex_color: str) -> QPixmap:
    """success 图标：语义色圆底 + 白色对勾。"""
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(round(size * dpr), round(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(hex_color))
    p.drawEllipse(QRectF(0, 0, size, size))
    inner = size * DIALOG_SPEC["success_check_ratio"]
    check = load_svg_icon(DIALOG_ICONS["success"][0], size=round(inner), color="#ffffff")
    off = (size - inner) / 2
    p.drawPixmap(QRectF(off, off, inner, inner), check, QRectF(check.rect()))
    p.end()
    return pm


def render_icon(name: str, size: int, color: str) -> QPixmap:
    """渲染图标。

    Args:
        name: 预设图标名（info / success 等），或任意内置图标名 / SVG 路径。
        size: 边长 px。
        color: 语义色名。
    """
    hex_color = semantic_hex(color)
    if name == "success":
        return _success_pixmap(size, hex_color)
    file = DIALOG_ICONS[name][0] if name in DIALOG_ICONS else name
    return load_svg_icon(file, size=size, color=hex_color)


class _Body(QWidget):
    """图标在左、小标题与正文在右；文字固定宽度下自动换行，高度随文字走。"""

    def __init__(
        self, *, theme: str, selectable: bool, icon_size: int, parent: QWidget | None = None
    ):
        """创建内置内容。

        Args:
            theme: auto / light / dark，转给内部文字。
            selectable: 文字能否选中复制。
            icon_size: 图标边长 px。
            parent: 父控件。
        """
        super().__init__(parent)
        self._icon: str | QWidget | None = "info"
        self._color = "primary"
        self._icon_size = icon_size
        self._custom_icon: QWidget | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(DIALOG_SPEC["icon_gap"])

        self._holder = QWidget(self)
        hl = QVBoxLayout(self._holder)
        hl.setContentsMargins(0, 0, 0, 0)
        self._icon_label = QLabel(self._holder)
        hl.addWidget(self._icon_label)
        row.addWidget(self._holder, 0, Qt.AlignmentFlag.AlignTop)

        # 文字列用独立控件承载：文字变化时 Qt 才会同步失效各级布局缓存，高度测量才准
        self._column = QWidget(self)
        col = QVBoxLayout(self._column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(DIALOG_SPEC["text_gap"])
        self._heading = Text(
            "",
            size="sm",
            transparency=DIALOG_SPEC["heading_opacity"],
            selectable=selectable,
            word_wrap=True,
            theme=theme,
            parent=self._column,
        )
        self._message = Text(
            "",
            size="md",
            selectable=selectable,
            word_wrap=True,
            theme=theme,
            parent=self._column,
        )
        col.addWidget(self._heading)
        col.addWidget(self._message)
        col.addStretch(1)
        row.addWidget(self._column, 1)

        self._heading.hide()
        self._message.hide()
        self._refresh_icon()

    def height_for_width(self, width: int) -> int:
        """给定宽度下需要的高度：图标与文字列取高者。

        Note:
            不走 QHBoxLayout 的 heightForWidth：横向布局算它时拿不到文字列的真实宽度，
            结果偏小，这里自己扣掉图标与间距再问文字列。
        """
        icon_w = icon_h = 0
        if not self._holder.isHidden():
            hint = self._holder.sizeHint()
            icon_w, icon_h = hint.width() + DIALOG_SPEC["icon_gap"], hint.height()
        text_h = self._column.layout().totalHeightForWidth(max(1, width - icon_w))
        return max(icon_h, text_h)

    # ---- 文字 ----
    def set_heading(self, text: str | None):
        """设置小标题；None 或空字符串隐藏。"""
        self._heading.setText(text or "")
        self._heading.setHidden(not text)

    def set_message(self, text: str | None):
        """设置正文；None 或空字符串隐藏。"""
        self._message.setText(text or "")
        self._message.setHidden(not text)

    def is_empty(self) -> bool:
        """小标题与正文都没有内容。"""
        return self._heading.isHidden() and self._message.isHidden()

    def set_selectable(self, value: bool):
        """文字能否选中复制。"""
        self._heading.set_selectable(value)
        self._message.set_selectable(value)

    def set_theme(self, theme: str):
        """同步内部文字的主题。"""
        self._heading.set_theme(theme)
        self._message.set_theme(theme)

    # ---- 图标 ----
    def set_icon(self, icon: str | QWidget | None, color: str):
        """设置图标。

        Args:
            icon: 预设图标名 / 内置图标名 / SVG 路径 / 自己的 QWidget / None（不显示）。
            color: 语义色名；自带 QWidget 时不使用。
        """
        self._icon = icon
        self._color = color
        self._refresh_icon()

    def set_icon_size(self, size: int):
        """图标边长 px。"""
        self._icon_size = size
        self._refresh_icon()

    def _refresh_icon(self):
        """按当前图标设置刷新显示：自定义控件优先，其次渲染图标，None 则整块隐藏。"""
        if self._custom_icon is not None and self._custom_icon is not self._icon:
            safe_delete(self._custom_icon)
            self._custom_icon = None
        icon = self._icon
        if isinstance(icon, QWidget):
            self._icon_label.hide()
            if self._custom_icon is not icon:
                icon.setParent(self._holder)
                self._holder.layout().addWidget(icon)
                self._custom_icon = icon
            icon.show()
            self._holder.show()
            return
        if not icon:
            self._holder.hide()
            return
        self._holder.show()
        self._icon_label.setFixedSize(self._icon_size, self._icon_size)
        self._icon_label.setPixmap(render_icon(icon, self._icon_size, self._color))
        self._icon_label.show()


__all__ = ["_Body", "default_icon_color", "render_icon", "semantic_hex"]
