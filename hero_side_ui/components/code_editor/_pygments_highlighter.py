"""pygments 驱动的通用语法高亮器（QSyntaxHighlighter 适配）。

复用 ``code_block/_highlight.py`` 的现成管线：``_token_color``（语义 token →
颜色，与 CodeBlock 完全同源）与 ``lex``（pygments 流式切词）。这里只做
QSyntaxHighlighter 的桥接：

pygments lexer 是流式（跨行 token 由 lexer 状态推进），无法直接映射到按
block 回调；策略是文档变化时全文 lex 一遍，把结果缓存成"每 block 的
(start, end, color) 片段"，``highlightBlock`` 查缓存上色。护栏：超过
``_MAX_LEX_LINES`` 行不重扫（保留旧缓存），避免超大粘贴卡 UI。
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QTextDocument

from ...themes import CODE_EDITOR_SYNTAX
from ..code_block._highlight import _token_color

_MAX_LEX_LINES = 20000


class PygmentsHighlighter(QSyntaxHighlighter):
    """任意 pygments 语言的实时高亮器（全文重扫 + block 缓存）。

    Args:
        doc:      编辑器的 document()
        language: pygments lexer 短名（如 "python" / "json" / "sql"）；识别失败降级纯文本
        theme:    "light" / "dark"
    """

    def __init__(self, doc: QTextDocument, language: str, theme: str) -> None:
        super().__init__(doc)
        self._theme = theme
        self._lexer = None
        self._cache: dict[int, list[tuple[int, int, str]]] = {}   # blockNumber → [(start,end,hex)]
        try:
            from pygments.lexers import get_lexer_by_name
            self._lexer = get_lexer_by_name(language, stripnl=False)
        except Exception:
            self._lexer = None
        self._fmt_cache: dict[str, QTextCharFormat] = {}

    # -- 对外 --------------------------------------------------------------

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._fmt_cache.clear()
        self.rescan()

    def set_language(self, language: str) -> None:
        try:
            from pygments.lexers import get_lexer_by_name
            self._lexer = get_lexer_by_name(language, stripnl=False)
        except Exception:
            self._lexer = None
        self._cache.clear()
        self.rehighlight()

    def rescan(self) -> None:
        """全文跑一遍 lexer 重建缓存并重画（识别失败/超行数上限时跳过）。"""
        if self._lexer is None:
            return
        doc = self.document()
        if doc.blockCount() > _MAX_LEX_LINES:
            return
        syn = CODE_EDITOR_SYNTAX["dark" if self._theme == "dark" else "light"]

        # block 起始位置表（用于绝对偏移 → block 归属换算）
        block_starts: list[int] = []
        blk = doc.firstBlock()
        while blk.isValid():
            block_starts.append(blk.position())
            blk = blk.next()

        new_cache: dict[int, list[tuple[int, int, str]]] = {}
        import bisect
        from pygments import lex

        pos = 0   # 跨 token 累加；每个 token 内部的 \n 段间再各 +1
        for ttype, value in lex(doc.toPlainText(), self._lexer):
            color = _token_color(ttype, syn)
            first = True
            for seg in value.split("\n"):
                if not first:
                    pos += 1   # 跨过 token 内的换行符
                first = False
                if seg:
                    bno = bisect.bisect_right(block_starts, pos) - 1
                    if 0 <= bno < len(block_starts):
                        rel = pos - block_starts[bno]
                        new_cache.setdefault(bno, []).append(
                            (rel, rel + len(seg), color)
                        )
                pos += len(seg)

        self._cache = new_cache
        self.rehighlight()

    # -- 内部 --------------------------------------------------------------

    def _fmt(self, hex_color: str) -> QTextCharFormat:
        fmt = self._fmt_cache.get(hex_color)
        if fmt is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(hex_color))
            self._fmt_cache[hex_color] = fmt
        return fmt

    # QSyntaxHighlighter 接口 ----------------------------------------------

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        spans = self._cache.get(self.currentBlock().blockNumber())
        if not spans:
            return
        for start, end, color in spans:
            if end > start:
                self.setFormat(start, end - start, self._fmt(color))


__all__ = ["PygmentsHighlighter"]
