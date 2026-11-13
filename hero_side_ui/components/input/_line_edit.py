"""_LineEdit：palette.Base 透明的 QLineEdit，防 Fusion 画白底。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QLineEdit, QWidget


# ============================================================
# 内部控件：无边框/无焦点框的 QLineEdit
# ============================================================
class _LineEdit(QLineEdit):
    """无边框透明背景的 QLineEdit，融入 InputWrapper 底色。

    Note:
        背景完全由 wrapper paintEvent 负责；每次 setPalette 须保持
        Base=transparent。
    """

    def __init__(self, parent: QWidget | None = None):
        """创建无边框透明背景的输入框。

        Args:
            parent: Qt 父对象。

        Note:
            关掉 frame 与 Mac 焦点框，并把 palette.Base 设为全透明，
            防止 Fusion 画白底盖住 wrapper 的自绘背景。
        """
        super().__init__(parent)
        self.setFrame(False)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.setPalette(pal)
