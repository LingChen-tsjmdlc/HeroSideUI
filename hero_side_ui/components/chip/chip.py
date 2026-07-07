"""HeroSideUI Chip — 标签/徽章 (HeroUI v2)。完整 API/示例见 docs/chip.md。

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/chip.ts
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import CHIP_DOT_SIZE, CHIP_SIZES, RADIUS
from ..button import Button
from ..text import Text
from ._styling import build_chip_styles


class Chip(QWidget):
    """HeroUI 风格 Chip 标签。用法::

        Chip("标签", color="primary")
        Chip("可关闭", color="success", is_closable=True, on_close=fn)
        Chip("New", color="danger", variant="dot")
    """

    closed = Signal()

    def __init__(
        self,
        text: str = "",
        color: str = "default",
        variant: str = "solid",
        size: str = "md",
        radius: str = "full",
        avatar: Optional[QWidget] = None,
        start_content: Optional[QWidget] = None,
        end_content: Optional[QWidget] = None,
        is_disabled: bool = False,
        is_closable: bool = False,
        on_close: Optional[Callable[[], None]] = None,
        is_text_selectable: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroChip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._text = text
        self._color = color
        self._variant = variant
        self._size = size if size in CHIP_SIZES else "md"
        self._radius = radius
        self._avatar = avatar
        self._start_content = start_content
        self._end_content = end_content
        self._is_disabled = is_disabled
        self._is_closable = is_closable
        self._on_close = on_close
        self._is_text_selectable = is_text_selectable
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme

        self._build_ui()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._apply_styles()

    # ---- build ----

    @property
    def _is_one_char(self) -> bool:
        # 单字符且无任何附加内容时 → 渲染为正方形
        return (
            len(self._text) == 1
            and self._avatar is None
            and self._start_content is None
            and self._end_content is None
            and not self._is_closable
            and self._variant != "dot"
        )

    def _build_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(CHIP_SIZES[self._size]["gap"])

        vc = Qt.AlignmentFlag.AlignVCenter

        # dot 指示器（仅 dot variant 显示）
        self._dot = QWidget(self)
        self._dot.setObjectName("HeroChipDot")
        self._dot.setFixedSize(CHIP_DOT_SIZE, CHIP_DOT_SIZE)
        self._layout.addWidget(self._dot, 0, vc)

        # avatar / start_content
        if self._avatar is not None:
            av = CHIP_SIZES[self._size]["avatar_size"]
            self._avatar.setFixedSize(av, av)
            self._layout.addWidget(self._avatar, 0, vc)
        if self._start_content is not None:
            self._layout.addWidget(self._start_content, 0, vc)

        # 文本
        self._label = Text(
            self._text,
            size=CHIP_SIZES[self._size]["text_size"],
            weight="normal",
            theme=self._theme,
            selectable=self._is_text_selectable,
        )
        self._label.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._label, 0, vc)

        # end_content
        if self._end_content is not None:
            self._layout.addWidget(self._end_content, 0, vc)

        # 关闭按钮
        self._close_btn = Button(
            icon_only=True,
            icon="heroicons--x-mark-16-solid",
            icon_size=CHIP_SIZES[self._size]["close_icon_size"],
            variant="light",
            color="default",
            radius="full",
            size="sm",
            theme=self._theme,
        )
        self._close_btn.set_icon_only_side(CHIP_SIZES[self._size]["close_icon_size"] + 4)
        self._close_btn.clicked.connect(self._handle_close)
        self._layout.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._update_children_visibility()
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def _update_children_visibility(self):
        self._dot.setVisible(self._variant == "dot")
        self._close_btn.setVisible(bool(self._is_closable or self._on_close))

    # ---- styles ----

    def _apply_styles(self):
        s = build_chip_styles(self._variant, self._color, self._theme)
        size_cfg = CHIP_SIZES[self._size]
        h = size_cfg["height"]
        pad_x = size_cfg["padding_x"]

        # 布局边距 + 尺寸；box_h 记实际盒子的「短边」，供圆角参照
        if self._is_one_char:
            side = size_cfg["one_char_size"]
            box_h = side
            self.setFixedSize(side, side)
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 单字符方块：label 撑满方块并居中，layout cell 也整体居中
            self._label.setFixedSize(side, side)
            self._layout.setAlignment(self._label, Qt.AlignmentFlag.AlignCenter)
        else:
            box_h = h
            self.setFixedHeight(h)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            # avatar/dot 贴左，左侧留小边距；右侧关闭按钮时收紧
            left = pad_x // 2 if (self._avatar or self._variant == "dot") else pad_x
            right = pad_x // 2 if (self._is_closable or self._on_close) else pad_x
            self._layout.setContentsMargins(left, 0, right, 0)
            self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            # 还原普通模式：解除方块固定尺寸
            self._label.setMinimumSize(0, 0)
            self._label.setMaximumSize(16777215, 16777215)
            self._layout.setAlignment(self._label, Qt.AlignmentFlag.AlignVCenter)

        # 圆角：full 取短边一半；其余取 token，但绝不超过短边一半
        # （Qt border-radius 超过短边一半会渲染异常，不像 CSS 那样裁圆）
        if self._radius == "full":
            r_px = f"{box_h // 2}px"
        else:
            token_px = int(RADIUS.get(self._radius, RADIUS["md"]).rstrip("px"))
            r_px = f"{min(token_px, box_h // 2)}px"

        self.setStyleSheet(
            f"QWidget#HeroChip {{ "
            f"background-color: {s['bg']}; "
            f"border: {s['border']}; "
            f"border-radius: {r_px}; "
            f"}}"
        )
        self._dot.setStyleSheet(
            f"QWidget#HeroChipDot {{ "
            f"background-color: {s['dot_color']}; "
            f"border-radius: {CHIP_DOT_SIZE // 2}px; "
            f"}}"
        )
        self._label.set_color(s["fg"])
        self._close_btn.set_icon_color(s["close_color"])

        self._apply_effect(s)
        self.setEnabled(not self._is_disabled)

    def _apply_effect(self, s: dict):
        # 单效果约束：disabled 优先用半透明，否则 shadow variant 用投影
        if self._is_disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
        elif s["has_shadow"] and s["shadow_color"]:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(18)
            shadow.setColor(self._shadow_qcolor(s["shadow_color"]))
            shadow.setOffset(0, 4)
            self.setGraphicsEffect(shadow)
        else:
            self.setGraphicsEffect(None)

    @staticmethod
    def _shadow_qcolor(hex_color: str) -> QColor:
        c = QColor(hex_color)
        c.setAlphaF(0.5)
        return c

    # ---- close ----

    def _handle_close(self):
        if self._on_close:
            self._on_close()
        self.closed.emit()
        self.hide()

    # ---- setters ----

    def set_text(self, text: str):
        self._text = text
        self._label.setText(text)
        self._apply_styles()

    def text(self) -> str:
        return self._text

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        self._variant = variant
        self._update_children_visibility()
        self._apply_styles()

    def set_size(self, size: str):
        if size not in CHIP_SIZES:
            return
        self._size = size
        cfg = CHIP_SIZES[size]
        self._label.set_size(cfg["text_size"])
        self._close_btn.set_icon_size(cfg["close_icon_size"])
        self._close_btn.set_icon_only_side(cfg["close_icon_size"] + 4)
        self._layout.setSpacing(cfg["gap"])
        if self._avatar is not None:
            self._avatar.setFixedSize(cfg["avatar_size"], cfg["avatar_size"])
        self._apply_styles()

    def set_radius(self, radius: str):
        self._radius = radius
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._apply_styles()

    def set_closable(self, closable: bool):
        self._is_closable = closable
        self._update_children_visibility()
        self._apply_styles()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._label.set_theme(self._theme)
        self._close_btn.set_theme(self._theme)
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        # ThemeProvider 广播专用入口：不重新 register/unregister。
        self._theme = theme
        self._label.set_theme(theme)
        self._close_btn.set_theme(theme)
        self._apply_styles()
