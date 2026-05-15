"""hero_side_ui.animation.underline_expand 单元测试

UnderlineBar: progress ∈ [0,1] 的下划线 widget。
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QImage

from hero_side_ui.animation import UnderlineBar


class TestExpandCollapse:
    def test_initial_progress_zero(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(200, 2)
        assert bar.progress == 0.0

    def test_expand_animates_to_one(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(200, 2)
        bar._anim.setDuration(60)
        bar.expand()
        qtbot.wait(120)
        assert bar.progress == pytest.approx(1.0, abs=0.01)

    def test_collapse_back_to_zero(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(200, 2)
        bar._anim.setDuration(60)
        bar.expand()
        qtbot.wait(120)
        bar.collapse()
        qtbot.wait(120)
        assert bar.progress == pytest.approx(0.0, abs=0.01)


class TestClampProgress:
    def test_set_progress_clamped_to_zero_one(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar._set_progress(1.5)
        assert bar.progress == 1.0
        bar._set_progress(-0.5)
        assert bar.progress == 0.0


class TestSetExpanded:
    def test_set_expanded_instant(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.set_expanded(True, animate=False)
        assert bar.progress == 1.0
        bar.set_expanded(False, animate=False)
        assert bar.progress == 0.0


class TestPaint:
    """paint 验证：progress=1 时画满 bar，progress=0 时不画。"""

    def test_paints_full_width_at_progress_one(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(50, 2)
        bar.set_expanded(True, animate=False)
        # render 到 QImage
        img = QImage(50, 2, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("white"))
        bar.render(img)
        # 中部至少有红色像素
        c = img.pixelColor(25, 0)
        assert c.red() > 200 and c.green() < 50 and c.blue() < 50

    def test_paints_nothing_at_progress_zero(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(50, 2)
        bar.set_expanded(False, animate=False)
        img = QImage(50, 2, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("white"))
        bar.render(img)
        # progress=0 时 paintEvent 直接 return，不画红色矩形
        # （widget 的默认背景仍会被 render 画上来，但绝不会是红色）
        for x in range(50):
            c = img.pixelColor(x, 0)
            is_red = c.red() > 200 and c.green() < 50 and c.blue() < 50
            assert not is_red, f"progress=0 时不应有红色像素，但 x={x} 是 {c.name()}"


class TestSetColor:
    def test_set_color_changes_rendered_color(self, qtbot):
        bar = UnderlineBar(color="#FF0000")
        qtbot.addWidget(bar)
        bar.resize(50, 2)
        bar.set_color("#00FF00")
        bar.set_expanded(True, animate=False)
        img = QImage(50, 2, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("white"))
        bar.render(img)
        c = img.pixelColor(25, 0)
        assert c.green() > 200 and c.red() < 50
