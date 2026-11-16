"""Card 组件测试"""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from hero_side_ui import Button, Card, CardBody, CardFooter, CardHeader, Divider, Text


# ============================================================
# CardHeader 测试
# ============================================================
class TestCardHeaderInit:
    """CardHeader 构造测试"""

    def test_default(self, qtbot):
        h = CardHeader()
        qtbot.addWidget(h)

        assert h.objectName() == "heroCardHeader"
        assert h.layout() is not None
        assert h.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed

    def test_add_widget(self, qtbot):
        h = CardHeader()
        qtbot.addWidget(h)

        label = QLabel("Title")
        h.layout().addWidget(label)
        assert h.layout().count() == 1


# ============================================================
# CardBody 测试
# ============================================================
class TestCardBodyInit:
    """CardBody 构造测试"""

    def test_default(self, qtbot):
        b = CardBody()
        qtbot.addWidget(b)

        assert b.objectName() == "heroCardBody"
        assert b.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding

    def test_add_widget(self, qtbot):
        b = CardBody()
        qtbot.addWidget(b)

        label = QLabel("Content")
        b.layout().addWidget(label)
        assert b.layout().count() == 1

    def test_word_wrap_label_not_clipped(self, qtbot):
        """窄 Card 内 wordWrap QLabel 应按 heightForWidth 拿到足够高度。"""
        card = Card(shadow="none")
        qtbot.addWidget(card)
        body = CardBody()
        label = QLabel("Make beautiful websites regardless of your design experience.")
        label.setWordWrap(True)
        body.layout().addWidget(label)
        card.add_body(body)
        card.setFixedWidth(200)
        card.show()
        qtbot.waitExposed(card)

        required = label.heightForWidth(label.width())
        assert label.height() >= required


# ============================================================
# CardFooter 测试
# ============================================================
class TestCardFooterInit:
    """CardFooter 构造测试"""

    def test_default(self, qtbot):
        f = CardFooter()
        qtbot.addWidget(f)

        assert f.objectName() == "heroCardFooter"
        assert f.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed

    def test_set_blurred(self, qtbot):
        f = CardFooter()
        qtbot.addWidget(f)

        f.set_blurred(True)
        assert f._is_blurred is True

    def test_add_widget(self, qtbot):
        f = CardFooter()
        qtbot.addWidget(f)

        label = QLabel("Action")
        f.layout().addWidget(label)
        assert f.layout().count() == 1


