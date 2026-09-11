"""Badge 组件测试"""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QLabel, QPushButton

from hero_side_ui import Badge, Button
from hero_side_ui.themes import BADGE_PLACEMENT_OFFSETS, BADGE_SIZES

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("solid", "flat", "faded", "shadow")
SIZES = ("sm", "md", "lg")
SHAPES = ("rectangle", "circle")
PLACEMENTS = ("top-right", "top-left", "bottom-right", "bottom-left")


class TestBadgeInit:
    """构造参数与默认值"""

    def test_default_no_args(self, qtbot):
        b = Badge()
        qtbot.addWidget(b)
        assert b._content == ""
        assert b._color == "default"
        assert b._variant == "solid"
        assert b._size == "md"
        assert b._shape == "rectangle"
        assert b._placement == "top-right"
        assert b._show_outline is True
        assert b._is_invisible is False
        assert b._disable_animation is False
        assert b._theme_mode == "auto"

    def test_custom_params(self, qtbot):
        b = Badge(
            content="9",
            color="danger",
            variant="flat",
            size="lg",
            shape="circle",
            placement="bottom-left",
            show_outline=False,
            theme="dark",
        )
        qtbot.addWidget(b)
        assert b._content == "9"
        assert b._color == "danger"
        assert b._variant == "flat"
        assert b._size == "lg"
        assert b._shape == "circle"
        assert b._placement == "bottom-left"
        assert b._show_outline is False
        assert b._theme == "dark"

    def test_invalid_values_fall_back(self, qtbot):
        b = Badge(variant="ghost", size="xxl", shape="hex", placement="middle")
        qtbot.addWidget(b)
        assert b._variant == "solid"
        assert b._size == "md"
        assert b._shape == "rectangle"
        assert b._placement == "top-right"

    def test_widget_wrapped(self, qtbot):
        child = QPushButton("点我")
        b = Badge(child, content="3")
        qtbot.addWidget(b)
        assert b.widget() is child
        assert child.parent() is b


class TestContentShapes:
    """isDot / isOneChar / 多字符自动判定与尺寸"""

    def test_dot_size(self, qtbot):
        b = Badge(content="", size="md")
        qtbot.addWidget(b)
        assert b._badge.width() == BADGE_SIZES["md"]["dot"]
        assert b._badge.height() == BADGE_SIZES["md"]["dot"]

    def test_one_char_size(self, qtbot):
        b = Badge(content="5", size="md")
        qtbot.addWidget(b)
        assert b._badge.width() == BADGE_SIZES["md"]["one_char"]
        assert b._badge.height() == BADGE_SIZES["md"]["one_char"]

    def test_multi_char_size(self, qtbot):
        b = Badge(content="99+", size="md")
        qtbot.addWidget(b)
        cfg = BADGE_SIZES["md"]
        assert b._badge.height() == cfg["multi_height"]
        assert b._badge.width() >= cfg["multi_height"]

    def test_set_content_updates_shape(self, qtbot):
        b = Badge(content="5", size="md")
        qtbot.addWidget(b)
        one = BADGE_SIZES["md"]["one_char"]
        dot = BADGE_SIZES["md"]["dot"]
        assert b._badge.width() == one
        b.set_content("")
        assert b._badge.width() == dot
        b.set_content("ab")
        assert b._badge.width() > BADGE_SIZES["md"]["one_char"]
        assert b.content() == "ab"
        assert b._label.text() == "ab"

    def test_dot_label_empty_text(self, qtbot):
        b = Badge(content="")
        qtbot.addWidget(b)
        assert isinstance(b._label, QLabel)
        assert b._label.text() == ""


