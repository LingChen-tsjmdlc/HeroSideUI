"""Accordion 组件测试"""

import pytest

from hero_side_ui import Accordion, AccordionItem


class TestAccordionItemInit:
    """AccordionItem 构造参数测试"""

    def test_default_params(self, qtbot):
        item = AccordionItem(title="标题", content_text="内容")
        qtbot.addWidget(item)

        assert item._title_text == "标题"
        assert item._expanded is False
        assert item._is_disabled is False

    def test_expanded_init(self, qtbot):
        item = AccordionItem(title="展开", expanded=True)
        qtbot.addWidget(item)

        assert item.is_expanded() is True

    def test_disabled(self, qtbot):
        item = AccordionItem(title="禁用", is_disabled=True)
        qtbot.addWidget(item)

        assert not item.isEnabled()


class TestAccordionInit:
    """Accordion 容器测试"""

    @pytest.mark.parametrize("variant", ["light", "shadow", "bordered", "splitted"])
    def test_all_variants(self, qtbot, variant):
        """四种变体都不应该报错"""
        acc = Accordion(variant=variant)
        qtbot.addWidget(acc)

        item = AccordionItem(title="测试", content_text="内容")
        acc.add_item(item)
        assert len(acc._items) == 1

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg"])
    def test_all_radius(self, qtbot, radius):
        """所有圆角都不应该报错"""
        acc = Accordion(variant="shadow", radius=radius)
        qtbot.addWidget(acc)
        assert acc._radius == radius

    def test_default_params(self, qtbot):
        acc = Accordion()
        qtbot.addWidget(acc)

        assert acc._variant == "light"
        assert acc._allow_multiple is False
        assert acc._size == "md"
        assert acc._theme == "light"


class TestAccordionExpandCollapse:
    """展开/收起逻辑测试"""

    def test_expand_collapse(self, qtbot):
        """手动展开和收起"""
        item = AccordionItem(title="测试", content_text="内容")
        acc = Accordion()
        acc.add_item(item)
        qtbot.addWidget(acc)

        assert not item.is_expanded()

        item.expand()
        assert item.is_expanded()

        item.collapse()
        assert not item.is_expanded()

    def test_toggle(self, qtbot):
        """toggle 切换"""
        item = AccordionItem(title="测试", content_text="内容")
        acc = Accordion()
        acc.add_item(item)
        qtbot.addWidget(acc)

        item.toggle()
        assert item.is_expanded()

        item.toggle()
        assert not item.is_expanded()

    def test_single_expand_mode(self, qtbot):
        """单项展开模式：展开一个应该收起其他"""
        acc = Accordion(allow_multiple=False)
        item1 = AccordionItem(title="A", content_text="aaa")
        item2 = AccordionItem(title="B", content_text="bbb")
        acc.add_item(item1)
        acc.add_item(item2)
        qtbot.addWidget(acc)

        item1.expand()
        assert item1.is_expanded()

        item2.expand()
        assert item2.is_expanded()
        assert not item1.is_expanded()  # 应该被自动收起

    def test_multiple_expand_mode(self, qtbot):
        """多项展开模式：可以同时展开多个"""
        acc = Accordion(allow_multiple=True)
        item1 = AccordionItem(title="A", content_text="aaa")
        item2 = AccordionItem(title="B", content_text="bbb")
        acc.add_item(item1)
        acc.add_item(item2)
        qtbot.addWidget(acc)

        item1.expand()
        item2.expand()
        assert item1.is_expanded()
        assert item2.is_expanded()  # 两个都应该展开


class TestAccordionSignals:
    """信号测试"""

    def test_expanded_changed_signal(self, qtbot):
        """展开时应该发射 expanded_changed(True)"""
        item = AccordionItem(title="测试", content_text="内容")
        acc = Accordion()
        acc.add_item(item)
        qtbot.addWidget(acc)

        with qtbot.waitSignal(item.expanded_changed, timeout=1000):
            item.expand()


class TestAccordionDynamicAPI:
    """动态 API 测试"""

    def test_set_theme(self, qtbot):
        acc = Accordion()
        acc.add_item(AccordionItem(title="A", content_text="a"))
        qtbot.addWidget(acc)

        acc.set_theme("dark")
        assert acc._theme == "dark"

    def test_set_variant(self, qtbot):
        acc = Accordion()
        acc.add_item(AccordionItem(title="A", content_text="a"))
        qtbot.addWidget(acc)

        acc.set_variant("bordered")
        assert acc._variant == "bordered"

    def test_set_radius(self, qtbot):
        acc = Accordion(variant="shadow")
        qtbot.addWidget(acc)

        acc.set_radius("lg")
        assert acc._radius == "lg"

    def test_expand_collapse_all(self, qtbot):
        acc = Accordion(allow_multiple=True)
        item1 = AccordionItem(title="A", content_text="a")
        item2 = AccordionItem(title="B", content_text="b")
        acc.add_item(item1)
        acc.add_item(item2)
        qtbot.addWidget(acc)

        acc.expand_all()
        assert item1.is_expanded()
        assert item2.is_expanded()

        acc.collapse_all()
        assert not item1.is_expanded()
        assert not item2.is_expanded()
