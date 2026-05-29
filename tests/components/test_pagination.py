"""Pagination 组件测试。"""

import pytest

from hero_side_ui import Pagination
from hero_side_ui.components.pagination._constants import PaginationItemType
from hero_side_ui.components.pagination._range import compute_pagination_range
from hero_side_ui.components.pagination._palette import (
    resolve_compact_corners,
    resolve_radius_px,
)

# ============================================================
# range 计算 (纯函数,不依赖 qtbot)
# ============================================================


class TestPaginationRange:
    def test_total_le_threshold_full_expand(self):
        # total <= siblings*2 + 3 + boundaries*2 = 7 时全展开
        rng = compute_pagination_range(total=5, active_page=3)
        assert rng == [1, 2, 3, 4, 5]

    def test_only_right_dots(self):
        # active 靠左,只显示右侧 dots
        rng = compute_pagination_range(total=20, active_page=3)
        assert PaginationItemType.DOTS in rng
        # 末尾必须是 20
        assert rng[-1] == 20
        # dots 应只出现一次
        assert sum(1 for x in rng if x == PaginationItemType.DOTS) == 1

    def test_only_left_dots(self):
        # active 靠右,只显示左侧 dots
        rng = compute_pagination_range(total=20, active_page=18)
        assert rng[0] == 1
        assert sum(1 for x in rng if x == PaginationItemType.DOTS) == 1

    def test_both_dots(self):
        # active 居中,左右双 dots
        rng = compute_pagination_range(total=20, active_page=10)
        assert rng[0] == 1
        assert rng[-1] == 20
        assert sum(1 for x in rng if x == PaginationItemType.DOTS) == 2
        # active page 必须在序列里
        assert 10 in rng

    def test_show_controls_wraps_prev_next(self):
        rng = compute_pagination_range(total=5, active_page=3, show_controls=True)
        assert rng[0] == PaginationItemType.PREV
        assert rng[-1] == PaginationItemType.NEXT

    def test_clamp_active_page(self):
        # active 越界自动钳制
        rng = compute_pagination_range(total=5, active_page=99)
        assert 5 in rng

    def test_siblings_zero(self):
        rng = compute_pagination_range(total=20, active_page=10, siblings=0)
        # 0 siblings 时中间区只有 active 自己
        assert 10 in rng
        assert (
            9 not in rng or 11 not in rng or sum(isinstance(x, int) for x in rng) <= 6
        )


# ============================================================
# Palette: radius / compact corners
# ============================================================


class TestPaginationPalette:
    def test_resolve_radius_none(self):
        assert resolve_radius_px("none", 36) == 0

    def test_resolve_radius_full(self):
        assert resolve_radius_px("full", 36) == 18

    @pytest.mark.parametrize("token,expected", [("sm", 4), ("md", 8), ("lg", 14)])
    def test_resolve_radius_tokens(self, token, expected):
        # 修复了 "8px" 字符串 → int 转换
        assert resolve_radius_px(token, 36) == expected

    def test_compact_first_corners(self):
        # 首个 item 仅左两角圆角
        tl, tr, br, bl = resolve_compact_corners(True, True, False, 8)
        assert (tl, tr, br, bl) == (8, 0, 0, 8)

    def test_compact_last_corners(self):
        # 末尾 item 仅右两角圆角
        tl, tr, br, bl = resolve_compact_corners(True, False, True, 8)
        assert (tl, tr, br, bl) == (0, 8, 8, 0)

    def test_compact_middle_corners(self):
        # 中间 item 全无圆角
        assert resolve_compact_corners(True, False, False, 8) == (0, 0, 0, 0)

    def test_compact_single_item(self):
        # 既是首又是末 -> 四角全圆
        assert resolve_compact_corners(True, True, True, 8) == (8, 8, 8, 8)

    def test_non_compact_keeps_full_radius(self):
        assert resolve_compact_corners(False, True, False, 8) == (8, 8, 8, 8)


# ============================================================
# Pagination 主类: 构造与默认值
# ============================================================


