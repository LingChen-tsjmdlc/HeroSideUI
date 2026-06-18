"""HeroSideUI Link 组件 —— 复刻 HeroUI v2 Link。

样式锚点：packages/core/theme/src/components/link.ts
组件锚点：packages/components/link/src/{link.tsx,use-link.ts,link-icon.tsx}

视觉规格：
  base:   relative inline-flex items-center
  size:   sm=14 / md=16 / lg=18 (px)
  color:  foreground / primary / secondary / success / warning / danger
  underline: none / hover / always / active / focus  (offset 4px)
  isBlock=False: hover→opacity-hover(0.8/0.9)  active→opacity-disabled(0.5)
  isBlock=True:  px-2 py-1 + hover 显示 rounded-xl(12px) 半透明色块
                 (foreground/10  其余 5 色 /20)

外部交互：
  href + isExternal → 通过 webbrowser 打开
  showAnchorIcon → 默认 icon-park-outline--share
"""

from __future__ import annotations

import webbrowser
from typing import Optional, Union

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFocusEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from ...animation.tween import stop_tween, tween_value
from ...core import ThemeProvider
from ...themes import (
    HEROUI_COLORS,
    LINK_BLOCK,
    LINK_OPACITY,
    LINK_OPACITY_DURATION,
    LINK_SIZES,
    VALID_LINK_COLORS,
    VALID_LINK_SIZES,
    VALID_LINK_UNDERLINES,
)
from ...utils.icon_utils import load_svg_icon
from ..text import Text

# 默认锚点图标（HeroUI 自带 LinkIcon = 外链小箭头）
DEFAULT_ANCHOR_ICON = "icon-park-outline--share"


# ============================================================
# 私有 SVG icon 子控件（命中铁律 9 例外清单第 1 条）
# ============================================================


