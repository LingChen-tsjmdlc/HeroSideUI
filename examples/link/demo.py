"""Link 组件示例 — 对齐 HeroUI v2 Link 全维度。

覆盖：默认/Sizes/Colors/Underline 五档/isBlock/External + showAnchorIcon/
自定义 anchorIcon/Disabled/disableAnimation。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from hero_side_ui import Body, Caption, Link
from _base import DemoBase


# ============================================================
# 布局工具
# ============================================================
def _row(*widgets: QWidget, spacing: int = 16) -> QWidget:
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for w in widgets:
        lay.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    box.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    return box


def _column(*widgets: QWidget, spacing: int = 8) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
    for w in widgets:
        lay.addWidget(w)
    return box


def _labeled(label: str, widget: QWidget) -> QWidget:
    return _row(Caption(label), widget, spacing=10)


# ============================================================
# 1. Default
# ============================================================
def _make_default() -> list[QWidget]:
    return [
        Link("HeroSideUI", href="https://github.com/LingChen-tsjmdlc/HeroSideUI"),
    ]


# ============================================================
# 2. Sizes
# ============================================================
def _make_sizes() -> QWidget:
    return _row(
        _labeled("sm", Link("Small link", size="sm")),
        _labeled("md", Link("Medium link", size="md")),
        _labeled("lg", Link("Large link", size="lg")),
        spacing=24,
    )


# ============================================================
# 3. Colors（6 种）
# ============================================================
def _make_colors() -> list[QWidget]:
    return [
        Link("Foreground", color="foreground"),
        Link("Primary", color="primary"),
        Link("Secondary", color="secondary"),
        Link("Success", color="success"),
        Link("Warning", color="warning"),
        Link("Danger", color="danger"),
    ]


# ============================================================
# 4. Underline 五档
# ============================================================
def _make_underline() -> QWidget:
    return _row(
        _labeled("none", Link("None", underline="none")),
        _labeled("hover", Link("Hover me", underline="hover")),
        _labeled("always", Link("Always", underline="always")),
        _labeled("active", Link("Press me", underline="active")),
        _labeled("focus", Link("Focus me (Tab)", underline="focus")),
        spacing=24,
    )


# ============================================================
# 5. isBlock —— hover 显示色块
# ============================================================
def _make_block() -> QWidget:
    return _row(
        Link("Foreground block", color="foreground", is_block=True),
        Link("Primary block", color="primary", is_block=True),
        Link("Secondary block", color="secondary", is_block=True),
        Link("Success block", color="success", is_block=True),
        Link("Warning block", color="warning", is_block=True),
        Link("Danger block", color="danger", is_block=True),
        spacing=8,
    )


# ============================================================
# 6. External + showAnchorIcon（默认 share 图标）
# ============================================================
def _make_external() -> QWidget:
    return _row(
        Link(
            "Visit HeroUI",
            href="https://heroui.com",
            is_external=True,
            show_anchor_icon=True,
        ),
        Link(
            "GitHub",
            href="https://github.com/heroui-inc/heroui",
            is_external=True,
            show_anchor_icon=True,
            color="foreground",
        ),
        Link(
            "Disabled external",
            href="https://heroui.com",
            is_external=True,
            show_anchor_icon=True,
            is_disabled=True,
            color="primary",
        ),
        spacing=24,
    )


# ============================================================
# 7. 自定义 anchor icon（传 svg 名称）
# ============================================================
def _make_custom_anchor() -> QWidget:
    return _row(
        # 内置 svg 名（注：项目内已有的图标）
        Link(
            "Open external",
            show_anchor_icon=True,
            anchor_icon="icon-park-outline--share",
            color="primary",
        ),
        # 备用：用 heroicons 风格也行（若已存在）
        Link(
            "Help link",
            show_anchor_icon=True,
            anchor_icon="material-symbols--help-outline",
            color="success",
        ),
        spacing=24,
    )


# ============================================================
# 8. Disabled
# ============================================================
def _make_disabled() -> QWidget:
    return _row(
        Link("Disabled (no underline)", is_disabled=True),
        Link("Disabled (always)", is_disabled=True, underline="always"),
        Link(
            "Disabled block",
            is_disabled=True,
            is_block=True,
            color="primary",
        ),
        spacing=24,
    )


# ============================================================
# 9. disableAnimation
# ============================================================
def _make_no_anim() -> QWidget:
    return _row(
        _labeled("animated", Link("Hover me", color="primary")),
        _labeled(
            "no animation",
            Link("Hover me", color="primary", disable_animation=True),
        ),
        spacing=24,
    )


# ============================================================
# 10. 行内嵌入
# ============================================================
def _make_inline() -> QWidget:
    """将 Link 与正文 Body 同行，演示行内可读性。"""
    return _row(
        Body("HeroSideUI 灵感来自"),
        Link(
            "HeroUI v2",
            href="https://heroui.com",
            is_external=True,
            show_anchor_icon=True,
            underline="hover",
        ),
        Body("，欢迎在"),
        Link(
            "GitHub",
            href="https://github.com/LingChen-tsjmdlc/HeroSideUI",
            is_external=True,
            color="foreground",
            underline="hover",
        ),
        Body("提 issue。"),
        spacing=4,
    )


# ============================================================
# 11. 点击事件
# ============================================================
def _make_clicked_demo() -> QWidget:
    counter = Caption("clicked: 0")
    state = {"n": 0}

    def _on_click():
        state["n"] += 1
        counter.setText(f"clicked: {state['n']}")

    link = Link("Click me!", color="success", underline="hover")
    link.clicked.connect(_on_click)
    return _row(link, counter, spacing=20)


# ============================================================
# Demo 主类
# ============================================================
class LinkDemo(DemoBase):
    component_name = "Link"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        self.add_section(layout, "Default", _make_default(), spacing=16)

        layout.addWidget(self._section_title("Sizes"))
        layout.addWidget(_make_sizes())

        self.add_section(layout, "Colors", _make_colors(), spacing=20)

        layout.addWidget(self._section_title("Underline"))
        layout.addWidget(_make_underline())

        layout.addWidget(self._section_title("isBlock (hover 显示色块)"))
        layout.addWidget(_make_block())

        layout.addWidget(
            self._section_title("External + showAnchorIcon (点击在浏览器打开)")
        )
        layout.addWidget(_make_external())

        layout.addWidget(self._section_title("自定义 anchor_icon"))
        layout.addWidget(_make_custom_anchor())

        layout.addWidget(self._section_title("Disabled"))
        layout.addWidget(_make_disabled())

        layout.addWidget(self._section_title("disable_animation"))
        layout.addWidget(_make_no_anim())

        layout.addWidget(self._section_title("行内嵌入"))
        layout.addWidget(_make_inline())

        layout.addWidget(self._section_title("clicked 信号"))
        layout.addWidget(_make_clicked_demo())


if __name__ == "__main__":
    LinkDemo.run()
