"""CodeBlock 标题栏：左侧文件名 / 多 tab，右侧自动换行开关 + 复制按钮。

纯视觉 + 交互转发：tab 切换、wrap 切换、复制都以信号/回调抛给宿主 CodeBlock，
自身不持有代码内容。所有子 widget 显式传 parent，避免无父瞬间闪窗。
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ...themes import CODE_BLOCK_SPEC, HEROUI_COLORS
from ..button import Button
from ..text import Text


class _CodeHeaderBar(QWidget):
    """代码块标题栏。

    Args:
        filename:    单文件模式的文件名 / 语言标签
        tabs:        多 tab 模式的 tab 名列表（非空则显示 tab）
        theme:       当前主题
        on_tab:      切换 tab 回调 (index)
        on_wrap:     切换自动换行回调 (bool)
        on_copy:     点击复制回调 ()
    """

    def __init__(
        self,
        filename: str,
        tabs: List[str],
        theme: str,
        on_tab: Callable[[int], None],
        on_wrap: Callable[[bool], None],
        on_copy: Callable[[], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._tabs = tabs
        self._on_tab = on_tab
        self._on_wrap = on_wrap
        self._on_copy = on_copy
        self._active_tab = 0
        self._wrap = False
        self._tab_buttons: List[Button] = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(
            CODE_BLOCK_SPEC["header_pad_x"],
            CODE_BLOCK_SPEC["header_pad_y"],
            CODE_BLOCK_SPEC["header_pad_x"],
            CODE_BLOCK_SPEC["header_pad_y"],
        )
        lay.setSpacing(4)

        # 左侧：tab 组 或 文件名
        if tabs:
            for i, name in enumerate(tabs):
                btn = Button(
                    name,
                    variant="light",
                    size="sm",
                    color="default",
                    theme=theme,
                    parent=self,
                )
                btn.clicked.connect(lambda _=False, idx=i: self._select_tab(idx))
                self._tab_buttons.append(btn)
                lay.addWidget(btn)
            self._sync_tab_styles()
        else:
            label = Text(
                filename,
                size="sm",
                color=HEROUI_COLORS["default"][CODE_BLOCK_SPEC["filename_shade"]],
                theme=theme,
                parent=self,
            )
            lay.addWidget(label)

        lay.addStretch()

        # 右侧：自动换行开关 + 复制按钮（Button icon_only flat）
        self._wrap_btn = Button(
            icon_only=True,
            icon="lucide--wrap-text",
            variant="flat",
            size="sm",
            color="default",
            theme=theme,
            parent=self,
        )
        self._wrap_btn.clicked.connect(self._toggle_wrap)
        lay.addWidget(self._wrap_btn)

        self._copy_btn = Button(
            icon_only=True,
            icon="lucide--copy",
            variant="flat",
            size="sm",
            color="default",
            theme=theme,
            parent=self,
        )
        self._copy_btn.clicked.connect(self._on_copy)
        lay.addWidget(self._copy_btn)

    # ---- tab ----
    def _select_tab(self, idx: int) -> None:
        self._active_tab = idx
        self._sync_tab_styles()
        self._on_tab(idx)

    def _sync_tab_styles(self) -> None:
        # 选中 tab 用 flat 实底，其余 light；靠切 variant 表达激活态
        for i, btn in enumerate(self._tab_buttons):
            btn.set_variant("flat" if i == self._active_tab else "light")

    # ---- wrap ----
    def _toggle_wrap(self) -> None:
        self._wrap = not self._wrap
        # 激活态用 primary 色，未激活回 default
        self._wrap_btn.set_color("primary" if self._wrap else "default")
        self._on_wrap(self._wrap)

    # ---- copy 反馈 ----
    def flash_copied(self) -> None:
        """复制成功后把图标临时切成 check，2s 后还原。"""
        self._copy_btn.set_icon("lucide--check")
        self._copy_btn.set_color("success")
        QTimer.singleShot(2000, self._restore_copy_icon)

    def _restore_copy_icon(self) -> None:
        self._copy_btn.set_icon("lucide--copy")
        self._copy_btn.set_color("default")


__all__ = ["_CodeHeaderBar"]
