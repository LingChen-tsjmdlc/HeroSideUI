"""
HeroSideUI Drawer 组件 — 侧滑面板（私有）

结构:
    _DrawerPanel (QWidget, objectName="heroDrawer"，QSS 背景 + 圆角 + 边框)
        ├── content  (QWidget，对外内容容器，已带 QVBoxLayout)
        └── close 按钮（parent=panel，按 modal closeButton 的
                       absolute top-1 end-1 浮在右上角）

圆角按 placement 削平贴边那一侧（HeroUI drawer.ts）：
    top → rounded-t-none / right → rounded-r-none
    bottom → rounded-b-none / left → rounded-l-none
size=full 时四角全平（!rounded-none）。

样式来源:
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/drawer.ts
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/modal.ts
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...themes import DRAWER_SPEC, HEROUI_COLORS, RADIUS
from ...utils import clear_layout, safe_delete
from ...core import ThemeProvider
from ..button import Button


def _radius_px(key: str) -> int:
    """把 radius token（值为 "8px" 这类字符串）转成像素整数。"""
    raw = str(RADIUS.get(key, RADIUS["lg"]))
    try:
        return int(raw.rstrip("px"))
    except ValueError:
        return 14


class _DrawerPanel(QWidget):
    """侧滑面板 — 承载背景、圆角、内容容器与关闭按钮。"""

    close_requested = Signal()

    def __init__(self, theme: str = "auto", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroDrawer")
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._radius = "lg"
        self._placement = "right"
        self._is_full = False
        self._hide_close = False
        self._close_btn: Optional[QWidget] = None

        # QWidget 子类的 QSS 背景必须显式开 WA_StyledBackground 才会绘制
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        pad = DRAWER_SPEC["padding"]
        self._content = QWidget(self)
        self._content.setObjectName("heroDrawerContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(pad, pad, pad, pad)
        self._content_layout.setSpacing(DRAWER_SPEC["content_gap"])
        # 内容从顶部堆叠（HeroUI drawer 是 flex-start，不做垂直居中）
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        outer.addWidget(self._content)

        if theme == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 内容容器
    # ============================================================
    def content_widget(self) -> QWidget:
        """对外开放的内容容器 —— 用户往它的 layout 里塞任意组件。"""
        return self._content

    def _content_mutated(self):
        """内容增删后同步刷新几何缓存 —— 布局的 invalidate()/activate() 只发异步
        LayoutRequest、不碰 hint 缓存，唯有对 content 调 updateGeometry() 才同步
        失效其几何缓存并通知父布局，保证打开中追加内容后面板 sizeHint 立即可用。"""
        self._content.updateGeometry()

    def add_widget(self, widget: QWidget):
        """向内容容器追加一个组件。"""
        if widget is None:
            return
        self._content_layout.addWidget(widget)
        widget.show()
        self._content_mutated()

    def set_content(self, widget: Optional[QWidget]):
        """用单个组件替换全部内容（旧的会被销毁）。"""
        clear_layout(self._content_layout)
        if widget is not None:
            widget.setParent(self._content)
            self._content_layout.addWidget(widget)
            widget.show()
        self._content_mutated()

    def clear_content(self):
        """清空内容容器。"""
        clear_layout(self._content_layout)
        self._content_mutated()

    # ============================================================
    # 样式
    # ============================================================
    def apply_style(self, radius: str, placement: str, is_full: bool):
        """按 radius / placement / size 刷新面板外观。

        radius    - none | sm | md | lg
        placement - left | right | top | bottom（决定削平哪一侧）
        is_full   - size=full 时四角全平
        """
        self._radius = radius
        self._placement = placement
        self._is_full = is_full

        r = 0 if is_full else _radius_px(radius)
        tl, tr, bl, br = r, r, r, r
        if placement == "top":
            tl = tr = 0
        elif placement == "bottom":
            bl = br = 0
        elif placement == "left":
            tl = bl = 0
        elif placement == "right":
            tr = br = 0

        bg = self._bg()
        dc = HEROUI_COLORS["default"]
        is_dark = self._theme == "dark"
        border = f"border: 1px solid {dc[800]};" if is_dark else "border: none;"
        fg = dc[100] if is_dark else dc[900]

        self.setStyleSheet(
            f"""
            #heroDrawer {{
                background-color: rgba({bg.red()}, {bg.green()}, {bg.blue()}, {bg.alpha()});
                border-top-left-radius: {tl}px;
                border-top-right-radius: {tr}px;
                border-bottom-left-radius: {bl}px;
                border-bottom-right-radius: {br}px;
                {border}
            }}
            """
        )
        self._content.setStyleSheet(
            f"#heroDrawerContent {{ background: transparent; color: {fg}; }}"
        )

        # 同步 palette，让子孙 widget 能读到面板实际底色
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(bg))
        self.setPalette(pal)
        self.update()

    def _bg(self) -> QColor:
        """面板底色 —— HeroUI bg-content1（无独立 token，用 default 色阶换算）。"""
        dc = HEROUI_COLORS["default"]
        return QColor(dc[900]) if self._theme == "dark" else QColor("#ffffff")

    def bg_color(self) -> QColor:
        """返回面板当前底色，供需要与面板融合的子组件读取。"""
        return QColor(self._bg())

    # ============================================================
    # 关闭按钮
    # ============================================================
    def set_hide_close_button(self, hide: bool):
        self._hide_close = bool(hide)
        self._sync_close_button()

    def set_close_button(self, widget: Optional[QWidget]):
        """换成自定义关闭按钮；传 None 恢复内置默认按钮。"""
        if self._close_btn is not None:
            safe_delete(self._close_btn)
            self._close_btn = None
        if widget is None:
            self._sync_close_button()
            return
        # 先挂父再显示，避免无父 widget 被系统当成顶层窗口闪一帧
        widget.setParent(self)
        self._close_btn = widget
        clicked = getattr(widget, "clicked", None)
        if clicked is not None:
            clicked.connect(lambda *_: self.close_requested.emit())
        self._place_close_button()
        self._sync_close_button()

    def _sync_close_button(self):
        """按 hide_close_button 决定是否创建 / 显示关闭按钮。"""
        if self._hide_close:
            if self._close_btn is not None:
                self._close_btn.setVisible(False)
            return
        if self._close_btn is None:
            self._ensure_default_close_button()
        self._close_btn.setVisible(True)
        self._close_btn.raise_()

    def _ensure_default_close_button(self):
        """内置关闭按钮 —— modal.ts 的 closeButton 规格（icon_only 圆形 light）。"""
        btn = Button(
            icon="heroicons--x-mark",
            icon_only=True,
            variant="light",
            color="default",
            size="sm",
            radius="full",
            theme=self._theme,
            parent=self,
        )
        btn.set_icon_only_side(DRAWER_SPEC["close_size"])
        btn.set_icon_size(DRAWER_SPEC["close_icon"])
        # clicked 带 checked 参数，丢掉避免把 bool 传进信号
        btn.clicked.connect(lambda *_: self.close_requested.emit())
        self._close_btn = btn
        self._place_close_button()

    def _place_close_button(self):
        """关闭按钮绝对定位到右上角（top-1 / end-1）。"""
        btn = self._close_btn
        if btn is None:
            return
        off = DRAWER_SPEC["close_offset"]
        # 构造期未显示的 widget width()/height() 是 640x480 默认值，不可信；
        # 用户锁定过尺寸（min==max）就尊重，否则按 sizeHint 收敛，避免铺满面板
        locked_w = btn.minimumWidth() == btn.maximumWidth()
        locked_h = btn.minimumHeight() == btn.maximumHeight()
        if not (locked_w and locked_h):
            sh = btn.sizeHint()
            if sh.isValid() and (btn.width(), btn.height()) != (sh.width(), sh.height()):
                btn.resize(sh)
        btn.move(self.width() - btn.width() - off, off)
        btn.raise_()

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self.apply_style(self._radius, self._placement, self._is_full)
        if isinstance(self._close_btn, Button):
            self._close_btn.set_theme(self._theme)

    def apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用 —— 只改色，不重复注册。"""
        self._theme = theme
        self.apply_style(self._radius, self._placement, self._is_full)
        if isinstance(self._close_btn, Button):
            self._close_btn.set_theme(theme)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_close_button()
