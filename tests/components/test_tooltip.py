"""Tooltip 组件测试

Tooltip = Popover 的 hover-only 简化版。测试关注：
- 构造参数（color/size/radius/shadow/placement/offset/delays/show_arrow…）
- 非法 placement 静默回退到 "top"
- 内容 API（str / QWidget / set_content / 替换）
- attach 触发器 + eventFilter（hover schedule open/close）
- open/close 状态机（_is_open、is_disabled 屏蔽 open）
- 主题：auto 注册 / hardcode 不注册
- _flip_placement 工具函数

不测真实 hover 显隐（依赖 window manager + 动画 timing），改为测调度路径
和状态——参考 MEMORY 第 38 条 + tests/test_autocomplete.py::test_toggle 的经验。
"""

from __future__ import annotations

import pytest

from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from hero_side_ui import ThemeProvider, Tooltip


@pytest.fixture(autouse=True)
def reset_provider():
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


# ============================================================
# 构造
# ============================================================
class TestTooltipInit:
    def test_default(self, qtbot):
        tt = Tooltip(content="Hi")
        qtbot.addWidget(tt)
        assert tt._color == "default"
        assert tt._size == "md"
        assert tt._radius == "md"
        assert tt._shadow == "sm"
        assert tt._placement == "top"
        assert tt._offset == 7
        assert tt._open_delay == 0
        assert tt._close_delay == 150
        assert tt._show_arrow is False
        assert tt._is_disabled is False
        assert tt._theme_mode == "auto"
        assert tt._is_open is False

    def test_default_hidden_initially(self, qtbot):
        tt = Tooltip(content="Hi")
        qtbot.addWidget(tt)
        assert tt.isHidden()

    def test_invalid_placement_falls_back(self, qtbot):
        tt = Tooltip(content="x", placement="diagonal")
        qtbot.addWidget(tt)
        assert tt._placement == "top"

    @pytest.mark.parametrize(
        "place",
        [
            "top", "top-start", "top-end",
            "bottom", "bottom-start", "bottom-end",
            "left", "left-start", "left-end",
            "right", "right-start", "right-end",
        ],
    )
    def test_all_placements(self, qtbot, place):
        tt = Tooltip(content="x", placement=place)
        qtbot.addWidget(tt)
        assert tt._placement == place

    @pytest.mark.parametrize(
        "color", ["default", "primary", "secondary", "success", "warning", "danger"]
    )
    def test_all_colors(self, qtbot, color):
        tt = Tooltip(content="x", color=color)
        qtbot.addWidget(tt)
        assert tt._color == color

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, size):
        tt = Tooltip(content="x", size=size)
        qtbot.addWidget(tt)
        assert tt._size == size

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_all_radius(self, qtbot, radius):
        tt = Tooltip(content="x", radius=radius)
        qtbot.addWidget(tt)
        assert tt._radius == radius

    @pytest.mark.parametrize("shadow", ["none", "sm", "md", "lg"])
    def test_all_shadow(self, qtbot, shadow):
        tt = Tooltip(content="x", shadow=shadow)
        qtbot.addWidget(tt)
        assert tt._shadow == shadow

    def test_custom_offset(self, qtbot):
        tt = Tooltip(content="x", offset=15)
        qtbot.addWidget(tt)
        assert tt._offset == 15

    def test_custom_delays(self, qtbot):
        tt = Tooltip(content="x", open_delay=300, close_delay=500)
        qtbot.addWidget(tt)
        assert tt._open_delay == 300
        assert tt._close_delay == 500

    def test_show_arrow(self, qtbot):
        tt = Tooltip(content="x", show_arrow=True)
        qtbot.addWidget(tt)
        assert tt._show_arrow is True

    def test_is_disabled(self, qtbot):
        tt = Tooltip(content="x", is_disabled=True)
        qtbot.addWidget(tt)
        assert tt._is_disabled is True

    def test_disable_animation(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        assert tt._disable_animation is True


# ============================================================
# 内容
# ============================================================
class TestTooltipContent:
    def test_string_content_creates_label(self, qtbot):
        tt = Tooltip(content="Hello tooltip")
        qtbot.addWidget(tt)
        assert tt._content is not None
        # 容器内应该有一个 QLabel
        labels = tt._content.findChildren(QLabel)
        assert any(lbl.text() == "Hello tooltip" for lbl in labels)

    def test_widget_content(self, qtbot):
        custom = QWidget()
        tt = Tooltip(content=custom)
        qtbot.addWidget(tt)
        assert tt._content is custom

    def test_no_content_creates_empty(self, qtbot):
        tt = Tooltip()
        qtbot.addWidget(tt)
        assert tt._content is not None  # 空容器，但不为 None

    def test_set_content_replaces(self, qtbot):
        tt = Tooltip(content="old")
        qtbot.addWidget(tt)
        tt.set_content("new")
        labels = tt._content.findChildren(QLabel)
        # 新内容里应该是 "new"
        assert any(lbl.text() == "new" for lbl in labels)

    def test_set_content_widget(self, qtbot):
        tt = Tooltip(content="old")
        qtbot.addWidget(tt)
        new_widget = QWidget()
        tt.set_content(new_widget)
        assert tt._content is new_widget


# ============================================================
# attach 触发器
# ============================================================
class TestTooltipAttach:
    def test_attach_records_trigger(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        btn = QPushButton("trigger")
        qtbot.addWidget(btn)

        tt.attach(btn)
        assert tt._trigger is btn

    def test_attach_replaces_old(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        btn1 = QPushButton("a")
        btn2 = QPushButton("b")
        qtbot.addWidget(btn1)
        qtbot.addWidget(btn2)

        tt.attach(btn1)
        tt.attach(btn2)
        assert tt._trigger is btn2


# ============================================================
# eventFilter（trigger 的 Enter / Leave 调度）
# ============================================================
class TestTooltipScheduling:
    def test_enter_with_zero_delay_opens_immediately(self, qtbot):
        """open_delay=0 → trigger Enter 立刻 _do_open"""
        tt = Tooltip(content="x", open_delay=0)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        # 直接调度 schedule_open 模拟 Enter 的核心逻辑
        tt._schedule_open()
        assert tt._is_open is True
        # 收尾：把 tooltip 关掉避免影响后面测试
        tt._do_close()

    def test_enter_with_delay_starts_timer(self, qtbot):
        """open_delay>0 → 启动 _open_timer，未立刻 _is_open"""
        tt = Tooltip(content="x", open_delay=500)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        tt.attach(btn)

        tt._schedule_open()
        assert tt._is_open is False
        assert tt._open_timer.isActive()
        tt._open_timer.stop()  # 清理

    def test_disabled_blocks_open(self, qtbot):
        tt = Tooltip(content="x", is_disabled=True, open_delay=0)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        tt.attach(btn)

        tt._schedule_open()
        assert tt._is_open is False

    def test_schedule_close_stops_open_timer_when_not_open(self, qtbot):
        """未 open 时 schedule_close 应该把还在排队的 open_timer 停掉"""
        tt = Tooltip(content="x", open_delay=500)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        tt.attach(btn)

        tt._schedule_open()
        assert tt._open_timer.isActive()
        tt._schedule_close()
        assert not tt._open_timer.isActive()

    def test_schedule_close_when_open(self, qtbot):
        """已 open 时 schedule_close → 启动 close_timer"""
        tt = Tooltip(content="x", open_delay=0, close_delay=500)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        tt._do_open()
        assert tt._is_open is True

        tt._schedule_close()
        assert tt._close_timer.isActive()
        tt._close_timer.stop()
        tt._do_close()


# ============================================================
# open / close API
# ============================================================
class TestTooltipOpenClose:
    def test_open_sets_state(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        tt.open()
        assert tt._is_open is True
        assert tt.is_open() is True
        tt.close()

    def test_open_without_trigger_noop(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        # 没 attach trigger
        tt.open()
        assert tt._is_open is False

    def test_close_resets_state(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        tt.open()
        tt.close()
        assert tt._is_open is False
        assert tt.is_open() is False

    def test_opened_signal(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        with qtbot.waitSignal(tt.opened, timeout=500):
            tt.open()
        tt.close()

    def test_closed_signal(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        tt.open()
        with qtbot.waitSignal(tt.closed, timeout=500):
            tt.close()

    def test_set_disabled_closes_if_open(self, qtbot):
        tt = Tooltip(content="x", disable_animation=True)
        qtbot.addWidget(tt)
        btn = QPushButton("t")
        qtbot.addWidget(btn)
        btn.show()
        qtbot.waitExposed(btn)
        tt.attach(btn)

        tt.open()
        assert tt._is_open is True
        tt.set_is_disabled(True)
        # set_is_disabled 调 close()
        assert tt._is_open is False


# ============================================================
# 动态 setter
# ============================================================
class TestTooltipSetters:
    def test_set_color(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_color("primary")
        assert tt._color == "primary"

    def test_set_size(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_size("lg")
        assert tt._size == "lg"

    def test_set_radius(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_radius("full")
        assert tt._radius == "full"

    def test_set_shadow(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_shadow("lg")
        assert tt._shadow == "lg"

    def test_set_placement(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_placement("bottom")
        assert tt._placement == "bottom"

    def test_set_placement_invalid_ignored(self, qtbot):
        tt = Tooltip(content="x", placement="top")
        qtbot.addWidget(tt)
        tt.set_placement("diagonal")
        # 非法值被忽略，保持原值
        assert tt._placement == "top"

    def test_set_offset(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_offset(20)
        assert tt._offset == 20

    def test_set_open_delay(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_open_delay(300)
        assert tt._open_delay == 300

    def test_set_close_delay(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_close_delay(800)
        assert tt._close_delay == 800

    def test_set_show_arrow(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_show_arrow(True)
        assert tt._show_arrow is True


# ============================================================
# 主题
# ============================================================
class TestTooltipTheme:
    def test_auto_registers(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        assert ThemeProvider.instance().is_registered(tt)

    def test_hardcode_does_not_register(self, qtbot):
        tt = Tooltip(content="x", theme="dark")
        qtbot.addWidget(tt)
        assert not ThemeProvider.instance().is_registered(tt)

    def test_set_theme_auto_to_hardcode_unregisters(self, qtbot):
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        tt.set_theme("dark")
        assert tt._theme == "dark"
        assert not ThemeProvider.instance().is_registered(tt)

    def test_set_theme_hardcode_to_auto_registers(self, qtbot):
        tt = Tooltip(content="x", theme="light")
        qtbot.addWidget(tt)
        tt.set_theme("auto")
        assert ThemeProvider.instance().is_registered(tt)

    def test_provider_toggle_updates_theme(self, qtbot):
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        tt = Tooltip(content="x")
        qtbot.addWidget(tt)
        assert tt._theme == "light"
        provider.set_mode("dark")
        assert tt._theme == "dark"


# ============================================================
# _flip_placement 工具
# ============================================================
class TestFlipPlacement:
    @pytest.mark.parametrize(
        "place,flipped",
        [
            ("top", "bottom"),
            ("top-start", "bottom-start"),
            ("top-end", "bottom-end"),
            ("bottom", "top"),
            ("bottom-start", "top-start"),
            ("left", "right"),
            ("left-start", "right-start"),
            ("right", "left"),
            ("right-end", "left-end"),
        ],
    )
    def test_flip(self, place, flipped):
        assert Tooltip._flip_placement(place) == flipped


# ============================================================
# 颜色
# ============================================================
class TestColors:
    def test_default_color_light_bg(self, qtbot):
        tt = Tooltip(content="x", color="default", theme="light")
        qtbot.addWidget(tt)
        assert tt._bg_color().name().lower() == "#ffffff"

    def test_default_color_dark_bg(self, qtbot):
        tt = Tooltip(content="x", color="default", theme="dark")
        qtbot.addWidget(tt)
        assert tt._bg_color().name().lower() == "#27272a"

    def test_warning_text_is_black(self, qtbot):
        """warning 色文字应是黑色（亮底反色规则）"""
        tt = Tooltip(content="x", color="warning")
        qtbot.addWidget(tt)
        assert tt._text_color().name().lower() == "#000000"

    def test_default_text_light(self, qtbot):
        tt = Tooltip(content="x", color="default", theme="light")
        qtbot.addWidget(tt)
        assert tt._text_color().name().lower() == "#11181c"

    def test_default_text_dark(self, qtbot):
        tt = Tooltip(content="x", color="default", theme="dark")
        qtbot.addWidget(tt)
        assert tt._text_color().name().lower() == "#ecedee"

    def test_primary_text_is_white(self, qtbot):
        """非 default、非 warning 的语义色文字 = 白色"""
        tt = Tooltip(content="x", color="primary")
        qtbot.addWidget(tt)
        assert tt._text_color().name().lower() == "#ffffff"
