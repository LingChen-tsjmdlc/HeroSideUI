"""Tabs 组件测试。

覆盖：
- 构造校验、默认值、所有变体/颜色/尺寸/圆角/位置/主题
- add_tab / remove_tab / clear / count
- 选中切换、key 路径、disabled tab 跳过
- selection_changed 信号
- 全套动态 setter
- full_width / is_disabled / disable_animation
- compoundSlots: underlined 强制 rounded-none
"""

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from hero_side_ui import Tabs, TabItem


# ============================================================
# 构造与默认值
# ============================================================


class TestTabsInit:
    def test_default(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        assert t._variant == "solid"
        assert t._color == "default"
        assert t._size == "md"
        assert t._radius == "md"
        assert t._placement == "top"
        assert t._theme_mode == "auto"
        assert t._full_width is False
        assert t._is_disabled is False
        assert t._disable_animation is False
        assert t.count() == 0

    def test_init_with_str_items(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        assert t.count() == 3
        assert t.tab_at(0).title() == "a"
        assert t.tab_at(2).key() == "c"

    def test_init_with_tuple_items(self, qtbot):
        t = Tabs([("Photos", QLabel("p")), ("Music", QLabel("m"), "music_key")])
        qtbot.addWidget(t)
        assert t.count() == 2
        assert t.tab_at(1).key() == "music_key"

    def test_init_with_dict_items(self, qtbot):
        t = Tabs([
            {"title": "A", "content": QLabel("a")},
            {"title": "B", "content": QLabel("b"), "disabled": True},
        ])
        qtbot.addWidget(t)
        assert t.count() == 2
        assert t.tab_at(1).is_disabled() is True

    @pytest.mark.parametrize("v", ["solid", "bordered", "light", "underlined"])
    def test_all_variants(self, qtbot, v):
        t = Tabs(variant=v)
        qtbot.addWidget(t)
        assert t._variant == v

    @pytest.mark.parametrize("c", ["default", "primary", "secondary", "success", "warning", "danger"])
    def test_all_colors(self, qtbot, c):
        t = Tabs(color=c)
        qtbot.addWidget(t)
        assert t._color == c

    @pytest.mark.parametrize("s", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, s):
        t = Tabs(size=s)
        qtbot.addWidget(t)
        assert t._size == s

    @pytest.mark.parametrize("r", ["none", "sm", "md", "lg", "full"])
    def test_all_radius(self, qtbot, r):
        t = Tabs(radius=r)
        qtbot.addWidget(t)
        assert t._radius == r

    @pytest.mark.parametrize("p", ["top", "bottom", "start", "end"])
    def test_all_placements(self, qtbot, p):
        t = Tabs(placement=p)
        qtbot.addWidget(t)
        assert t._placement == p

    @pytest.mark.parametrize("th", ["light", "dark"])
    def test_themes(self, qtbot, th):
        t = Tabs(theme=th)
        qtbot.addWidget(t)
        assert t._theme == th

    def test_invalid_raises(self, qtbot):
        with pytest.raises(ValueError):
            Tabs(variant="weird")
        with pytest.raises(ValueError):
            Tabs(color="rainbow")
        with pytest.raises(ValueError):
            Tabs(size="xl")
        with pytest.raises(ValueError):
            Tabs(placement="upside-down")
        with pytest.raises(ValueError):
            Tabs(theme="sepia")

    def test_underlined_forces_radius_none(self, qtbot):
        """compoundSlots: underlined → rounded-none"""
        t = Tabs(variant="underlined", radius="lg")
        qtbot.addWidget(t)
        assert t._radius == "none"


# ============================================================
# add_tab / remove_tab / clear
# ============================================================


class TestTabManagement:
    def test_add_tab(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("Photos")
        assert isinstance(item, TabItem)
        assert t.count() == 1
        assert t.tab_at(0) is item

    def test_add_tab_with_content(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        content = QLabel("photo content")
        t.add_tab("Photos", content)
        assert t.panel_at(0) is content

    def test_add_tab_with_key(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        t.add_tab("Photos", key="photo_key")
        assert t.tab_at(0).key() == "photo_key"

    def test_add_tab_disabled(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        t.add_tab("Disabled", disabled=True)
        assert t.tab_at(0).is_disabled() is True

    def test_remove_tab(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        t.remove_tab(1)
        assert t.count() == 2
        assert t.tab_at(0).title() == "a"
        assert t.tab_at(1).title() == "c"

    def test_clear(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        t.clear()
        assert t.count() == 0
        assert t.current_index() == -1


# ============================================================
# 选中切换 / 信号
# ============================================================


class TestSelection:
    def test_set_selected_by_index(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        t.set_selected(2)
        assert t.current_index() == 2
        assert t.tab_at(2).isChecked() is True
        assert t.tab_at(0).isChecked() is False

    def test_set_selected_by_key(self, qtbot):
        t = Tabs([("a", None, "alpha"), ("b", None, "beta")])
        qtbot.addWidget(t)
        t.set_selected("beta")
        assert t.current_index() == 1
        assert t.current_key() == "beta"

    def test_disabled_tab_cannot_be_selected(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        t.add_tab("ok")
        t.add_tab("nope", disabled=True)
        t.set_selected(0)
        t.set_selected(1)
        # 仍然停在 0
        assert t.current_index() == 0

    def test_selection_changed_signal(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        t.set_selected(0)  # 先确定起点
        with qtbot.waitSignal(t.selection_changed, timeout=1000) as sig:
            t.set_selected(2)
        assert sig.args == [2, "c"]

    def test_signal_not_fired_when_same_index(self, qtbot):
        t = Tabs(["a", "b"])
        qtbot.addWidget(t)
        t.set_selected(0)
        emitted = []
        t.selection_changed.connect(lambda i, k: emitted.append((i, k)))
        t.set_selected(0)
        assert emitted == []

    def test_remove_tab_resyncs_current_index(self, qtbot):
        t = Tabs(["a", "b", "c"])
        qtbot.addWidget(t)
        t.set_selected(2)
        t.remove_tab(2)
        assert t.current_index() == 1


# ============================================================
# 动态 setter
# ============================================================


class TestDynamicSetters:
    def test_set_variant(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_variant("underlined")
        assert t._variant == "underlined"
        # underlined 应强制 radius=none
        assert t._radius == "none"

    def test_set_color(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_color("danger")
        assert t._color == "danger"

    def test_set_size(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_size("lg")
        assert t._size == "lg"

    def test_set_radius(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_radius("full")
        assert t._radius == "full"

    def test_set_radius_blocked_by_underlined(self, qtbot):
        t = Tabs(["a"], variant="underlined")
        qtbot.addWidget(t)
        t.set_radius("lg")
        # underlined 强制 none
        assert t._radius == "none"

    def test_set_placement(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_placement("end")
        assert t._placement == "end"

    def test_set_theme(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_theme("dark")
        assert t._theme == "dark"

    def test_set_full_width(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_full_width(True)
        assert t._full_width is True

    def test_set_disabled(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_disabled(True)
        assert t._is_disabled is True
        assert t._list.isEnabled() is False

    def test_set_disable_animation(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        t.set_disable_animation(True)
        assert t._disable_animation is True
        assert t.tab_at(0)._disable_animation is True

    def test_invalid_setter_args_raise(self, qtbot):
        t = Tabs(["a"])
        qtbot.addWidget(t)
        with pytest.raises(ValueError):
            t.set_variant("zzz")
        with pytest.raises(ValueError):
            t.set_color("magenta")
        with pytest.raises(ValueError):
            t.set_size("XXL")
        with pytest.raises(ValueError):
            t.set_radius("huge")
        with pytest.raises(ValueError):
            t.set_placement("???")
        with pytest.raises(ValueError):
            t.set_theme("invalid_theme")


# ============================================================
# TabItem 单独测试
# ============================================================


class TestTabItem:
    def test_set_title(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("orig")
        item.set_title("new")
        assert item.title() == "new"

    def test_set_disabled(self, qtbot):
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("a")
        item.set_disabled(True)
        assert item.is_disabled() is True
        item.set_disabled(False)
        assert item.is_disabled() is False


# ============================================================
# TabItem 三档插槽
# ============================================================


class TestTabItemSlots:
    def test_level1_text_only(self, qtbot):
        """档 1: 纯文本"""
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("Photos")
        assert item.title() == "Photos"
        assert item._start_icon_pixmap is None
        assert item._end_icon_pixmap is None
        assert item.custom() is None

    def test_level2_start_icon(self, qtbot):
        """档 2: start_icon"""
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("Next", start_icon="heroicons--chevron-right-solid")
        assert item.has_icons()
        assert item._start_icon_pixmap is not None
        assert item._end_icon_pixmap is None

    def test_level2_end_icon(self, qtbot):
        """档 2: end_icon"""
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("Show", end_icon="heroicons--eye-solid")
        assert item.has_icons()
        assert item._end_icon_pixmap is not None
        assert item._start_icon_pixmap is None

    def test_level2_both_icons(self, qtbot):
        """档 2: 同时设置 start + end"""
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab(
            "Both",
            start_icon="heroicons--check-solid",
            end_icon="heroicons--chevron-right-solid",
        )
        assert item._start_icon_pixmap is not None
        assert item._end_icon_pixmap is not None

    def test_level2_dynamic_icon_setter(self, qtbot):
        """档 2: 运行时 set_start_icon / set_end_icon"""
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("a")
        assert item._start_icon_pixmap is None
        item.set_start_icon("heroicons--check-solid")
        assert item._start_icon_pixmap is not None
        item.set_start_icon(None)
        assert item._start_icon_pixmap is None

    def test_level3_custom_widget(self, qtbot):
        """档 3: custom widget"""
        from PySide6.QtWidgets import QLabel
        t = Tabs()
        qtbot.addWidget(t)
        custom_w = QLabel("Custom!")
        item = t.add_tab(custom=custom_w, key="mine")
        assert item.custom() is custom_w
        assert item.key() == "mine"
        # 自定义模式下 paintEvent 不画文字 / icon
        # 但 toggled 信号仍然工作
        assert item.isCheckable() is True

    def test_level3_set_custom_runtime(self, qtbot):
        """运行时切换 custom widget 与回退"""
        from PySide6.QtWidgets import QLabel
        t = Tabs()
        qtbot.addWidget(t)
        item = t.add_tab("regular")
        assert item.custom() is None
        # 切换到 custom 模式
        new_widget = QLabel("now custom")
        item.set_custom(new_widget)
        assert item.custom() is new_widget
        # 回退
        item.set_custom(None)
        assert item.custom() is None

    def test_level3_selected_changed_signal(self, qtbot):
        """custom widget 可以监听 selected_changed 信号"""
        from PySide6.QtWidgets import QLabel
        t = Tabs()
        qtbot.addWidget(t)
        t.add_tab("first")
        custom_w = QLabel("c")
        t.add_tab(custom=custom_w, key="custom")
        # 切换到 custom，selected_changed 应触发
        with qtbot.waitSignal(t.tab_at(1).selected_changed, timeout=1000) as sig:
            t.set_selected("custom")
        assert sig.args == [True]

    def test_init_dict_with_icons(self, qtbot):
        """构造时 dict 形式支持 icons 字段"""
        t = Tabs([
            {"title": "Photos", "start_icon": "heroicons--eye-solid"},
            {"title": "Next", "end_icon": "heroicons--chevron-right-solid"},
        ])
        qtbot.addWidget(t)
        assert t.tab_at(0)._start_icon_pixmap is not None
        assert t.tab_at(1)._end_icon_pixmap is not None