class TestPlacementGeometry:
    """官方 placement×shape 定位：中心悬在内容边缘 5%/10% 锚点上，
    且角标完整落在 Badge 容器内（父 widget 会裁剪悬出子件）。"""

    def _center(self, b: Badge) -> QPointF:
        # 连续几何中心：QRect.center() 整数语义有 (w-1)/2 偏差，会引入 1px 假差
        g = b._badge.geometry()
        return QPointF(g.x() + g.width() / 2, g.y() + g.height() / 2)

    def _content_rect(self, b: Badge):
        m = b._badge_margin()
        return b.rect().adjusted(m, m, -m, -m)

    def _resized(self, b: Badge, w: int, h: int) -> None:
        # 隐藏态 resize 的 QResizeEvent 被 Qt 延迟到 show 才派发，直接调几何更新验证定位公式
        b.resize(w, h)
        b._update_badge_geometry()

    def test_top_right_rectangle(self, qtbot):
        b = Badge(content="5", placement="top-right")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        p = BADGE_PLACEMENT_OFFSETS["rectangle"]
        r = self._content_rect(b)
        c = self._center(b)
        assert abs(c.x() - (r.x() + r.width() * (1 - p))) <= 1
        assert abs(c.y() - (r.y() + r.height() * p)) <= 1

    def test_top_left_rectangle(self, qtbot):
        b = Badge(content="5", placement="top-left")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        p = BADGE_PLACEMENT_OFFSETS["rectangle"]
        r = self._content_rect(b)
        c = self._center(b)
        assert abs(c.x() - (r.x() + r.width() * p)) <= 1
        assert abs(c.y() - (r.y() + r.height() * p)) <= 1

    def test_bottom_right_circle(self, qtbot):
        b = Badge(content="5", placement="bottom-right", shape="circle")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        self._assert_circle_anchor(b)

    def test_bottom_left_circle(self, qtbot):
        b = Badge(content="5", placement="bottom-left", shape="circle")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        self._assert_circle_anchor(b)

    def _assert_circle_anchor(self, b: Badge):
        # circle：角标中心在 45° 对角线上，悬出内容中心距离 = half + 0.65*角标半径
        r = self._content_rect(b)
        half = min(r.width(), r.height()) / 2
        d = half + 0.65 * b._badge.width() / 2
        step = d / 2 ** 0.5
        c = self._center(b)
        cx0, cy0 = r.x() + r.width() / 2, r.y() + r.height() / 2
        sx = 1 if "right" in b._placement else -1
        sy = -1 if b._placement.startswith("top") else 1
        assert abs(c.x() - (cx0 + sx * step)) <= 1
        assert abs(c.y() - (cy0 + sy * step)) <= 1

    def test_circle_bite_constant_across_content_sizes(self, qtbot):
        # 回归：官方矩形百分比锚点对圆形内容咬合随内容半径漂移（大内容悬空），
        # circle 模型咬合恒为 0.35 倍角标半径
        for side in (40, 56, 80):
            inner = QLabel("J")
            inner.setFixedSize(side, side)
            b = Badge(inner, content="9", shape="circle", placement="top-right")
            qtbot.addWidget(b)
            b.resize(side + 40, side + 40)
            b._update_badge_geometry()
            c = self._center(b)
            r = b.widget().geometry()
            dist = ((c.x() - (r.x() + r.width() / 2)) ** 2 + (c.y() - (r.y() + r.height() / 2)) ** 2) ** 0.5
            overshoot = dist - r.width() / 2
            expected = 0.65 * b._badge.width() / 2
            # 容差 1.2px：setGeometry 取整损失约 0.7px
            assert abs(overshoot - expected) <= 1.2, f"side={side}: overshoot {overshoot:.1f} != {expected:.1f}"

    def test_badge_fully_inside_container(self, qtbot):
        # 回归：角标悬出内容边缘但不得超出 Badge 容器（超出部分被父裁剪）
        for placement in PLACEMENTS:
            b = Badge(Button("通知"), content="99+", placement=placement)
            qtbot.addWidget(b)
            self._resized(b, b.sizeHint().width(), b.sizeHint().height())
            g = b._badge.geometry()
            assert b.rect().contains(g), f"{placement}: {g} not in {b.rect()}"

    def test_stretched_container_anchors_to_wrapped_widget(self, qtbot):
        # 回归：父布局把 Badge 拉大（宽于 hint）时，Fixed 内容居中不填满，
        # 角标必须贴被包裹件实际矩形而不是整个容器
        inner = QLabel("J")
        inner.setFixedSize(56, 56)
        b = Badge(inner, content="9", placement="top-right")
        qtbot.addWidget(b)
        b.resize(159, 80)
        b._update_badge_geometry()
        p = BADGE_PLACEMENT_OFFSETS["rectangle"]
        r = inner.geometry()
        c = self._center(b)
        assert abs(c.x() - (r.x() + r.width() * (1 - p))) <= 1
        assert abs(c.y() - (r.y() + r.height() * p)) <= 1
        assert b.rect().contains(b._badge.geometry())

    def test_set_placement_updates_geometry(self, qtbot):
        b = Badge(content="5", placement="top-right")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        y_top = self._center(b).y()
        b.set_placement("bottom-right")
        y_bottom = self._center(b).y()
        assert y_bottom > y_top

    def test_set_shape_updates_geometry(self, qtbot):
        b = Badge(content="5", placement="top-right")
        qtbot.addWidget(b)
        self._resized(b, 100, 100)
        x_rect = self._center(b).x()
        b.set_shape("circle")
        x_circle = self._center(b).x()
        assert x_circle < x_rect  # circle 偏移 10% > rectangle 5%，更靠内


