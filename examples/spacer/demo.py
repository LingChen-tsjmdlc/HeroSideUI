"""Spacer 组件演示。"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, Button, Spacer


class SpacerDemo(DemoBase):
    component_name = "Spacer"

    def build_content(self, layout: QVBoxLayout, _labels):
        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法（两个按钮之间 Spacer x=4 → 16px）"))
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(Button("左边"))
        h.addWidget(Spacer(x=4))
        h.addWidget(Button("右边"))
        h.addStretch()
        layout.addWidget(row)

        # ---------- X 档位 ----------
        layout.addWidget(self._section_title("X 档位（spacing scale：1=4px 递增）"))
        for x in (1, 2, 4, 8):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)
            h.addWidget(Body(f"x={x} ({int(4 * x)}px)"))
            h.addWidget(Spacer(x=x))
            h.addWidget(Button("按钮"))
            h.addStretch()
            layout.addWidget(row)

        # ---------- Y ----------
        layout.addWidget(self._section_title("Y 纵向间距（y=4 → 16px）"))
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        for text in ("上方", "下方"):
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(Button(text))
            h.addStretch()
            v.addLayout(h)
            if text == "上方":
                v.addWidget(Spacer(y=4))
        v.addStretch()
        layout.addWidget(col)

        # ---------- X + Y 同时传入 ----------
        layout.addWidget(self._section_title(
            "X + Y 同时传入（一个 Spacer 双轴）"))
        # 对照：单轴 x=4，行高 = 按钮高
        layout.addWidget(Body("对照：仅 x（行高 = 按钮高）"))
        ref = QWidget()
        rh = QHBoxLayout(ref)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(0)
        rh.addWidget(Button("A"))
        rh.addWidget(Spacer(x=4))
        rh.addWidget(Button("B"))
        rh.addStretch()
        layout.addWidget(ref)

        layout.addWidget(Spacer(y=1))

        # 双轴：y=14（56px）把行高撑到超过按钮高，上下多出空白
        layout.addWidget(Body("双轴：x=4 + y=14（行高被撑到 56px，上下多出约 10px 空白）"))
        diag = QWidget()
        dh = QHBoxLayout(diag)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(0)
        dh.addWidget(Button("A"))
        dh.addWidget(Spacer(x=4, y=14))
        dh.addWidget(Button("B"))
        dh.addStretch()
        layout.addWidget(diag)

        # ---------- 综合案例 ----------
        layout.addWidget(self._section_title("综合案例：工具条（标题左 + x=8 撑开 + 操作按钮右）与分区（y=3 分隔上下两块）"))
        card = QWidget()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 12, 16, 12)
        cv.setSpacing(0)

        # 顶部工具条：左标题、右侧按钮组
        toolbar = QWidget()
        th = QHBoxLayout(toolbar)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(0)
        th.addWidget(Body("我的文档"))
        th.addWidget(Spacer(x=8))
        th.addWidget(Button("新建", size="sm"))
        th.addWidget(Spacer(x=1))
        th.addWidget(Button("导入", size="sm", variant="bordered"))
        th.addStretch()
        cv.addWidget(toolbar)

        cv.addWidget(Spacer(y=3))

        # 底部内容区：左侧文本、右侧 x=2 间隔的两个按钮
        content = QWidget()
        ch = QHBoxLayout(content)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(0)
        ch.addWidget(Body("共 12 个文件 · 上次修改今天"))
        ch.addWidget(Spacer(x=8))
        ch.addStretch()
        ch.addWidget(Button("分享", size="sm", variant="flat", color="primary"))
        ch.addWidget(Spacer(x=2))
        ch.addWidget(Button("删除", size="sm", variant="flat", color="danger"))
        cv.addWidget(content)
        layout.addWidget(card)


if __name__ == "__main__":
    SpacerDemo.run()
