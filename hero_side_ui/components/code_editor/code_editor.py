"""CodeEditor 可编辑代码编辑器：QPlainTextEdit + pygments 实时高亮。

等宽字体（内置 Maple Mono）+ 行号栏 + Tab 转空格 + 回车保持缩进；
主题切换只换配色不重建编辑区。API 见 docs/code_editor.md。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import (
    CODE_EDITOR_LINE,
    CODE_EDITOR_SPEC,
    CODE_EDITOR_SYNTAX,
    HEROUI_COLORS,
)
from ..code_block._font import mono_qfont
from ._gutter import _Gutter
from ._pygments_highlighter import PygmentsHighlighter


class _EditArea(QPlainTextEdit):
    """编辑区本体：只管输入行为（Tab/Shift+Tab/回车缩进），外观由 CodeEditor 管。"""

    def __init__(self, tab_width: int, parent: QWidget | None = None) -> None:
        """创建编辑区本体。

        Args:
            tab_width: Tab 转空格宽度。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._tab_width = tab_width
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCursorWidth(2)

    def keyPressEvent(self, e) -> None:  # type: ignore[override]
        """接管 Tab / Shift+Tab / 回车的缩进行为。

        Args:
            e: Qt 键盘事件。

        Note:
            回车后先清掉 QPlainTextEdit 自带缩进，再统一补目标缩进；
            冒号结尾的行额外多缩进一级（v1 简化：不判断字符串内）。
        """
        if e.key() == Qt.Key.Key_Tab and not e.modifiers():
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._indent_selection(+1)
            else:
                cursor.insertText(" " * self._tab_width)
            return
        if e.key() == Qt.Key.Key_Backtab:
            self._indent_selection(-1)
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not e.modifiers():
            cursor = self.textCursor()
            if not cursor.hasSelection():
                # 目标缩进 = 光标所在行行首空白（截到光标处）；
                # 冒号结尾的行（未在字符串内，v1 简化）多缩进一级
                block = cursor.block()
                line_text = block.text()
                head = line_text[: cursor.positionInBlock()]
                indent = head[: len(head) - len(head.lstrip(" \t"))]
                if line_text.rstrip().endswith(":"):
                    indent += " " * self._tab_width
                super().keyPressEvent(e)
                # super() 可能同时插入换行与默认缩进（QPlainTextEdit 的
                # insertParagraphSeparator 自带缩进）；把新行行首空白
                # 全部清掉再统一补目标缩进
                after = self.textCursor()
                line = after.block().text()
                lead = len(line) - len(line.lstrip(" \t"))
                if lead:
                    cleaner = QTextCursor(after)
                    cleaner.movePosition(
                        QTextCursor.MoveOperation.StartOfLine,
                        QTextCursor.MoveMode.MoveAnchor,
                    )
                    cleaner.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        lead,
                    )
                    cleaner.removeSelectedText()
                if indent:
                    self.textCursor().insertText(indent)
                return
        super().keyPressEvent(e)

    def _indent_selection(self, direction: int) -> None:
        """选区覆盖的行整体增 / 删一级缩进；无选区时作用于当前行。

        Args:
            direction: +1 增加缩进，-1 减少缩进。

        Note:
            所有行的修改包在同一个 edit block 里，保证一次撤销可回退。
        """
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor
            )
        doc = self.document()
        blk = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        cursor.beginEditBlock()
        while True:
            if direction > 0:
                self._insert_block_indent(blk, " " * self._tab_width)
            else:
                self._remove_block_indent(blk)
            if blk == last:
                break
            blk = blk.next()
        cursor.endEditBlock()

    def _insert_block_indent(self, blk: object, text: str) -> None:
        """在指定 block 行首插入缩进文本。

        Args:
            blk: 目标 QTextBlock（以 object 标注避免循环依赖）。
            text: 要插入的空白串。
        """
        QTextCursor(blk).insertText(text)

    def _remove_block_indent(self, blk: object) -> None:
        """删掉行首最多 tab_width 个空格（或 1 个 tab）。

        Args:
            blk: 目标 QTextBlock。
        """
        line = blk.text()
        strip = 0
        for ch in line:
            if ch == " " and strip < self._tab_width:
                strip += 1
            elif ch == "\t":
                strip += 1
                break
            else:
                break
        if not strip:
            return
        cur = QTextCursor(blk)
        cur.setPosition(blk.position() + strip, QTextCursor.MoveMode.KeepAnchor)
        cur.removeSelectedText()