class TestStyles:
    """配色 / 描边 / 投影 / 主题"""

    def test_all_variants_apply(self, qtbot):
        for v in VARIANTS:
            for c in COLORS:
                b = Badge(content="5", variant=v, color=c, theme="light")
                qtbot.addWidget(b)
                b._apply_styles()
                assert b._badge._bg is not None
                assert b._badge._bg.isValid()

    def test_show_outline_border(self, qtbot):
        b = Badge(content="5", show_outline=True, theme="light")
        qtbot.addWidget(b)
        assert b._badge._border_width == 2
        assert b._badge._border_color.name() == "#ffffff"
        b.set_show_outline(False)
        assert b._badge._border_color is None
        assert b._badge._border_width == 0

    def test_outline_dark_uses_black(self, qtbot):
        b = Badge(content="5", show_outline=True, theme="dark")
        qtbot.addWidget(b)
        assert b._badge._border_color.name() == "#000000"

    def test_shadow_variant_has_effect(self, qtbot):
        b = Badge(content="5", variant="shadow", color="primary")
        qtbot.addWidget(b)
        assert b._badge.graphicsEffect() is not None

    def test_solid_variant_no_effect(self, qtbot):
        b = Badge(content="5", variant="solid")
        qtbot.addWidget(b)
        assert b._badge.graphicsEffect() is None

    def test_set_color_updates(self, qtbot):
        b = Badge(content="5", color="default")
        qtbot.addWidget(b)
        b.set_color("danger")
        assert b._color == "danger"

    def test_set_size_updates(self, qtbot):
        b = Badge(content="5", size="sm")
        qtbot.addWidget(b)
        b.set_size("lg")
        assert b._badge.width() == BADGE_SIZES["lg"]["one_char"]


class TestVisibility:
    """isInvisible 显隐逻辑"""

    def test_invisible_at_ctor_hides_badge(self, qtbot):
        b = Badge(content="5", is_invisible=True)
        qtbot.addWidget(b)
        b.show()
        assert b._badge.isHidden()
        assert b.is_invisible() is True

    def test_set_invisible_no_animation(self, qtbot):
        b = Badge(content="5", disable_animation=True)
        qtbot.addWidget(b)
        b.show()
        assert not b._badge.isHidden()
        b.set_invisible(True)
        assert b._badge.isHidden()
        b.set_invisible(False)
        assert not b._badge.isHidden()

    def test_set_invisible_same_value_noop(self, qtbot):
        b = Badge(content="5", disable_animation=True)
        qtbot.addWidget(b)
        b.show()
        b.set_invisible(False)
        assert not b._badge.isHidden()


class TestWrappedWidget:
    """children 管理"""

    def test_set_widget_replaces(self, qtbot):
        b = Badge(QPushButton("A"), content="1")
        qtbot.addWidget(b)
        child2 = QPushButton("B")
        b.set_widget(child2)
        assert b.widget() is child2

    def test_set_widget_none_clears(self, qtbot):
        b = Badge(QPushButton("A"), content="1")
        qtbot.addWidget(b)
        b.set_widget(None)
        assert b.widget() is None

    def test_wrapped_button(self, qtbot):
        btn = Button("消息")
        b = Badge(btn, content="3")
        qtbot.addWidget(b)
        assert b.widget() is btn
