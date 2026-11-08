"""_TextEdit：palette.Base 透明 + 纯文本 + margin 0 + focus 信号的 QTextEdit。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QTextEdit, QWidget


# ============================================================
# 内部控件：无边框 / 透明背景的 QTextEdit
# ============================================================
class _TextEdit(QTextEdit):
    """无边框透明背景的 QTextEdit，融入 _InputWrapper 底色。

    Note:
        选 QTextEdit 而非 QPlainTextEdit——后者 scrollbar 单位是行号
        整数，拖动永远跳行（框架级限制）。
    """

    def __init__(self, parent: QWidget | None = None):
        """初始化透明无边框的 QTextEdit，关闭富文本并去掉文档默认 margin。"""
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
