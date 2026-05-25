"""_EndContentWidget — Select 触发钮右侧的 clear / arrow 复合槽（私有）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ..button import Button

from ._selector_button import _SelectorButton


class _EndContentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._h = QHBoxLayout(self)
        self._h.setContentsMargins(8, 0, 0, 0)
        self._h.setSpacing(4)
        self._h.setAlignment(Qt.AlignVCenter)

        self.clear_btn = Button(
            variant="light",
            color="default",
            size="sm",
            radius="full",
            icon_only=True,
        )
        self.clear_btn.setFocusPolicy(Qt.NoFocus)
        self.clear_btn.hide()
        self._h.addWidget(self.clear_btn, 0, Qt.AlignVCenter)

        self.selector_btn = _SelectorButton(self)
        self._h.addWidget(self.selector_btn, 0, Qt.AlignVCenter)
