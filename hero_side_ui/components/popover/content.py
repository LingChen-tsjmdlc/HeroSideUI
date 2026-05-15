"""PopoverContent — Popover 浮层的内容容器（用户传入的内容会挂在这里）。"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ._constants import DEFAULT_PADDING




# ============================================================
# PopoverContent（插槽，类似 CardBody）
# ============================================================
class PopoverContent(QWidget):
    """Popover 内容插槽 — 任意 widget 都可以塞进来。

    用法::

        pc = PopoverContent()
        pc.layout().addWidget(QLabel("Hello"))
        pc.layout().addWidget(some_button)
        popover.set_content(pc)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("heroPopoverContent")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING, DEFAULT_PADDING
        )
        layout.setSpacing(8)