class _LinkIconLabel(QLabel):
    """Link 锚点图标槽：QLabel + setPixmap，永不 setText，跟主题着色。"""

    def __init__(
        self,
        icon_name: str,
        size: int,
        color: QColor,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
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

    def set_icon_name(self, icon_name: str, color: QColor) -> None:
        self._icon_name = icon_name
        self.set_color(color)

    def set_size_px(self, size: int, color: QColor) -> None:
        self._size = int(size)
        self.set_color(color)


# ============================================================
# Link 主组件
# ============================================================


class Link(QFrame):
    """HeroUI v2 风格的链接组件。完整 API/示例见 ``docs/link.md``。

    信号:
        clicked()  — 鼠标释放在 widget 内 / 键盘 Space/Enter 触发
        pressed()  — 鼠标按下
        released() — 鼠标释放（无论是否在 widget 内）
    """

    clicked = Signal()
    pressed = Signal()
    released = Signal()

    def __init__(
        self,
        children: str = "",
        *,
        href: str = "",
        size: str = "md",
        color: str = "primary",
        underline: str = "none",
        is_block: bool = False,
        is_external: bool = False,
        is_disabled: bool = False,
        show_anchor_icon: bool = False,
        anchor_icon: Optional[Union[str, QWidget]] = None,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---- 状态 ----
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._children_text = str(children or "")
        self._href = str(href or "")
        self._size = self._validate_size(size)
        self._color = self._validate_color(color)
        self._underline = self._validate_underline(underline)
        self._is_block = bool(is_block)
        self._is_external = bool(is_external)
        self._is_disabled = bool(is_disabled)
        self._show_anchor_icon = bool(show_anchor_icon)
        self._anchor_icon_input: Optional[Union[str, QWidget]] = anchor_icon
        self._disable_animation = bool(disable_animation)

        # 交互状态
        self._is_hovered = False
        self._is_pressed = False
        self._is_focused = False

        # 动画 runners
        self._opacity_anim_runner = None  # type: ignore[assignment]
        self._block_bg_anim_runner = None  # type: ignore[assignment]

        # block 模式 hover 背景透明度（0.0~1.0），随动画刷新
        self._block_bg_progress: float = 0.0

        self.setObjectName("heroLink")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        # block 模式自绘背景，需要透明壳
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # 焦点 / 光标
        self._apply_focus_and_cursor()

        # opacity 效果（仅 is_block=False 时驱动 hover/press）
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(self._target_opacity())
        self.setGraphicsEffect(self._opacity_effect)

        # layout
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(0)  # icon mx-1 已经在 _add_icon 单独处理
        self._layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 子控件
        self._text: Optional[Text] = None
        self._icon: Optional[QWidget] = None
        self._build_children()
        self._apply_padding()

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
    def _validate_size(size: str) -> str:
        if size not in VALID_LINK_SIZES:
            raise ValueError(f"Link: size 必须是 {VALID_LINK_SIZES}，传入 {size!r}")
        return size

    @staticmethod
    def _validate_color(color: str) -> str:
        if color not in VALID_LINK_COLORS:
            raise ValueError(f"Link: color 必须是 {VALID_LINK_COLORS}，传入 {color!r}")
        return color

    @staticmethod
    def _validate_underline(underline: str) -> str:
        if underline not in VALID_LINK_UNDERLINES:
            raise ValueError(
                f"Link: underline 必须是 {VALID_LINK_UNDERLINES}，传入 {underline!r}"
            )
        return underline

    def _spec(self) -> dict:
        return LINK_SIZES[self._size]

    # ============================================================
    # 颜色解析
    # ============================================================
    def _text_color(self) -> QColor:
        """根据 color/theme 推出文字颜色（未叠加 opacity）。"""
        if self._color == "foreground":
            # foreground = 主题正文色
            return QColor("#18181b" if self._theme == "light" else "#ECEDEE")
        # 其余 5 个语义色：HeroUI 在亮色用 500、暗色亦用 500（不变）
        return QColor(HEROUI_COLORS[self._color][500])

    def _block_bg_color(self) -> QColor:
        """is_block=True 时 hover 显示的色块底色（含 alpha）。"""
        alpha = (
            LINK_BLOCK["bg_alpha_foreground"]
            if self._color == "foreground"
            else LINK_BLOCK["bg_alpha_color"]
        )
        if self._color == "foreground":
            base = self._text_color()
        else:
            base = QColor(HEROUI_COLORS[self._color][500])
        c = QColor(base)
        c.setAlphaF(alpha * self._block_bg_progress)
        return c

    # ============================================================
    # 子控件构建
    # ============================================================
    def _build_children(self) -> None:
        spec = self._spec()
        c = self._text_color()

        # 文本：走 Text 组件（铁律 9）
        self._text = Text(
            self._children_text,
            size=spec["font_size"],
            weight="normal",
            color=c,
            selectable=False,  # link 不参与文本选区
            theme=self._theme,
            parent=self,
        )
        self._apply_text_underline()
        self._layout.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        # 锚点图标（show_anchor_icon=True 才显示）
        if self._show_anchor_icon:
            self._mount_anchor_icon()

    def _mount_anchor_icon(self) -> None:
        spec = self._spec()
        c = self._text_color()
        # mx-1 = 4px（HeroUI linkAnchorClasses）
        if isinstance(self._anchor_icon_input, QWidget):
            self._icon = self._anchor_icon_input
            self._icon.setParent(self)
        else:
            name = self._anchor_icon_input or DEFAULT_ANCHOR_ICON
            self._icon = _LinkIconLabel(str(name), spec["icon_size"], c, parent=self)
        # 间距：text 与 icon 之间留 4px（mx-1）
        self._layout.addSpacing(4)
        self._layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)

    def _unmount_anchor_icon(self) -> None:
        # 移除 icon 与它前面的间隔 spacer。layout 末尾两项即 spacer + icon。
        if self._icon is None:
            return
        # 取出 icon
        self._layout.removeWidget(self._icon)
        from ...utils import safe_delete
        safe_delete(self._icon)
        self._icon = None
        # 取出 spacer（layout 最后一项）
        last = self._layout.takeAt(self._layout.count() - 1)
        if last is not None:
            del last

    # ============================================================
    # 样式 / 几何
    # ============================================================
    def _apply_padding(self) -> None:
        """is_block=True 时启用 px-2 py-1；否则零内边距（行内文字）。"""
        spec = self._spec()
        if self._is_block:
            self._layout.setContentsMargins(
                spec["block_pad_x"],
                spec["block_pad_y"],
                spec["block_pad_x"],
                spec["block_pad_y"],
            )
        else:
            self._layout.setContentsMargins(0, 0, 0, 0)

    def _apply_text_underline(self) -> None:
        """根据 underline 维度 + 当前状态决定文字是否带下划线。"""
        if self._text is None:
            return
        show = self._should_underline()
        f = self._text.font()
        if f.underline() != show:
            f.setUnderline(show)
            self._text.setFont(f)

    def _should_underline(self) -> bool:
        u = self._underline
        if u == "always":
            return True
        if u == "none":
            return False
        if u == "hover":
            return self._is_hovered
        if u == "active":
            return self._is_pressed
        if u == "focus":
            return self._is_focused
        return False

    def _apply_focus_and_cursor(self) -> None:
        if self._is_disabled:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            # tab 可达，参与键盘焦点
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ============================================================
    # opacity / 背景动画
    # ============================================================
    def _hover_opacity(self) -> float:
        return (
            LINK_OPACITY["hover_dark"]
            if self._theme == "dark"
            else LINK_OPACITY["hover_light"]
        )

    def _target_opacity(self) -> float:
        """is_block=False 时根据状态返回目标透明度；is_block=True 永远 1.0。"""
        if self._is_disabled:
            return LINK_OPACITY["disabled"]
        if self._is_block:
            return 1.0
        if self._is_pressed:
            return LINK_OPACITY["disabled"]  # active = opacity-disabled = 0.5
        if self._is_hovered:
            return self._hover_opacity()
        return 1.0

    def _animate_opacity(self) -> None:
        target = self._target_opacity()
        if self._disable_animation:
            stop_tween(self, "_opacity_anim_runner")
            self._opacity_effect.setOpacity(target)
            return
        cur = self._opacity_effect.opacity()
        tween_value(
            self,
            "_opacity_anim_runner",
            float(cur),
            float(target),
            self._opacity_effect.setOpacity,
            duration=LINK_OPACITY_DURATION,
        )

    def _animate_block_bg(self) -> None:
        """is_block=True 时根据 hover 状态切换背景 alpha 进度。"""
        target = 1.0 if (self._is_hovered and not self._is_disabled) else 0.0
        if self._disable_animation:
            stop_tween(self, "_block_bg_anim_runner")
            self._block_bg_progress = target
            self.update()
            return

        def _on_step(v):
            self._block_bg_progress = float(v)
            self.update()

        tween_value(
            self,
            "_block_bg_anim_runner",
            float(self._block_bg_progress),
            float(target),
            _on_step,
            duration=LINK_BLOCK["anim_duration"],
        )

    # ============================================================
    # 文字色 / icon 色推送
    # ============================================================
    def _push_color_to_children(self) -> None:
        c = self._text_color()
        if self._text is not None:
            self._text.set_color(c)
        if isinstance(self._icon, _LinkIconLabel):
            self._icon.set_color(c)

    # ============================================================
    # paintEvent —— is_block hover 色块
    # ============================================================
    def paintEvent(self, event):  # type: ignore[override]
        super().paintEvent(event)
        if not self._is_block:
            return
        if self._block_bg_progress <= 0.0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        radius = float(LINK_BLOCK["radius"])
        path.addRoundedRect(self.rect(), radius, radius)
        painter.fillPath(path, self._block_bg_color())
        painter.end()

    # ============================================================
    # 鼠标 / 键盘事件
    # ============================================================
    def enterEvent(self, event: QEnterEvent) -> None:  # type: ignore[override]
        if not self._is_disabled:
            self._is_hovered = True
            self._apply_text_underline()
            self._animate_opacity()
            if self._is_block:
                self._animate_block_bg()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        self._is_hovered = False
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        if self._is_block:
            self._animate_block_bg()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._is_disabled or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._is_pressed = True
        self._apply_text_underline()
        self._animate_opacity()
        self.pressed.emit()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._is_disabled or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        was_pressed = self._is_pressed
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        self.released.emit()
        # 仅当释放点仍在 widget 内时触发 click（标准按钮语义）
        if was_pressed and self.rect().contains(event.position().toPoint()):
            self._activate()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if self._is_disabled:
            super().keyPressEvent(event)
            return
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self._is_pressed = True
            self._apply_text_underline()
            self._animate_opacity()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if self._is_disabled:
            super().keyReleaseEvent(event)
            return
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self._is_pressed = False
            self._apply_text_underline()
            self._animate_opacity()
            self._activate()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # type: ignore[override]
        self._is_focused = True
        self._apply_text_underline()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # type: ignore[override]
        self._is_focused = False
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        super().focusOutEvent(event)

    def _activate(self) -> None:
        """触发点击行为：发 clicked + 按需打开外链。"""
        self.clicked.emit()
        if self._is_external and self._href:
            try:
                webbrowser.open(self._href)
            except Exception:
                # 跨平台 webbrowser 失败不应崩组件
                pass

    # ============================================================
    # 公共 API
    # ============================================================
    def set_children(self, text: str) -> None:
        self._children_text = str(text or "")
        if self._text is not None:
            self._text.setText(self._children_text)

    def children_text(self) -> str:
        return self._children_text

    def set_href(self, href: str) -> None:
        self._href = str(href or "")

    def href(self) -> str:
        return self._href

    def set_size(self, size: str) -> None:
        size = self._validate_size(size)
        if size == self._size:
            return
        self._size = size
        spec = self._spec()
        if self._text is not None:
            self._text.set_size(spec["font_size"])
            self._apply_text_underline()
        if isinstance(self._icon, _LinkIconLabel):
            self._icon.set_size_px(spec["icon_size"], self._text_color())
        self._apply_padding()

    def set_color(self, color: str) -> None:
        color = self._validate_color(color)
        if color == self._color:
            return
        self._color = color
        self._push_color_to_children()
        if self._is_block:
            self.update()

    def set_underline(self, underline: str) -> None:
        underline = self._validate_underline(underline)
        if underline == self._underline:
            return
        self._underline = underline
        self._apply_text_underline()

    def set_is_block(self, is_block: bool) -> None:
        is_block = bool(is_block)
        if is_block == self._is_block:
            return
        self._is_block = is_block
        self._apply_padding()
        # 切换时立刻把 opacity 重置（block 模式恒为 1.0）
        self._animate_opacity()
        if not self._is_block:
            self._block_bg_progress = 0.0
        self.update()

    def set_is_external(self, is_external: bool) -> None:
        self._is_external = bool(is_external)

    def set_is_disabled(self, is_disabled: bool) -> None:
        is_disabled = bool(is_disabled)
        if is_disabled == self._is_disabled:
            return
        self._is_disabled = is_disabled
        self._apply_focus_and_cursor()
        self._is_hovered = False
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        if self._is_block:
            self._animate_block_bg()

    def set_show_anchor_icon(self, show: bool) -> None:
        show = bool(show)
        if show == self._show_anchor_icon:
            return
        self._show_anchor_icon = show
        if show:
            self._mount_anchor_icon()
        else:
            self._unmount_anchor_icon()

    def set_anchor_icon(self, anchor_icon: Optional[Union[str, QWidget]]) -> None:
        """切换锚点图标内容。show_anchor_icon=False 时仅记录，不挂载。"""
        self._anchor_icon_input = anchor_icon
        if not self._show_anchor_icon:
            return
        # 已挂载 → 拆掉重挂（覆盖 QWidget / str 双形态）
        self._unmount_anchor_icon()
        self._mount_anchor_icon()

    def set_disable_animation(self, disable: bool) -> None:
        self._disable_animation = bool(disable)

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
        if self._text is not None:
            self._text.set_theme(self._theme)
        self._push_color_to_children()
        # 主题变化时 hover 透明度档位也变（亮 0.8 / 暗 0.9）
        self._animate_opacity()
        if self._is_block:
            self.update()

    def _apply_provider_theme(self, theme: str) -> None:
        """ThemeProvider 广播专用入口。"""
        self._theme = theme
        if self._text is not None:
            self._text.set_theme(theme)
        self._push_color_to_children()
        self._animate_opacity()
        if self._is_block:
            self.update()

    # ============================================================
    # 元信息
    # ============================================================
    @staticmethod
    def valid_sizes() -> tuple:
        return VALID_LINK_SIZES

    @staticmethod
    def valid_colors() -> tuple:
        return VALID_LINK_COLORS

    @staticmethod
    def valid_underlines() -> tuple:
        return VALID_LINK_UNDERLINES

    # ============================================================
    # sizeHint —— 让 Layout 给到合适宽度
    # ============================================================
    def sizeHint(self) -> QSize:  # type: ignore[override]
        # 由 layout 决定，QFrame 默认实现已正确，仅显式声明便于阅读
        return super().sizeHint()


__all__ = ["Link"]
