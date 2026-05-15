"""hero_side_ui.animation.check_draw 单元测试

两部分：
    - paint_animated_check 纯绘制函数（QImage + QPainter 直接画 → 像素采样）
    - CheckDrawAnimation 驱动器（progress 0↔1 + delay_in / draw_out 行为）
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect, QObject
from PySide6.QtGui import QColor, QImage, QPainter

from hero_side_ui.animation import paint_animated_check, CheckDrawAnimation


def _make_canvas(size: int = 60) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("white"))
    return img


def _count_dark_pixels(img: QImage, threshold: int = 80) -> int:
    """统计明显非白的像素（笔画痕迹）。"""
    cnt = 0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.red() < threshold and c.green() < threshold and c.blue() < threshold:
                cnt += 1
    return cnt


# ============================================================
# paint_animated_check
# ============================================================


class TestPaintAnimatedCheckProgress:
    def test_progress_zero_paints_nothing(self, qtbot):
        img = _make_canvas()
        p = QPainter(img)
        paint_animated_check(p, img.rect(), QColor("black"), progress=0.0)
        p.end()
        assert _count_dark_pixels(img) == 0

    def test_progress_one_paints_full_check(self, qtbot):
        img = _make_canvas()
        p = QPainter(img)
        paint_animated_check(p, img.rect(), QColor("black"), progress=1.0)
        p.end()
        assert _count_dark_pixels(img) > 50  # 完整对勾应留足像素

    def test_progress_half_paints_partial(self, qtbot):
        img_half = _make_canvas()
        p = QPainter(img_half)
        paint_animated_check(p, img_half.rect(), QColor("black"), progress=0.5)
        p.end()
        half_count = _count_dark_pixels(img_half)

        img_full = _make_canvas()
        p2 = QPainter(img_full)
        paint_animated_check(p2, img_full.rect(), QColor("black"), progress=1.0)
        p2.end()
        full_count = _count_dark_pixels(img_full)

        assert 0 < half_count < full_count

    def test_clamps_progress_above_one(self, qtbot):
        """progress > 1 应被 clamp，效果 = progress=1.0。"""
        img = _make_canvas()
        p = QPainter(img)
        paint_animated_check(p, img.rect(), QColor("black"), progress=2.5)
        p.end()
        assert _count_dark_pixels(img) > 50

    def test_negative_progress_paints_nothing(self, qtbot):
        img = _make_canvas()
        p = QPainter(img)
        paint_animated_check(p, img.rect(), QColor("black"), progress=-0.5)
        p.end()
        assert _count_dark_pixels(img) == 0


class TestPaintAnimatedCheckRect:
    """rect 可以是 QRect / 元组，都能画出来。"""

    def test_accepts_tuple_rect(self, qtbot):
        img = _make_canvas()
        p = QPainter(img)
        paint_animated_check(p, (0, 0, 60, 60), QColor("black"), progress=1.0)
        p.end()
        assert _count_dark_pixels(img) > 0


# ============================================================
# CheckDrawAnimation 驱动器
# ============================================================


class _Holder(QObject):
    pass


class TestCheckDrawAnimationProgress:
    def test_initial_progress_zero(self, qtbot):
        h = _Holder()
        anim = CheckDrawAnimation(h)
        assert anim.progress == 0.0

    def test_play_true_animates_to_one(self, qtbot):
        h = _Holder()
        anim = CheckDrawAnimation(h, duration_in=80, delay_in=10)
        anim.play(True)
        qtbot.wait(150)
        assert anim.progress == pytest.approx(1.0, abs=0.01)

    def test_play_false_default_jumps_to_one(self, qtbot):
        """默认 draw_out=False：play(False) 立即把 progress 置 1（外部 fade 擦掉）。"""
        h = _Holder()
        anim = CheckDrawAnimation(h, duration_in=50, delay_in=0, draw_out=False)
        anim.play(True)
        qtbot.wait(120)
        assert anim.progress == pytest.approx(1.0, abs=0.01)
        anim.play(False)
        # 立即跳到 1.0（与"取消时整条对勾可见，让外部 fade 把它擦掉"语义一致）
        assert anim.progress == pytest.approx(1.0, abs=0.01)

    def test_play_false_with_draw_out_animates_down(self, qtbot):
        """draw_out=True：play(False) 播 1→0。"""
        h = _Holder()
        anim = CheckDrawAnimation(h, duration_in=50, duration_out=60,
                                  delay_in=0, draw_out=True)
        anim.play(True)
        qtbot.wait(120)
        assert anim.progress == pytest.approx(1.0, abs=0.01)
        anim.play(False)
        qtbot.wait(150)
        assert anim.progress == pytest.approx(0.0, abs=0.01)


class TestCheckDrawAnimationCallback:
    def test_on_step_called_for_each_progress_change(self, qtbot):
        h = _Holder()
        seen: list[float] = []
        anim = CheckDrawAnimation(h, on_step=seen.append, duration_in=60, delay_in=0)
        anim.play(True)
        qtbot.wait(120)
        # 至少推到 1.0
        assert seen
        assert seen[-1] == pytest.approx(1.0, abs=0.01)


class TestSetImmediate:
    def test_set_immediate_skips_animation(self, qtbot):
        h = _Holder()
        anim = CheckDrawAnimation(h, duration_in=500, delay_in=200)
        anim.set_immediate(True)
        assert anim.progress == 1.0
        anim.set_immediate(False)
        assert anim.progress == 0.0


class TestDelayCancellation:
    """delay_in 期间被 play(False) 取消应不再触发 in 动画。"""

    def test_play_false_during_delay_cancels(self, qtbot):
        h = _Holder()
        anim = CheckDrawAnimation(h, duration_in=200, delay_in=100, draw_out=False)
        anim.play(True)
        # 在 delay_in 期间立刻取消
        qtbot.wait(30)
        anim.play(False)
        # play(False) 默认把 progress 立即设为 1.0
        assert anim.progress == pytest.approx(1.0, abs=0.01)
        # 再等过原本 delay+duration 的时间，pending_target 已被改，
        # _start_in_anim 早 return，progress 不会再变化
        qtbot.wait(350)
        assert anim.progress == pytest.approx(1.0, abs=0.01)
