"""Skeleton 组件示例 — 对齐 HeroUI Skeleton 页面全部示例。

示例:
1. Default — 卡片布局骨架（Skeleton 包裹灰色 content）
2. Standalone — 独立使用（头像+文本行，无 children）
3. LoadedState — isLoaded 切换（Skeleton 包裹紫色 content，按钮控制）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from hero_side_ui import (
    Skeleton,
    Button,
    Card,
    CardBody,
    Title,
    Body,
)
from _base import DemoBase


# ============================================================
# 1. Default — 卡片布局骨架
# ============================================================

def _make_default_skeleton_example() -> QWidget:
    """复刻 HeroUI Default 示例。

    官方源码（skeleton.stories.tsx DefaultTemplate）：
    Card w-[200px] space-y-5 p-4, radius="lg"
    └ Skeleton rounded-lg
      └ div h-24 rounded-lg bg-default-300
    └ div space-y-3
      ├ Skeleton w-3/5 rounded-lg → div h-3 w-3/5 bg-default-200
      ├ Skeleton w-4/5 rounded-lg → div h-3 w-4/5 bg-default-200
      └ Skeleton w-2/5 rounded-lg → div h-3 w-2/5 bg-default-300
    """
    card = Card(radius="lg")
    card.setFixedWidth(200)
    card_body = CardBody()
    body_layout = card_body.layout()
    body_layout.setContentsMargins(16, 16, 16, 16)
    body_layout.setSpacing(20)

    # 大矩形骨架 → div h-24 rounded-lg bg-default-300 (#d4d4d8)
    img_content = QWidget()
    img_content.setFixedHeight(96)
    img_content.setStyleSheet("background-color: #d4d4d8; border-radius: 8px;")
    img_skeleton = Skeleton(child=img_content, radius="lg")
    body_layout.addWidget(img_skeleton)

    # 3 个文本行 → div space-y-3
    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(12)

    # Skeleton w-3/5 → div h-3 w-3/5 bg-default-200 (#e4e4e7)
    line1_content = QWidget()
    line1_content.setFixedHeight(12)
    line1_content.setStyleSheet("background-color: #e4e4e7; border-radius: 8px;")
    line1 = Skeleton(child=line1_content, radius="lg")
    line1.setFixedHeight(12)
    line1.setMinimumWidth(int(200 * 3 / 5))
    text_layout.addWidget(line1)

    # Skeleton w-4/5 → div h-3 w-4/5 bg-default-200 (#e4e4e7)
    line2_content = QWidget()
    line2_content.setFixedHeight(12)
    line2_content.setStyleSheet("background-color: #e4e4e7; border-radius: 8px;")
    line2 = Skeleton(child=line2_content, radius="lg")
    line2.setFixedHeight(12)
    line2.setMinimumWidth(int(200 * 4 / 5))
    text_layout.addWidget(line2)

    # Skeleton w-2/5 → div h-3 w-2/5 bg-default-300 (#d4d4d8)
    line3_content = QWidget()
    line3_content.setFixedHeight(12)
    line3_content.setStyleSheet("background-color: #d4d4d8; border-radius: 8px;")
    line3 = Skeleton(child=line3_content, radius="lg")
    line3.setFixedHeight(12)
    line3.setMinimumWidth(int(200 * 2 / 5))
    text_layout.addWidget(line3)

    body_layout.addWidget(text_container)
    card.add_body(card_body)
    return card


# ============================================================
# 2. Standalone — 独立使用
# ============================================================

def _make_standalone_skeleton_example() -> QWidget:
    """复刻 HeroUI Standalone 示例。

    官方源码：max-w-[300px] w-full flex items-center gap-3
    └ Skeleton flex rounded-full w-12 h-12
    └ div w-full flex flex-col gap-2
      ├ Skeleton h-3 w-3/5 rounded-lg
      └ Skeleton h-3 w-4/5 rounded-lg
    """
    wrapper = QWidget()
    wrapper.setMaximumWidth(300)
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    # 圆形头像骨架 → Skeleton rounded-full w-12 h-12
    avatar = Skeleton(radius="full")
    avatar.setFixedSize(48, 48)
    layout.addWidget(avatar)

    # 文本行 → div w-full flex flex-col gap-2
    lines = QWidget()
    lines_layout = QVBoxLayout(lines)
    lines_layout.setContentsMargins(0, 0, 0, 0)
    lines_layout.setSpacing(8)

    # Skeleton h-3 w-3/5 rounded-lg
    line1 = Skeleton(radius="lg")
    line1.setFixedHeight(12)
    line1.setMinimumWidth(int(300 * 3 / 5))
    lines_layout.addWidget(line1)

    # Skeleton h-3 w-4/5 rounded-lg
    line2 = Skeleton(radius="lg")
    line2.setFixedHeight(12)
    line2.setMinimumWidth(int(300 * 4 / 5))
    lines_layout.addWidget(line2)

    layout.addWidget(lines, 1)
    wrapper.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return wrapper


# ============================================================
# 3. LoadedState — 按钮切换 isLoaded
# ============================================================

def _make_loaded_state_example() -> QWidget:
    """复刻 HeroUI LoadedState 示例。

    官方源码（skeleton.stories.tsx LoadedStateTemplate）：
    Card w-[200px] space-y-5 p-4, radius="lg"
    └ Skeleton rounded-lg isLoaded={isLoaded}
      └ div h-24 rounded-lg bg-secondary (#7828c8)
    └ div space-y-3
      ├ Skeleton w-3/5 rounded-lg isLoaded={isLoaded}
      │   └ div h-3 w-full rounded-lg bg-secondary
      ├ Skeleton w-4/5 rounded-lg isLoaded={isLoaded}
      │   └ div h-3 w-full rounded-lg bg-secondary-300 (#a855f7)
      └ Skeleton w-2/5 rounded-lg isLoaded={isLoaded}
          └ div h-3 w-full rounded-lg bg-secondary-200 (#c084fc)
    Button color="secondary" size="sm" variant="flat" max-w-[200px]
      └ {isLoaded ? "Show" : "Hide"} Skeleton
    """
    wrapper = QWidget()
    wrapper_layout = QVBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(0, 0, 0, 0)
    wrapper_layout.setSpacing(12)

    skeletons = []

    # Card: w-[200px] space-y-5 p-4
    card = Card(radius="lg")
    card.setFixedWidth(200)
    card_body = CardBody()
    body_layout = card_body.layout()
    body_layout.setContentsMargins(16, 16, 16, 16)
    body_layout.setSpacing(20)

    # 大矩形 → div h-24 rounded-lg bg-secondary
    img_content = QWidget()
    img_content.setFixedHeight(96)
    img_content.setStyleSheet("background-color: #7828c8; border-radius: 8px;")
    img_skeleton = Skeleton(child=img_content, radius="lg", is_loaded=False)
    skeletons.append(img_skeleton)
    body_layout.addWidget(img_skeleton)

    # 3 个文本行 → div space-y-3
    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(12)

    # Skeleton w-3/5 → div h-3 w-full bg-secondary
    line1_content = QWidget()
    line1_content.setFixedHeight(12)
    line1_content.setStyleSheet("background-color: #7828c8; border-radius: 8px;")
    line1_skeleton = Skeleton(child=line1_content, radius="lg", is_loaded=False)
    line1_skeleton.setFixedHeight(12)
    line1_skeleton.setMinimumWidth(int(200 * 3 / 5))
    skeletons.append(line1_skeleton)
    text_layout.addWidget(line1_skeleton)

    # Skeleton w-4/5 → div h-3 w-full bg-secondary-300
    line2_content = QWidget()
    line2_content.setFixedHeight(12)
    line2_content.setStyleSheet("background-color: #a855f7; border-radius: 8px;")
    line2_skeleton = Skeleton(child=line2_content, radius="lg", is_loaded=False)
    line2_skeleton.setFixedHeight(12)
    line2_skeleton.setMinimumWidth(int(200 * 4 / 5))
    skeletons.append(line2_skeleton)
    text_layout.addWidget(line2_skeleton)

    # Skeleton w-2/5 → div h-3 w-full bg-secondary-200
    line3_content = QWidget()
    line3_content.setFixedHeight(12)
    line3_content.setStyleSheet("background-color: #c084fc; border-radius: 8px;")
    line3_skeleton = Skeleton(child=line3_content, radius="lg", is_loaded=False)
    line3_skeleton.setFixedHeight(12)
    line3_skeleton.setMinimumWidth(int(200 * 2 / 5))
    skeletons.append(line3_skeleton)
    text_layout.addWidget(line3_skeleton)

    body_layout.addWidget(text_container)
    card.add_body(card_body)
    wrapper_layout.addWidget(card)

    # Button: color="secondary" size="sm" variant="flat" max-w-[200px]
    toggle_btn = Button(
        text="Hide Skeleton",
        variant="flat",
        color="secondary",
        size="sm",
    )
    toggle_btn.setFixedWidth(200)

    _state = {"loaded": False}

    def _toggle():
        _state["loaded"] = not _state["loaded"]
        loaded = _state["loaded"]
        for s in skeletons:
            s.set_loaded(loaded)
        # 官方：isLoaded ? "Show" : "Hide" Skeleton
        toggle_btn.setText("Show Skeleton" if loaded else "Hide Skeleton")

    toggle_btn.clicked.connect(_toggle)
    wrapper_layout.addWidget(toggle_btn)

    return wrapper


# ============================================================
# Demo 主类
# ============================================================

class SkeletonDemo(DemoBase):
    component_name = "Skeleton"

    def build_content(self, layout, labels_bag):
        # 1. Default
        layout.addWidget(self._section_title("Default"))
        default_card = _make_default_skeleton_example()
        layout.addWidget(default_card)

        # 间距
        layout.addSpacing(24)

        # 2. Standalone
        layout.addWidget(self._section_title("Standalone"))
        standalone = _make_standalone_skeleton_example()
        layout.addWidget(standalone)

        # 间距
        layout.addSpacing(24)

        # 3. LoadedState
        layout.addWidget(self._section_title("Loaded State"))
        loaded = _make_loaded_state_example()
        layout.addWidget(loaded)


if __name__ == "__main__":
    SkeletonDemo.run()
