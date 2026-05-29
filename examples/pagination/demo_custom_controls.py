"""Pagination 自定义方向控件演示。

要点:
  - Pagination 默认通过 show_controls=True 自带 prev/next 按钮
  - 也可以关闭 show_controls,改用任意外部控件(如 Button)调用
    set_page / go_next / go_previous / go_first / go_last 来驱动
  - 文字滚动方向自动跟随页码增减语义化:增大向上,减小向下
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, Button, Pagination


class PaginationCustomControlsDemo(DemoBase):
    component_name = "Pagination · 自定义方向控件"

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- 示例 1: Button 控制 prev/next ----------
        layout.addWidget(self._section_title("Button 控制 上一页 / 下一页"))
        pag1 = Pagination(total=12, initial_page=1, show_controls=False)
        status1 = Body("当前页: 1")
        pag1.page_changed.connect(lambda p: status1.setText(f"当前页: {p}"))

        prev_btn = Button(
            icon="heroicons--chevron-left",
            icon_only=True,
            variant="flat",
            size="md",
        )
        next_btn = Button(
            icon="heroicons--chevron-right",
            icon_only=True,
            variant="flat",
            size="md",
        )
        prev_btn.clicked.connect(pag1.go_previous)
        next_btn.clicked.connect(pag1.go_next)

        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(8)
        row1_layout.addWidget(prev_btn)
        row1_layout.addWidget(pag1)
        row1_layout.addWidget(next_btn)
        row1_layout.addStretch()
        layout.addWidget(row1)
        layout.addWidget(status1)

        # ---------- 示例 2: 跳到首/末页 ----------
        layout.addWidget(self._section_title("Button 控制 首页 / 末页"))
        pag2 = Pagination(total=20, initial_page=10, show_controls=False)
        status2 = Body("当前页: 10")
        pag2.page_changed.connect(lambda p: status2.setText(f"当前页: {p}"))

        first_btn = Button(
            "首页", icon="heroicons--chevron-double-left-solid", variant="bordered"
        )
        last_btn = Button(
            "末页", icon="heroicons--chevron-double-right", variant="bordered"
        )
        first_btn.clicked.connect(pag2.go_first)
        last_btn.clicked.connect(pag2.go_last)

        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(8)
        row2_layout.addWidget(first_btn)
        row2_layout.addWidget(pag2)
        row2_layout.addWidget(last_btn)
        row2_layout.addStretch()
        layout.addWidget(row2)
        layout.addWidget(status2)

        # ---------- 示例 3: 任意 set_page 跳转 ----------
        layout.addWidget(self._section_title("Button 任意跳页 (set_page)"))
        pag3 = Pagination(total=15, initial_page=1, color="secondary")
        status3 = Body("当前页: 1")
        pag3.page_changed.connect(lambda p: status3.setText(f"当前页: {p}"))

        jump_btns_row = QWidget()
        jump_btns_layout = QHBoxLayout(jump_btns_row)
        jump_btns_layout.setContentsMargins(0, 0, 0, 0)
        jump_btns_layout.setSpacing(8)
        for target in (1, 5, 10, 15):
            btn = Button(f"跳到 {target}", variant="light", size="sm")
            btn.clicked.connect(lambda _=False, t=target: pag3.set_page(t))
            jump_btns_layout.addWidget(btn)
        jump_btns_layout.addStretch()
        layout.addWidget(pag3)
        layout.addWidget(jump_btns_row)
        layout.addWidget(status3)

        # ---------- 示例 4: 全自定义方向语义 ----------
        layout.addWidget(self._section_title("混搭: 自带控件 + 外部 Button 共存"))
        pag4 = Pagination(total=10, initial_page=5, show_controls=True, color="success")
        random_btn = Button("随机跳页", variant="flat", color="success")

        import random

        # 用闭包变量同步当前页
        cur_page = {"v": 5}
        pag4.page_changed.connect(lambda p: cur_page.update(v=p))

        def _random_jump():
            choices = [i for i in range(1, 11) if i != cur_page["v"]]
            pag4.set_page(random.choice(choices))

        random_btn.clicked.connect(_random_jump)
        row4 = QWidget()
        row4_layout = QHBoxLayout(row4)
        row4_layout.setContentsMargins(0, 0, 0, 0)
        row4_layout.setSpacing(8)
        row4_layout.addWidget(pag4)
        row4_layout.addWidget(random_btn)
        row4_layout.addStretch()
        layout.addWidget(row4)


if __name__ == "__main__":
    PaginationCustomControlsDemo.run()
