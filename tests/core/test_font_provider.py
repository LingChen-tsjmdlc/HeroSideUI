"""FontProvider 单元测试。

覆盖：

- 单例语义（``instance()`` 复用 + 每次重入触发 ``ensure_loaded``）。
- 内置 VF 思源黑体加载（``ensure_loaded`` 幂等、加载成功后状态正确）。
- 字体栈输出（``font_family_css``，含成功/失败两种分支）。
- 运行时切换字体（``set_family`` + ``family_changed`` 信号 + 广播）。
- **字重解析（VF 6 档物理 instance 路由）**：1~250→ExtraLight、251~350→Light、
  351~450→Regular、451~600→Medium、601~800→Bold、801~1000→Heavy。
- 基准字号（``set_base_size_px`` + ``base_size_changed``）。
- 注册/反注册 + WeakSet 自动清理。
- ``make_qfont`` 工厂便捷函数。
"""

from __future__ import annotations

import gc

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from hero_side_ui.core import FontProvider, make_qfont
from hero_side_ui.core.font_provider import (
    _FALLBACK_FAMILY_CSS,
    _NATIVE_INSTANCES,
    _VF_FAMILY_NAME,
    _is_ghost_family,
)

# ============================================================
# fixtures
# ============================================================


@pytest.fixture(autouse=True)
def reset_font_provider():
    FontProvider._reset_for_test()
    yield
    FontProvider._reset_for_test()


class _FakeWidget:
    """最小注册目标：只暴露 ``_apply_font()``。"""

    def __init__(self):
        self.apply_called = 0

    def _apply_font(self):
        self.apply_called += 1


class _LegacyWidget:
    """走 ``set_font_family(...)`` 旧分支的注册目标。"""

    def __init__(self):
        self.last_family = None

    def set_font_family(self, family: str):
        self.last_family = family


# ============================================================
# 单例
# ============================================================


class TestSingleton:
    def test_instance_returns_same_object(self, qtbot):
        a = FontProvider.instance()
        b = FontProvider.instance()
        assert a is b

    def test_instance_triggers_ensure_loaded(self, qtbot):
        FontProvider._reset_for_test()
        p = FontProvider.instance()
        assert p._loaded is True

    def test_reset_for_test_creates_new_instance(self, qtbot):
        a = FontProvider.instance()
        FontProvider._reset_for_test()
        b = FontProvider.instance()
        assert a is not b


# ============================================================
# ensure_loaded
# ============================================================


class TestEnsureLoaded:
    def test_loaded_after_first_access(self, qtbot):
        p = FontProvider.instance()
        assert p.builtin_loaded is True
        assert p.family == _VF_FAMILY_NAME

    def test_idempotent(self, qtbot):
        p = FontProvider.instance()
        first_id = p._font_id
        p.ensure_loaded()
        p.ensure_loaded()
        assert p._font_id == first_id

    def test_default_base_size_is_16(self, qtbot):
        assert FontProvider.instance().base_size_px == 16

    def test_native_instances_has_6_buckets(self, qtbot):
        p = FontProvider.instance()
        # 6 档原生 instance 必须齐全
        expected = {
            "ExtraLight": 200,
            "Light": 300,
            "Regular": 400,
            "Medium": 500,
            "Bold": 700,
            "Heavy": 900,
        }
        assert p.native_instances == expected
        assert _NATIVE_INSTANCES == expected


# ============================================================
# font_family_css
# ============================================================


class TestFontFamilyCSS:
    def test_success_starts_with_main_family(self, qtbot):
        css = FontProvider.instance().font_family_css()
        assert css.startswith(f'"{_VF_FAMILY_NAME}",')

    def test_success_contains_fallback_stack(self, qtbot):
        css = FontProvider.instance().font_family_css()
        assert _FALLBACK_FAMILY_CSS in css

    def test_fallback_when_builtin_failed(self, qtbot):
        p = FontProvider.instance()
        p._builtin_ok = False
        p._family = _FALLBACK_FAMILY_CSS
        assert p.font_family_css() == _FALLBACK_FAMILY_CSS


# ============================================================
# set_family
# ============================================================


