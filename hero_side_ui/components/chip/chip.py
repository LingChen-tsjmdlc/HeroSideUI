"""HeroSideUI Chip — 标签/徽章 (HeroUI v2)。完整 API/示例见 docs/chip.md。

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/chip.ts
"""

from __future__ import annotations

from collections.abc import Callable

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
    """HeroUI 风格 Chip 标签。"""

    closed = Signal()

    def __init__(
        self,
        text: str = "",
        color: str = "default",
        variant: str = "solid",
        size: str = "md",
        radius: str = "full",
        avatar: QWidget | None = None,
        start_content: QWidget | None = None,
        end_content: QWidget | None = None,
        is_disabled: bool = False,
        is_closable: bool = False,
        on_close: Callable[[], None] | None = None,
        is_text_selectable: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建 Chip 并装配 dot、头像、文本与关闭按钮。

        Args:
            text: 标签文本。
            color: 语义色。
            variant: 视觉变体；dot 会显示前置圆点。
            size: 尺寸档位，未命中 CHIP_SIZES 时回退 md。
            radius: 圆角档位；full 按盒子短边一半计算。
            avatar: 前置头像 widget。
            start_content: 头像之后、文本之前插入的自定义 widget。
            end_content: 文本之后插入的自定义 widget。
            is_disabled: 是否禁用，影响交互与半透明效果。
            is_closable: 是否显示关闭按钮。
            on_close: 关闭时先于 closed 信号调用的回调。
            is_text_selectable: 文本是否可选中。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。
        """
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
        """是否为「单字符且无附加内容」，决定渲染成正方形。

        Returns:
            文本长度为 1、且没有 avatar / start / end / 关闭按钮，
            并且 variant 不是 dot 时为 True。
        """
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
        """按 CHIP_SIZES 装配横向布局的全部子元素。

        dot 始终创建、再由可见性开关控制；avatar / start_content /
        end_content 按是否传入决定是否插入布局。

        Note:
            末尾固定为 Minimum × Fixed 的尺寸策略，实际高度由 _apply_styles 给出。
        """
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
        """同步 dot 与关闭按钮的可见性。

        Note:
            提供过 on_close 回调时关闭按钮始终保留，与 is_closable 取或。
        """
        self._dot.setVisible(self._variant == "dot")
        self._close_btn.setVisible(bool(self._is_closable or self._on_close))

    # ---- styles ----

    def _apply_styles(self):
        """按当前尺寸、圆角与配色刷新 QSS 和布局约束。

        单字符方块走 setFixedSize 并清零边距；普通模式必须解除上一轮设下的
        固定尺寸与最大宽度，否则从方块切回长文本时尺寸会锁死。

        Note:
            Qt 的 border-radius 超过短边一半会渲染异常，所以非 full 档也要
            用 min(token_px, box_h // 2) 截断。
        """
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
        """应用单个图形效果：disabled 半透明优先于 shadow 投影。

        Args:
            s: 配色 token 字典，读取 has_shadow / shadow_color。

        Note:
            Qt 一个 widget 只能挂一个 graphics effect，三分支互斥；
            都不命中时置 None 清掉旧效果。
        """
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
        """把十六进制阴影色转成带 50% 透明度的 QColor。

        Args:
            hex_color: 十六进制颜色字符串。

        Returns:
            alpha 设为 0.5 的 QColor。
        """
        c = QColor(hex_color)
        c.setAlphaF(0.5)
        return c

    # ---- close ----

    def _handle_close(self):
        """执行关闭：回调、closed 信号、隐藏。

        Note:
            与 Alert 一致，只隐藏不销毁对象，便于复用。
        """
        if self._on_close:
            self._on_close()
        self.closed.emit()
        self.hide()

    # ---- setters ----

    def set_text(self, text: str):
        """更新标签文本并重算样式。

        Args:
            text: 新文本；长度变化会影响是否走单字符方块布局。
        """
        self._text = text
        self._label.setText(text)
        self._apply_styles()

    def text(self) -> str:
        """返回当前标签文本。

        Returns:
            构造或 set_text 设置的文本。
        """
        return self._text

    def set_color(self, color: str):
        """切换语义色并重算配色。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        """切换视觉变体，并同步 dot 可见性。

        Args:
            variant: 变体名；dot 会显示前置圆点。
        """
        self._variant = variant
        self._update_children_visibility()
        self._apply_styles()

    def set_size(self, size: str):
        """切换尺寸档位，同步字号、图标与间距。

        Args:
            size: 档位名；不在 CHIP_SIZES 中时直接忽略本次调用。

        Note:
            除布局外还要重设 label 字号、关闭按钮图标尺寸与 icon_only_side，
            以及已挂载 avatar 的固定尺寸。
        """
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
        """切换圆角档位并重算 QSS。

        Args:
            radius: 圆角档位；非 full 档仍按短边一半截断。
        """
        self._radius = radius
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        """切换禁用状态。

        Args:
            disabled: True 时挂半透明效果并禁用交互。
        """
        self._is_disabled = disabled
        self._apply_styles()

    def set_closable(self, closable: bool):
        """切换关闭按钮是否显示。

        Args:
            closable: 是否可关闭；提供过 on_close 时按钮始终保留。
        """
        self._is_closable = closable
        self._update_children_visibility()
        self._apply_styles()

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 的注册状态。

        auto 模式注册接收广播；从 auto 切回固定主题时必须先 unregister，
        否则后续广播会覆盖用户设定。

        Args:
            theme: 主题名，或 auto 表示跟随全局主题。
        """
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
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._label.set_theme(theme)
        self._close_btn.set_theme(theme)
        self._apply_styles()