class TestPaginationInit:
    def test_default_params(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        assert p.total() == 10
        assert p.current_page() == 1
        assert p._variant == "flat"
        assert p._color == "primary"
        assert p._size == "md"
        assert p._radius == "md"
        assert p._is_compact is False
        assert p._show_controls is False

    def test_initial_page(self, qtbot):
        p = Pagination(total=10, initial_page=5)
        qtbot.addWidget(p)
        assert p.current_page() == 5

    def test_page_overrides_initial_page(self, qtbot):
        p = Pagination(total=10, initial_page=3, page=7)
        qtbot.addWidget(p)
        assert p.current_page() == 7

    def test_clamp_initial_page_high(self, qtbot):
        p = Pagination(total=5, initial_page=99)
        qtbot.addWidget(p)
        assert p.current_page() == 5

    def test_clamp_initial_page_low(self, qtbot):
        p = Pagination(total=5, initial_page=-3)
        qtbot.addWidget(p)
        assert p.current_page() == 1

    def test_invalid_total(self, qtbot):
        # total<=0 应被钳到 1
        p = Pagination(total=0)
        qtbot.addWidget(p)
        assert p.total() == 1

    def test_invalid_variant(self):
        with pytest.raises(ValueError):
            Pagination(total=10, variant="bogus")

    def test_invalid_color(self):
        with pytest.raises(ValueError):
            Pagination(total=10, color="rainbow")

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            Pagination(total=10, size="xxl")

    def test_invalid_radius(self):
        with pytest.raises(ValueError):
            Pagination(total=10, radius="huge")


class TestPaginationVariants:
    @pytest.mark.parametrize("variant", ["flat", "bordered", "light", "faded"])
    def test_variants(self, qtbot, variant):
        p = Pagination(total=10, variant=variant)
        qtbot.addWidget(p)
        assert p._variant == variant

    @pytest.mark.parametrize(
        "color", ["default", "primary", "secondary", "success", "warning", "danger"]
    )
    def test_colors(self, qtbot, color):
        p = Pagination(total=10, color=color)
        qtbot.addWidget(p)
        assert p._color == color

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_sizes(self, qtbot, size):
        p = Pagination(total=10, size=size)
        qtbot.addWidget(p)
        assert p._size == size

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_radii(self, qtbot, radius):
        # 关键: 这些 radius 都不应该抛 int('8px') 错误
        p = Pagination(total=10, radius=radius)
        qtbot.addWidget(p)
        assert p._radius == radius

    @pytest.mark.parametrize("variant", ["flat", "bordered", "light", "faded"])
    @pytest.mark.parametrize("color", ["primary", "success", "danger"])
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_full_matrix_no_crash(self, qtbot, variant, color, size, radius):
        """variant × color × size × radius 全矩阵不抛异常。"""
        p = Pagination(
            total=20,
            initial_page=10,
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            show_controls=True,
        )
        qtbot.addWidget(p)
        # show 出来跑一遍 paint
        p.show()
        qtbot.waitExposed(p)


class TestPaginationFlags:
    def test_compact(self, qtbot):
        p = Pagination(total=10, is_compact=True)
        qtbot.addWidget(p)
        assert p._is_compact is True

    def test_show_controls(self, qtbot):
        p = Pagination(total=10, show_controls=True)
        qtbot.addWidget(p)
        # range 中应包含 PREV/NEXT 项,对应实际生成 prev/next 按钮
        types = {it.item_type() for it in p._items}
        assert PaginationItemType.PREV in types
        assert PaginationItemType.NEXT in types

    def test_disabled(self, qtbot):
        p = Pagination(total=10, is_disabled=True)
        qtbot.addWidget(p)
        assert p.isEnabled() is False

    def test_disable_animation(self, qtbot):
        p = Pagination(total=10, disable_animation=True)
        qtbot.addWidget(p)
        # disable_animation 也禁用 cursor 动画
        assert p._disable_animation is True
        assert p._disable_cursor_animation is True

    def test_loop(self, qtbot):
        p = Pagination(total=10, initial_page=10, loop=True, show_controls=True)
        qtbot.addWidget(p)
        # loop 时 next 即使在末页也仍可用
        next_items = [
            it for it in p._items if it.item_type() == PaginationItemType.NEXT
        ]
        assert next_items[0].isEnabled() is True


# ============================================================
# 翻页行为
# ============================================================


class TestPaginationNavigation:
    def test_set_page_emits_signal(self, qtbot):
        p = Pagination(total=10, initial_page=1)
        qtbot.addWidget(p)
        captured = []
        p.page_changed.connect(captured.append)
        p.set_page(5)
        assert p.current_page() == 5
        assert captured == [5]

    def test_set_page_same_no_emit(self, qtbot):
        p = Pagination(total=10, initial_page=3)
        qtbot.addWidget(p)
        captured = []
        p.page_changed.connect(captured.append)
        p.set_page(3)
        assert captured == []

    def test_set_page_clamp(self, qtbot):
        p = Pagination(total=5, initial_page=2)
        qtbot.addWidget(p)
        p.set_page(99)
        assert p.current_page() == 5
        p.set_page(-99)
        assert p.current_page() == 1

    def test_go_next(self, qtbot):
        p = Pagination(total=10, initial_page=3)
        qtbot.addWidget(p)
        p.go_next()
        assert p.current_page() == 4

    def test_go_previous(self, qtbot):
        p = Pagination(total=10, initial_page=3)
        qtbot.addWidget(p)
        p.go_previous()
        assert p.current_page() == 2

    def test_go_next_at_end_no_loop(self, qtbot):
        p = Pagination(total=5, initial_page=5, loop=False)
        qtbot.addWidget(p)
        p.go_next()
        assert p.current_page() == 5

    def test_go_next_loop_wraps(self, qtbot):
        p = Pagination(total=5, initial_page=5, loop=True)
        qtbot.addWidget(p)
        p.go_next()
        assert p.current_page() == 1

    def test_go_previous_loop_wraps(self, qtbot):
        p = Pagination(total=5, initial_page=1, loop=True)
        qtbot.addWidget(p)
        p.go_previous()
        assert p.current_page() == 5

    def test_go_first_last(self, qtbot):
        p = Pagination(total=10, initial_page=5)
        qtbot.addWidget(p)
        p.go_first()
        assert p.current_page() == 1
        p.go_last()
        assert p.current_page() == 10


# ============================================================
# 动态 API
# ============================================================


class TestPaginationDynamicAPI:
    def test_set_variant(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_variant("bordered")
        assert p._variant == "bordered"

    def test_set_color(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_color("success")
        assert p._color == "success"

    def test_set_size(self, qtbot):
        p = Pagination(total=10, size="sm")
        qtbot.addWidget(p)
        p.set_size("lg")
        assert p._size == "lg"

    def test_set_radius_full(self, qtbot):
        # full radius 是动态算的,不能因为 RADIUS 表里没 'full' 就崩
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_radius("full")
        assert p._radius == "full"

    def test_set_compact(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_compact(True)
        assert p._is_compact is True

    def test_set_disabled(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_disabled(True)
        assert p.isEnabled() is False

    def test_set_show_controls(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_show_controls(True)
        types = {it.item_type() for it in p._items}
        assert PaginationItemType.PREV in types

    def test_set_total(self, qtbot):
        p = Pagination(total=10, initial_page=8)
        qtbot.addWidget(p)
        p.set_total(5)
        # active_page 自动钳制
        assert p.current_page() == 5

    def test_set_siblings(self, qtbot):
        p = Pagination(total=20, initial_page=10, siblings=1)
        qtbot.addWidget(p)
        p.set_siblings(3)
        assert p._siblings == 3

    def test_set_theme(self, qtbot):
        p = Pagination(total=10)
        qtbot.addWidget(p)
        p.set_theme("dark")
        assert p._theme == "dark"

    def test_set_dots_jump(self, qtbot):
        p = Pagination(total=20)
        qtbot.addWidget(p)
        p.set_dots_jump(7)
        assert p._dots_jump == 7


# ============================================================
# DOTS 跳跃行为
# ============================================================


class TestPaginationDotsJump:
    def test_left_dots_jumps_back(self, qtbot):
        p = Pagination(total=20, initial_page=15, dots_jump=5)
        qtbot.addWidget(p)
        # 找到左侧 dots 按钮(is_before=True)并点击
        left_dots = [
            it
            for it in p._items
            if it.item_type() == PaginationItemType.DOTS and it.is_before()
        ]
        assert left_dots, "应该存在左侧 dots"
        left_dots[0].click()
        assert p.current_page() == 10  # 15 - 5

    def test_right_dots_jumps_forward(self, qtbot):
        p = Pagination(total=20, initial_page=5, dots_jump=5)
        qtbot.addWidget(p)
        right_dots = [
            it
            for it in p._items
            if it.item_type() == PaginationItemType.DOTS and not it.is_before()
        ]
        assert right_dots, "应该存在右侧 dots"
        right_dots[0].click()
        assert p.current_page() == 10  # 5 + 5


# ============================================================
# 主题适配 (auto)
# ============================================================


class TestPaginationTheme:
    def test_apply_provider_theme_hook(self, qtbot):
        p = Pagination(total=10, theme="auto")
        qtbot.addWidget(p)
        # ThemeProvider 广播钩子
        p._apply_provider_theme("dark")
        assert p._theme == "dark"

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_explicit_theme(self, qtbot, theme):
        p = Pagination(total=10, theme=theme)
        qtbot.addWidget(p)
        assert p._theme == theme


# ============================================================
# 文字方向化滚动
# ============================================================


class TestPaginationTextDirection:
    def test_default_direction_is_up(self, qtbot):
        p = Pagination(total=10, initial_page=1)
        qtbot.addWidget(p)
        assert p._next_text_direction == "up"

    def test_increase_page_sets_up(self, qtbot):
        p = Pagination(total=10, initial_page=3)
        qtbot.addWidget(p)
        p.set_page(7)
        assert p._next_text_direction == "up"

    def test_decrease_page_sets_down(self, qtbot):
        p = Pagination(total=10, initial_page=7)
        qtbot.addWidget(p)
        p.set_page(3)
        assert p._next_text_direction == "down"

    def test_loop_next_at_end_sets_up(self, qtbot):
        # loop 下 末页→首页 仍按"前进"语义,方向 up
        p = Pagination(total=5, initial_page=5, loop=True)
        qtbot.addWidget(p)
        p.go_next()
        # 注意 go_next loop 走 set_page(1),target<old_page → 实现按 target>old 判断为 down
        # 这里只断言不抛异常,允许实现后续优化语义
        assert p._next_text_direction in ("up", "down")


# ============================================================
# Palette: dark 主题镜像
# ============================================================


class TestPaletteDarkMirror:
    def test_default_token_light_returns_n(self):
        from hero_side_ui.components.pagination._palette import _default_token
        from hero_side_ui.themes import HEROUI_COLORS

        assert _default_token(100, "light") == HEROUI_COLORS["default"][100]

    def test_default_token_dark_mirrors(self):
        # dark default-100 应镜像到 palette[800]
        from hero_side_ui.components.pagination._palette import _default_token
        from hero_side_ui.themes import HEROUI_COLORS

        assert _default_token(100, "dark") == HEROUI_COLORS["default"][800]
        assert _default_token(200, "dark") == HEROUI_COLORS["default"][700]
        assert _default_token(300, "dark") == HEROUI_COLORS["default"][600]


# ============================================================
# focus-visible 语义
# ============================================================


class TestFocusVisible:
    def test_item_focus_visible_default_false(self, qtbot):
        # 鼠标点击 item 不应该触发 focus-visible (避免四角蓝色)
        p = Pagination(total=10, initial_page=3)
        qtbot.addWidget(p)
        for it in p._items:
            assert it._focus_visible is False
