"""阴影不占布局：Card / Image / Table 的尺寸与间距不随阴影档位变化。"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from hero_side_ui import Card, Image, Table
from hero_side_ui.components.card import CardBody
from hero_side_ui.core.shadow_paint import ShadowLayer
from tests._waits import flush, until

# pytest-qt 的 qtbot.addWidget 只持弱引用。调用方若不接住 _show_row 的返回值，宿主窗口会立刻被回收，
# 里面的 Card / Image 跟着在 C++ 侧被删除（macOS 上表现为 "already deleted"），所以这里统一强引用到测试结束。
_LIVE_HOSTS: list[QWidget] = []


@pytest.fixture(autouse=True)
def _release_hosts():
    yield
    _LIVE_HOSTS.clear()


def _layers_in(host: QWidget) -> list:
    return [c for c in host.children() if isinstance(c, ShadowLayer)]


def _show_row(qtbot, widgets, spacing: int = 24) -> QWidget:
    host = QWidget()
    host.resize(1500, 400)
    lay = QHBoxLayout(host)
    lay.setContentsMargins(130, 60, 130, 130)
    lay.setSpacing(spacing)
    for w in widgets:
        lay.addWidget(w)
    lay.addStretch(1)  # 多出来的宽度给弹簧：否则固定宽度的控件会被布局均分空白，间距不再是 spacing
    qtbot.addWidget(host)
    _LIVE_HOSTS.append(host)
    host.show()
    flush(qtbot)
    return host


def _card(tier: str, theme: str = "light") -> Card:
    c = Card(shadow=tier, theme=theme)
    body = CardBody()
    body.layout().addWidget(QLabel(f"card {tier}"))
    c.add_body(body)
    c.setFixedWidth(200)
    return c


class TestCardLayout:
    def test_size_and_spacing_do_not_depend_on_shadow_tier(self, qtbot):
        cards = [_card(t) for t in ("none", "sm", "md", "lg")]
        _show_row(qtbot, cards)
        sizes = {(c.width(), c.height()) for c in cards}
        assert len(sizes) == 1
        geo = [c.geometry() for c in cards]
        gaps = {geo[i + 1].left() - geo[i].right() - 1 for i in range(3)}
        assert gaps == {24}

    def test_one_shadow_layer_per_shadowed_card(self, qtbot):
        cards = [_card(t) for t in ("none", "sm", "md", "lg")]
        host = _show_row(qtbot, cards)
        layers = _layers_in(host)
        assert len(layers) == 3
        assert sum(1 for s in layers if not s.isHidden()) == 3

    def test_disabled_card_hides_shadow_and_restores(self, qtbot):
        card = _card("md")
        host = _show_row(qtbot, [card])
        (layer,) = _layers_in(host)
        card.set_is_disabled(True)
        assert layer.isHidden()
        card.set_is_disabled(False)
        assert not layer.isHidden()

    def test_set_shadow_none_hides_layer(self, qtbot):
        card = _card("lg")
        host = _show_row(qtbot, [card])
        (layer,) = _layers_in(host)
        card.set_shadow("none")
        assert layer.isHidden()

    def test_shell_is_exactly_the_visible_card(self, qtbot):
        card = _card("md")
        _show_row(qtbot, [card])
        # 外壳与卡片本体永远一样大（不再有"外壳比卡片宽"的空白区）
        assert card.width() == 200
        assert card._content.width() == 200
        assert card._content.height() == card.height()

    def test_card_without_parent_creates_no_window(self, qtbot):
        card = _card("lg")
        qtbot.addWidget(card)
        assert card._shadow_ctl._layer is None


class TestShadowEscapesCompactWrappers:
    """阴影不能被包着目标的紧凑容器裁掉（只有滚动区视口与窗口才是裁剪边界）。"""

    def _wrapped(self, qtbot, tier: str):
        from PySide6.QtWidgets import QScrollArea, QVBoxLayout

        host = QWidget()
        host.resize(700, 320)
        scroll = QScrollArea(host)
        scroll.setGeometry(0, 0, 700, 320)
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("pg")
        page.setStyleSheet("#pg{background:#FAFBFD;}")
        scroll.setWidget(page)
        row = QHBoxLayout(page)
        row.setContentsMargins(40, 40, 40, 40)
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        card = Card(shadow=tier, theme="light")
        body = CardBody()
        body.layout().addWidget(QLabel("c"))
        card.add_body(body)
        card.setFixedSize(160, 90)
        v.addWidget(card)
        row.addWidget(wrap)
        row.addStretch(1)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        flush(qtbot)
        return host, scroll, wrap, card

    def _darkness_outside(self, host, wrap, card) -> int:
        """容器右侧 12px、卡片垂直中线处比背景暗多少（亮度差）；该点在 wrap 矩形之外。"""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QColor

        pt = card.mapTo(host, QPoint(card.width() + 12, card.height() // 2))
        assert pt.x() > wrap.mapTo(host, QPoint(wrap.width(), 0)).x()
        img = host.grab().toImage()
        return QColor("#FAFBFD").lightness() - QColor(img.pixel(pt.x(), pt.y())).lightness()

    def test_layer_is_mounted_on_the_viewport_not_on_the_wrapper(self, qtbot):
        _host, scroll, wrap, _card = self._wrapped(qtbot, "md")
        assert [c for c in wrap.children() if isinstance(c, ShadowLayer)] == []
        assert len([c for c in scroll.viewport().children() if isinstance(c, ShadowLayer)]) == 1

    def test_shadow_shows_outside_the_wrapper_and_grows_with_the_tier(self, qtbot):
        values = {}
        for tier in ("none", "md", "lg"):
            host, _scroll, wrap, card = self._wrapped(qtbot, tier)
            values[tier] = self._darkness_outside(host, wrap, card)
        assert values["none"] == 0
        assert values["md"] > 0
        assert values["lg"] > values["md"]


class TestPressableHitArea:
    def test_clicking_next_to_a_pressable_card_does_not_press_it(self, qtbot):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest

        card = Card(is_pressable=True, shadow="sm", theme="light")
        body = CardBody()
        body.layout().addWidget(QLabel("press me"))
        card.add_body(body)
        card.setFixedWidth(200)
        fired: list = []
        card.pressed.connect(lambda: fired.append(1))
        host = QWidget()
        host.resize(700, 300)
        lay = QHBoxLayout(host)
        lay.addWidget(card)
        lay.addStretch(0)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)

        def click(local: QPoint) -> bool:
            fired.clear()
            QTest.mouseClick(
                host.windowHandle(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                card.mapTo(host, local),
            )
            flush(qtbot)
            return bool(fired)

        h = card.height() // 2
        assert click(QPoint(card.width() // 2, h)) is True  # 卡片里面
        assert click(QPoint(card.width() - 3, card.height() - 3)) is True  # 卡片右下角里面
        assert click(QPoint(card.width() + 40, h)) is False  # 右侧空白
        assert click(QPoint(card.width() // 2, card.height() + 20)) is False  # 下方空白


class TestImageLayout:
    def test_size_is_visible_size_regardless_of_shadow(self, qtbot):
        imgs = [Image(width=150, height=100, shadow=t) for t in ("none", "sm", "md", "lg")]
        _show_row(qtbot, imgs)
        assert {(i.width(), i.height()) for i in imgs} == {(150, 100)}

    def test_blur_margin_is_the_only_extra(self, qtbot):
        plain = Image(width=150, height=100, shadow="lg")
        blurred = Image(width=150, height=100, shadow="lg", is_blurred=True)
        _show_row(qtbot, [plain, blurred])
        assert (plain.width(), plain.height()) == (150, 100)
        assert (blurred.width(), blurred.height()) == (150 + 36, 100 + 34)

    def test_set_shadow_does_not_resize(self, qtbot):
        img = Image(width=150, height=100, shadow="none")
        _show_row(qtbot, [img])
        img.set_shadow("lg")
        assert (img.width(), img.height()) == (150, 100)


class TestTableShadow:
    def test_shadow_lives_on_table_not_on_inner_card(self, qtbot):
        table = Table(shadow="md")
        table.set_columns([{"key": "a", "label": "A"}])
        table.add_row("r1", ["1"])
        host = _show_row(qtbot, [table])
        assert len(_layers_in(host)) == 1
        assert _layers_in(table) == []

    def test_set_shadow_none_hides(self, qtbot):
        table = Table(shadow="md")
        host = _show_row(qtbot, [table])
        (layer,) = _layers_in(host)
        table.set_shadow("none")
        assert layer.isHidden()

    def test_remove_wrapper_has_no_shadow(self, qtbot):
        table = Table(shadow="md", remove_wrapper=True)
        host = _show_row(qtbot, [table])
        assert all(s.isHidden() for s in _layers_in(host))


def test_kbd_has_shadow_layer(qtbot):
    from hero_side_ui import Kbd

    host = _show_row(qtbot, [Kbd("K")])
    assert len(_layers_in(host)) == 1
