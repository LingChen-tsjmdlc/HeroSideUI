"""HeroSideUI Alert — notification banner (HeroUI v2)."""

from __future__ import annotations

from typing import Callable, Optional

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
    """HeroUI 风格 Alert。用法::

        Alert(title="注意", description="内容", color="warning")
        Alert(title="成功", color="success", is_closable=True, on_close=fn)
    """

    closed = Signal()

    def __init__(
        self,
        title: str = "",
        description: str = "",
        color: str = "default",
        variant: str = "flat",
        radius: str = "md",
        icon: Optional[str] = None,
        start_content: Optional[QWidget] = None,
        end_content: Optional[QWidget] = None,
        is_visible: bool = True,
        is_closable: bool = False,
        hide_icon: bool = False,
        hide_icon_wrapper: bool = False,
        on_close: Optional[Callable[[], None]] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
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
            icon_only=True, icon="heroicons--x-mark-16-solid",
            icon_size=18, variant="light", radius="full", size="sm",
            theme=self._theme,
        )
        self._close_btn.clicked.connect(self._handle_close)
        self._close_btn.setVisible(bool(self._is_closable or self._on_close))
        self._layout.addWidget(self._close_btn)

        # icon visibility
        self._apply_icon_visibility()

    # ---- styles ----

    def _apply_styles(self):
        s = build_alert_styles(
            variant=self._variant, color=self._color, theme=self._theme,
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
        iwr_bg = "transparent" if self._hide_icon_wrapper else s['icon_wrapper_bg']
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

    def _resolve_icon_name(self) -> Optional[str]:
        if self._icon_src:
            return self._icon_src
        return _ICON_MAP.get(self._color, _ICON_MAP["primary"])

    def _refresh_icon(self):
        name = self._resolve_icon_name()
        if name is None:
            self._icon_label.setText("")
            return
        clr = getattr(self, "_icon_color", "#71717a")
        pix = load_svg_icon(name, size=_ICO_SIZE, color=clr)
        self._icon_label.clear()
        size = _ICO_SIZE
        self._icon_label.setPixmap(
            pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    # ---- close ----

    def _handle_close(self):
        if self._on_close:
            self._on_close()
        self.closed.emit()
        self.hide()

    def close(self):
        self._handle_close()

    # ---- setters ----

    def set_color(self, color: str):
        self._color = color; self._apply_styles()

    def set_variant(self, variant: str):
        self._variant = variant; self._apply_styles()

    def set_radius(self, radius: str):
        self._radius = radius; self._apply_styles()

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
        self._title_label.set_theme(self._theme)
        self._desc_label.set_theme(self._theme)
        self._close_btn.set_theme(self._theme)
        if not self._custom_styled:
            self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        self._theme = theme
        self._title_label.set_theme(theme)
        self._desc_label.set_theme(theme)
        self._close_btn.set_theme(theme)
        if not self._custom_styled:
            self._apply_styles()

    def set_stylesheet(self, qss: str):
        """覆盖 Alert 的 QSS 样式。设置后主题切换不再重写 QSS。"""
        self._custom_styled = True
        super().setStyleSheet(qss)

    def set_title(self, title: str):
        self._title_label.setText(title)

    def set_description(self, description: str):
        self._desc_label.setText(description)

    def set_icon(self, icon: Optional[str]):
        self._icon_src = icon; self._refresh_icon()

    def set_hide_icon(self, hide: bool):
        self._hide_icon = hide
        self._apply_icon_visibility()

    def set_hide_icon_wrapper(self, hide: bool):
        self._hide_icon_wrapper = hide
        self._apply_icon_visibility()

    def _apply_icon_visibility(self):
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
        self.setVisible(visible)

    def is_visible(self) -> bool:
        return self.isVisible()

    def set_closable(self, closable: bool):
        self._is_closable = closable
        self._close_btn.setVisible(closable or self._on_close is not None)

    def set_start_content(self, widget: QWidget):
        self._layout.insertWidget(0, widget)

    def set_end_content(self, widget: QWidget):
        self._layout.insertWidget(self._layout.count() - 1, widget)
