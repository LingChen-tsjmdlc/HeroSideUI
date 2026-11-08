"""空状态占位 widget 构建（mixin）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...core import StatePalette
from ...themes import LISTBOX_SIZES
from ...utils import load_svg_icon
from ..text import Text


class _EmptyContentMixin:
    """empty 占位 widget 的构造/重建/显隐 mixin；宿主提供尺寸与列表字段。"""

    def set_empty_content(self, text: str | None):
        """设置空态文案（None/"" 走默认 icon + 中英双语，非空则单行文字）。

        Args:
            text: 自定义空态文字；None 恢复默认。
        """
        # None / "" 恢复默认 icon + 中英双语；非空 str 单行文字
        self._empty_content_text = text
        self._rebuild_empty_widget()

    def _rebuild_empty_widget(self):
        """销毁并重建空态 widget，恢复可见性并放回到原位置。"""
        idx = self._list_v.indexOf(self._empty_widget)
        # 用 isHidden() 而非 isVisible()：popover 关闭时 isVisible 会被父级压成 False
        was_visible = not self._empty_widget.isHidden()
        self._list_v.removeWidget(self._empty_widget)
        from ...utils import safe_delete

        safe_delete(self._empty_widget)
        self._empty_widget = self._build_empty_widget()
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        if self._empty_content_text:
            self._empty_widget.setMinimumHeight(cfg["empty_height"])
        else:
            # icon (3×title) + 两行文字 + 上下 padding + spacing
            self._empty_widget.setMinimumHeight(
                cfg["title_font_size"] * 3
                + cfg["title_font_size"]
                + cfg["desc_font_size"]
                + cfg["item_padding_y"] * 4
                + 16
            )
        if idx < 0:
            self._list_v.addWidget(self._empty_widget)
        else:
            self._list_v.insertWidget(idx, self._empty_widget)
        self._empty_label = self._empty_widget.findChild(QLabel, "heroEmptyText") or Text("")
        self._empty_widget.setVisible(was_visible)

    def _refresh_empty(self):
        """根据条目数显隐空态 widget（无条目时显示）。"""
        empty = len(self._items) == 0
        self._empty_widget.setVisible(empty)

    def _build_empty_widget(self) -> QWidget:
        """构建空态 widget（默认模式 icon+双语，兼容模式单行文字）。

        Returns:
            QWidget: 新构建的空态占位控件。
        """
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        w = QWidget(self._list)
        w.setAttribute(Qt.WA_TranslucentBackground, True)

        # 兼容模式：单行文字
        if self._empty_content_text:
            v = QVBoxLayout(w)
            v.setContentsMargins(
                cfg["item_padding_x"],
                cfg["item_padding_y"],
                cfg["item_padding_x"],
                cfg["item_padding_y"],
            )
            v.setSpacing(0)
            text_label = Text(
                self._empty_content_text,
                parent=w,
                color=StatePalette.text_description(self._theme).name(),
                selectable=False,
            )
            text_label.setObjectName("heroEmptyText")
            text_label.setAttribute(Qt.WA_TranslucentBackground, True)
            text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            v.addWidget(text_label)
            return w

        # 默认模式：居中 icon + 中英双语
        v = QVBoxLayout(w)
        v.setContentsMargins(
            cfg["item_padding_x"],
            cfg["item_padding_y"] * 2,
            cfg["item_padding_x"],
            cfg["item_padding_y"] * 2,
        )
        v.setSpacing(8)
        v.setAlignment(Qt.AlignCenter)

        icon_size = cfg["title_font_size"] * 3
        icon_color = StatePalette.text_description(self._theme)
        icon_label = QLabel(w)
        icon_label.setObjectName("heroEmptyIcon")
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(
            load_svg_icon("mingcute--empty-box-line", size=icon_size, color=icon_color)
        )
        icon_label.setFixedSize(icon_size, icon_size)
        v.addWidget(icon_label, 0, Qt.AlignCenter)

        en_label = Text(
            "Nothing to show",
            parent=w,
            size=cfg["title_font_size"],
            color=StatePalette.text_description(self._theme).name(),
            selectable=False,
        )
        en_label.setObjectName("heroEmptyText")
        en_label.setAttribute(Qt.WA_TranslucentBackground, True)
        en_label.setAlignment(Qt.AlignCenter)
        v.addWidget(en_label, 0, Qt.AlignCenter)

        cn_label = Text(
            "暂无内容",
            parent=w,
            size=cfg["desc_font_size"],
            color=StatePalette.text_description(self._theme).name(),
            selectable=False,
        )
        cn_label.setObjectName("heroEmptyTextCn")
        cn_label.setAttribute(Qt.WA_TranslucentBackground, True)
        cn_label.setAlignment(Qt.AlignCenter)
        v.addWidget(cn_label, 0, Qt.AlignCenter)

        return w
