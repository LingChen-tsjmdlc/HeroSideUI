"""Toast 组件测试"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from hero_side_ui import (
    Toast,
    ToastRegion,
    add_toast,
    clear_toasts,
    close_toast,
    configure_toasts,
    get_toast_provider,
)
from hero_side_ui.components.toast._provider import _DEFAULTS
from hero_side_ui.components.toast._styling import build_toast_styles
from hero_side_ui.themes import HEROUI_COLORS, TOAST_SPEC

COLORS = ("default", "foreground", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("flat", "bordered", "solid")
RADII = ("none", "sm", "md", "lg", "full")
SHADOWS = ("none", "sm", "md", "lg")
PLACEMENTS = (
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)

_EXIT_WAIT = TOAST_SPEC["duration_exit"] + 120


@pytest.fixture
def host(qtbot) -> QWidget:
    """宿主窗口（不 show，避免测试期间弹真实窗口）。"""
    w = QWidget()
    qtbot.addWidget(w)
    w.resize(800, 600)
    return w


@pytest.fixture(autouse=True)
def _restore_defaults():
    saved = dict(_DEFAULTS)
    yield
    _DEFAULTS.clear()
    _DEFAULTS.update(saved)


def _cards(region: ToastRegion, count: int, **kw) -> list:
    """往 region 里塞 count 张卡片，默认不自动关闭。"""
    kw.setdefault("timeout", 0)
    cards = [Toast(title=f"t{i}", parent=region, **kw) for i in range(count)]
    for c in cards:
        region.add(c)
    return cards


def _seek_mid(anim, wait: int = 20) -> None:
    """把进行中的动画确定性地推进到中点，再采样中间态。

    固定 qWait(30) 采样依赖平台动画驱动的首帧时机：macOS 上首帧常在 30ms
    之后才到，采到的是尚未起步的起点值。seek 直接写属性值，不受墙钟影响。
    """
    assert anim is not None
    anim.setCurrentTime(anim.duration() // 2)
    QTest.qWait(wait)


class TestToastInit:
    """构造参数与默认值"""

    def test_defaults(self, qtbot, host):
        t = Toast(parent=host)
        qtbot.addWidget(t)
        assert t._color == "default"
        assert t._variant == "flat"
        assert t._radius == "md"
        assert t._shadow == "sm"
        assert t._placement == "bottom-right"
        assert t._timeout == TOAST_SPEC["timeout"]
        assert t._hide_icon is False
        assert t._hide_close is False
        assert t._show_progress is False

    def test_content_params(self, qtbot, host):
        t = Toast(title="标题", description="描述", parent=host)
        qtbot.addWidget(t)
        assert t._title_text == "标题"
        assert t._desc_label.text() == "描述"
        assert not t._desc_label.isHidden()

    @pytest.mark.parametrize("color", COLORS)
    def test_all_colors(self, qtbot, host, color):
        t = Toast(color=color, parent=host)
        qtbot.addWidget(t)
        assert t._color == color

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_all_variants(self, qtbot, host, variant):
        t = Toast(variant=variant, parent=host)
        qtbot.addWidget(t)
        assert t._variant == variant

    @pytest.mark.parametrize("radius", RADII)
    def test_all_radius(self, qtbot, host, radius):
        t = Toast(radius=radius, parent=host)
        qtbot.addWidget(t)
        assert t._radius == radius

    @pytest.mark.parametrize("shadow", SHADOWS)
    def test_all_shadow(self, qtbot, host, shadow):
        t = Toast(shadow=shadow, parent=host)
        qtbot.addWidget(t)
        assert t._shadow == shadow

    @pytest.mark.parametrize("placement", PLACEMENTS)
    def test_all_placements(self, qtbot, host, placement):
        t = Toast(placement=placement, parent=host)
        qtbot.addWidget(t)
        assert t._placement == placement

    def test_timeout_zero_means_never(self, qtbot, host):
        t = Toast(timeout=0, parent=host)
        qtbot.addWidget(t)
        assert t._timeout == 0
        t.start_countdown()
        assert t._timer.isActive() is False

    def test_size_hint_not_narrower_than_spec(self, qtbot, host):
        t = Toast(parent=host)
        qtbot.addWidget(t)
        assert t.sizeHint().width() >= TOAST_SPEC["width"]


class TestToastContent:
    """内容与附加区"""

    def test_empty_description_hidden(self, qtbot, host):
        t = Toast(title="仅标题", parent=host)
        qtbot.addWidget(t)
        assert t._desc_label.isHidden()

    def test_long_title_elided(self, qtbot, host):
        t = Toast(title="A" * 200, parent=host)
        qtbot.addWidget(t)
        assert t._title_label.text().endswith("…")
        assert len(t._title_label.text()) < 200

    def test_title_elide_fits_column(self, qtbot, host):
        """回归：可用宽漏减右侧 padding_x，elide 判定的宽比文本列实际宽
        12px，临界长度标题不截断、钻进关闭按钮区。渲染文本不得超出列宽。"""
        t = Toast(title="标题" * 60, parent=host)
        qtbot.addWidget(t)
        t.resize(384, 90)
        t.sync_height()
        t.layout().activate()
        fm = t._title_label.fontMetrics()
        assert fm.horizontalAdvance(t._title_label.text()) <= t._title_label.width()

    def test_text_avail_width_with_end_content(self, qtbot, host):
        """回归：end_content 占据文本列右侧，可用宽需一并扣除。"""
        from hero_side_ui import Button

        t = Toast(title="t", end_content=Button("撤销", size="sm"), parent=host)
        qtbot.addWidget(t)
        plain = Toast(title="t", parent=host)
        qtbot.addWidget(plain)
        assert t._text_avail_width() < plain._text_avail_width()

    def test_set_title_emits_content_changed(self, qtbot, host):
        t = Toast(title="旧", parent=host)
        qtbot.addWidget(t)
        with qtbot.waitSignal(t.content_changed, timeout=1000):
            t.set_title("新")
        assert t._title_text == "新"

    def test_set_description_shows_and_hides(self, qtbot, host):
        t = Toast(title="t", parent=host)
        qtbot.addWidget(t)
        with qtbot.waitSignal(t.content_changed, timeout=1000):
            t.set_description("后来加的")
        assert not t._desc_label.isHidden()
        t.set_description("")
        assert t._desc_label.isHidden()

    def test_end_content_set_and_replace(self, qtbot, host):
        t = Toast(title="t", parent=host)
        qtbot.addWidget(t)
        first = QLabel("first")
        t.set_end_content(first)
        assert t._end_content is first
        with qtbot.waitSignal(t.content_changed, timeout=1000):
            t.set_end_content(None)
        assert t._end_content is None

    def test_hide_icon_and_close_button(self, qtbot, host):
        t = Toast(title="t", hide_icon=True, hide_close_button=True, parent=host)
        qtbot.addWidget(t)
        assert t._icon_label.isHidden()
        assert t._close_btn.isHidden()
        t.set_hide_icon(False)
        t.set_hide_close_button(False)
        assert not t._icon_label.isHidden()
        assert not t._close_btn.isHidden()

    def test_loading_swaps_icon_for_spinner(self, qtbot, host):
        t = Toast(title="上传中", is_loading=True, timeout=5000, parent=host)
        qtbot.addWidget(t)
        assert not t._spinner.isHidden()
        assert t._icon_label.isHidden()
        t.start_countdown()
        assert t._timer.isActive() is False

        t.set_loading(False)
        assert t._spinner.isHidden()
        assert not t._icon_label.isHidden()
        assert t._timer.isActive()
        t.stop_countdown()

    def test_fade_snapshot_preserves_hidden_children(self, qtbot, host):
        """淡入淡出快照结束后，故意隐藏的子件（Spinner/icon）不能被恢复显示。"""
        t = Toast(title="上传中", is_loading=True, timeout=0, parent=host)
        qtbot.addWidget(t)
        t.resize(400, 80)
        t.set_opacity(0.5)
        assert t._fade_pixmap is not None
        t.set_opacity(1.0)
        assert t._fade_pixmap is None
        assert not t._spinner.isHidden()
        assert t._icon_label.isHidden()

    def test_fade_snapshot_padding_stays_transparent(self, qtbot, host):
        """回归：render 默认 DrawWindowBackground 会把窗口底色（亮=白/暗=黑）
        整矩形不透明地画进快照，四周阴影留白变成一圈实色边——半透明绘制时
        就是用户看到的「主题色矩形块（像边距一样）」。外圈必须保持透明。"""
        t = Toast(title="t", description="d", color="danger", variant="solid",
                  timeout=0, theme="light", parent=host)
        qtbot.addWidget(t)
        t.resize(400, 80)
        t.set_opacity(0.5)
        pm = t._fade_pixmap
        assert pm is not None
        img = pm.toImage()
        w, h = img.width(), img.height()
        assert w > 0 and h > 0
        for x in range(0, w, 5):
            for y in (0, 1, h - 2, h - 1):
                assert img.pixelColor(x, y).alpha() < 200, (x, y)
        for y in range(0, h, 5):
            for x in (0, 1, w - 2, w - 1):
                assert img.pixelColor(x, y).alpha() < 200, (x, y)


class TestToastCountdown:
    """倒计时与暂停"""

    def test_timeout_reached(self, qtbot, host):
        t = Toast(title="t", timeout=150, parent=host)
        qtbot.addWidget(t)
        with qtbot.waitSignal(t.timeout_reached, timeout=2000):
            t.start_countdown()

    def test_paused_stops_timer(self, qtbot, host):
        t = Toast(title="t", timeout=200, parent=host)
        qtbot.addWidget(t)
        t.start_countdown()
        t.set_paused(True)
        QTest.qWait(60)
        assert t._timer.isActive() is False
        assert t._paused is True

        with qtbot.waitSignal(t.timeout_reached, timeout=2000):
            t.set_paused(False)

    def test_never_timeout_no_signal(self, qtbot, host):
        t = Toast(title="t", timeout=0, parent=host)
        qtbot.addWidget(t)
        t.start_countdown()
        QTest.qWait(120)
        assert t._timer.isActive() is False
        assert t._progress == 0.0


class TestToastDrag:
    """拖拽阈值判定"""

    @pytest.mark.parametrize(
        "placement,dx,dy,expected",
        [
            ("bottom-right", 150, 0, True),
            ("bottom-right", 20, 0, False),
            ("top-right", 150, 0, True),
            ("top-left", -150, 0, True),
            ("top-left", 150, 0, False),
            ("bottom-center", 0, 40, True),
            ("bottom-center", 0, 5, False),
            ("top-center", 0, -40, True),
            ("top-center", 0, 40, False),
        ],
    )
    def test_should_close(self, qtbot, host, placement, dx, dy, expected):
        t = Toast(title="t", placement=placement, parent=host)
        qtbot.addWidget(t)
        assert t._should_close_by_drag(dx, dy) is expected


class TestToastStyling:
    """配色换算"""

    def test_flat_light_bg(self):
        s = build_toast_styles("flat", "warning", "light")
        assert s["base_bg"] == HEROUI_COLORS["warning"][50]

    def test_flat_dark_uses_swapped_shade(self):
        """HeroUI swapColorValues 是首尾反转：50 ↔ 900。"""
        s = build_toast_styles("flat", "warning", "dark")
        assert s["base_bg"] == HEROUI_COLORS["warning"][900]
        assert build_toast_styles("flat", "warning", "dark")["icon_color"] == HEROUI_COLORS["warning"][300]

    def test_bordered_uses_400_border(self):
        s = build_toast_styles("bordered", "danger", "light")
        assert s["border_color"] == HEROUI_COLORS["danger"][400]
        assert s["border_width"] == 1

    def test_solid_no_border(self):
        s = build_toast_styles("solid", "primary", "light")
        assert s["border_width"] == 0
        assert s["base_bg"] == HEROUI_COLORS["primary"][500]

    @pytest.mark.parametrize(
        "color,fg", [("primary", "#ffffff"), ("danger", "#ffffff"), ("warning", "#000000")]
    )
    def test_solid_text_contrast(self, color, fg):
        assert build_toast_styles("solid", color, "light")["title_color"] == fg

    def test_set_color_refreshes_styles(self, qtbot, host):
        # 显式锁亮色：测试进程的全局主题不确定
        t = Toast(title="t", theme="light", parent=host)
        qtbot.addWidget(t)
        t.set_color("danger")
        assert t._styles["base_bg"] == HEROUI_COLORS["danger"][50]
        t.set_variant("solid")
        assert t._styles["border_width"] == 0

    def test_set_theme_dark(self, qtbot, host):
        t = Toast(title="t", theme="dark", parent=host)
        qtbot.addWidget(t)
        assert t._theme == "dark"
        t.set_theme("light")
        assert t._theme == "light"


class TestToastRegion:
    """堆叠区编排"""

    def test_quota_hides_oldest(self, qtbot, host):
        """HeroUI 语义：超配额的旧卡隐藏但保留计时，不销毁。"""
        region = ToastRegion(parent=host, max_visible_toasts=2, disable_animation=True)
        qtbot.addWidget(region)
        cards = [Toast(title=f"t{i}", timeout=0, parent=region) for i in range(3)]
        for c in cards:
            region.add(c)
        # 三张卡都在，只有最新两张显示；最旧的隐藏、存活且在计时
        assert len(region._items) == 3
        assert cards[0].isHidden()
        assert not cards[1].isHidden()
        assert not cards[2].isHidden()
        assert region._find("toast-1") is not None
        assert region._active_items()[-1].card is cards[2]
        # 折叠态只有最新卡带关闭按钮（旧卡露边不带 X，且 X 会被最新卡挡住）
        assert cards[1]._close_btn.isHidden()
        assert not cards[2]._close_btn.isHidden()

    def test_hover_expands_hidden_cards(self, qtbot, host):
        region = ToastRegion(parent=host, max_visible_toasts=2, disable_animation=True)
        qtbot.addWidget(region)
        cards = [Toast(title=f"t{i}", timeout=0, parent=region) for i in range(3)]
        for c in cards:
            region.add(c)
        assert cards[0].isHidden()
        region._set_hovering(True)
        QTest.qWait(20)
        assert not cards[0].isHidden()
        region._set_hovering(False)
        QTest.qWait(20)
        assert cards[0].isHidden()
        for c in cards:
            c.stop_countdown()

    def test_dismiss_removes_card(self, qtbot, host):
        region = ToastRegion(parent=host, max_visible_toasts=2, disable_animation=True)
        qtbot.addWidget(region)
        _cards(region, 3)
        # t0 只是隐藏；dismiss 最新的 t2 后只剩 t0 / t1 且都显示
        region.dismiss(region.keys()[-1])
        QTest.qWait(_EXIT_WAIT)
        assert len(region._items) == 2
        assert all(not it.card.isHidden() for it in region._items)

    def test_collapsed_inset_grows_with_depth(self, qtbot, host):
        region = ToastRegion(parent=host, max_visible_toasts=3, disable_animation=True)
        qtbot.addWidget(region)
        cards = _cards(region, 3)
        step = TOAST_SPEC["collapsed_width_step"] / 2
        assert cards[0]._width_inset == pytest.approx(2 * step)
        assert cards[1]._width_inset == pytest.approx(step)
        assert cards[2]._width_inset == pytest.approx(0.0)

    def test_hover_expands_and_pauses(self, qtbot, host):
        region = ToastRegion(parent=host, disable_animation=True)
        qtbot.addWidget(region)
        cards = _cards(region, 3, timeout=30000)
        y_old = cards[0].y()
        region._set_hovering(True)
        QTest.qWait(20)
        assert cards[0].y() < y_old
        assert all(c._paused for c in cards)
        region._set_hovering(False)
        assert all(not c._paused for c in cards)
        for c in cards:
            c.stop_countdown()

    def test_enter_fade_not_stomped_by_relayout(self, qtbot, host):
        """回归：add() 内 _relayout 不得把入场淡入踩回 1.0（否则闪现一帧不透明）。"""
        region = ToastRegion(parent=host)  # 动画开启
        qtbot.addWidget(region)
        card = Toast(title="t", timeout=0, parent=host)
        region.add(card)
        # add 刚返回、事件循环尚未跑动画帧：透明度必须仍处于淡入起点附近
        assert card.paint_opacity < 0.5
        item = region._active_items()[-1]
        assert item.entering
        QTest.qWait(400)
        assert not item.entering
        assert card.paint_opacity == pytest.approx(1.0, abs=0.05)
        card.stop_countdown()

    def test_close_button_matches_heroui_spec(self, qtbot, host):
        """回归：X 按钮 24px、中心距内容区右缘/顶缘 12px（右缘与顶缘平齐）。"""
        card = Toast(title="t", parent=host)
        assert card._close_btn.width() == TOAST_SPEC["close"] == 24
        rect = card._content_rect()
        g = card._close_btn.geometry()
        assert g.right() - rect.right() == pytest.approx(0, abs=1)
        assert rect.top() - g.top() == pytest.approx(0, abs=1)

    def test_no_toplevel_flash_during_construction(self, qtbot, host):
        """回归：desc_label 曾在挂父前 setVisible(True)，无父 widget 被
        Windows 当成顶层窗口闪出一帧带标题栏的原生窗口。"""
        before = set(QApplication.topLevelWidgets())
        card = Toast(title="t", description="带描述的卡片", parent=host)
        qtbot.addWidget(card)
        strangers = [w for w in QApplication.topLevelWidgets()
                     if w not in before and w.isWindow()]
        assert strangers == []

    def test_clear_removes_all(self, qtbot, host):
        region = ToastRegion(parent=host, disable_animation=True)
        qtbot.addWidget(region)
        _cards(region, 2)
        region.clear()
        QTest.qWait(_EXIT_WAIT)
        assert region.keys() == []

    def test_expanded_cards_have_gap(self, qtbot, host):
        """回归：stack_gap 曾只加一次、被相邻卡差值精确抵消，展开态卡片
        零间距贴合（对齐 HeroUI 每卡 mb-1 语义，应为逐卡 4px 间隔）。"""
        region = ToastRegion(parent=host, disable_animation=True)
        qtbot.addWidget(region)
        cards = _cards(region, 3)
        region._expanded = True
        region._relayout(False)
        gap_spec = TOAST_SPEC["stack_gap"]
        for older, newer in zip(cards, cards[1:]):
            # body 底 = top + height - pad（Qt 的 bottom() 自带 -1，须补偿）
            body_bot_old = older.geometry().top() + older.height() - older.pad_bottom
            body_top_new = newer.geometry().top() + newer.pad_top
            assert body_top_new - body_bot_old == gap_spec

    def test_revealed_cards_fade_in_on_expand(self, qtbot, host):
        """回归：hover 展开时超配额被揭示的卡曾瞬间满透明度出现（无动画）。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        cards = _cards(region, 5)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)  # 入场动画结束
        assert sum(c.isHidden() for c in cards) == 2
        region._expanded = True
        region._relayout(True)
        # 被揭示的两张应从透明淡入，原可见三张保持不透明
        assert all(cards[i].paint_opacity < 0.6 for i in range(2))
        assert all(cards[i].paint_opacity > 0.9 for i in range(2, 5))
        QTest.qWait(TOAST_SPEC["duration_enter"] + 200)
        assert all(c.paint_opacity > 0.95 for c in cards)
        expanded_top = cards[0].geometry().top()

        # 第二次展开也应有滑动+淡入（折叠淡出的卡现在停在折叠堆叠位，
        # 二次展开的起点天然 != 展开位，滑动真实发生）
        region._set_hovering(False)
        QTest.qWait(TOAST_SPEC["duration_move"] + 150)
        assert cards[0].isHidden()
        folded_top = cards[0].geometry().top()
        region._set_hovering(True)
        assert cards[0].paint_opacity < 0.6
        _seek_mid(region._items[0].geo_anim)
        # 中点处必须严格落在折叠位与展开位之间（滑动真实发生）
        assert expanded_top < cards[0].geometry().top() < folded_top
        QTest.qWait(TOAST_SPEC["duration_move"] + 150)
        assert cards[0].geometry().top() == expanded_top
        assert cards[0].paint_opacity > 0.95

    def test_collapse_fades_out_hidden_cards(self, qtbot, host):
        """回归：折叠时超配额被藏的卡曾瞬间消失（突然回去）。应先淡出
        再 hide，与位移动画同步收尾。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        cards = _cards(region, 5)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        region._set_hovering(True)
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        assert all(not c.isHidden() and c.paint_opacity > 0.95 for c in cards)
        region._set_hovering(False)
        _seek_mid(region._items[0].fade_anim)
        # 采样窗口内：被藏的卡仍在淡出（未隐藏、透明度未回到满值）
        assert not cards[0].isHidden()
        assert 0.0 < cards[0].paint_opacity < 1.0
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        assert cards[0].isHidden()
        assert not cards[2].isHidden()  # 停留卡不受影响

    def test_collapse_slides_hidden_card_to_folded_spot(self, qtbot, host):
        """回归：折叠退出时超配额卡曾只原地淡出，不跟着堆叠一起下浮。
        应同步滑回折叠堆叠位（与展开揭示的起飞点对称）。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        cards = _cards(region, 5)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        region._set_hovering(True)
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        expanded_top = cards[0].geometry().top()
        region._set_hovering(False)
        QTest.qWait(TOAST_SPEC["duration_move"] // 2)
        # 淡出中途：位置已向折叠位移动（bottom-right 语义为向下浮）
        assert not cards[0].isHidden()
        assert cards[0].geometry().top() > expanded_top
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        assert cards[0].isHidden()
        # 落点即下次展开的起飞点（_folded_y 共用）
        assert cards[0].y() == region._folded_y(0, 5, cards[0])

    def test_collapse_tweens_width_inset(self, qtbot, host):
        """回归：折叠时停留卡的内缩量曾瞬跳 0→8，位置在滑而宽度瞬变
        （割裂感）。内缩量应随位移同步渐变。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        cards = _cards(region, 5)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        region._set_hovering(True)
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        assert cards[2]._width_inset == pytest.approx(0.0, abs=0.5)
        region._set_hovering(False)
        _seek_mid(cards[2]._inset_anim)
        mid = cards[2]._width_inset
        assert 0.0 < mid < TOAST_SPEC["collapsed_width_step"]
        QTest.qWait(TOAST_SPEC["duration_move"] + 200)
        assert cards[2]._width_inset == pytest.approx(TOAST_SPEC["collapsed_width_step"])

    def test_drag_close_from_text_area(self, qtbot, host):
        """回归：title/desc 曾因 Text 文字选择吃掉 press，拖拽只对边缘
        12px 的阴影留白生效；文字区应能冒泡触发整卡拖拽甩出。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        card = Toast(title="drag me", description="d", timeout=0, parent=region)
        region.add(card)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        # press 落在 title 文字上（子件），依赖冒泡到卡片驱动拖拽
        QTest.mousePress(card._title_label, Qt.MouseButton.LeftButton)
        for i in range(1, 6):
            QTest.mouseMove(card, QPoint(card.width() // 2 + 30 * i, 30))
            QTest.qWait(20)
        QTest.mouseRelease(
            card, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(card.width() // 2 + 150, 30),
        )
        QTest.qWait(_EXIT_WAIT)
        assert region.keys() == []

    def test_rapid_add_finalizes_entering_cards(self, qtbot, host):
        """回归：连点时上一张入场中的卡曾保持半透明，在新卡滑上来遮住
        之前的 300ms 里把半透明内容暴露在堆叠缝隙中（白/黑色矩形块）。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        c2 = Toast(title="first", timeout=0, parent=region)
        region.add(c2)
        QTest.qWait(60)
        item2 = region._find(region.keys()[-1])
        assert item2.entering  # 入场进行中（半透明）
        c3 = Toast(title="second", timeout=0, parent=region)
        region.add(c3)
        # 上一张被立即定格为实色，不再半透明暴露
        assert not item2.entering
        assert c2.paint_opacity == pytest.approx(1.0, abs=0.05)
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        assert c3.paint_opacity == pytest.approx(1.0, abs=0.05)

    def test_snapshot_takes_over_child_visibility(self, qtbot, host):
        """回归：入场快照期间 set_folded 曾把关闭按钮以全不透明提前
        show 出来，叠在半透明快照上（入场卡右下角出现实心 X）。"""
        region = ToastRegion(parent=host)
        qtbot.addWidget(region)
        card = Toast(title="t", timeout=0, parent=region)
        region.add(card)
        # 入场动画进行中：快照接管子件显隐，folded 变更只记意图
        card.set_folded(False)
        assert card._close_btn.isHidden()
        QTest.qWait(TOAST_SPEC["duration_enter"] + 150)
        assert not card._close_btn.isHidden()

    @pytest.mark.parametrize("placement", PLACEMENTS)
    def test_placement_positions(self, qtbot, host, placement):
        region = ToastRegion(parent=host, placement=placement, disable_animation=True)
        qtbot.addWidget(region)
        cards = _cards(region, 1)
        QTest.qWait(20)
        card = cards[0]
        if "left" in placement:
            assert card.x() < host.width() // 2
        elif "right" in placement:
            assert card.x() + card.width() > host.width() // 2
        if placement.startswith("top"):
            assert card.y() < host.height() // 2
        else:
            assert card.y() + card.height() > host.height() // 2

    def test_set_placement_moves_existing(self, qtbot, host):
        region = ToastRegion(parent=host, placement="bottom-right", disable_animation=True)
        qtbot.addWidget(region)
        cards = _cards(region, 1)
        QTest.qWait(20)
        bottom_y = cards[0].y()
        region.set_placement("top-right")
        QTest.qWait(20)
        assert cards[0].y() < bottom_y

    def test_card_by_key(self, qtbot, host):
        region = ToastRegion(parent=host, disable_animation=True)
        qtbot.addWidget(region)
        (card,) = _cards(region, 1)
        key = region.keys()[0]
        assert region.card(key) is card
        assert region.card("nope") is None


class TestToastProvider:
    """provider 与全局函数"""

    def test_provider_per_window(self, qtbot, host):
        p1 = get_toast_provider(host)
        p2 = get_toast_provider(host)
        assert p1 is p2
        assert p1.region.parent() is host

    def test_add_close_clear(self, qtbot, host):
        key = add_toast(title="t", timeout=0, parent=host)
        provider = get_toast_provider(host)
        assert key in provider.region.keys()
        assert provider.card(key) is not None

        close_toast(key)
        QTest.qWait(_EXIT_WAIT)
        assert key not in provider.region.keys()

        add_toast(title="a", timeout=0, parent=host)
        clear_toasts(host)
        QTest.qWait(_EXIT_WAIT)
        assert provider.region.keys() == []

    def test_placement_override(self, qtbot, host):
        add_toast(title="t", timeout=0, placement="top-left", parent=host)
        assert get_toast_provider(host).placement == "top-left"

    def test_configure_defaults(self, qtbot, host):
        configure_toasts(placement="top-center", max_visible_toasts=5)
        provider = get_toast_provider(host)
        assert provider.placement == "top-center"
        assert provider.region._max_visible == 5