# ============================================================
# Card 构造测试
# ============================================================
class TestCardInit:
    """Card 构造参数测试"""

    def test_default_params(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        assert card._shadow == "sm"
        assert card._radius == "lg"
        assert card._is_hoverable is False
        assert card._is_pressable is False
        assert card._is_disabled is False
        assert card._is_blurred is False
        assert card._is_footer_blurred is False
        assert card._full_width is False
        assert card._theme_mode == "auto"

    def test_custom_params(self, qtbot):
        card = Card(
            shadow="lg",
            radius="sm",
            is_hoverable=True,
            is_pressable=True,
            is_disabled=False,
            is_blurred=True,
            is_footer_blurred=True,
            full_width=True,
            theme="dark",
        )
        qtbot.addWidget(card)

        assert card._shadow == "lg"
        assert card._radius == "sm"
        assert card._is_hoverable is True
        assert card._is_pressable is True
        assert card._is_blurred is True
        assert card._is_footer_blurred is True
        assert card._full_width is True
        assert card._theme == "dark"

    def test_disabled(self, qtbot):
        card = Card(is_disabled=True)
        qtbot.addWidget(card)

        assert card._is_disabled is True


# ============================================================
# Card 三层装配测试
# ============================================================
class TestCardAssembly:
    """三层装配测试"""

    def test_add_header(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        header = CardHeader()
        header.layout().addWidget(QLabel("Title"))
        card.add_header(header)

        assert card.header() is header
        assert card._layout.count() == 1

    def test_add_body(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        body = CardBody()
        body.layout().addWidget(QLabel("Content"))
        card.add_body(body)

        assert card.body() is body
        assert card._layout.count() == 1

    def test_add_footer(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        footer = CardFooter()
        footer.layout().addWidget(QLabel("Action"))
        card.add_footer(footer)

        assert card.footer() is footer
        assert card._layout.count() == 1

    def test_full_assembly(self, qtbot):
        """完整的三层装配"""
        card = Card()
        qtbot.addWidget(card)

        header = CardHeader()
        header.layout().addWidget(QLabel("Title"))
        card.add_header(header)

        body = CardBody()
        body.layout().addWidget(QLabel("Content"))
        card.add_body(body)

        footer = CardFooter()
        footer.layout().addWidget(QLabel("Action"))
        card.add_footer(footer)

        assert card.header() is header
        assert card.body() is body
        assert card.footer() is footer
        assert card._layout.count() == 3

    def test_add_divider(self, qtbot):
        """插入分割线"""
        card = Card()
        qtbot.addWidget(card)

        header = CardHeader()
        card.add_header(header)
        divider = card.add_divider()
        body = CardBody()
        card.add_body(body)

        assert isinstance(divider, Divider)
        assert card._layout.count() == 3

    def test_no_header_body_footer(self, qtbot):
        """空卡片: header/body/footer 均为 None"""
        card = Card()
        qtbot.addWidget(card)

        assert card.header() is None
        assert card.body() is None
        assert card.footer() is None


# ============================================================
# Card 阴影测试
# ============================================================
class TestCardShadow:
    """阴影测试"""

    @pytest.mark.parametrize("shadow", ["none", "sm", "md", "lg"])
    def test_all_shadows(self, qtbot, shadow):
        """所有阴影级别都不应报错"""
        card = Card(shadow=shadow)
        qtbot.addWidget(card)
        assert card._shadow == shadow

    def test_shadow_none_no_effect(self, qtbot):
        """shadow=none 不应添加阴影效果"""
        card = Card(shadow="none")
        qtbot.addWidget(card)
        # shadow=none 且未 disabled → graphicsEffect 应该是 None
        assert card.graphicsEffect() is None


# ============================================================
# Card 圆角测试
# ============================================================
class TestCardRadius:
    """圆角测试"""

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg"])
    def test_all_radius(self, qtbot, radius):
        """所有圆角都不应报错"""
        card = Card(radius=radius)
        qtbot.addWidget(card)
        assert card._radius == radius


# ============================================================
# Card 主题测试
# ============================================================
class TestCardTheme:
    """主题测试"""

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_both_themes(self, qtbot, theme):
        """两种主题都不应报错"""
        card = Card(theme=theme)
        qtbot.addWidget(card)
        assert card._theme == theme

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_theme_with_sections(self, qtbot, theme):
        """主题切换不应影响已装配的子区域"""
        card = Card(theme=theme)
        qtbot.addWidget(card)

        header = CardHeader()
        header.layout().addWidget(QLabel("Title"))
        card.add_header(header)

        body = CardBody()
        body.layout().addWidget(QLabel("Content"))
        card.add_body(body)

        footer = CardFooter()
        footer.layout().addWidget(QLabel("Action"))
        card.add_footer(footer)

        assert card._theme == theme


# ============================================================
# Card 动态 API 测试
# ============================================================
class TestCardDynamicAPI:
    """动态 API 测试"""

    def test_set_shadow(self, qtbot):
        card = Card(shadow="sm")
        qtbot.addWidget(card)

        card.set_shadow("lg")
        assert card._shadow == "lg"

    def test_set_radius(self, qtbot):
        card = Card(radius="md")
        qtbot.addWidget(card)

        card.set_radius("none")
        assert card._radius == "none"

    def test_set_theme(self, qtbot):
        card = Card(theme="light")
        qtbot.addWidget(card)

        card.set_theme("dark")
        assert card._theme == "dark"

    def test_set_is_hoverable(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        card.set_is_hoverable(True)
        assert card._is_hoverable is True

    def test_set_is_pressable(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        card.set_is_pressable(True)
        assert card._is_pressable is True
        assert card._ripple_overlay is not None
        assert card._press_scale is not None

    def test_set_is_disabled(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        card.set_is_disabled(True)
        assert card._is_disabled is True

    def test_set_is_blurred(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        card.set_is_blurred(True)
        assert card._is_blurred is True

    def test_set_is_footer_blurred(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        footer = CardFooter()
        card.add_footer(footer)
        card.set_is_footer_blurred(True)
        assert card._is_footer_blurred is True

    def test_set_full_width(self, qtbot):
        card = Card()
        qtbot.addWidget(card)

        card.set_full_width(True)
        assert card._full_width is True
        assert card.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding


# ============================================================
# Card 信号测试
# ============================================================
class TestCardSignals:
    """信号测试"""

    def test_pressed_signal_when_pressable(self, qtbot):
        """is_pressable=True 时，点击应该触发 pressed 信号"""
        card = Card(is_pressable=True)
        qtbot.addWidget(card)
        card.resize(200, 100)
        card.show()
        qtbot.waitExposed(card)

        with qtbot.waitSignal(card.pressed, timeout=1000):
            qtbot.mouseClick(card, Qt.MouseButton.LeftButton)

    def test_no_pressed_signal_when_disabled(self, qtbot):
        """is_disabled=True 时，点击不应触发 pressed 信号"""
        card = Card(is_pressable=True, is_disabled=True)
        qtbot.addWidget(card)
        card.show()

        signals_emitted = []
        card.pressed.connect(lambda: signals_emitted.append(True))
        qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
        assert len(signals_emitted) == 0

    def _card_with_text(self, qtbot, **kwargs):
        """搭一个标题/正文都是 Text 的 Pressable Card，返回宿主、卡片、标题文字。"""
        host = QWidget()
        host.resize(900, 300)
        lay = QHBoxLayout(host)
        lay.setContentsMargins(20, 20, 20, 100)
        card = Card(shadow="none", **kwargs)
        fired: list = []
        card.pressed.connect(lambda: fired.append(1))
        header = CardHeader()
        label = Text("Pressable", size="lg", weight="bold")
        header.layout().addWidget(label)
        card.add_header(header)
        body = CardBody()
        body.layout().addWidget(Text("Click me! I have a ripple animation."))
        card.add_body(body)
        card.setFixedWidth(220)
        lay.addWidget(card)
        lay.addStretch(1)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        return host, card, fired, label

    def _click_text(self, host, label):
        """走真实命中链点击文字局部坐标 (20, 中线)。"""
        QTest.mouseClick(
            host.windowHandle(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            label.mapTo(host, QPoint(20, label.height() // 2)),
        )

    def test_clicking_text_triggers_one_press_and_one_ripple(self, qtbot):
        """点标题/正文文字应像点卡片空白处一样触发一次水波纹和 pressed。"""
        host, card, fired, label = self._card_with_text(qtbot, is_pressable=True)
        body_label = card._body.findChild(Text)
        for text in (label, body_label):
            fired.clear()
            before = len(card._ripple_overlay._ripples)
            self._click_text(host, text)
            qtbot.wait(30)
            assert len(fired) == 1
            assert len(card._ripple_overlay._ripples) - before == 1  # 逐层传播不能重复加水波纹

    def test_clicking_text_ignored_when_not_pressable_or_disabled(self, qtbot):
        for kwargs in (dict(is_pressable=False), dict(is_pressable=True, is_disabled=True)):
            host, card, fired, label = self._card_with_text(qtbot, **kwargs)
            before = len(card._ripple_overlay._ripples) if card._ripple_overlay else 0
            self._click_text(host, label)
            qtbot.wait(30)
            assert fired == []
            after = len(card._ripple_overlay._ripples) if card._ripple_overlay else 0
            assert after == before

    def test_child_added_after_construction_also_passes_through(self, qtbot):
        """后置装配的文字也触发（ChildAdded 自动挂过滤器）。"""
        host, card, _fired, _label = self._card_with_text(qtbot, is_pressable=True)
        footer = CardFooter()
        late = Text("Late footer", size="sm")
        footer.layout().addWidget(late)
        card.add_footer(footer)
        qtbot.wait(20)
        fired = []
        card.pressed.connect(lambda: fired.append(1))
        self._click_text(host, late)
        qtbot.wait(30)
        assert len(fired) == 1

    def test_interactive_child_still_receives_clicks(self, qtbot):
        """卡片内 Button 自己的点击不能被子控件透传吞掉。"""
        host = QWidget()
        host.resize(600, 200)
        lay = QHBoxLayout(host)
        card = Card(shadow="none")
        btn = Button("go")
        body = CardBody()
        body.layout().addWidget(btn)
        card.add_body(body)
        card.setFixedWidth(200)
        lay.addWidget(card)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        clicked: list = []
        btn.clicked.connect(lambda *_: clicked.append(1))
        QTest.mouseClick(
            host.windowHandle(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            btn.mapTo(host, QPoint(10, 10)),
        )
        qtbot.wait(30)
        assert len(clicked) == 1


# ============================================================
# Card 组合测试
# ============================================================
class TestCardCombinations:
    """组合测试"""

    @pytest.mark.parametrize("shadow", ["none", "sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_shadow_x_theme(self, qtbot, shadow, theme):
        """所有阴影 x 主题组合都不应报错"""
        card = Card(shadow=shadow, theme=theme)
        qtbot.addWidget(card)
        assert card._shadow == shadow
        assert card._theme == theme

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_radius_x_theme(self, qtbot, radius, theme):
        """所有圆角 x 主题组合都不应报错"""
        card = Card(radius=radius, theme=theme)
        qtbot.addWidget(card)

    def test_full_card_with_dividers(self, qtbot):
        """完整卡片 + 分割线"""
        card = Card(shadow="md", radius="lg")
        qtbot.addWidget(card)

        header = CardHeader()
        header.layout().addWidget(QLabel("Title"))
        card.add_header(header)

        card.add_divider()

        body = CardBody()
        body.layout().addWidget(QLabel("Content line 1"))
        body.layout().addWidget(QLabel("Content line 2"))
        card.add_body(body)

        card.add_divider()

        footer = CardFooter()
        footer.layout().addWidget(QLabel("Footer"))
        card.add_footer(footer)

        assert card._layout.count() == 5  # header + divider + body + divider + footer

    def test_pressable_hoverable_card(self, qtbot):
        """可按压 + 可悬停卡片"""
        card = Card(is_pressable=True, is_hoverable=True)
        qtbot.addWidget(card)
        card.show()

        assert card._is_pressable is True
        assert card._is_hoverable is True
        assert card._ripple_overlay is not None
        assert card._press_scale is not None

    def test_blurred_card(self, qtbot):
        """模糊卡片"""
        card = Card(is_blurred=True, is_footer_blurred=True)
        qtbot.addWidget(card)

        footer = CardFooter()
        card.add_footer(footer)

        assert card._is_blurred is True
        assert card._is_footer_blurred is True