class TestSetFamily:
    def test_change_family_updates_property(self, qtbot):
        p = FontProvider.instance()
        p.set_family("Microsoft YaHei")
        assert p.family == "Microsoft YaHei"

    def test_set_same_family_does_not_emit(self, qtbot):
        p = FontProvider.instance()
        original = p.family
        emitted = []
        p.family_changed.connect(emitted.append)
        p.set_family(original)
        assert emitted == []

    def test_set_family_emits_signal(self, qtbot):
        p = FontProvider.instance()
        emitted = []
        p.family_changed.connect(emitted.append)
        p.set_family("Custom Font")
        assert emitted == ["Custom Font"]

    def test_set_family_strips_whitespace(self, qtbot):
        p = FontProvider.instance()
        p.set_family("  Spaced Font  ")
        assert p.family == "Spaced Font"

    def test_set_empty_restores_builtin_vf(self, qtbot):
        p = FontProvider.instance()
        p.set_family("Custom Font")
        p.set_family("")
        assert p.family == _VF_FAMILY_NAME

    def test_set_family_broadcasts_to_widgets(self, qtbot):
        p = FontProvider.instance()
        w = _FakeWidget()
        p.register(w)
        p.set_family("Some Font")
        assert w.apply_called >= 1

    def test_set_family_uses_legacy_setter(self, qtbot):
        p = FontProvider.instance()
        w = _LegacyWidget()
        p.register(w)
        p.set_family("Legacy Font")
        assert w.last_family == "Legacy Font"


# ============================================================
# resolve_qfont_weight：VF 6 档兜底
# ============================================================


class TestResolveQFontWeight:
    @pytest.mark.parametrize(
        "input_weight,expected",
        [
            # ExtraLight 桶 (1~250)
            (1, 200),
            (100, 200),
            (200, 200),
            (250, 200),
            # Light 桶 (251~350)
            (251, 300),
            (300, 300),
            (350, 300),
            # Regular 桶 (351~450)
            (351, 400),
            (400, 400),
            (450, 400),
            # Medium 桶 (451~600)
            (451, 500),
            (500, 500),
            (600, 500),
            # Bold 桶 (601~800)
            (601, 700),
            (700, 700),
            (800, 700),
            # Heavy 桶 (801~1000)
            (801, 900),
            (900, 900),
            (1000, 900),
        ],
    )
    def test_buckets(self, qtbot, input_weight, expected):
        assert FontProvider.instance().resolve_qfont_weight(input_weight) == expected

    def test_clamps_below_1(self, qtbot):
        assert FontProvider.instance().resolve_qfont_weight(-100) == 200

    def test_clamps_above_1000(self, qtbot):
        assert FontProvider.instance().resolve_qfont_weight(99999) == 900

    @pytest.mark.parametrize("w", [100, 400, 600, 900])
    def test_after_set_family_no_collapse(self, qtbot, w):
        """切到第三方字体后，weight 原值传出，不再走 VF 兜底。"""
        p = FontProvider.instance()
        p.set_family("Arial")
        assert p.resolve_qfont_weight(w) == max(1, min(1000, w))

    def test_when_builtin_failed_no_collapse(self, qtbot):
        p = FontProvider.instance()
        p._builtin_ok = False
        assert p.resolve_qfont_weight(600) == 600


# ============================================================
# style_for_weight：VF 6 档兜底
# ============================================================


class TestStyleForWeight:
    @pytest.mark.parametrize(
        "input_weight,expected_style",
        [
            (100, "ExtraLight"),
            (200, "ExtraLight"),
            (250, "ExtraLight"),
            (251, "Light"),
            (300, "Light"),
            (350, "Light"),
            (351, "Regular"),
            (400, "Regular"),
            (450, "Regular"),
            (451, "Medium"),
            (500, "Medium"),
            (600, "Medium"),
            (601, "Bold"),
            (700, "Bold"),
            (800, "Bold"),
            (801, "Heavy"),
            (900, "Heavy"),
            (1000, "Heavy"),
        ],
    )
    def test_buckets(self, qtbot, input_weight, expected_style):
        assert FontProvider.instance().style_for_weight(input_weight) == expected_style

    def test_returns_none_when_user_changed_family(self, qtbot):
        p = FontProvider.instance()
        p.set_family("Arial")
        assert p.style_for_weight(500) is None

    def test_returns_none_when_builtin_failed(self, qtbot):
        p = FontProvider.instance()
        p._builtin_ok = False
        assert p.style_for_weight(500) is None


# ============================================================
# 基准字号
# ============================================================


class TestBaseSize:
    def test_change_base_size(self, qtbot):
        p = FontProvider.instance()
        p.set_base_size_px(20)
        assert p.base_size_px == 20

    def test_emit_signal(self, qtbot):
        p = FontProvider.instance()
        emitted = []
        p.base_size_changed.connect(emitted.append)
        p.set_base_size_px(18)
        assert emitted == [18]

    def test_same_value_no_emit(self, qtbot):
        p = FontProvider.instance()
        emitted = []
        p.base_size_changed.connect(emitted.append)
        p.set_base_size_px(p.base_size_px)
        assert emitted == []

    def test_clamp_to_at_least_1(self, qtbot):
        p = FontProvider.instance()
        p.set_base_size_px(0)
        assert p.base_size_px == 1

    def test_broadcasts_to_widgets(self, qtbot):
        p = FontProvider.instance()
        w = _FakeWidget()
        p.register(w)
        p.set_base_size_px(22)
        assert w.apply_called >= 1


