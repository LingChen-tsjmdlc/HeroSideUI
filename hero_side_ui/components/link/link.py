"""Link 链接组件：6 色 3 号 5 档下划线；isBlock hover 色块。

is_external 经 webbrowser 打开；show_anchor_icon 默认 share 图标。
"""

from __future__ import annotations

import webbrowser

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

from ...animation.tween import tween_value
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
        parent: QWidget | None = None,
    ):
        """创建锚点图标槽。

        Args:
            icon_name: SVG icon 名。
            size: 图标边长（像素）。
            color: 图标颜色。
            parent: Qt 父对象。
        """
        super().__init__(parent)
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

    def set_icon_name(self, icon_name: str, color: QColor) -> None:
        """切换图标名并重渲染。

        Args:
            icon_name: 新 SVG icon 名。
            color: 图标颜色。
        """
        self._icon_name = icon_name
        self.set_color(color)

    def set_size_px(self, size: int, color: QColor) -> None:
        """调整图标边长并重渲染。

        Args:
            size: 新边长（像素）。
            color: 图标颜色。
        """
        self._size = int(size)
        self.set_color(color)


# ============================================================
# Link 主组件
# ============================================================


class Link(QFrame):
    """HeroUI v2 风格链接组件，完整 API 见 docs/link.md。

    Signals:
        clicked: 释放在 widget 内或键盘触发。
        pressed: 鼠标按下。
        released: 鼠标释放。
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
        anchor_icon: str | QWidget | None = None,
        disable_animation: bool = False,
        is_text_selectable: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建链接组件。

        Args:
            children: 链接文本。
            href: 链接地址。
            size: 尺寸档位。
            color: 语义色（primary / foreground 等）。
            underline: 下划线策略（none / hover / active / focus / always）。
            is_block: 是否为块级（hover 色块）。
            is_external: 点击是否用浏览器打开 href。
            is_disabled: 是否禁用。
            show_anchor_icon: 是否显示锚点图标。
            anchor_icon: 锚点图标名或自定义 QWidget。
            disable_animation: 是否关闭动画。
            is_text_selectable: 文本是否可选中。
            theme: auto / light / dark。
            parent: Qt 父对象。
        """
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
        self._anchor_icon_input: str | QWidget | None = anchor_icon
        self._disable_animation = bool(disable_animation)
        self._is_text_selectable = bool(is_text_selectable)

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
        self._text: Text | None = None
        self._icon: QWidget | None = None
        self._build_children()
        self._apply_padding()

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
    def _validate_size(size: str) -> str:
        """校验尺寸档位，非法值抛 ValueError。

        Args:
            size: 待校验尺寸。

        Returns:
            str: 合法尺寸。
        """
        if size not in VALID_LINK_SIZES:
            raise ValueError(f"Link: size 必须是 {VALID_LINK_SIZES}，传入 {size!r}")
        return size

    @staticmethod
    def _validate_color(color: str) -> str:
        """校验语义色，非法值抛 ValueError。

        Args:
            color: 待校验颜色。

        Returns:
            str: 合法颜色。
        """
        if color not in VALID_LINK_COLORS:
            raise ValueError(f"Link: color 必须是 {VALID_LINK_COLORS}，传入 {color!r}")
        return color

    @staticmethod
    def _validate_underline(underline: str) -> str:
        """校验下划线策略，非法值抛 ValueError。

        Args:
            underline: 待校验下划线策略。

        Returns:
            str: 合法下划线策略。
        """
        if underline not in VALID_LINK_UNDERLINES:
            raise ValueError(f"Link: underline 必须是 {VALID_LINK_UNDERLINES}，传入 {underline!r}")
        return underline

    def _spec(self) -> dict:
        """当前 size 的像素规格表。

        Returns:
            dict: 含 font_size / icon_size / block_pad 等规格。
        """
        return LINK_SIZES[self._size]

    # ============================================================
    # 颜色解析
    # ============================================================
    def _text_color(self) -> QColor:
        """根据 color/theme 推出文字颜色（未叠加 opacity）。

        Returns:
            QColor: 文字颜色。
        """
        if self._color == "foreground":
            # foreground = 主题正文色
            return QColor("#18181b" if self._theme == "light" else "#ECEDEE")
        # 其余 5 个语义色：HeroUI 在亮色用 500、暗色亦用 500（不变）
        return QColor(HEROUI_COLORS[self._color][500])

    def _block_bg_color(self) -> QColor:
        """is_block=True 时 hover 显示的色块底色（含 alpha）。

        Returns:
            QColor: 随 _block_bg_progress 渐变的色块底色。
        """
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
        """构建文本子控件与（按需）锚点图标。"""
        spec = self._spec()
        c = self._text_color()

        # 文本：走 Text 组件（铁律 9）
        self._text = Text(
            self._children_text,
            size=spec["font_size"],
            weight="normal",
            color=c,
            selectable=self._is_text_selectable,
            theme=self._theme,
            parent=self,
        )
        self._apply_text_underline()
        self._layout.addWidget(self._text, 0, Qt.AlignmentFlag.AlignVCenter)

        # 锚点图标（show_anchor_icon=True 才显示）
        if self._show_anchor_icon:
            self._mount_anchor_icon()

    def _mount_anchor_icon(self) -> None:
        """挂载锚点图标（自定义 QWidget 或默认 SVG），并加 4px 间距。"""
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
        """移除锚点图标与前面的间隔 spacer（layout 末尾两项）。"""
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
        """is_block=True 时启用 px-2 py-1；否则零内边距（行内文字）。

        Note:
            block 模式用内边距撑出可点击色块，行内模式零内边距。
        """
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
        """根据 underline 维度 + 当前状态决定文字是否带下划线。

        Note:
            仅在 _should_underline() 结果变化时才重设字体，避免无谓刷新。
        """
        if self._text is None:
            return
        show = self._should_underline()
        f = self._text.font()
        if f.underline() != show:
            f.setUnderline(show)
            self._text.setFont(f)

    def _should_underline(self) -> bool:
        """按 underline 维度与当前交互状态决定下划线开关。

        Returns:
            bool: 是否应显示下划线。
        """
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
        """按禁用态设置光标与焦点策略（禁用=箭头+不可聚焦，否则手型+强焦点）。"""
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
        """hover 目标透明度（暗色 0.9 / 亮色 0.8）。

        Returns:
            float: hover 透明度。
        """
        return LINK_OPACITY["hover_dark"] if self._theme == "dark" else LINK_OPACITY["hover_light"]

    def _target_opacity(self) -> float:
        """is_block=False 时根据状态返回目标透明度；is_block=True 永远 1.0。

        Returns:
            float: 目标透明度。
        """
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
        """把 opacity 补间到 _target_opacity（关动画时瞬切）。"""
        tween_value(
            self,
            "_opacity_anim_runner",
            float(self._opacity_effect.opacity()),
            float(self._target_opacity()),
            self._opacity_effect.setOpacity,
            duration=LINK_OPACITY_DURATION,
            animated=not self._disable_animation,
        )

    def _animate_block_bg(self) -> None:
        """补间 block 色块背景进度（hover 且非禁用→1.0，否则 0.0）。"""
        target = 1.0 if self._is_hovered and not self._is_disabled else 0.0

        def step(value):
            self._block_bg_progress = float(value)
            self.update()

        tween_value(
            self,
            "_block_bg_anim_runner",
            float(self._block_bg_progress),
            target,
            step,
            duration=LINK_BLOCK["anim_duration"],
            animated=not self._disable_animation,
        )

    # ============================================================
    # 文字色 / icon 色推送
    # ============================================================
    def _push_color_to_children(self) -> None:
        """把当前文字色推送到 Text 与图标子控件。"""
        c = self._text_color()
        if self._text is not None:
            self._text.set_color(c)
        if isinstance(self._icon, _LinkIconLabel):
            self._icon.set_color(c)

    # ============================================================
    # paintEvent —— is_block hover 色块
    # ============================================================
    def paintEvent(self, event):  # type: ignore[override]
        """绘制 block 模式 hover 色块（行内模式不绘制）。

        Args:
            event: Qt 绘制事件。
        """
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
        """进入：标记 hover 并触发下划线 / 透明度 / block 背景动画。

        Args:
            event: Qt 进入事件。
        """
        if not self._is_disabled:
            self._is_hovered = True
            self._apply_text_underline()
            self._animate_opacity()
            if self._is_block:
                self._animate_block_bg()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """离开：清除 hover/press 并重算下划线与透明度。

        Args:
            event: Qt 离开事件。
        """
        self._is_hovered = False
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        if self._is_block:
            self._animate_block_bg()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """左键按下：标记 press 并发 pressed 信号。

        Args:
            event: Qt 鼠标事件。
        """
        if self._is_disabled or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._is_pressed = True
        self._apply_text_underline()
        self._animate_opacity()
        self.pressed.emit()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """左键释放：发 released；落在 widget 内则触发 click + 外链。

        Args:
            event: Qt 鼠标事件。
        """
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
        """键盘按下：Enter/Space 标记 press 并触发视觉反馈。

        Args:
            event: Qt 按键事件。
        """
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
        """键盘释放：Enter/Space 触发激活（click + 外链）。

        Args:
            event: Qt 按键事件。
        """
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
        """获得焦点：标记 focused 刷新下划线。

        Args:
            event: Qt 焦点事件。
        """
        self._is_focused = True
        self._apply_text_underline()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # type: ignore[override]
        """失去焦点：清除 focused/press 刷新下划线与透明度。

        Args:
            event: Qt 焦点事件。
        """
        self._is_focused = False
        self._is_pressed = False
        self._apply_text_underline()
        self._animate_opacity()
        super().focusOutEvent(event)

    def _activate(self) -> None:
        """触发点击行为：发 clicked + 按需打开外链。

        Note:
            is_external 且 href 非空时调用 webbrowser.open，异常被吞掉以防崩组件。
        """
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
        """更新链接文本。

        Args:
            text: 新文本。
        """
        self._children_text = str(text or "")
        if self._text is not None:
            self._text.setText(self._children_text)

    def children_text(self) -> str:
        """返回当前链接文本。

        Returns:
            str: 当前文本。
        """
        return self._children_text

    def set_href(self, href: str) -> None:
        """设置链接地址。

        Args:
            href: 新地址。
        """
        self._href = str(href or "")

    def href(self) -> str:
        """返回当前链接地址。

        Returns:
            str: 当前 href。
        """
        return self._href

    def set_size(self, size: str) -> None:
        """设置尺寸档位（同步文本与图标尺寸、padding）。

        Args:
            size: 尺寸名（非法值抛 ValueError）。
        """
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
        """设置语义色（推送子控件配色）。

        Args:
            color: 语义色名（非法值抛 ValueError）。
        """
        color = self._validate_color(color)
        if color == self._color:
            return
        self._color = color
        self._push_color_to_children()
        if self._is_block:
            self.update()

    def set_underline(self, underline: str) -> None:
        """设置下划线策略。

        Args:
            underline: none / hover / active / focus / always（非法值抛 ValueError）。
        """
        underline = self._validate_underline(underline)
        if underline == self._underline:
            return
        self._underline = underline
        self._apply_text_underline()

    def set_is_block(self, is_block: bool) -> None:
        """切换块级模式（影响 padding 与 opacity 策略）。

        Args:
            is_block: 是否块级。
        """
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
        """设置是否外链（点击用浏览器打开 href）。

        Args:
            is_external: 是否外链。
        """
        self._is_external = bool(is_external)

    def set_is_disabled(self, is_disabled: bool) -> None:
        """设置禁用态（同步光标/焦点/透明度/视觉）。

        Args:
            is_disabled: 是否禁用。
        """
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
        """切换锚点图标显隐（按需挂载/卸载）。

        Args:
            show: 是否显示锚点图标。
        """
        show = bool(show)
        if show == self._show_anchor_icon:
            return
        self._show_anchor_icon = show
        if show:
            self._mount_anchor_icon()
        else:
            self._unmount_anchor_icon()

    def set_anchor_icon(self, anchor_icon: str | QWidget | None) -> None:
        """切换锚点图标内容。show_anchor_icon=False 时仅记录，不挂载。

        Args:
            anchor_icon: 新图标名或自定义 QWidget。
        """
        self._anchor_icon_input = anchor_icon
        if not self._show_anchor_icon:
            return
        # 已挂载 → 拆掉重挂（覆盖 QWidget / str 双形态）
        self._unmount_anchor_icon()
        self._mount_anchor_icon()

    def set_disable_animation(self, disable: bool) -> None:
        """设置是否关闭所有动画。

        Args:
            disable: True 关闭动画。
        """
        self._disable_animation = bool(disable)

    def set_theme(self, theme: str) -> None:
        """设置主题（auto 注册 ThemeProvider 跟随全局）。

        Args:
            theme: auto / light / dark。

        Note:
            会同步子 Text 主题与配色，并刷新透明度档位。
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
        if self._text is not None:
            self._text.set_theme(self._theme)
        self._push_color_to_children()
        # 主题变化时 hover 透明度档位也变（亮 0.8 / 暗 0.9）
        self._animate_opacity()
        if self._is_block:
            self.update()

    def _apply_provider_theme(self, theme: str) -> None:
        """ThemeProvider 广播回调：更新主题并推送子控件配色。

        Args:
            theme: 广播下发的实际主题（light/dark）。
        """
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
        """返回所有合法尺寸档位。

        Returns:
            tuple: 合法 size 集合。
        """
        return VALID_LINK_SIZES

    @staticmethod
    def valid_colors() -> tuple:
        """返回所有合法语义色。

        Returns:
            tuple: 合法 color 集合。
        """
        return VALID_LINK_COLORS

    @staticmethod
    def valid_underlines() -> tuple:
        """返回所有合法下划线策略。

        Returns:
            tuple: 合法 underline 集合。
        """
        return VALID_LINK_UNDERLINES

    # ============================================================
    # sizeHint —— 让 Layout 给到合适宽度
    # ============================================================
    def sizeHint(self) -> QSize:  # type: ignore[override]
        """返回建议尺寸（由 layout 决定）。

        Returns:
            QSize: 父类根据 layout 计算出的建议尺寸。
        """
        # 由 layout 决定，QFrame 默认实现已正确，仅显式声明便于阅读
        return super().sizeHint()


__all__ = ["Link"]
