"""PopoverContent — Popover 浮层的内容容器（用户传入的内容会挂在这里）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ._constants import DEFAULT_PADDING


# ============================================================
# PopoverContent（插槽，类似 CardBody）
# ============================================================
class PopoverContent(QWidget):
    """Popover 内容插槽，任意 widget 塞进 layout。"""

    def __init__(self, parent: QWidget | None = None):
        """构造 Popover 内容插槽。

        Args:
            parent: 父控件，通常为 Popover 自身。
        """
        super().__init__(parent)
        self.setObjectName("heroPopoverContent")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING
        )
        layout.setSpacing(8)