# ============================================================
# 组件注册
# ============================================================


class TestRegistration:
    def test_register_adds_widget(self, qtbot):
        p = FontProvider.instance()
        w = _FakeWidget()
        p.register(w)
        assert p.is_registered(w)

    def test_unregister(self, qtbot):
        p = FontProvider.instance()
        w = _FakeWidget()
        p.register(w)
        p.unregister(w)
        assert not p.is_registered(w)

    def test_register_rejects_unsupported(self, qtbot):
        p = FontProvider.instance()
        with pytest.raises(TypeError):
            p.register(object())

    def test_weakset_auto_cleanup(self, qtbot):
        p = FontProvider.instance()
        w = _FakeWidget()
        p.register(w)
        assert p.registered_count == 1
        del w
        gc.collect()
        assert p.registered_count == 0

    def test_qwidget_register_and_cleanup(self, qtbot):
        p = FontProvider.instance()
        label = QLabel()
        qtbot.addWidget(label)

        # QLabel 没 _apply_font，但有 set_font_family？默认没有；
        # 我们直接给它打补丁来模拟用户组件
        called = []
        label._apply_font = lambda: called.append(1)
        p.register(label)
        p.set_family("Test Font")
        assert called == [1]

    def test_broadcast_skips_failing_widgets(self, qtbot):
        p = FontProvider.instance()

        class BadWidget:
            def _apply_font(self):
                raise RuntimeError("boom")

        good = _FakeWidget()
        bad = BadWidget()
        p.register(bad)
        p.register(good)
        # 不应抛异常
        p.set_family("Test Font")
        assert good.apply_called >= 1


# ============================================================
# make_qfont
# ============================================================


class TestMakeQFont:
    def test_default_uses_provider_family_and_base_size(self, qtbot):
        f = make_qfont()
        assert f.family() == _VF_FAMILY_NAME
        assert f.pixelSize() == 16

    def test_custom_size(self, qtbot):
        f = make_qfont(size_px=24)
        assert f.pixelSize() == 24

    @pytest.mark.parametrize(
        "weight_in,expected_style,expected_weight",
        [
            (100, "ExtraLight", 200),
            (200, "ExtraLight", 200),
            (300, "Light", 300),
            (400, "Regular", 400),
            (500, "Medium", 500),
            (600, "Medium", 500),  # 451~600 路由到 Medium
            (700, "Bold", 700),
            (800, "Bold", 700),  # 601~800 路由到 Bold
            (900, "Heavy", 900),
        ],
    )
    def test_weight_routes_to_native_style(
        self, qtbot, weight_in, expected_style, expected_weight
    ):
        f = make_qfont(weight=weight_in)
        assert f.styleName() == expected_style
        assert int(f.weight()) == expected_weight

    def test_weight_normal_default(self, qtbot):
        f = make_qfont()
        assert int(f.weight()) == 400
        assert f.styleName() == "Regular"

    def test_make_qfont_follows_set_family(self, qtbot):
        p = FontProvider.instance()
        p.set_family("Arial")
        f = make_qfont(weight=500)
        assert f.family() == "Arial"
        # 切到第三方字体后不再设 styleName
        assert f.styleName() == ""

    def test_make_qfont_follows_set_base_size(self, qtbot):
        p = FontProvider.instance()
        p.set_base_size_px(20)
        f = make_qfont()
        assert f.pixelSize() == 20


# ============================================================
# 诊断
# ============================================================


class TestDiagnostics:
    def test_returns_string_with_key_fields(self, qtbot):
        s = FontProvider.instance().dump_diagnostics()
        assert "FontProvider" in s
        assert "builtin_loaded" in s
        assert "main family" in s
        assert "native instances" in s

    def test_does_not_raise_when_builtin_failed(self, qtbot):
        p = FontProvider.instance()
        p._builtin_ok = False
        p._font_id = -1
        # 不应抛异常
        s = p.dump_diagnostics()
        assert "FontProvider" in s


# ============================================================
# 幽灵 family 过滤
# ============================================================


class TestGhostFamilyFilter:
    def test_main_family_is_not_ghost(self):
        assert _is_ghost_family(_VF_FAMILY_NAME, _VF_FAMILY_NAME) is False

    def test_unrelated_family_is_not_ghost(self):
        assert _is_ghost_family("Microsoft YaHei", _VF_FAMILY_NAME) is False

    def test_instance_subnames_are_ghost(self):
        assert (
            _is_ghost_family(f"{_VF_FAMILY_NAME} ExtraLight", _VF_FAMILY_NAME) is True
        )
        assert _is_ghost_family(f"{_VF_FAMILY_NAME} Heavy", _VF_FAMILY_NAME) is True

    def test_empty_name_is_not_ghost(self):
        assert _is_ghost_family("", _VF_FAMILY_NAME) is False
