"""公共阴影：留白计算、缓存、渲染一致性，以及 ShadowLayer / ShadowController 的行为。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from hero_side_ui.core import shadow_paint as sp
from hero_side_ui.themes import theme_values
from hero_side_ui.themes.shadow import Layer


@pytest.fixture(autouse=True)
def clean(qapp):
    theme_values.reset()
    sp.clear_cache()
    yield
    theme_values.reset()
    sp.clear_cache()


def _layers(tier: str, theme: str = "light"):
    return theme_values.get_shadow_layers(tier, theme)


def _render(layers, w: int, h: int, direct: bool = False, radius: float = 14.0, dpr: float = 1.0):
    """在透明画布上画一档阴影，返回 (图, 留白 m)。"""
    m = sp.shadow_margin(layers) + 2
    img = QImage(round((w + 2 * m) * dpr), round((h + 2 * m) * dpr), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    img.setDevicePixelRatio(dpr)
    p = QPainter(img)
    body = QRectF(m, m, w, h)
    if direct:
        sp._paint_direct(p, body, radius, layers, dpr)
    else:
        assert sp._paint_nine(p, body, radius, layers, dpr)
    p.end()
    return img, m


def _alpha(img: QImage, x: int, y: int) -> int:
    return QColor.fromRgba(img.pixel(x, y)).alpha()


class TestMargins:
    @pytest.mark.parametrize("tier,expected", [("sm", 18), ("md", 48), ("lg", 121)])
    def test_default_tier_margin(self, tier, expected):
        assert sp.shadow_margin(_layers(tier)) == expected
        assert sp.tier_margin(tier) == expected

    def test_dark_inset_layer_does_not_add_margin(self):
        assert sp.shadow_margin(_layers("md", "dark")) == sp.shadow_margin(_layers("md", "light"))

    @pytest.mark.parametrize("tier", ["none", "unknown", ""])
    def test_no_shadow_tiers_have_zero_margin(self, tier):
        assert sp.tier_margin(tier) == 0
        assert sp.layers_for(tier, "light") == ()

    def test_tier_margin_takes_the_larger_theme(self):
        big = (Layer(0, 40, "#020304", 0.1),)
        small = (Layer(0, 4, "#020304", 0.1),)
        side = lambda x: {"sm": x, "md": x, "lg": x}  # noqa: E731
        theme_values.apply({"shadow": {"light": side(small), "dark": side(big)}})
        assert sp.tier_margin("sm") == sp.shadow_margin(big)


class TestRendering:
    def test_empty_layers_paint_nothing(self):
        img = QImage(50, 50, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sp.paint_shadow(p, QRectF(10, 10, 30, 30), 8.0, ())
        p.end()
        assert all(_alpha(img, x, y) == 0 for x in range(0, 50, 7) for y in range(0, 50, 7))

    @pytest.mark.parametrize("tier", ["sm", "md", "lg"])
    def test_body_is_hollowed_and_outside_is_shaded(self, tier):
        layers = _layers(tier)
        img, m = _render(layers, 320, 240)
        assert _alpha(img, m + 160, m + 120) == 0  # 本体内部不透出阴影
        assert _alpha(img, m + 160, m + 240 + 4) > 0  # 本体下方有阴影

    @pytest.mark.parametrize("tier", ["sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_nine_patch_matches_direct_composition(self, tier, theme):
        layers = _layers(tier, theme)
        side = max(sp._nine_size(layers, 14.0) + 20, 300)
        a, _ = _render(layers, side, side)
        b, _ = _render(layers, side, side, direct=True)
        worst = max(
            abs(_alpha(a, x, y) - _alpha(b, x, y))
            for x in range(0, a.width(), 3)
            for y in range(0, a.height(), 3)
        )
        assert worst <= 8

    def test_inset_stroke_draws_on_the_edge(self):
        layers = _layers("md", "dark")
        img = QImage(120, 80, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sp.paint_inset(p, QRectF(10, 10, 100, 60), 8.0, layers)
        p.end()
        assert _alpha(img, 10, 40) > 0  # 左边缘一条细线
        assert _alpha(img, 60, 40) == 0  # 内部不画

    def test_light_has_no_inset(self):
        img = QImage(120, 80, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sp.paint_inset(p, QRectF(10, 10, 100, 60), 8.0, _layers("md", "light"))
        p.end()
        assert _alpha(img, 10, 40) == 0


class TestCache:
    def test_cache_fills_and_clears(self):
        _render(_layers("md"), 320, 240)
        assert len(sp._cache) > 0 and sp._cache_bytes > 0
        sp.clear_cache()
        assert len(sp._cache) == 0 and sp._cache_bytes == 0

    def test_same_tier_reuses_one_entry_for_different_sizes(self):
        _render(_layers("md"), 320, 240)
        n = len(sp._cache)
        _render(_layers("md"), 500, 400)
        assert len(sp._cache) == n

    def test_byte_budget_evicts_oldest(self, monkeypatch):
        monkeypatch.setattr(sp, "_CACHE_BYTES", 1)
        _render(_layers("sm"), 100, 100, direct=True)
        _render(_layers("sm"), 120, 120, direct=True)
        assert len(sp._cache) == 1

    def test_prewarm_populates_three_tiers(self):
        sp.prewarm("light")
        assert len(sp._cache) == 3


class TestShadowLayer:
    def _host(self, qtbot):
        host = QWidget()
        host.resize(600, 500)
        qtbot.addWidget(host)
        host.show()
        return host

    def test_layer_hugs_target_with_margin_and_sits_above(self, qtbot):
        host = self._host(qtbot)
        target = QWidget(host)
        target.setGeometry(100, 100, 200, 120)
        target.show()
        layers = _layers("md")
        layer = sp.ShadowLayer(target, 14.0, layers)
        m = sp.shadow_margin(layers) + 2
        assert layer.parentWidget() is host
        assert layer.geometry() == target.geometry().adjusted(-m, -m, m, m)
        kids = host.children()
        assert kids.index(layer) > kids.index(target)  # 叠在目标上方（本体已挖空，不遮住目标）

    def test_layer_follows_move_resize_hide_show(self, qtbot):
        host = self._host(qtbot)
        target = QWidget(host)
        target.setGeometry(100, 100, 200, 120)
        target.show()
        layer = sp.ShadowLayer(target, 14.0, _layers("sm"))
        target.move(150, 160)
        assert layer.geometry().center() == target.geometry().center()
        target.resize(260, 140)
        assert layer.width() - target.width() == layer.height() - target.height()
        target.hide()
        assert layer.isHidden()
        target.show()
        assert not layer.isHidden()

    def test_layer_is_mouse_transparent_and_not_in_layout(self, qtbot):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QVBoxLayout

        host = self._host(qtbot)
        lay = QVBoxLayout(host)
        target = QWidget(host)
        lay.addWidget(target)
        layer = sp.ShadowLayer(target, 8.0, _layers("sm"))
        assert layer.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert lay.count() == 1

    def test_set_style_with_no_layers_hides(self, qtbot):
        host = self._host(qtbot)
        target = QWidget(host)
        target.setGeometry(50, 50, 100, 100)
        target.show()
        layer = sp.ShadowLayer(target, 8.0, _layers("sm"))
        layer.set_style(8.0, ())
        assert layer.isHidden()

    def test_body_provider_overrides_target_rect(self, qtbot):
        host = self._host(qtbot)
        target = QWidget(host)
        target.setGeometry(100, 100, 300, 200)
        target.show()
        layer = sp.ShadowLayer(target, 8.0, _layers("sm"))
        layer.set_body_provider(lambda: QRectF(0, 0, 100, 80))
        img = layer.grab().toImage()
        m = sp.shadow_margin(_layers("sm")) + 2
        # 本体只有左上 100×80：本体右侧远处没有阴影，本体正下方有
        assert _alpha(img, m + 250, m + 40) == 0
        assert _alpha(img, m + 50, m + 80 + 3) > 0


class TestClipRoot:
    def test_window_is_the_boundary_for_a_direct_child(self, qtbot):
        host = QWidget()
        qtbot.addWidget(host)
        w = QWidget(host)
        assert sp.clip_root(w) is host

    def test_plain_containers_are_not_boundaries(self, qtbot):
        host = QWidget()
        qtbot.addWidget(host)
        wrap = QWidget(host)
        inner = QWidget(wrap)
        target = QWidget(inner)
        assert sp.clip_root(target) is host

    def test_scroll_viewport_is_a_boundary(self, qtbot):
        from PySide6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        qtbot.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        wrap = QWidget(page)
        target = QWidget(wrap)
        assert sp.clip_root(target) is scroll.viewport()

    def test_no_parent_means_no_boundary(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        assert sp.clip_root(w) is None


class TestShadowLayerFollowsAncestors:
    def test_layer_follows_a_scrolled_ancestor(self, qtbot):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout

        scroll = QScrollArea()
        scroll.resize(400, 300)
        scroll.setWidgetResizable(True)
        page = QWidget()
        scroll.setWidget(page)
        lay = QVBoxLayout(page)
        wrap = QWidget()
        target = QWidget(wrap)
        target.setFixedSize(120, 60)
        wrap.setFixedSize(120, 60)
        lay.addWidget(wrap)
        for i in range(30):
            lay.addWidget(QLabel(f"row {i}"))
        qtbot.addWidget(scroll)
        scroll.show()
        qtbot.waitExposed(scroll)
        layer = sp.ShadowLayer(target, 8.0, _layers("md"))
        vp = scroll.viewport()

        def gap():
            return layer.pos() - target.mapTo(vp, QPoint(0, 0))

        before = gap()
        scroll.verticalScrollBar().setValue(40)
        qtbot.wait(30)
        assert gap() == before
        assert layer.parentWidget() is vp

    def test_hiding_an_ancestor_hides_the_layer(self, qtbot):
        host = QWidget()
        host.resize(300, 300)
        qtbot.addWidget(host)
        wrap = QWidget(host)
        wrap.setGeometry(40, 40, 150, 100)
        target = QWidget(wrap)
        target.setGeometry(10, 10, 100, 60)
        host.show()
        qtbot.waitExposed(host)
        layer = sp.ShadowLayer(target, 8.0, _layers("md"))
        qtbot.wait(20)
        assert layer.isVisible()
        wrap.hide()
        qtbot.wait(20)
        assert not layer.isVisible()
        wrap.show()
        qtbot.wait(20)
        assert layer.isVisible()

    def test_layer_follows_the_target_to_a_new_window(self, qtbot):
        a, b = QWidget(), QWidget()
        for h in (a, b):
            h.resize(300, 300)
            qtbot.addWidget(h)
        target = QWidget(a)
        target.setGeometry(50, 50, 100, 80)
        a.show()
        qtbot.waitExposed(a)
        layer = sp.ShadowLayer(target, 8.0, _layers("md"))
        assert layer.parentWidget() is a
        target.setParent(b)
        target.move(60, 60)
        b.show()
        target.show()
        qtbot.waitUntil(lambda: layer.parentWidget() is b)
        assert layer.isVisible()

    def test_layer_does_not_block_the_mouse(self, qtbot):
        from PySide6.QtCore import QPoint

        host = QWidget()
        host.resize(300, 300)
        qtbot.addWidget(host)
        target = QWidget(host)
        target.setGeometry(60, 60, 120, 80)
        host.show()
        qtbot.waitExposed(host)
        sp.ShadowLayer(target, 8.0, _layers("lg"))
        # 阴影层叠在目标上方，但鼠标命中仍应落在目标上
        assert host.childAt(QPoint(100, 100)) is target


class TestShadowController:
    def test_no_layer_without_parent(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        ctl = sp.ShadowController(w)
        ctl.set_style("md", 8.0, "light")
        assert ctl._layer is None

    def test_layer_created_after_reparent_and_follows_new_parent(self, qtbot):
        a, b = QWidget(), QWidget()
        for h in (a, b):
            h.resize(300, 300)
            qtbot.addWidget(h)
        w = QWidget()
        w.resize(100, 80)
        ctl = sp.ShadowController(w)
        ctl.set_style("md", 8.0, "light")
        w.setParent(a)
        a.show()
        qtbot.waitUntil(lambda: ctl._layer is not None)
        assert ctl._layer.parentWidget() is a
        w.setParent(b)
        b.show()
        qtbot.waitUntil(lambda: ctl._layer.parentWidget() is b)

    def test_none_tier_hides_layer(self, qtbot):
        host = QWidget()
        host.resize(300, 300)
        qtbot.addWidget(host)
        w = QWidget(host)
        w.setGeometry(50, 50, 100, 80)
        ctl = sp.ShadowController(w)
        host.show()
        w.show()  # 父控件显示后新建的子控件需要显式 show
        ctl.set_style("md", 8.0, "light")
        assert not ctl._layer.isHidden()
        ctl.set_style("none", 8.0, "light")
        assert ctl._layer.isHidden()
