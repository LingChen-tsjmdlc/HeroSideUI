"""_LineEdit — Input 内部的 QLineEdit 子类（私有）。

负责：
- palette.Base 透明（避免 Fusion 风格画白底覆盖父级背景）
- 焦点事件与 readonly 状态共享
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QLineEdit




# ============================================================
# 内部控件：无边框/无焦点框的 QLineEdit
# ============================================================
class _LineEdit(QLineEdit):
    """无边框透明背景的 QLineEdit，融入 _InputWrapper 底色。

    - setFrame(False): 去掉默认边框
    - palette.Base = transparent: 阻止 Qt Fusion 的 PE_PanelLineEdit 绘制白色背景
      （背景完全由外层 _InputWrapper paintEvent 负责）
    - _apply_styles 里每次 setPalette 时必须同步保持 Base = transparent
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrame(False)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.setPalette(pal)
