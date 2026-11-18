"""Dialog 单元测试：结果码与信号、按钮角色、自动高度、定位、关闭路径、一行调用。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QKeyEvent

from hero_side_ui import Button, Dialog, Window
from hero_side_ui.components.dialog._footer import parse_item, parse_role
from hero_side_ui.components.dialog._placement import clamp_point, place, split_placement
from tests._waits import flush, until


def _parent(qtbot) -> Window:
    w = Window(width=900, height=600, theme="light")
    qtbot.addWidget(w)
    w.move(100, 100)
    w.show()
    flush(qtbot)
    return w


def _dialog(qtbot, parent=None, **kw) -> Dialog:
    kw.setdefault("theme", "light")
    d = Dialog(parent=parent, **kw)
    qtbot.addWidget(d)
    return d


def _later(fn):
    """事件循环起来后立刻执行 fn（给 exec() 里的操作用，不是定时等待）。"""
    QTimer.singleShot(0, fn)


def _key(dlg: Dialog, key):
    dlg.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))


class TestPlacementMath:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("center", ("center", "middle")),
            ("top", ("center", "top")),
            ("left", ("left", "middle")),
            ("bottom-right", ("right", "bottom")),
            ("top-left", ("left", "top")),
        ],
    )
    def test_split(self, name, expected):
        assert split_placement(name) == expected

    def test_center_top_left_bottom_right(self):
        ref, avail, size = QRect(100, 100, 800, 600), QRect(0, 0, 1920, 1040), QSize(400, 200)
        assert place(ref, size, "center", (0, 0), avail) == QPoint(300, 300)
        assert place(ref, size, "top-left", (0, 0), avail) == QPoint(100, 100)
        assert place(ref, size, "bottom-right", (0, 0), avail) == QPoint(500, 500)

    def test_offset_applied_then_clamped(self):
        ref, avail, size = QRect(0, 0, 800, 600), QRect(0, 0, 800, 600), QSize(400, 200)
        assert place(ref, size, "center", (50, -20), avail) == QPoint(250, 180)
        assert place(ref, size, "bottom-right", (500, 500), avail) == QPoint(400, 400)

    def test_larger_than_screen_sticks_top_left(self):
        assert clamp_point(QPoint(50, 50), QSize(2000, 2000), QRect(0, 0, 800, 600)) == QPoint(0, 0)


class TestRoles:
    def test_named_and_int_roles(self):
        assert parse_role("accept") == 1
        assert parse_role("reject") == 0
        assert parse_role("none") is None
        assert parse_role(-1) == -1

    @pytest.mark.parametrize("bad", [True, False, "ok", 1.5, None])
    def test_bad_roles_raise(self, bad):
        with pytest.raises(ValueError):
            parse_role(bad)

    def test_item_shapes(self, qtbot):
        btn = Button("x")
        qtbot.addWidget(btn)
        assert parse_item(btn) == (btn, None, None)
        assert parse_item(("跳过", -1)) == ("跳过", -1, None)
        assert parse_item(("好", "accept", {"k": 1})) == ("好", 1, {"k": 1})
        with pytest.raises(ValueError):
            parse_item(("only",))
        with pytest.raises(ValueError):
            parse_item((3, "accept"))


class TestConstruct:
    def test_defaults(self, qtbot):
        d = _dialog(qtbot)
        assert (d.placement(), d.modality(), d.backdrop(), d.stay_on_top()) == (
            "center",
            "window",
            "none",
            "system",
        )
        assert d.dismiss_on_escape() is False
        assert d.width() == 420
        assert d.resolved_controls()[:2] == (False, False)
        assert d.resolved_resizable() is False

    @pytest.mark.parametrize(
        "kw",
        [
            {"placement": "middle"},
            {"modality": "x"},
            {"backdrop": "x"},
            {"stay_on_top": "x"},
            {"footer_align": "x"},
            {"button_order": "x"},
            {"color": "pink"},
            {"height": 0},
            {"placement_offset": (1,)},
            {"placement_offset": (1.5, 2)},
            {"dismiss_on_escape": 1},
        ],
    )
    def test_invalid_args_raise(self, qtbot, kw):
        with pytest.raises(ValueError):
            Dialog(**kw)

    def test_is_a_window(self, qtbot):
        assert isinstance(_dialog(qtbot), Window)


class TestResult:
    def test_custom_code_only_emits_finished(self, qtbot):
        d = _dialog(qtbot, message="x")
        d.set_footer([("跳过", -1), ("取消", "reject"), ("覆盖", "accept")])
        seen = []
        d.finished.connect(lambda c: seen.append(("finished", c)))
        d.accepted.connect(lambda: seen.append("accepted"))
        d.rejected.connect(lambda: seen.append("rejected"))
        _later(lambda: d.buttons()[0].click())
        assert d.exec() == -1
        assert d.result() == -1
        assert seen == [("finished", -1)]

    def test_accept_signal_order_and_data_before_signals(self, qtbot):
        d = _dialog(qtbot, message="x")
        d.set_footer([("好", "accept", "payload")])
        seen = []
        d.finished.connect(lambda c: seen.append(("finished", d.result_data())))
        d.accepted.connect(lambda: seen.append("accepted"))
        _later(lambda: d.buttons()[0].click())
        assert d.exec() == Dialog.Accepted
        assert seen == [("finished", "payload"), "accepted"]

    def test_reject_signal(self, qtbot):
        d = _dialog(qtbot, message="x")
        d.set_footer([("取消", "reject")])
        with qtbot.waitSignal(d.rejected, timeout=2000):
            _later(lambda: d.buttons()[0].click())
            d.exec()

    def test_done_validates_code(self, qtbot):
        d = _dialog(qtbot)
        for bad in (True, 1.5, "1", None):
            with pytest.raises(ValueError):
                d.done(bad)

    def test_done_ignored_when_not_open(self, qtbot):
        d = _dialog(qtbot)
        seen = []
        d.finished.connect(seen.append)
        d.done(7)
        assert seen == [] and d.result() == 0

    def test_second_done_ignored(self, qtbot):
        d = _dialog(qtbot)
        _later(lambda: (d.done(3), d.done(9)))
        assert d.exec() == 3 and d.result() == 3

    def test_result_is_zero_while_open_and_reset_on_reopen(self, qtbot):
        d = _dialog(qtbot)
        seen = []
        _later(lambda: (seen.append(d.result()), d.done(5)))
        assert d.exec() == 5
        _later(lambda: seen.append(d.result()))
        _later(lambda: d.done(0))
        d.exec()
        assert seen == [0, 0]

    def test_provider_runs_on_accept_only(self, qtbot):
        d = _dialog(qtbot)
        d.set_result_data_provider(lambda: "typed")
        _later(lambda: d.accept())
        assert d.exec() == 1 and d.result_data() == "typed"
        _later(lambda: d.reject())
        assert d.exec() == 0 and d.result_data() is None

    def test_done_data_overrides_provider_and_set_data(self, qtbot):
        d = _dialog(qtbot)
        d.set_result_data_provider(lambda: "from-provider")
        _later(lambda: (d.set_result_data("early"), d.done(2, "explicit")))
        d.exec()
        assert d.result_data() == "explicit"

    def test_provider_error_keeps_dialog_open(self, qtbot):
        d = _dialog(qtbot)

        def boom():
            raise RuntimeError("x")

        d.set_result_data_provider(boom)
        d.open()
        with pytest.raises(RuntimeError):
            d.done(1)
        assert d._active
        d.set_result_data_provider(None)
        d.reject()


class TestClosePaths:
    def test_close_is_reject(self, qtbot):
        d = _dialog(qtbot)
        _later(lambda: d.close())
        assert d.exec() == 0

    def test_hide_is_reject(self, qtbot):
        d = _dialog(qtbot)
        d.show()
        assert d._active
        d.hide()
        assert not d._active and d.result() == 0

    def test_escape_blocked_by_default(self, qtbot):
        d = _dialog(qtbot)
        d.open()
        _key(d, Qt.Key.Key_Escape)
        assert d._active
        d.reject()

    def test_escape_closes_when_enabled(self, qtbot):
        d = _dialog(qtbot, dismiss_on_escape=True)
        _later(lambda: _key(d, Qt.Key.Key_Escape))
        assert d.exec() == 0

    def test_enter_triggers_first_reject_button_by_default(self, qtbot):
        d = _dialog(qtbot)
        d.set_footer([("确定", "accept"), ("取消", "reject")])
        _later(lambda: _key(d, Qt.Key.Key_Return))
        assert d.exec() == 0

    def test_enter_triggers_explicit_default_button(self, qtbot):
        d = _dialog(qtbot)
        d.set_footer([("确定", "accept"), ("取消", "reject")])
        d.set_default_button(d.buttons()[0])
        _later(lambda: _key(d, Qt.Key.Key_Return))
        assert d.exec() == 1

    def test_parent_close_ends_exec(self, qtbot):
        parent = _parent(qtbot)
        d = _dialog(qtbot, parent)
        _later(lambda: parent.close())
        assert d.exec() == 0


class TestFooter:
    def test_set_footer_builds_buttons(self, qtbot):
        d = _dialog(qtbot)
        d.set_footer([("取消", "reject"), ("确定", "accept")])
        assert [b.text() for b in d.buttons()] == ["取消", "确定"]

    def test_bad_footer_keeps_old_buttons(self, qtbot):
        d = _dialog(qtbot)
        d.set_footer([("取消", "reject")])
        with pytest.raises(ValueError):
            d.set_footer([("好", "accept"), ("坏", True)])
        assert [b.text() for b in d.buttons()] == ["取消"]

    def test_add_button_with_custom_code_and_data(self, qtbot):
        d = _dialog(qtbot)
        btn = d.add_button("稍后", 42, {"k": 1})
        _later(lambda: btn.click())
        assert d.exec() == 42 and d.result_data() == {"k": 1}

    def test_none_role_does_not_close(self, qtbot):
        d = _dialog(qtbot)
        btn = d.add_button("帮助")
        d.open()
        btn.click()
        assert d._active
        d.reject()

    def test_own_button_is_reused_not_destroyed(self, qtbot):
        d = _dialog(qtbot)
        mine = Button("我的")
        d.set_footer([(mine, "accept")])
        d.set_footer([(mine, "reject"), ("新", "accept")])
        assert d.buttons()[0] is mine

    @pytest.mark.parametrize("system", ["windows", "linux", "mac"])
    def test_auto_button_order_is_cancel_first_everywhere(self, qtbot, system):
        d = _dialog(qtbot, system=system)
        d.set_footer([("确定", "accept"), ("取消", "reject")])
        order = d._footer._display_order()
        assert [e.button.text() for e in order] == ["取消", "确定"]

    def test_ok_first_order(self, qtbot):
        d = _dialog(qtbot, button_order="ok_first")
        d.set_footer([("取消", "reject"), ("确定", "accept")])
        assert [e.button.text() for e in d._footer._display_order()] == ["确定", "取消"]

    def test_no_window_is_shown_while_building(self, qtbot):
        """构造期间不能有无父控件被显示成顶层窗口（打开对话框前会闪一下）。"""
        from PySide6.QtCore import QObject
        from PySide6.QtWidgets import QApplication

        shown = []

        class Spy(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == QEvent.Type.Show and obj.isWidgetType() and obj.isWindow():
                    shown.append(type(obj).__name__)
                return False

        spy = Spy()
        app = QApplication.instance()
        app.installEventFilter(spy)
        try:
            d = _dialog(qtbot, heading="小标题", message="正文")
            d.set_footer([("取消", "reject"), ("确定", "accept")])
        finally:
            app.removeEventFilter(spy)
        assert shown == []

    def test_forced_button_order(self, qtbot):
        d = _dialog(qtbot, button_order="cancel_first")
        d.set_footer([("跳过", -1), ("确定", "accept"), ("取消", "reject")])
        assert [e.button.text() for e in d._footer._display_order()] == ["跳过", "取消", "确定"]


class TestAutoHeight:
    def test_grows_and_shrinks_with_content(self, qtbot):
        d = _dialog(qtbot, message="短")
        short = d.height()
        d.set_message("很长的文案。" * 80)
        assert d.height() > short
        d.set_message("短")
        assert d.height() == short

    def test_capped_by_screen_ratio(self, qtbot):
        d = _dialog(qtbot, message="很长的文案。" * 400)
        avail = d.screen().availableGeometry().height()
        assert d.height() <= int(avail * 0.8)

    def test_max_height_overrides_cap(self, qtbot):
        d = _dialog(qtbot, message="很长的文案。" * 400, max_height=300)
        assert d.height() == 300

    def test_fixed_height_ignores_content(self, qtbot):
        d = _dialog(qtbot, message="很长的文案。" * 40, height=250)
        assert d.height() == 250
        d.set_message("更长的文案。" * 80)
        assert d.height() == 250

    def test_set_height_none_restores_auto(self, qtbot):
        d = _dialog(qtbot, message="x", height=400)
        d.set_height(None)
        assert d.height() < 400

    def test_footer_adds_height(self, qtbot):
        d = _dialog(qtbot, message="两行\n文案\n三行")
        before = d.height()
        d.set_footer([("取消", "reject"), ("确定", "accept")])
        assert d.height() >= before

    def test_empty_body_uses_min_height(self, qtbot):
        d = _dialog(qtbot)
        assert d.height() == d.minimumHeight()

    def test_custom_body_measured(self, qtbot):
        from PySide6.QtWidgets import QWidget

        d = _dialog(qtbot)
        w = QWidget()
        w.setFixedHeight(400)
        d.set_body(w)
        assert d.height() >= 400
        d.set_body(None)
        assert d.height() == d.minimumHeight()


class TestPlacementOnScreen:
    def test_center_on_parent(self, qtbot):
        parent = _parent(qtbot)
        d = _dialog(qtbot, parent, message="x")
        d.open()
        g, p = d.geometry(), parent.geometry()
        assert abs(g.center().x() - p.center().x()) <= 1
        assert abs(g.center().y() - p.center().y()) <= 1
        d.reject()

    def test_top_left_on_parent(self, qtbot):
        parent = _parent(qtbot)
        d = _dialog(qtbot, parent, message="x", placement="top-left")
        d.open()
        assert d.geometry().topLeft() == parent.geometry().topLeft()
        d.reject()

    def test_set_placement_moves_open_dialog(self, qtbot):
        parent = _parent(qtbot)
        d = _dialog(qtbot, parent, message="x")
        d.open()
        d.set_placement("bottom-right")
        g, p = d.geometry(), parent.geometry()
        assert g.right() == p.right() and g.bottom() == p.bottom()
        d.reject()

    def test_height_change_keeps_top_anchor(self, qtbot):
        parent = _parent(qtbot)
        d = _dialog(qtbot, parent, message="x", placement="top")
        d.open()
        top = d.geometry().top()
        d.set_message("很长的文案。" * 40)
        assert d.geometry().top() == top
        d.reject()


class TestShadeAndFlags:
    def test_dim_shade_created_and_removed(self, qtbot):
        from hero_side_ui._shared.overlays import Backdrop

        parent = _parent(qtbot)
        d = _dialog(qtbot, parent, message="x", backdrop="dim")
        d.open()
        assert parent.findChildren(Backdrop)
        d.reject()
        until(qtbot, lambda: not parent.findChildren(Backdrop))

    def test_no_shade_without_parent(self, qtbot):
        d = _dialog(qtbot, message="x", backdrop="blur")
        d.open()
        assert d._shade._backdrop is None
        d.reject()

    def test_stay_on_top_flag_follows_setting(self, qtbot):
        d = _dialog(qtbot, message="x")
        hint = Qt.WindowType.WindowStaysOnTopHint
        d.open()
        assert d.windowFlags() & hint
        d.reject()
        d.set_stay_on_top("none")
        d.open()
        assert not d.windowFlags() & hint
        d.reject()

    def test_switching_stay_on_top_while_open_keeps_dialog_active(self, qtbot):
        d = _dialog(qtbot, message="x")
        d.open()
        d.set_stay_on_top("none")
        assert d._active
        d.reject()

    @pytest.mark.parametrize(
        "name,mode",
        [
            ("window", Qt.WindowModality.WindowModal),
            ("application", Qt.WindowModality.ApplicationModal),
            ("none", Qt.WindowModality.NonModal),
        ],
    )
    def test_modality_applied_on_open(self, qtbot, name, mode):
        d = _dialog(qtbot, message="x", modality=name)
        d.open()
        assert d.windowModality() == mode
        d.reject()


class TestIconAndColor:
    def test_color_follows_icon_until_overridden(self, qtbot):
        d = _dialog(qtbot, icon="danger")
        assert d._accent() == "danger"
        d.set_icon("success")
        assert d._accent() == "success"
        d.set_color("secondary")
        d.set_icon("info")
        assert d._accent() == "secondary"
        d.set_color(None)
        assert d._accent() == "primary"

    def test_invalid_color_raises(self, qtbot):
        with pytest.raises(ValueError):
            _dialog(qtbot).set_color("pink")

    def test_custom_icon_widget_and_none(self, qtbot):
        from PySide6.QtWidgets import QLabel

        d = _dialog(qtbot, message="x")
        lab = QLabel("!")
        d.set_icon(lab)
        assert lab.parentWidget() is d._body._holder
        d.set_icon(None)
        assert d._body._holder.isHidden()


class TestQuick:
    @staticmethod
    def _click(parent, index):
        def go():
            dlgs = [w for w in parent.findChildren(Dialog) if not w.isHidden()]
            dlgs[0].buttons()[index].click()

        _later(go)

    def test_confirm_ok_true_cancel_false(self, qtbot):
        parent = _parent(qtbot)
        self._click(parent, 1)
        assert Dialog.confirm(parent, "删除", "确定删除？", color="danger") is True
        self._click(parent, 0)
        assert Dialog.confirm(parent, "删除", "确定删除？") is False

    def test_alert_returns_none(self, qtbot):
        parent = _parent(qtbot)
        self._click(parent, 0)
        assert Dialog.alert(parent, "提示", "完成", icon="success") is None

    def test_alert_enter_closes(self, qtbot):
        parent = _parent(qtbot)

        def press():
            dlg = next(w for w in parent.findChildren(Dialog) if not w.isHidden())
            _key(dlg, Qt.Key.Key_Return)

        _later(press)
        assert Dialog.alert(parent, "提示", "完成") is None

    def test_choose_returns_custom_code(self, qtbot):
        parent = _parent(qtbot)
        self._click(parent, 0)
        code = Dialog.choose(parent, "导入", "怎么处理？", [("跳过", -1), ("取消", "reject")])
        assert code == -1

    def test_quick_dialog_is_destroyed_after_use(self, qtbot):
        parent = _parent(qtbot)
        self._click(parent, 0)
        Dialog.alert(parent, "提示", "完成")
        flush(qtbot)
        assert not parent.findChildren(Dialog)
