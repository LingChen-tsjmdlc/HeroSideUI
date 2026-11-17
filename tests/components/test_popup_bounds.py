"""弹出层与宿主窗口：边界辅助函数、超出窗口时的裁剪，以及点击外部关闭（防止同时开两个）。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel, QWidget

from hero_side_ui import Autocomplete, Button, Dropdown, Popover, Select, Tooltip
from hero_side_ui._shared.overlays import bounds
from hero_side_ui._shared.overlays.hit_test import HitThroughMixin


def _pt(p) -> tuple:
    """QPoint 转元组，便于打印。"""
    return (p.x(), p.y())


def _screens() -> list:
    """所有屏幕的 (名称, 全区, 可用区, 缩放)。"""
    return [
        (s.name(), s.geometry().getRect(), s.availableGeometry().getRect(), s.devicePixelRatio())
        for s in QGuiApplication.screens()
    ]


def _host(qtbot, w: int = 520, h: int = 420) -> QWidget:
    """比屏幕小的宿主窗口：弹层可以越过它的边缘但仍在屏幕内。"""
    host = QWidget()
    host.setGeometry(60, 40, w, h)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host


def _put(host: QWidget, widget: QWidget, x: int, y: int) -> QWidget:
    widget.setParent(host)
    widget.move(x, y)
    widget.show()
    return widget


def _click(qtbot, host: QWidget, widget: QWidget) -> None:
    """走窗口句柄的真实点击（命中链与全局事件过滤器都会经过），并等淡入淡出走完。"""
    pt = widget.mapTo(host, QPoint(widget.width() // 2, widget.height() // 2))
    QTest.mouseClick(
        host.windowHandle(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt
    )
    qtbot.wait(450)


# ============================================================
# 边界辅助函数
# ============================================================
class TestHostBounds:
    def test_host_rect_is_the_client_area(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 100, 60)
        assert bounds.host_rect(btn) == QRect(host.mapToGlobal(QPoint(0, 0)), host.size())

    def test_host_rect_is_none_when_the_window_is_not_shown(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        btn = Button("x")
        btn.setParent(w)
        assert bounds.host_rect(btn) is None

    def test_space_below_and_above_are_measured_to_the_window_edges(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 100, 60)
        rect = bounds.host_rect(btn)
        top = btn.mapToGlobal(QPoint(0, 0)).y()
        assert bounds.space_below(btn) == rect.bottom() - (top + btn.height())
        assert bounds.space_above(btn) == top - rect.top()

    def test_space_falls_back_to_the_screen_without_a_visible_window(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        btn = Button("x")
        btn.setParent(w)
        assert bounds.space_below(btn) > 0

    def test_popup_inside_a_popup_resolves_to_the_application_window(self, qtbot):
        host = _host(qtbot)
        outer_btn = _put(host, Button("outer"), 120, 120)
        inner_btn = Button("inner")
        outer = Popover(placement="bottom")
        qtbot.addWidget(outer)
        outer.set_content(inner_btn)
        outer.attach(outer_btn)
        outer.open(outer_btn)
        qtbot.wait(50)
        assert bounds.host_window(inner_btn) is host
        outer.close()


# ============================================================
# 超出宿主窗口的部分被裁掉
# ============================================================
class TestClipToHost:
    def test_popover_below_the_window_edge_is_masked_to_the_window(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("low"), 200, 380)
        pop = Popover(placement="bottom")
        qtbot.addWidget(pop)
        pop.set_content(QLabel("x\n" * 8 + "tall"))
        pop.attach(btn)
        pop.open(btn)
        qtbot.wait(400)
        window = bounds.host_rect(btn)
        assert pop.geometry().bottom() > window.bottom()  # 窗口本身确实越界了
        assert not pop.mask().isEmpty()
        visible_bottom = pop.mapToGlobal(pop.mask().boundingRect().bottomLeft()).y()
        assert visible_bottom <= window.bottom()
        pop.close()

    def test_popover_inside_the_window_has_no_mask(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("top"), 200, 40)
        pop = Popover(placement="bottom")
        qtbot.addWidget(pop)
        pop.set_content(QLabel("hi"))
        pop.attach(btn)
        pop.open(btn)
        qtbot.wait(400)
        assert pop.mask().isEmpty()
        pop.close()

    def test_clip_to_host_without_an_anchor_clears_the_mask(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 100, 60)
        popup = QWidget()
        qtbot.addWidget(popup)
        popup.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        origin = host.mapToGlobal(QPoint(10, 380))
        popup.setGeometry(origin.x(), origin.y(), 100, 100)
        popup.show()
        bounds.clip_to_host(popup, btn)
        assert not popup.mask().isEmpty()
        bounds.clip_to_host(popup, None)
        assert popup.mask().isEmpty()


# ============================================================
# 翻转：下面放不下翻到上面，两边都放不下才用切断兜底
# ============================================================
ITEMS = [(f"k{i}", f"Item {i}") for i in range(30)]


def _inside(anchor: QWidget, pop) -> bool:
    return bounds.popup_area(anchor).contains(pop._body_global())


class TestFlipInsideWindow:
    def _open_popover(self, qtbot, host, btn, content, **kw):
        pop = Popover(**kw)
        qtbot.addWidget(pop)
        pop.set_content(content)
        pop.attach(btn)
        pop.open(btn)
        qtbot.wait(400)
        return pop

    def test_overflow_counts_every_side(self):
        area = QRect(0, 0, 100, 100)
        assert bounds.overflow(QRect(10, 10, 20, 20), area) == 0
        assert bounds.overflow(QRect(-5, -3, 20, 20), area) == 8
        assert bounds.overflow(QRect(90, 90, 20, 20), area) == 20

    def test_popover_flips_up_near_the_window_bottom(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 200, 350)
        pop = self._open_popover(
            qtbot, host, btn, QLabel("x\n" * 6 + "content"), placement="bottom"
        )
        assert pop._actual_placement.startswith("top")
        assert _inside(btn, pop)
        pop.close()

    def test_popover_does_not_flip_when_it_fits(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 200, 60)
        pop = self._open_popover(qtbot, host, btn, QLabel("hello"), placement="bottom")
        assert pop._actual_placement == "bottom"
        pop.close()

    def test_top_placement_flips_down_near_the_window_top(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 200, 4)
        pop = self._open_popover(qtbot, host, btn, QLabel("x\n" * 3 + "c"), placement="top")
        assert pop._actual_placement.startswith("bottom")
        assert _inside(btn, pop)
        pop.close()

    def test_when_neither_side_fits_the_part_outside_the_window_is_cut(self, qtbot):
        host = _host(qtbot, w=420, h=160)
        btn = _put(host, Button("s"), 150, 60)
        pop = self._open_popover(qtbot, host, btn, QLabel("t\n" * 24), placement="bottom")
        window = bounds.host_rect(btn)
        assert not pop.mask().isEmpty()
        assert pop.mapToGlobal(pop.mask().boundingRect().bottomLeft()).y() <= window.bottom()
        pop.close()

    def test_flip_disabled_keeps_the_placement(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("a"), 200, 350)
        pop = self._open_popover(
            qtbot, host, btn, QLabel("x\n" * 6), placement="bottom", allow_flip=False
        )
        assert pop._actual_placement == "bottom"
        pop.close()

    @pytest.mark.parametrize("factory", [Select, Autocomplete])
    @pytest.mark.parametrize("y,expect", [(120, "bottom"), (345, "top")])
    def test_select_like_prefers_below_and_flips_only_when_needed(self, qtbot, factory, y, expect):
        host = _host(qtbot)
        w = factory(items=ITEMS)
        _put(host, w, 150, y)
        w.open()
        qtbot.wait(450)
        pop = w._popover
        trigger = QRect(w.mapToGlobal(QPoint(0, 0)), w.size())
        assert pop._actual_placement.startswith(expect)
        assert _inside(w, pop)
        assert not pop._body_global().intersects(trigger)
        w.close()

    @pytest.mark.parametrize("y,expect", [(100, "bottom"), (345, "top"), (380, "top")])
    def test_dropdown_flips_and_stays_complete(self, qtbot, y, expect):
        host = _host(qtbot)
        items = ITEMS if y != 380 else [("a", "Item A"), ("b", "Item B"), ("c", "Item C")]
        dd = Dropdown(trigger=Button("menu"), items=[{"key": k, "label": v} for k, v in items])
        _put(host, dd, 150, y)
        dd.open()
        qtbot.wait(450)
        pop = dd._popover
        trigger = QRect(dd._trigger.mapToGlobal(QPoint(0, 0)), dd._trigger.size())
        body = pop._body_global()
        # 失败时带上定位用到的全部区域，平台差异（窗口被系统挪动）靠这些数字定位
        info = (
            f"body={body.getRect()} trigger={trigger.getRect()} "
            f"screen={bounds.screen_rect(dd._trigger).getRect()} "
            f"host={(bounds.host_rect(dd._trigger) or QRect()).getRect()} "
            f"area={bounds.popup_area(dd._trigger).getRect()} "
            f"above={bounds.space_above(dd._trigger)} below={bounds.space_below(dd._trigger)} "
            f"room={dd._room_for_menu()} cap={dd._menu_height_cap(True)} "
            f"scroll_h={dd._scroll.height()} placement={pop._actual_placement} "
            f"pop_geo={pop.geometry().getRect()} pop_frame={pop.frameGeometry().getRect()} "
            f"calc_pos={_pt(pop._calc_position(dd._trigger))} "
            f"margins={pop._frame_margins()} body_local={pop._body_local().getRect()} "
            f"host_frame={host.frameGeometry().getRect()} "
            f"screens={_screens()} platform={QGuiApplication.platformName()}"
        )
        assert pop._actual_placement.startswith(expect), info
        assert _inside(dd._trigger, pop), info
        assert not body.intersects(trigger), info
        dd.close()

    def test_tooltip_flips_down_near_the_window_top(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("tip"), 200, 4)
        tt = Tooltip(content="tooltip text here", placement="top")
        qtbot.addWidget(tt)
        tt.attach(btn)
        tt.open()
        qtbot.wait(300)
        assert tt._actual_placement == "bottom"
        assert bounds.popup_area(btn).contains(tt._body_global())
        tt.close()


# ============================================================
# 留白穿透需要的 _body_global
# ============================================================
class TestBodyGlobal:
    def test_popover_and_tooltip_implement_it(self):
        # HitThroughMixin 里那份是占位实现（直接抛 NotImplementedError），不能被它盖住
        assert Popover._body_global is not HitThroughMixin._body_global
        assert Tooltip._body_global is not HitThroughMixin._body_global

    def test_popover_body_excludes_the_shadow_and_arrow_margins(self, qtbot):
        host = _host(qtbot)
        btn = _put(host, Button("top"), 200, 40)
        pop = Popover(placement="bottom")
        qtbot.addWidget(pop)
        pop.set_content(QLabel("body"))
        pop.attach(btn)
        pop.open(btn)
        qtbot.wait(400)
        ml, mt, mr, mb = pop.frame_margins()
        g = pop.geometry()
        assert pop._body_global() == QRect(
            g.x() + ml, g.y() + mt, g.width() - ml - mr, g.height() - mt - mb
        )
        pop.close()


# ============================================================
# 点击外部关闭：不能同时开两个（回归：_body_global 缺失时外部点击会抛异常）
# ============================================================
class TestOutsideClick:
    def _two_dropdowns(self, qtbot):
        host = _host(qtbot, w=700)
        items = ["Item A", "Item B", "Item C"]
        a = Dropdown(trigger=Button("a"), items=items, placement="bottom-start")
        b = Dropdown(trigger=Button("b"), items=items, placement="bottom-start")
        _put(host, a, 40, 60)
        _put(host, b, 300, 60)
        qtbot.wait(30)
        return host, a, b

    def test_opening_the_second_closes_the_first(self, qtbot):
        host, a, b = self._two_dropdowns(qtbot)
        _click(qtbot, host, a._trigger)
        assert a.is_open() and not b.is_open()
        _click(qtbot, host, b._trigger)
        assert b.is_open() and not a.is_open()
        _click(qtbot, host, a._trigger)
        assert a.is_open() and not b.is_open()

    def test_clicking_blank_space_closes_everything(self, qtbot):
        host, a, b = self._two_dropdowns(qtbot)
        _click(qtbot, host, a._trigger)
        QTest.mouseClick(
            host.windowHandle(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(500, 380),
        )
        qtbot.wait(450)
        assert not a.is_open() and not b.is_open()

    def test_rapid_alternating_clicks_never_leave_two_open(self, qtbot):
        host, a, b = self._two_dropdowns(qtbot)
        for i in range(4):
            _click(qtbot, host, a._trigger if i % 2 == 0 else b._trigger)
            assert int(a.is_open()) + int(b.is_open()) <= 1


class TestScreenClipsAvailableSpace:
    """回归：窗口超出屏幕可用区时，菜单高度上限要按"窗口 ∩ 屏幕"算（macOS 菜单栏下的窗口）。"""

    def test_menu_stays_inside_the_screen_when_the_window_top_is_off_screen(
        self, qtbot, monkeypatch
    ):
        host = _host(qtbot)
        real = bounds.screen_rect
        # 屏幕可用区从 y=79 开始，比宿主窗口（y=40）低：窗口上沿 39px 在可用区之外
        monkeypatch.setattr(
            bounds,
            "screen_rect",
            lambda w: QRect(real(w).left(), 79, real(w).width(), real(w).height() - 79),
        )
        dd = Dropdown(trigger=Button("menu"), items=[{"key": k, "label": v} for k, v in ITEMS])
        _put(host, dd, 150, 345)
        dd.open()
        qtbot.wait(450)
        body = dd._popover._body_global()
        trigger = QRect(dd._trigger.mapToGlobal(QPoint(0, 0)), dd._trigger.size())
        assert body.top() >= 79
        assert not body.intersects(trigger)
        dd.close()

    def test_space_helpers_use_the_same_area_as_the_popup(self, qtbot, monkeypatch):
        host = _host(qtbot)
        btn = _put(host, Button("b"), 150, 100)
        real = bounds.screen_rect
        monkeypatch.setattr(
            bounds,
            "screen_rect",
            lambda w: QRect(real(w).left(), 79, real(w).width(), real(w).height() - 79),
        )
        area = bounds.popup_area(btn)
        top = btn.mapToGlobal(QPoint(0, 0)).y()
        assert bounds.space_above(btn) == top - area.top()
        assert bounds.space_below(btn) == area.bottom() - (top + btn.height())


class TestPopupOutlivesItsOwner:
    """回归：浮层是顶层窗口，比控件活得久；控件销毁后它关闭，不能再回调到已销毁的控件上。"""

    @pytest.mark.parametrize(
        "make",
        [
            lambda: Dropdown(trigger=Button("m"), items=["a", "b"]),
            lambda: Select(items=[("a", "A"), ("b", "B")], label="s"),
            lambda: Autocomplete(items=[("a", "A")], label="a"),
        ],
        ids=["Dropdown", "Select", "Autocomplete"],
    )
    def test_closing_after_the_owner_is_destroyed_raises_nothing(self, qtbot, make):
        import shiboken6

        host = _host(qtbot)
        w = make()
        _put(host, w, 40, 40)
        w.open()
        qtbot.wait(300)
        popover = w._popover
        with qtbot.capture_exceptions() as exceptions:
            shiboken6.delete(w)
            popover.closed.emit()
            qtbot.wait(30)
        assert exceptions == []


class TestWindowMarginsStayOnScreen:
    """回归：系统约束的是整个弹层窗口（含阴影边距），按可见主体算会被整体挪走并压住触发器。"""

    SCREEN = QRect(0, 31, 1024, 677)  # macOS 虚拟屏幕可用区（菜单栏占掉上方 31px）

    @pytest.fixture
    def clamped(self, monkeypatch):
        """固定屏幕可用区，并模拟 macOS：系统把弹层窗口整体夹进该区域。"""
        screen = self.SCREEN
        monkeypatch.setattr(bounds, "screen_rect", lambda w: QRect(screen))
        monkeypatch.setattr(bounds, "system_confines_windows", lambda: True)
        real_move = Popover.move

        def clamped_move(self, *args):
            p = args[0] if isinstance(args[0], QPoint) else QPoint(args[0], args[1])
            x = min(max(p.x(), screen.left()), screen.right() + 1 - self.width())
            y = min(max(p.y(), screen.top()), screen.bottom() + 1 - self.height())
            real_move(self, QPoint(x, y))

        monkeypatch.setattr(Popover, "move", clamped_move)

    @pytest.mark.parametrize("y", [100, 345, 380])
    def test_dropdown_never_covers_its_trigger(self, qtbot, clamped, y):
        host = QWidget()
        host.setGeometry(60, 59, 520, 420)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        items = ITEMS if y != 380 else ITEMS[:3]
        dd = Dropdown(trigger=Button("menu"), items=[{"key": k, "label": v} for k, v in items])
        _put(host, dd, 150, y)
        dd.open()
        qtbot.wait(450)
        pop = dd._popover
        trigger = QRect(dd._trigger.mapToGlobal(QPoint(0, 0)), dd._trigger.size())
        assert self.SCREEN.contains(pop.geometry())
        assert not pop._body_global().intersects(trigger)
        dd.close()

    def test_platforms_that_do_not_clamp_keep_the_full_screen(self, qtbot, monkeypatch):
        """Windows / 离屏不会挪动窗口，不能白白收缩可用区。"""
        monkeypatch.setattr(bounds, "screen_rect", lambda w: QRect(self.SCREEN))
        monkeypatch.setattr(bounds, "system_confines_windows", lambda: False)
        host = QWidget()
        host.setGeometry(0, 0, 400, 400)
        qtbot.addWidget(host)
        btn = _put(host, Button("b"), 100, 100)
        host.show()
        qtbot.waitExposed(host)
        assert bounds.popup_area(btn, (48, 48, 48, 48)) == bounds.popup_area(btn)
        assert bounds.space_above(btn, (0, 48, 0, 0)) == bounds.space_above(btn)
        assert bounds.space_below(btn, (0, 0, 0, 48)) == bounds.space_below(btn)

    def test_area_shrinks_the_screen_side_by_the_window_margins(self, qtbot, clamped):
        host = QWidget()
        host.setGeometry(0, 0, 400, 400)
        qtbot.addWidget(host)
        btn = _put(host, Button("b"), 100, 100)
        host.show()
        qtbot.waitExposed(host)
        plain = bounds.popup_area(btn)
        shrunk = bounds.popup_area(btn, (10, 20, 30, 40))
        assert shrunk.top() >= plain.top() and shrunk.bottom() <= plain.bottom()
        assert bounds.space_above(btn, (0, 20, 0, 0)) <= bounds.space_above(btn)
        assert bounds.space_below(btn, (0, 0, 0, 40)) <= bounds.space_below(btn)
