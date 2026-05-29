"""Pagination 组件演示。

覆盖维度: variant × color × size × radius × compact × shadow × controls × loop × disabled。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, Button, Pagination


class PaginationDemo(DemoBase):
    component_name = "Pagination"

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- 基础: 默认配置 ----------
        layout.addWidget(self._section_title("基础用法 (variant=flat color=primary)"))
        layout.addWidget(Pagination(total=10, initial_page=3))

        # ---------- 变体 ----------
        layout.addWidget(self._section_title("变体 (variant)"))
        for v in ("flat", "bordered", "light", "faded"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            label = Body(f"variant={v}")
            label.setFixedWidth(140)
            row_layout.addWidget(label)
            row_layout.addWidget(Pagination(total=10, initial_page=3, variant=v))
            row_layout.addStretch()
            layout.addWidget(row)

        # ---------- 颜色 ----------
        layout.addWidget(self._section_title("颜色 (color)"))
        for c in ("default", "primary", "secondary", "success", "warning", "danger"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            label = Body(f"color={c}")
            label.setFixedWidth(140)
            row_layout.addWidget(label)
            row_layout.addWidget(Pagination(total=10, initial_page=3, color=c))
            row_layout.addStretch()
            layout.addWidget(row)

        # ---------- 尺寸 ----------
        layout.addWidget(self._section_title("尺寸 (size)"))
        for s in ("sm", "md", "lg"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            label = Body(f"size={s}")
            label.setFixedWidth(140)
            row_layout.addWidget(label)
            row_layout.addWidget(Pagination(total=10, initial_page=3, size=s))
            row_layout.addStretch()
            layout.addWidget(row)

        # ---------- 圆角 ----------
        layout.addWidget(self._section_title("圆角 (radius)"))
        for r in ("none", "sm", "md", "lg", "full"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            label = Body(f"radius={r}")
            label.setFixedWidth(140)
            row_layout.addWidget(label)
            row_layout.addWidget(Pagination(total=10, initial_page=3, radius=r))
            row_layout.addStretch()
            layout.addWidget(row)

        # ---------- 紧凑模式 ----------
        layout.addWidget(self._section_title("紧凑模式 (is_compact)"))
        for v in ("flat", "bordered", "faded"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            label = Body(f"compact + {v}")
            label.setFixedWidth(140)
            row_layout.addWidget(label)
            row_layout.addWidget(
                Pagination(total=10, initial_page=3, variant=v, is_compact=True)
            )
            row_layout.addStretch()
            layout.addWidget(row)

        # ---------- prev/next 控件 ----------
        layout.addWidget(self._section_title("方向控件 (show_controls)"))
        layout.addWidget(Pagination(total=10, initial_page=5, show_controls=True))
        layout.addWidget(self._section_title("方向控件 + loop"))
        layout.addWidget(
            Pagination(total=10, initial_page=10, show_controls=True, loop=True)
        )

        # ---------- 自定义方向控件 (外部 Button) ----------
        layout.addWidget(
            self._section_title("自定义方向控件 (show_controls=False + 外部 Button)")
        )
        custom_pag = Pagination(total=10, initial_page=1, show_controls=False)
        custom_prev = Button(
            icon="heroicons--chevron-left",
            icon_only=True,
            variant="flat",
            size="md",
        )
        custom_next = Button(
            icon="heroicons--chevron-right",
            icon_only=True,
            variant="flat",
            size="md",
        )
        custom_prev.clicked.connect(custom_pag.go_previous)
        custom_next.clicked.connect(custom_pag.go_next)
        custom_row = QWidget()
        custom_row_layout = QHBoxLayout(custom_row)
        custom_row_layout.setContentsMargins(0, 0, 0, 0)
        custom_row_layout.setSpacing(8)
        custom_row_layout.addWidget(custom_prev)
        custom_row_layout.addWidget(custom_pag)
        custom_row_layout.addWidget(custom_next)
        custom_row_layout.addStretch()
        layout.addWidget(custom_row)

        # ---------- 大数据 (省略号 + dots_jump) ----------
        layout.addWidget(self._section_title("大数据集 (total=50, dots_jump=5)"))
        layout.addWidget(
            Pagination(total=50, initial_page=20, show_controls=True, dots_jump=5)
        )
        layout.addWidget(self._section_title("更大跨步 (dots_jump=10, siblings=2)"))
        layout.addWidget(
            Pagination(
                total=100,
                initial_page=50,
                show_controls=True,
                dots_jump=10,
                siblings=2,
            )
        )

        # ---------- 禁用动画 ----------
        layout.addWidget(
            self._section_title("禁用 cursor 动画 (disable_cursor_animation)")
        )
        layout.addWidget(
            Pagination(
                total=10,
                initial_page=3,
                color="primary",
                disable_cursor_animation=True,
            )
        )

        layout.addWidget(self._section_title("完全禁用动画 (disable_animation)"))
        layout.addWidget(Pagination(total=10, initial_page=3, disable_animation=True))

        # ---------- 禁用整体 ----------
        layout.addWidget(self._section_title("整体禁用 (is_disabled)"))
        layout.addWidget(Pagination(total=10, initial_page=3, is_disabled=True))

        # ---------- 信号联动 ----------
        layout.addWidget(self._section_title("信号: page_changed (查看控制台输出)"))
        live = Pagination(
            total=20, initial_page=1, show_controls=True, color="secondary"
        )
        status = Body("当前页: 1")
        live.page_changed.connect(lambda p: status.setText(f"当前页: {p}"))
        layout.addWidget(live)
        layout.addWidget(status)


if __name__ == "__main__":
    PaginationDemo.run()
