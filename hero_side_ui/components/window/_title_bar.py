"""标题栏：三个槽 + 窗口控制按钮组，几何由 relayout 手工计算。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
)

from ...themes import WINDOW_SPEC
from ..text import Text
from ._controls import _Controls
from ._style import window_colors

# 默认标题的字号 / 字重按风格区分
_TITLE_FONT = {
    "windows": ("xs", "normal"),
    "linux": ("sm", "medium"),
    "mac": ("sm", "medium"),
}

_H_EXPANDING = (QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)


class _TitleWidget(QWidget):
    """默认的"图标 + 标题"小部件，标题过长时尾部省略。"""

    def __init__(
        self,
        title: str,
        icon: QIcon,
        system: str,
        theme_mode: str,
        parent: QWidget | None = None,
    ):
        """创建标题小部件。

        Args:
            title: 标题文字。
            icon: 窗口图标；为空时不占位。
            system: windows / mac / linux（决定字号字重）。
            theme_mode: auto / light / dark，原样交给内部 Text。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._title = title
        self._icon = icon
        self._icon_size = WINDOW_SPEC["title_icon_size"]
        self._gap = WINDOW_SPEC["title_icon_gap"]

        size, weight = _TITLE_FONT[system]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(self._gap)
        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(self._icon_size, self._icon_size)
        self._text = Text(
            title, size=size, weight=weight, selectable=False, theme=theme_mode, parent=self
        )
        self._text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._icon_label)
        lay.addWidget(self._text, 1)
        self._refresh_icon()
        self._elide()

    # ---- 数据 ----
    def set_title(self, title: str):
        """更新标题文字。

        Args:
            title: 新标题。
        """
        self._title = title
        self._elide()
        self.updateGeometry()

    def set_icon(self, icon: QIcon):
        """更新图标。

        Args:
            icon: 新图标；为空时隐藏图标位。
        """
        self._icon = icon
        self._refresh_icon()
        self.updateGeometry()

    def set_system(self, system: str):
        """按风格切换字号字重。

        Args:
            system: windows / mac / linux。
        """
        size, weight = _TITLE_FONT[system]
        self._text.set_size(size)
        self._text.set_weight(weight)
        self._elide()
        self.updateGeometry()

    def set_theme(self, mode: str):
        """切换内部文字的主题模式。

        Args:
            mode: auto / light / dark。
        """
        self._text.set_theme(mode)

    # ---- 内部 ----
    def _refresh_icon(self):
        """按当前图标重画图标位。"""
        if self._icon.isNull():
            self._icon_label.hide()
            return
        dpr = self.devicePixelRatioF()
        self._icon_label.setPixmap(self._icon.pixmap(QSize(self._icon_size, self._icon_size), dpr))
        self._icon_label.show()

    def _elide(self):
        """按当前宽度对标题做尾部省略。"""
        avail = self.width() - (0 if self._icon_label.isHidden() else self._icon_size + self._gap)
        fm = self._text.fontMetrics()
        if avail <= 0 or fm.horizontalAdvance(self._title) <= avail:
            self._text.setText(self._title)
        else:
            self._text.setText(fm.elidedText(self._title, Qt.TextElideMode.ElideRight, avail))

    def resizeEvent(self, event):
        """宽度变化后重新省略。"""
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event):
        """字体变化后重算省略与尺寸提示。"""
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:
            self._elide()
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        """按完整标题（不含省略）计算期望尺寸。"""
        fm = self._text.fontMetrics()
        w = fm.horizontalAdvance(self._title)
        if not self._icon_label.isHidden():
            w += self._icon_size + self._gap
        return QSize(w, max(fm.height(), self._icon_size))

    def minimumSizeHint(self) -> QSize:
        """允许被槽压缩到只剩图标位。"""
        w = 0 if self._icon_label.isHidden() else self._icon_size
        return QSize(w, self.sizeHint().height())


