"""字色调色板窗口：点色块、输入 hex 或打开系统取色器，把选中的颜色发给主窗口。

窗口本身用的是库里的 Window 组件（子窗口）。
"""

from __future__ import annotations

import re

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hero_side_ui import Body, Button, Caption, Divider, Input, Subtitle, Window
from hero_side_ui.core._foreground_config import contrast
from hero_side_ui.themes import HEROUI_COLORS

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
COMMON = ("#FEFEFF", "#11181C", "#ECEDEE", "#D4D4D8", "#71717A", "#52525B", "#000000", "#FFFFFF")
_NEED = 4.5


class _Swatch(QPushButton):
    """一个色块：点击发 picked，鼠标移上去发 entered（用来预览对比度）。"""

    picked = Signal(str)
    entered = Signal(str)

    def __init__(self, hex_color: str, size: int = 26, parent: QWidget | None = None):
        super().__init__(parent)
        self._hex = hex_color
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(hex_color)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            f"QPushButton {{ background: {hex_color}; border: 1px solid rgba(128,128,128,0.45);"
            f" border-radius: 6px; }} QPushButton:hover {{ border: 2px solid #006FEE; }}"
        )
        self.clicked.connect(lambda *_: self.picked.emit(self._hex))

    def enterEvent(self, event):
        self.entered.emit(self._hex)
        super().enterEvent(event)


class PaletteWindow(Window):
    """调色板子窗口。"""

    color_picked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(width=460, height=720, min_width=420, min_height=480, parent=parent)
        self.setWindowTitle("字色调色板")
        self._refs: list[tuple[str, str]] = []
        self._recent: list[str] = []
        self._current = "#11181C"

        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(20, 14, 20, 20)
        root.setSpacing(8)

        self._target = Subtitle("尚未选择")
        root.addWidget(self._target)
        self._hint = Caption("先在主窗口里选好要改的位置，再点“选色”。")
        root.addWidget(self._hint)

        row = QHBoxLayout()
        self._hex = Input(placeholder="#RRGGBB", label_placement="outside", size="sm")
        self._hex.setFixedWidth(130)
        self._hex.text_changed.connect(self._on_hex_typing)
        self._hex.returned.connect(self._apply_hex)
        apply_btn = Button("应用", size="md", color="primary")
        apply_btn.clicked.connect(lambda *_: self._apply_hex())
        dialog_btn = Button("系统取色器…", size="md", variant="bordered")
        dialog_btn.clicked.connect(lambda *_: self._open_dialog())
        row.addWidget(self._hex)
        row.addWidget(apply_btn)
        row.addWidget(dialog_btn)
        row.addStretch()
        root.addLayout(row)

        root.addWidget(Divider())
        root.addWidget(Subtitle("对比度（建议 ≥ 4.5）"))
        self._contrast_box = QVBoxLayout()
        self._contrast_box.setSpacing(2)
        root.addLayout(self._contrast_box)

        root.addWidget(Divider())
        root.addWidget(Subtitle("语义色板（点击取色）"))
        self._ramps_box = QVBoxLayout()
        self._ramps_box.setSpacing(4)
        root.addLayout(self._ramps_box)

        root.addWidget(Subtitle("常用字色"))
        root.addLayout(self._swatch_row(COMMON))

        root.addWidget(Subtitle("最近使用"))
        self._recent_box = QHBoxLayout()
        self._recent_box.setSpacing(4)
        self._recent_holder = QWidget()
        self._recent_holder.setLayout(self._recent_box)
        root.addWidget(self._recent_holder)
        root.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(body)
        self.set_content(scroll)
        self._fill_ramps()
        self._refresh_contrast(self._current)

    # ---------------------------------------------------------------- 对外
    def set_target(self, text: str, current: str | None, refs: list[tuple[str, str]]):
        """切换正在编辑的位置。

        Args:
            text: 例如 "warning · 亮色 · flat.hover.text"。
            current: 这个位置现在已经写的颜色；没写为 None。
            refs: 该位置的参考底色 [(说明, hex), ...]，用来算对比度。
        """
        self._target.setText(f"正在编辑：{text}")
        self._refs = refs
        self._current = current or self._current
        self._hex.set_text(current or "")
        self._refresh_contrast(self._current)

    # ---------------------------------------------------------------- 内部
    def _swatch_row(self, colors) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(4)
        for c in colors:
            lay.addWidget(self._make_swatch(c))
        lay.addStretch()
        return lay

    def _make_swatch(self, color: str) -> _Swatch:
        sw = _Swatch(color)
        sw.picked.connect(self._pick)
        sw.entered.connect(self._refresh_contrast)
        return sw

    def _fill_ramps(self):
        for name in ("default", "primary", "secondary", "success", "warning", "danger"):
            row = QHBoxLayout()
            row.setSpacing(3)
            label = Caption(name)
            label.setFixedWidth(62)
            row.addWidget(label)
            for step in sorted(HEROUI_COLORS[name]):
                row.addWidget(self._make_swatch(HEROUI_COLORS[name][step]))
            row.addStretch()
            self._ramps_box.addLayout(row)

    def _pick(self, color: str):
        self._current = color
        self._hex.set_text(color)
        self._remember(color)
        self._refresh_contrast(color)
        self.color_picked.emit(color)

    def _remember(self, color: str):
        if color in self._recent:
            self._recent.remove(color)
        self._recent.insert(0, color)
        del self._recent[14:]
        while self._recent_box.count():
            item = self._recent_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for c in self._recent:
            self._recent_box.addWidget(self._make_swatch(c))
        self._recent_box.addStretch()

    def _on_hex_typing(self, text: str):
        if _HEX.match(text.strip()):
            self._refresh_contrast(text.strip())

    def _apply_hex(self):
        text = self._hex.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        if _HEX.match(text):
            self._pick(text.upper())
        else:
            self._hint.setText(f"{text!r} 不是 #RRGGBB / is not #RRGGBB")

    def _open_dialog(self):
        color = QColorDialog.getColor(QColor(self._current), self, "选择字色")
        if color.isValid():
            self._pick(color.name().upper())

    def _refresh_contrast(self, color: str):
        """用 color 对每个参考底色算对比度并列出。"""
        while self._contrast_box.count():
            item = self._contrast_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._contrast_box.addWidget(Body(f"候选颜色 {color}"))
        if not self._refs:
            self._contrast_box.addWidget(Caption("这个位置没有可比较的底色"))
            return
        for who, bg in self._refs:
            ratio = contrast(color, bg)
            ok = ratio >= _NEED
            line = Body(f"{who}  底 {bg}   {ratio:.2f}:1   {'通过' if ok else '不足'}")
            line.set_color("#17c964" if ok else "#f31260")
            self._contrast_box.addWidget(line)


__all__ = ["PaletteWindow"]
