"""ScrollShadow 组件测试

ScrollShadow 是 QScrollArea 的派生，关键测试点：
- 构造参数（orientation/size/offset/visibility/is_enabled/hide_scrollbar）
- 非法参数 raise ValueError
- 滚动条策略按 orientation/hide_scrollbar 配置
- visibility 计算逻辑（_compute_effective_visibility）
- 插槽 API（add_widget/insert_widget/add_stretch/layout/content）
- 自定义 fade_color 同步到 palette
- 主题切换 auto 模式注册/注销
- visibility_changed 信号
- duck typing 父链 current_bg_color()/current_corner_radius()

不测试视觉绘制（_ShadowOverlay paintEvent）——靠 examples 人工验证。
"""

from __future__ import annotations

import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from hero_side_ui import ScrollShadow, ThemeProvider


@pytest.fixture(autouse=True)
def reset_provider():
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


def _make_long_content(rows: int = 50) -> QWidget:
    """造一个比 viewport 高的内容 widget，用来触发可滚动状态"""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    for i in range(rows):
        lbl = QLabel(f"row {i}")
        lbl.setFixedHeight(30)
        lay.addWidget(lbl)
    return w


# ============================================================
# 构造
# ============================================================
class TestScrollShadowInit:
    def test_default_params(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert sc._orientation == "vertical"
        assert sc._size == 40
        assert sc._offset == 0
        assert sc._visibility == "auto"
        assert sc._is_enabled is True
        assert sc._hide_scrollbar is False
        assert sc._fade_color_user is None
        assert sc._theme_mode == "auto"

    def test_horizontal(self, qtbot):
        sc = ScrollShadow(orientation="horizontal")
        qtbot.addWidget(sc)
        assert sc._orientation == "horizontal"

    def test_custom_size_and_offset(self, qtbot):
        sc = ScrollShadow(size=60, offset=5)
        qtbot.addWidget(sc)
        assert sc._size == 60
        assert sc._offset == 5

    def test_invalid_orientation_raises(self, qtbot):
        with pytest.raises(ValueError):
            ScrollShadow(orientation="diagonal")

    def test_invalid_visibility_raises(self, qtbot):
        with pytest.raises(ValueError):
            ScrollShadow(visibility="banana")

    def test_no_frame_shape(self, qtbot):
        """frameShape 应该是 NoFrame，避免 1px 边框干扰阴影"""
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        from PySide6.QtWidgets import QScrollArea
        assert sc.frameShape() == QScrollArea.Shape.NoFrame

    def test_widget_resizable(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert sc.widgetResizable() is True


# ============================================================
# 滚动条策略
# ============================================================
class TestScrollBarPolicy:
    def test_vertical_default(self, qtbot):
        sc = ScrollShadow(orientation="vertical")
        qtbot.addWidget(sc)
        assert sc.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert sc.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    def test_horizontal_default(self, qtbot):
        sc = ScrollShadow(orientation="horizontal")
        qtbot.addWidget(sc)
        assert sc.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert sc.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    def test_hide_scrollbar(self, qtbot):
        sc = ScrollShadow(hide_scrollbar=True)
        qtbot.addWidget(sc)
        assert sc.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert sc.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def test_set_hide_scrollbar(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_hide_scrollbar(True)
        assert sc.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


# ============================================================
# 插槽 API
# ============================================================
class TestSlotAPI:
    def test_layout_returns_qlayout(self, qtbot):
        sc = ScrollShadow(orientation="vertical")
        qtbot.addWidget(sc)
        assert isinstance(sc.layout(), QVBoxLayout)

    def test_layout_horizontal(self, qtbot):
        sc = ScrollShadow(orientation="horizontal")
        qtbot.addWidget(sc)
        assert isinstance(sc.layout(), QHBoxLayout)

    def test_content_returns_widget(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert isinstance(sc.content(), QWidget)
        assert sc.content().objectName() == "heroScrollShadowContent"

    def test_add_widget(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        before = sc.layout().count()
        lbl = QLabel("hi")
        sc.add_widget(lbl)
        assert sc.layout().count() == before + 1
        assert sc.layout().itemAt(before).widget() is lbl

    def test_insert_widget(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        a = QLabel("a")
        b = QLabel("b")
        sc.add_widget(a)
        sc.insert_widget(0, b)  # b 应该在 a 之前
        assert sc.layout().itemAt(0).widget() is b
        assert sc.layout().itemAt(1).widget() is a

    def test_add_stretch(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        before = sc.layout().count()
        sc.add_stretch()
        assert sc.layout().count() == before + 1

    def test_setwidget_replaces_content(self, qtbot):
        """高级用法：setWidget 替换整个内容容器"""
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        new_content = QWidget()
        sc.setWidget(new_content)
        assert sc.content() is new_content


# ============================================================
# fade_color
# ============================================================
class TestFadeColor:
    def test_user_fade_color_takes_priority(self, qtbot):
        sc = ScrollShadow(fade_color="#ff0000")
        qtbot.addWidget(sc)
        assert sc._fade_color_user == "#ff0000"
        # 透出的色应该是用户传的
        assert sc._fade_color().name().lower() == "#ff0000"

    def test_user_fade_color_paints_palette(self, qtbot):
        """传 fade_color 时，self + viewport 的 palette.Window 同步成该色"""
        sc = ScrollShadow(fade_color="#123456")
        qtbot.addWidget(sc)
        assert sc.palette().color(QPalette.ColorRole.Window).name().lower() == "#123456"
        assert sc.viewport().palette().color(QPalette.ColorRole.Window).name().lower() == "#123456"

    def test_set_fade_color_none_restores(self, qtbot):
        sc = ScrollShadow(fade_color="#ff0000")
        qtbot.addWidget(sc)
        sc.set_fade_color(None)
        assert sc._fade_color_user is None
        assert sc.autoFillBackground() is False

    def test_duck_typing_finds_ancestor_bg(self, qtbot):
        """父链找到 current_bg_color() 时，使用其返回值"""
        class FakeContainer(QWidget):
            def current_bg_color(self):
                return QColor("#abcdef")

        parent = FakeContainer()
        qtbot.addWidget(parent)
        # theme="light" 跳过 ThemeProvider 注册，避免单例持有的悬空引用
        # 在 parent 销毁后被回调触发 RuntimeError
        sc = ScrollShadow(parent=parent, theme="light")
        qtbot.addWidget(sc)
        # 没传 fade_color → 沿父链找
        assert sc._fade_color().name().lower() == "#abcdef"


# ============================================================
# clip_radius duck typing
# ============================================================
class TestClipRadius:
    def test_no_ancestor_returns_zero(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert sc._clip_radius() == 0.0

    def test_ancestor_with_radius(self, qtbot):
        class RoundedParent(QWidget):
            def current_corner_radius(self):
                return 14.0

        parent = RoundedParent()
        qtbot.addWidget(parent)
        # theme="light" 跳过 ThemeProvider 注册（parent 销毁时单例的悬空引用会炸）
        sc = ScrollShadow(parent=parent, theme="light")
        qtbot.addWidget(sc)
        assert sc._clip_radius() == 14.0

    def test_invalid_ancestor_radius_returns_zero(self, qtbot):
        """祖先返回非数字/0 → 回退 0"""
        class BadParent(QWidget):
            def current_corner_radius(self):
                return "not a number"

        parent = BadParent()
        qtbot.addWidget(parent)
        sc = ScrollShadow(parent=parent, theme="light")
        qtbot.addWidget(sc)
        assert sc._clip_radius() == 0.0


# ============================================================
# visibility 计算
# ============================================================
class TestVisibilityCompute:
    def test_disabled_returns_none(self, qtbot):
        sc = ScrollShadow(is_enabled=False)
        qtbot.addWidget(sc)
        start, end, label = sc._compute_effective_visibility()
        assert (start, end, label) == (False, False, "none")

    def test_visibility_none(self, qtbot):
        sc = ScrollShadow(visibility="none")
        qtbot.addWidget(sc)
        assert sc._compute_effective_visibility() == (False, False, "none")

    def test_visibility_both_force(self, qtbot):
        """visibility=both 强制两端都显示，无视滚动状态"""
        sc = ScrollShadow(visibility="both")
        qtbot.addWidget(sc)
        start, end, label = sc._compute_effective_visibility()
        assert (start, end, label) == (True, True, "both")

    def test_visibility_top_vertical(self, qtbot):
        sc = ScrollShadow(orientation="vertical", visibility="top")
        qtbot.addWidget(sc)
        assert sc._compute_effective_visibility() == (True, False, "top")

    def test_visibility_top_horizontal_invalid(self, qtbot):
        """horizontal 方向 visibility=top 无意义 → none"""
        sc = ScrollShadow(orientation="horizontal", visibility="top")
        qtbot.addWidget(sc)
        assert sc._compute_effective_visibility() == (False, False, "none")

    def test_visibility_left_horizontal(self, qtbot):
        sc = ScrollShadow(orientation="horizontal", visibility="left")
        qtbot.addWidget(sc)
        assert sc._compute_effective_visibility() == (True, False, "left")

    def test_visibility_left_vertical_invalid(self, qtbot):
        sc = ScrollShadow(orientation="vertical", visibility="left")
        qtbot.addWidget(sc)
        assert sc._compute_effective_visibility() == (False, False, "none")

    def test_auto_no_scroll_returns_none(self, qtbot):
        """没内容、不可滚动 → none"""
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.resize(200, 200)
        # 不加内容，scrollbar.maximum == minimum
        start, end, _ = sc._compute_effective_visibility()
        assert (start, end) == (False, False)


# ============================================================
# 信号
# ============================================================
class TestSignal:
    def test_visibility_changed_emit_on_force_change(self, qtbot):
        """visibility 改变时（值切换）发信号"""
        sc = ScrollShadow(visibility="none")
        qtbot.addWidget(sc)
        # 初始 _last_effective_vis="none" → set_visibility("both") 会触发 visibility_changed
        with qtbot.waitSignal(sc.visibility_changed, timeout=500) as sig:
            sc.set_visibility("both")
        assert sig.args == ["both"]


# ============================================================
# 动态 setter
# ============================================================
class TestSetters:
    def test_set_orientation(self, qtbot):
        sc = ScrollShadow(orientation="vertical")
        qtbot.addWidget(sc)
        sc.set_orientation("horizontal")
        assert sc._orientation == "horizontal"

    def test_set_orientation_invalid_raises(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        with pytest.raises(ValueError):
            sc.set_orientation("foo")

    def test_set_size(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_size(80)
        assert sc._size == 80

    def test_set_size_clamps_to_zero(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_size(-10)
        assert sc._size == 0

    def test_set_offset(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_offset(20)
        assert sc._offset == 20

    def test_set_visibility(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_visibility("both")
        assert sc._visibility == "both"

    def test_set_visibility_invalid_raises(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        with pytest.raises(ValueError):
            sc.set_visibility("xxx")

    def test_set_is_enabled(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_is_enabled(False)
        assert sc._is_enabled is False

    def test_set_fade_color(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_fade_color("#abcdef")
        assert sc._fade_color_user == "#abcdef"


# ============================================================
# 主题
# ============================================================
class TestTheme:
    def test_auto_registers(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert ThemeProvider.instance().is_registered(sc)

    def test_hardcode_does_not_register(self, qtbot):
        sc = ScrollShadow(theme="dark")
        qtbot.addWidget(sc)
        assert not ThemeProvider.instance().is_registered(sc)

    def test_set_theme_auto_to_hardcode_unregisters(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        sc.set_theme("dark")
        assert not ThemeProvider.instance().is_registered(sc)

    def test_set_theme_hardcode_to_auto_registers(self, qtbot):
        sc = ScrollShadow(theme="light")
        qtbot.addWidget(sc)
        sc.set_theme("auto")
        assert ThemeProvider.instance().is_registered(sc)

    def test_provider_toggle_updates_theme(self, qtbot):
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        assert sc._theme == "light"
        provider.set_mode("dark")
        assert sc._theme == "dark"


# ============================================================
# Getter
# ============================================================
class TestGetters:
    def test_orientation_property(self, qtbot):
        sc = ScrollShadow(orientation="horizontal")
        qtbot.addWidget(sc)
        assert sc.orientation == "horizontal"

    def test_size_px_property(self, qtbot):
        sc = ScrollShadow(size=50)
        qtbot.addWidget(sc)
        assert sc.size_px == 50

    def test_effective_visibility_initial(self, qtbot):
        sc = ScrollShadow()
        qtbot.addWidget(sc)
        # 初始无内容 → "none"
        assert sc.effective_visibility == "none"


# ============================================================
# 组合
# ============================================================
class TestCombinations:
    @pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
    @pytest.mark.parametrize(
        "visibility", ["auto", "both", "top", "bottom", "left", "right", "none"]
    )
    def test_construct_all(self, qtbot, orientation, visibility):
        """所有 orientation × visibility 组合都不应崩"""
        sc = ScrollShadow(orientation=orientation, visibility=visibility)
        qtbot.addWidget(sc)
        assert sc._orientation == orientation
        assert sc._visibility == visibility