class _Slot(QWidget):
    """标题栏里的一个槽：容纳一个控件，按对齐方式摆放。"""

    def __init__(self, align: Qt.AlignmentFlag, parent: QWidget | None = None):
        """创建槽。

        Args:
            align: 水平对齐，AlignLeft / AlignHCenter / AlignRight。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._align = align
        self._content: QWidget | None = None
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def content(self) -> QWidget | None:
        """当前内容控件。"""
        return self._content

    def set_align(self, align: Qt.AlignmentFlag):
        """改变水平对齐。

        Args:
            align: AlignLeft / AlignHCenter / AlignRight。
        """
        if align != self._align:
            self._align = align
            self._refill()

    def set_content(self, widget: QWidget | None):
        """放入控件；旧控件只被取出并隐藏，销毁由调用方决定。

        Args:
            widget: 新内容；None 清空。
        """
        old = self._content
        if old is widget:
            return
        if old is not None:
            self._lay.removeWidget(old)
            # 控件可能已被别的槽接走（换风格时默认标题会换槽），只隐藏仍属于本槽的
            if old.parentWidget() is self:
                old.hide()
        self._content = widget
        if widget is not None:
            widget.setParent(self)
            self._refill()
            widget.show()
        self.updateGeometry()

    def _refill(self):
        """按内容的横向策略重新加入布局：Expanding 撑满，其余按对齐摆放。"""
        while self._lay.count():
            self._lay.takeAt(0)
        w = self._content
        if w is None:
            return
        v = Qt.AlignmentFlag.AlignVCenter
        if w.sizePolicy().horizontalPolicy() in _H_EXPANDING:
            self._lay.addWidget(w, 1, v)
        else:
            self._lay.addWidget(w, 0, self._align | v)

    def hint_width(self) -> int:
        """内容期望宽度；空槽为 0。"""
        if self._content is None:
            return 0
        return self._lay.sizeHint().width()


def is_drag_area(child: QWidget | None, bar: QWidget) -> bool:
    """判断标题栏内某个控件所在位置能否拖动窗口。

    Args:
        child: 鼠标下最深的子控件；None 表示标题栏自身。
        bar: 标题栏。

    Returns:
        True 表示可拖动。按钮、可获得焦点的控件、以及带 heroWindowNoDrag 属性的控件不可拖动。
    """
    w = child
    while w is not None and w is not bar:
        if isinstance(w, QAbstractButton) or w.focusPolicy() != Qt.FocusPolicy.NoFocus:
            return False
        if w.property("heroWindowNoDrag"):
            return False
        w = w.parentWidget()
    return True


class _TitleBar(QWidget):
    """标题栏：槽 + 控制按钮组，负责布局、底色与（非原生时）拖动 / 双击。"""

    drag_requested = Signal()
    double_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        """创建标题栏与三个槽。

        Args:
            parent: Qt 父对象（窗口）。
        """
        super().__init__(parent)
        self._system = "windows"
        self._theme = "light"
        self._height = WINDOW_SPEC["min_title_bar_height"]
        self._colors = window_colors("light")
        self._left = _Slot(Qt.AlignmentFlag.AlignLeft, self)
        self._center = _Slot(Qt.AlignmentFlag.AlignHCenter, self)
        self._right = _Slot(Qt.AlignmentFlag.AlignRight, self)
        self._controls = _Controls(self)

    # ---- 访问 ----
    def controls(self) -> _Controls:
        """窗口控制按钮组。"""
        return self._controls

    def slot(self, name: str) -> _Slot:
        """按名字取槽。

        Args:
            name: left / center / right。
        """
        return {"left": self._left, "center": self._center, "right": self._right}[name]

    def title_bar_height(self) -> int:
        """当前栏高。"""
        return self._height

    # ---- 配置 ----
    def configure(self, system: str, theme: str, title_bar_height: int, visible: dict[str, bool]):
        """应用风格、主题、栏高、按钮显隐，并重排。

        Args:
            system: windows / mac / linux（已解析）。
            theme: light / dark。
            title_bar_height: 标题栏高度。
            visible: 三个控制按钮是否可见。
        """
        self._system = system
        self._theme = theme
        self._height = title_bar_height
        self._colors = window_colors(theme)
        self.setFixedHeight(title_bar_height)
        self._controls.configure(system, theme, title_bar_height, visible)
        # 左 / 右槽的对齐随风格不变；mac 的左槽靠左（紧邻红黄绿），windows 的右槽靠右（紧邻按钮）
        self._left.set_align(Qt.AlignmentFlag.AlignLeft)
        self._right.set_align(Qt.AlignmentFlag.AlignRight)
        self._center.set_align(Qt.AlignmentFlag.AlignHCenter)
        self.relayout()
        self.update()

    # ---- 布局 ----
    def relayout(self):
        """按风格重算控制按钮组与三个槽的几何。"""
        W, H = self.width(), self._height
        ctrl_w = self._controls.preferred_width()
        pad, gap = WINDOW_SPEC["slot_padding"], WINDOW_SPEC["slot_gap"]
        if self._system == "mac":
            self._layout_mac(W, H, ctrl_w, pad, gap)
        else:
            self._layout_default(W, H, ctrl_w, pad, gap)

    def _layout_default(self, W: int, H: int, ctrl_w: int, pad: int, gap: int):
        """windows / linux：左槽按内容定宽，中槽与右槽 1:1 均分剩余空间。"""
        self._controls.setGeometry(W - ctrl_w, 0, ctrl_w, H)
        left_w = min(self._left.hint_width(), max(0, W - ctrl_w - 2 * pad))
        self._left.setGeometry(pad, 0, left_w, H)
        start = pad + left_w + (gap if left_w > 0 else 0)
        end = W - ctrl_w - (gap if ctrl_w > 0 else pad)
        region = max(0, end - start)
        half = max(0, (region - gap) // 2)
        self._center.setGeometry(start, 0, half, H)
        self._right.setGeometry(start + half + gap, 0, max(0, region - half - gap), H)

    def _layout_mac(self, W: int, H: int, ctrl_w: int, pad: int, gap: int):
        """mac：红黄绿在左，中槽按内容定宽并居于窗口正中，左 / 右槽 1:1 均分两侧。

        Note:
            右侧预留与按钮组等宽的空位，两边对称，标题才落在整个窗口的正中间。
        """
        edge = max(ctrl_w, pad)
        self._controls.setGeometry(0, 0, ctrl_w, H)
        center_w = min(self._center.hint_width(), max(0, W - 2 * (edge + gap)))
        center_x = (W - center_w) // 2
        self._center.setGeometry(center_x, 0, center_w, H)
        left_end = center_x - gap
        right_start = center_x + center_w + gap
        self._left.setGeometry(edge, 0, max(0, left_end - edge), H)
        self._right.setGeometry(right_start, 0, max(0, W - edge - right_start), H)

    def resizeEvent(self, event):
        """宽度变化后重排。"""
        super().resizeEvent(event)
        self.relayout()

    def refresh_layout(self):
        """槽内容变化后重排。"""
        self.relayout()

    # ---- 绘制与交互 ----
    def paintEvent(self, _event):
        """铺标题栏底色；圆角由窗口的覆盖层统一裁出。"""
        p = QPainter(self)
        p.fillRect(self.rect(), self._colors.title_bar)

    def mousePressEvent(self, event: QMouseEvent):
        """非原生路径：左键按在空白处，请求窗口开始系统拖动。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """非原生路径：双击空白处，请求最大化 / 还原。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


__all__ = ["_Slot", "_TitleBar", "_TitleWidget", "is_drag_area"]