class CodeEditor(QWidget):
    """可编辑代码编辑器（Python 语法高亮 / 行号 / 智能缩进）。

    值 API 与 Input / Textarea 同构：构造参数 ``value``、``value()`` 取值、
    ``set_value()`` 赋值、``clear()`` 清空、``text_changed(str)`` 变化信号。

    用法::

        ed = CodeEditor()
        ed.set_value("def hello():\\n    print('hi')\\n")
        ed.text_changed.connect(do_something)   # 文本变化信号（str：全文）

        ed.value()   # 取全文
        ed.clear()   # 清空

    Args:
        value: 预填内容。
        language: 语言（pygments lexer 短名，如 "python"/"json"/"sql"/"javascript"）；识别失败降级纯文本。
        font: 代码字体 ttf 路径；None 用内置 Maple Mono NF CN。
        font_size: 代码字号(px)；None 用默认。
        tab_width: Tab 转空格宽度，默认 4。
        min_lines: 编辑区最小可见行数（决定最小高度）。
        max_lines: 最大行数上限，默认 10000；超限输入被截断。
        theme: "auto" / "light" / "dark"。
        parent: 父 widget。
    """

    text_changed = Signal(str)
    max_lines_exceeded = Signal(int)  # 载荷：被截断掉的行数

    def __init__(
        self,
        value: str = "",
        *,
        language: str = "python",
        font: str | None = None,
        font_size: int | None = None,
        tab_width: int | None = None,
        min_lines: int = 8,
        max_lines: int | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建代码编辑器：编辑区 + 行号栏 + 高亮器 + 行数上限。

        Args:
            value: 预填内容。
            language: pygments lexer 短名；识别失败降级纯文本。
            font: 代码字体 ttf 路径；None 用内置 Maple Mono NF CN。
            font_size: 代码字号（px）；None 用默认。
            tab_width: Tab 转空格宽度。
            min_lines: 最小可见行数（决定最小高度）。
            max_lines: 行数上限；超限输入被截断。
            theme: auto / light / dark。
            parent: 父 widget。

        Note:
            构造末尾主动 opt_out 全局平滑滚动——QPlainTextEdit
            整行滚动没有中间帧，平滑动画无收益；主题切换只换配色
            不重建编辑区，文本 / 光标 / 撤销栈全部保留。
        """
        super().__init__(parent)
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._language = language
        self._font_path = font
        self._font_size = int(font_size) if font_size else CODE_EDITOR_SPEC["font_size"]
        self._tab_width = int(tab_width) if tab_width else CODE_EDITOR_SPEC["tab_width"]
        self._max_lines = int(max_lines) if max_lines else CODE_EDITOR_SPEC["max_lines"]
        self._lh_cache: int = 0  # 行高缓存（0 = 待算）

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._gutter = _Gutter(self, parent=self)
        row.addWidget(self._gutter)

        self._edit = _EditArea(self._tab_width, parent=self)
        self._edit.setFont(mono_qfont(self._font_size, self._font_path))
        self._edit.viewport().setAutoFillBackground(False)
        row.addWidget(self._edit, stretch=1)

        host = QWidget(parent=self)
        host.setLayout(row)
        root.addWidget(host)

        # 高亮器：统一 pygments（语言识别失败降级纯文本）
        self._highlighter: PygmentsHighlighter | None = None
        self._rescan_timer = QTimer(self)
        self._rescan_timer.setSingleShot(True)
        self._rescan_timer.setInterval(150)
        self._rescan_timer.timeout.connect(self._rescan_highlight)
        self._set_highlighter(language)

        self._min_lines = max(1, int(min_lines))
        self._apply_min_height()
        self._apply_palette()

        if value:
            self._edit.setPlainText(value)

        self._edit.cursorPositionChanged.connect(self._on_cursor)
        self._edit.textChanged.connect(self._on_text_changed)
        self._edit.verticalScrollBar().valueChanged.connect(lambda _v: self._sync_gutter())

        self._clamp_lines(initial=True)
        self._rescan_highlight()
        self._on_cursor()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        # 永久退出全局平滑滚动：编辑器保持 Qt 原生整行滚动手感
        # （QPlainTextEdit 整行滚动没有中间帧，平滑动画无收益）
        try:
            from ...core import SmoothScroll

            SmoothScroll.opt_out(self._edit)
        except Exception:
            pass

    def _set_highlighter(self, language: str) -> None:
        """装配 pygments 高亮器（识别失败降级纯文本）。

        Args:
            language: pygments lexer 短名。

        Note:
            切换时先把旧高亮器 setDocument(None) 解绑，避免两个
            QSyntaxHighlighter 同时挂在同一文档上。
        """
        old = getattr(self, "_highlighter", None)
        if old is not None:
            old.setDocument(None)  # 解绑旧高亮器
        self._highlighter = PygmentsHighlighter(self._edit.document(), language, self._theme)

    def _rescan_highlight(self) -> None:
        """防抖重扫入口（文本变化 / 切语言 / 切主题后调用）。"""
        if self._highlighter is not None:
            self._highlighter.rescan()

    # ------------------------------------------------------------
    # 公共 API（与 Input / Textarea 的值 API 同构）
    # ------------------------------------------------------------

    def value(self) -> str:
        """返回编辑器全文。

        Returns:
            当前纯文本内容。
        """
        return self._edit.toPlainText()

    def text(self) -> str:
        """value() 的别名（对齐 Input.text()）。

        Returns:
            当前全文。
        """
        return self.value()

    def set_value(self, value: str) -> None:
        """整体替换全文并把光标移到文首。

        Args:
            value: 新全文；超出 max_lines 的部分会被截断。

        Note:
            setPlainText 进撤销栈；构造期传 initial=True 的截断不重置光标。
        """
        self._edit.setPlainText(value)
        self._clamp_lines()
        cursor = self._edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._edit.setTextCursor(cursor)

    def set_text(self, text: str) -> None:
        """set_value() 的别名（对齐 Input.set_text()）。

        Args:
            text: 新全文。
        """
        self.set_value(text)

    def clear(self) -> None:
        """清空编辑区全文。"""
        self._edit.clear()

    def set_read_only(self, ro: bool) -> None:
        """切换只读态。

        Args:
            ro: True 表示只读。
        """
        self._edit.setReadOnly(ro)

    def is_read_only(self) -> bool:
        """返回是否只读。

        Returns:
            True 表示编辑区只读。
        """
        return self._edit.isReadOnly()

    def insert_at_cursor(self, text: str) -> None:
        """在当前光标位置插入文本。

        Args:
            text: 要插入的文本。
        """
        self._edit.textCursor().insertText(text)

    def set_max_lines(self, max_lines: int) -> None:
        """改行数上限；当前内容超出时立即截断到新上限。

        Args:
            max_lines: 新上限（下限钳制为 1）。
        """
        self._max_lines = max(1, int(max_lines))
        self._clamp_lines()

    def max_lines(self) -> int:
        """返回当前行数上限。

        Returns:
            最大允许行数。
        """
        return self._max_lines

    def set_language(self, language: str) -> None:
        """切换语言高亮（pygments 短名；切换后立即重扫一次）。

        Args:
            language: pygments lexer 短名。
        """
        self._language = language
        self._set_highlighter(language)
        self._rescan_highlight()

    def set_font_size(self, size_px: int) -> None:
        """切换字号并刷新字体、行高缓存与最小高度。

        Args:
            size_px: 新字号（像素）。
        """
        self._font_size = int(size_px)
        self._edit.setFont(mono_qfont(self._font_size, self._font_path))
        self._invalidate_metrics()
        self._apply_min_height()
        self._on_cursor()

    @property
    def theme(self) -> str:
        """当前实际生效的主题名。

        Returns:
            light 或 dark（auto 已解析为具体值）。
        """
        return self._theme

    # ------------------------------------------------------------
    # 行数上限
    # ------------------------------------------------------------

    def _clamp_lines(self, initial: bool = False) -> None:
        """超过 max_lines 时截断尾部，并发射 max_lines_exceeded。

        Args:
            initial: True 用于构造期（初始 value 超限只截断不重置光标）。

        Note:
            至少保留一行；信号载荷为被截掉的行数。
        """
        doc = self._edit.document()
        excess = doc.blockCount() - self._max_lines
        if excess <= 0:
            return
        excess = min(excess, doc.blockCount() - 1)  # 至少保留一行
        last_keep = doc.findBlockByNumber(self._max_lines - 1)
        if not last_keep.isValid():
            return
        cur = QTextCursor(doc)
        cur.setPosition(last_keep.position() + last_keep.length() - 1)
        cur.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cur.removeSelectedText()
        self.max_lines_exceeded.emit(excess)

    # ------------------------------------------------------------
    # 内部：状态同步
    # ------------------------------------------------------------

    def _on_text_changed(self) -> None:
        """文本变化回调：截断、发信号、失效行高、同步行号栏、启动防抖重扫。

        Note:
            防抖窗口 150ms，停顿后才跑 pygments 全文重扫。
        """
        self._clamp_lines()
        self.text_changed.emit(self.value())
        self._invalidate_metrics()
        self._sync_gutter()
        self._rescan_timer.start()  # 防抖：停顿 150ms 后重扫（pygments 语言）

    def _on_cursor(self) -> None:
        """光标移动回调：同步行号栏当前行高亮。

        Note:
            当前行标识只由 gutter_current 承担，编辑区不加背景。
        """
        # 当前行的标识只由行号栏变色承担（gutter_current），编辑区不加背景
        self._sync_gutter()

    def _visible_metrics(self) -> tuple[int, int, int]:
        """取 (首行 y, 首行号, 总行数)。

        Returns:
            首行 y 需叠加 viewport 偏移与 block 偏移，防行号错位。
        """
        edit = self._edit
        first = edit.firstVisibleBlock()
        if first.isValid():
            top = int(edit.viewport().y()) + int(
                edit.blockBoundingGeometry(first).translated(edit.contentOffset()).top()
            )
            first_line = first.blockNumber() + 1
        else:
            top, first_line = int(edit.viewport().y()), 1
        total = edit.document().blockCount()
        return top, first_line, total

    def _line_height(self) -> int:
        """取真实行高（带缓存）。

        Returns:
            首 block boundingRect 的高度；空文档回退 fontMetrics().height()。
        """
        if self._lh_cache > 0:
            return self._lh_cache
        blk = self._edit.document().firstBlock()
        if blk.isValid() and blk.length() > 0:
            self._lh_cache = max(1, int(self._edit.blockBoundingRect(blk).height()))
        else:
            self._lh_cache = max(1, self._edit.fontMetrics().height())
        return self._lh_cache

    def _invalidate_metrics(self) -> None:
        """文本 / 字号变化后调用，下一帧重算行高。"""
        self._lh_cache = 0

    def _sync_gutter(self) -> None:
        """把字体、行高、当前行、可见范围推送给行号栏并自适应其宽度。

        Note:
            宽度不变时不触碰几何，避免滚动帧里反复布局。
        """
        line_height = self._line_height()
        top, first_line, total = self._visible_metrics()
        current = self._edit.textCursor().blockNumber() + 1
        self._gutter.sync(
            self._edit.font(),
            line_height,
            current,
            top,
            first_line,
            total,
        )
        # 行号栏宽度随位数自适应（宽度不变时不触碰几何，避免滚动帧里反复布局）
        digits = max(2, len(str(total)))
        char_w = self._edit.fontMetrics().horizontalAdvance("0")
        width = (
            CODE_EDITOR_LINE["dark" if self._theme == "dark" else "light"]["gutter_pad_x"]
            + digits * char_w
            + 6
        )
        if width != self._gutter.width():
            self._gutter.setFixedWidth(width)

    def _apply_min_height(self) -> None:
        """按 min_lines × 行高设置编辑区最小高度。"""
        self._edit.setMinimumHeight(self._line_height() * self._min_lines)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _apply_palette(self) -> None:
        """编辑区 QSS（透明底叠在外壳上）+ 行号栏主题。"""
        spec = CODE_EDITOR_SPEC
        line_cfg = CODE_EDITOR_LINE["dark" if self._theme == "dark" else "light"]
        syn = CODE_EDITOR_SYNTAX["dark" if self._theme == "dark" else "light"]
        self._gutter.set_theme(self._theme)
        self._edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                border: none;
                color: {syn["text"]};
                selection-background-color: {line_cfg["selection_bg"]};
                padding: {spec["code_pad_y"]}px {spec["code_pad_x"]}px;
            }}
            """)

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_theme(self, theme: str) -> None:
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._rebuild_theme()

    def _apply_provider_theme(self, theme: str) -> None:
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._rebuild_theme()

    def _rebuild_theme(self) -> None:
        """主题变更后只换配色，不重建编辑区。

        Note:
            文本 / 光标 / 撤销栈全部保留；高亮器 set_theme 内部已含重扫。
        """
        # 编辑区不重建：文本/光标/撤销栈全保留，只换配色
        self._apply_palette()
        if self._highlighter is not None:
            self._highlighter.set_theme(self._theme)  # set_theme 内部含重扫
        self._on_cursor()

    # ------------------------------------------------------------
    # 外观：圆角外壳
    # ------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """自绘圆角外壳底色与边框。

        Args:
            event: Qt 绘制事件。
        """
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        spec = CODE_EDITOR_SPEC
        dark = self._theme == "dark"
        bg = spec["code_bg_dark"] if dark else spec["code_bg_light"]
        border_shade = spec["border_shade_dark"] if dark else spec["border_shade"]
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QColor(HEROUI_COLORS["default"][border_shade]))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, spec["radius"], spec["radius"])
        painter.end()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        """尺寸变化后同步行号栏可见范围。

        Args:
            event: Qt 尺寸变化事件。
        """
        super().resizeEvent(event)
        self._sync_gutter()


__all__ = ["CodeEditor"]
