"""_TextEdit — Textarea 内部 QTextEdit 子类（私有）。

负责：
- ``palette.Base`` 透明（避免 Fusion 风格画白底）
- ``setAcceptRichText(False)`` 强制纯文本输入
- ``document().setDocumentMargin(0)`` 文字紧贴 viewport 顶
- 暴露 focus_in / focus_out 信号
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QTextEdit




# ============================================================
# 内部控件：无边框 / 透明背景的 QTextEdit
# ============================================================
class _TextEdit(QTextEdit):
    """无边框透明背景的 QTextEdit，融入 _InputWrapper 底色。

    选用 QTextEdit 而不是 QPlainTextEdit 的核心原因：
        QPlainTextEdit 的 verticalScrollBar.value 单位 = 行号（block index），
        是整数，没有"半行"概念，所以拖动 scrollbar 永远跳行（Qt 框架级限制，
        无法通过 hooks 解决）。QTextEdit 的 scrollbar 是像素单位，拖动天然平滑。

    - setFrameStyle(NoFrame): 去掉默认 frame
    - palette.Base = transparent: 防止 Fusion 风格画白底
    - viewport setAutoFillBackground(False) + palette.Base 透明 同步
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from PySide6.QtWidgets import QFrame
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

        # 主体调色板
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.setPalette(pal)

        # viewport 也要透明，否则会画白底
        vp = self.viewport()
        vp.setAutoFillBackground(False)
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        vp.setPalette(vp_pal)

        # 滚动策略
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 自动换行（widget 宽度）
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # 关闭富文本接受（粘贴时纯文本）
        self.setAcceptRichText(False)

        # 去掉 QTextDocument 默认 4px 上下 margin，让文字第一行紧贴 viewport 顶
        # 这样 label 浮起位置、top_right 槽等才能和文字光学对齐
        self.document().setDocumentMargin(0)
