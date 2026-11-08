"""HeroSideUI Alert — notification banner (HeroUI v2)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import RADIUS
from ...utils import load_svg_icon
from ..button import Button
from ..text import Text
from ._styling import build_alert_styles

_ICON_MAP = {
    "primary": "heroicons--information-circle-solid",
    "secondary": "heroicons--information-circle-solid",
    "success": "heroicons--check-solid",
    "warning": "heroicons--exclamation-triangle-solid",
    "danger": "heroicons--x-circle-solid",
}

# icon wrapper 直径 & 图标尺寸（统一常量）
_ICO_WRAPPER = 28
_ICO_SIZE = 18
_GAP = 6  # icon ↔ text 间距


class Alert(QWidget):
    """HeroUI 风格 Alert 通知组件。"""

    closed = Signal()

    def __init__(
        self,
        title: str = "",
        description: str = "",
        color: str = "default",
        variant: str = "flat",
        radius: str = "md",
        icon: str | None = None,
        start_content: QWidget | None = None,
        end_content: QWidget | None = None,
        is_visible: bool = True,
        is_closable: bool = False,
        hide_icon: bool = False,
        hide_icon_wrapper: bool = False,
        on_close: Callable[[], None] | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建 Alert 并装配图标、文本区与关闭按钮。

        装配顺序固定：先 _build_ui 建全部子控件，再插自定义内容，最后
        _apply_styles 统一上色，因为样式刷新会访问所有子控件。

        Args:
            title: 标题文本。
            description: 描述文本。
            color: 语义色，决定配色与默认图标。
            variant: 视觉变体，交给配色 token 构建器解释。
            radius: 圆角档位；full 按当前高度折算。
            icon: 自定义图标名，覆盖 color 对应的默认图标。
            start_content: 插到布局最前的自定义 widget。
            end_content: 插到关闭按钮之前的自定义 widget。
            is_visible: False 时构造后即隐藏。
            is_closable: 是否显示关闭按钮。
            hide_icon: 是否连图标与圆形容器一起隐藏。
            hide_icon_wrapper: 是否只去掉图标的圆形底色。
            on_close: 关闭时先于 closed 信号调用的回调。
            theme: 主题名；auto 时跟随 ThemeProvider。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self.setObjectName("HeroAlert")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._color = color
        self._variant = variant
        self._radius = radius
        self._icon_src = icon
        self._hide_icon = hide_icon
        self._hide_icon_wrapper = hide_icon_wrapper
        self._is_closable = is_closable
        self._on_close = on_close
        self._theme_mode = theme
        self._theme = ThemeProvider.instance().current_theme if theme == "auto" else theme
        self._custom_styled = False  # 用户手动覆盖样式后为 True，主题切换时跳过 QSS 重写

        self._build_ui(title, description)
        # 只在 is_visible=False 时显式隐藏；True 时靠父窗口 show() 自然可见，
        # 避免构造阶段 setVisible(True) 让无父组件的 Alert 闪成独立顶层窗口。
        if not is_visible:
            self.hide()

        if start_content:
            self._layout.insertWidget(0, start_content)
        if end_content:
            self._layout.insertWidget(self._layout.count() - 1, end_content)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._apply_styles()

    # ---- build ----

    def _build_ui(self, title: str, description: str):
        """搭建图标容器、文本区与关闭按钮三段布局。

        图标额外包一层 QWidget，让圆形底色由 #HeroAlertIconWrapper 独立控制，
        hide_icon_wrapper 时才能只去掉底色、保留图标本体。文本区用零边距零间距
        的纵向布局，标题与描述之间不留额外间距。

        Args:
            title: 标题文本，允许自动换行。
            description: 描述文本，允许自动换行。

        Note:
            _apply_icon_visibility 的非隐藏分支会调用 _apply_styles，后者依赖
            icon_wrapper、两个 label 与 close_btn 全部就绪，因此必须放在最后。
        """
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 16, 10)
        self._layout.setSpacing(_GAP)

        # icon wrapper
        self._icon_wrapper = QWidget(self)
        self._icon_wrapper.setObjectName("HeroAlertIconWrapper")
        self._icon_wrapper.setFixedSize(_ICO_WRAPPER, _ICO_WRAPPER)
        self._icon_wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._icon_label = Text(size="md")
        self._icon_label.setParent(self._icon_wrapper)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(_ICO_WRAPPER, _ICO_WRAPPER)

        self._layout.addWidget(self._icon_wrapper)

        # main wrapper — title + description
        self._main = QWidget(self)
        m_layout = QVBoxLayout(self._main)
        m_layout.setContentsMargins(0, 0, 0, 0)
        m_layout.setSpacing(0)

        self._title_label = Text(title, size="sm", weight="medium", theme=self._theme)
        self._title_label.setWordWrap(True)
        m_layout.addWidget(self._title_label)

        self._desc_label = Text(description, size="sm", weight="normal", theme=self._theme)
        self._desc_label.setWordWrap(True)
        m_layout.addWidget(self._desc_label)

        self._layout.addWidget(self._main, 1)

        # close button
        self._close_btn = Button(
            icon_only=True,
            icon="heroicons--x-mark-16-solid",
            icon_size=18,
            variant="light",
            radius="full",
            size="sm",
            theme=self._theme,
        )
        self._close_btn.clicked.connect(self._handle_close)
        self._close_btn.setVisible(bool(self._is_closable or self._on_close))
        self._layout.addWidget(self._close_btn)

        # icon visibility
        self._apply_icon_visibility()

    # ---- styles ----

    def _apply_styles(self):
        """按当前 color / variant / theme 重算并应用全部 QSS 与配色。

        圆角 full 档无法用固定 token 表达，改用当前高度的一半；构造阶段
        高度尚未确定时用 999px 兜底，否则 0 高度会算出 0px 圆角。

        Note:
            本方法不检查 _custom_styled，是否跳过由 set_theme 等调用方决定；
            hide_icon_wrapper 时图标容器底色强制为 transparent。
        """
        s = build_alert_styles(
            variant=self._variant,
            color=self._color,
            theme=self._theme,
            radius=self._radius,
        )
        r = self._radius
        if r == "full":
            r_px = f"{self.height() // 2}px" if self.height() > 0 else "999px"
        else:
            r_px = RADIUS.get(r, RADIUS["md"])

        self.setStyleSheet(
            f"QWidget#HeroAlert {{ "
            f"background-color: {s['base_bg']}; "
            f"border: {s['base_border']}; "
            f"border-radius: {r_px}; "
            f"}}"
        )
        # hide_icon_wrapper 时去掉圆形底色
        iwr_bg = "transparent" if self._hide_icon_wrapper else s["icon_wrapper_bg"]
        self._icon_wrapper.setStyleSheet(
            f"QWidget#HeroAlertIconWrapper {{ "
            f"background-color: {iwr_bg}; "
            f"border: none; "
            f"border-radius: {_ICO_WRAPPER // 2}px; "
            f"}}"
        )
        self._icon_color = s["icon_color"]
        self._title_label.set_color(s["title_color"])
        self._desc_label.set_color(s["desc_color"])
        self._close_btn.set_icon_color(s["close_btn_color"])
        self._refresh_icon()

    # ---- icon ----

    def _resolve_icon_name(self) -> str | None:
        """决定当前应显示的图标名。

        Returns:
            构造时指定的 icon 优先；否则取 _ICON_MAP 中 color 对应项，
            未命中时回退 primary。
        """
        if self._icon_src:
            return self._icon_src
        return _ICON_MAP.get(self._color, _ICON_MAP["primary"])

    def _refresh_icon(self):
        """按当前图标名与配色重绘 icon label 的像素图。

        SVG 资源需按 _ICO_SIZE 缩放后再 setPixmap；先 clear() 是为了避免
        切换图标时旧 pixmap 残留。无图标名时清空文本直接返回。

        Note:
            _icon_color 由 _apply_styles 写入，首次构造时可能尚未存在，
            因此用 getattr 兜底默认灰。
        """
        name = self._resolve_icon_name()
        if name is None:
            self._icon_label.setText("")
            return
        clr = getattr(self, "_icon_color", "#71717a")
        pix = load_svg_icon(name, size=_ICO_SIZE, color=clr)
        self._icon_label.clear()
        size = _ICO_SIZE
        self._icon_label.setPixmap(
            pix.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ---- close ----

    def _handle_close(self):
        """执行关闭：回调、信号、隐藏，顺序固定。

        on_close 回调先于 closed 信号，回调里仍能读到处于可见状态的 Alert；
        随后 emit 通知外部，最后 hide。

        Note:
            这里只隐藏不销毁对象，Alert 可以复用并重新 show()。
        """
        if self._on_close:
            self._on_close()
        self.closed.emit()
        self.hide()

    def close(self):
        """覆写 Qt 的 close()，复用 _handle_close 的回调与信号语义。

        Note:
            Alert 是嵌入式 widget 而非顶层窗口，用 hide() 表达关闭。
        """
        self._handle_close()

    # ---- setters ----

    def set_color(self, color: str):
        """切换语义色并重算配色。

        Args:
            color: 语义色名，同时决定默认图标。
        """
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        """切换视觉变体并重算配色。

        Args:
            variant: 变体名，由配色 token 构建器解释。
        """
        self._variant = variant
        self._apply_styles()

    def set_radius(self, radius: str):
        """切换圆角档位并重算 QSS。

        Args:
            radius: 圆角档位；full 会按当前高度折算。
        """
        self._radius = radius
        self._apply_styles()

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 的注册状态。

        auto 模式下注册到 ThemeProvider，后续变更由 _apply_provider_theme
        接收；从 auto 切回固定主题时必须先 unregister，否则会继续收到广播
        覆盖用户设定。

        Args:
            theme: 主题名，或 auto 表示跟随全局主题。

        Note:
            用户用 set_stylesheet 覆盖过 QSS 后（_custom_styled），这里跳过
            样式重算，只同步两个 label 与关闭按钮的主题。
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
        self._title_label.set_theme(self._theme)
        self._desc_label.set_theme(self._theme)
        self._close_btn.set_theme(self._theme)
        if not self._custom_styled:
            self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            与 set_theme 的区别是不改 _theme_mode、不触碰注册状态；
            _custom_styled 时同样跳过 QSS 重写。
        """
        self._theme = theme
        self._title_label.set_theme(theme)
        self._desc_label.set_theme(theme)
        self._close_btn.set_theme(theme)
        if not self._custom_styled:
            self._apply_styles()

    def set_stylesheet(self, qss: str):
        """覆盖 Alert 的 QSS，并锁定后续主题切换不再重写样式。

        Args:
            qss: 用户提供的完整 QSS 字符串。

        Note:
            置位 _custom_styled 后，set_theme 与 _apply_provider_theme 只同步
            子控件主题，保留用户样式；QSS 的正确性由调用方负责。
        """
        self._custom_styled = True
        super().setStyleSheet(qss)

    def set_title(self, title: str):
        """更新标题文本。

        Args:
            title: 新标题；label 已开启自动换行。
        """
        self._title_label.setText(title)

    def set_description(self, description: str):
        """更新描述文本。

        Args:
            description: 新描述；label 已开启自动换行。
        """
        self._desc_label.setText(description)

    def set_icon(self, icon: str | None):
        """覆盖图标名并立即重绘。

        Args:
            icon: 图标名；None 表示回退到 color 对应的默认图标。
        """
        self._icon_src = icon
        self._refresh_icon()

    def set_hide_icon(self, hide: bool):
        """切换图标及其容器的可见性。

        Args:
            hide: True 时连圆形容器一起隐藏，并移除布局间距。
        """
        self._hide_icon = hide
        self._apply_icon_visibility()

    def set_hide_icon_wrapper(self, hide: bool):
        """切换是否保留图标的圆形底色。

        Args:
            hide: True 时容器与图标仍在，只把底色改为 transparent。
        """
        self._hide_icon_wrapper = hide
        self._apply_icon_visibility()

    def _apply_icon_visibility(self):
        """按 hide_icon / hide_icon_wrapper 同步图标与布局间距。

        三个分支语义互斥：完全隐藏时连容器一起 hide 并把 spacing 归零；
        只去底色时保留容器与图标、重算 QSS；默认态两者都显示并恢复间距。

        Note:
            后两个分支会调用 _apply_styles，因此只能在所有子控件创建完成后
            调用；第一个分支不重算 QSS，间距由本方法直接改。
        """
        if self._hide_icon:
            # 无图标：icon + 圆形容器都不要，间距移除，文字左对齐
            self._icon_wrapper.hide()
            self._layout.setSpacing(0)
        elif self._hide_icon_wrapper:
            # 无图标容器：去掉圆形底色，只留 icon 图标
            self._icon_label.setVisible(True)
            self._icon_wrapper.show()
            self._layout.setSpacing(_GAP)
            self._apply_styles()
        else:
            self._icon_wrapper.show()
            self._icon_label.setVisible(True)
            self._layout.setSpacing(_GAP)
            self._apply_styles()

    def set_visible(self, visible: bool):
        """转发可见性到 QWidget.setVisible。

        Args:
            visible: 是否显示。
        """
        self.setVisible(visible)

    def is_visible(self) -> bool:
        """返回当前是否可见。

        Returns:
            QWidget.isVisible() 的结果。
        """
        return self.isVisible()

    def set_closable(self, closable: bool):
        """切换关闭按钮是否显示。

        Args:
            closable: 是否可关闭。

        Note:
            构造时传过 on_close 回调的话按钮始终保留，这里不会把它隐藏。
        """
        self._is_closable = closable
        self._close_btn.setVisible(closable or self._on_close is not None)

    def set_start_content(self, widget: QWidget):
        """把自定义 widget 插到布局最前。

        Args:
            widget: 要插入的 Qt widget，位置在图标容器之前。
        """
        self._layout.insertWidget(0, widget)

    def set_end_content(self, widget: QWidget):
        """把自定义 widget 插到关闭按钮之前。

        Args:
            widget: 要插入的 Qt widget。

        Note:
            用 count() - 1 定位，前提是关闭按钮始终是布局最后一个元素。
        """
        self._layout.insertWidget(self._layout.count() - 1, widget)
