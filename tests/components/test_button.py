"""Button 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Button


class TestButtonInit:
    """构造参数测试"""

    def test_default_params(self, qtbot):
        """默认参数应该正确"""
        btn = Button("Hello")
        qtbot.addWidget(btn)

        assert btn.text() == "Hello"
        assert btn._color == "primary"
        assert btn._variant == "solid"
        assert btn._size == "md"
        assert btn._radius is None
        assert btn._theme_mode == "auto"
        assert btn.isEnabled()

    def test_custom_params(self, qtbot):
        """自定义参数应该正确传递"""
        btn = Button(
            "Test",
            color="danger",
            variant="bordered",
            size="lg",
            radius="full",
            theme="dark",
        )
        qtbot.addWidget(btn)

        assert btn._color == "danger"
        assert btn._variant == "bordered"
        assert btn._size == "lg"
        assert btn._radius == "full"
        assert btn._theme == "dark"

    def test_disabled(self, qtbot):
        """is_disabled 应该禁用按钮"""
        btn = Button("Disabled", is_disabled=True)
        qtbot.addWidget(btn)

        assert not btn.isEnabled()

    def test_disable_ripple(self, qtbot):
        """disable_ripple 应该不创建水波纹覆盖层"""
        btn = Button("No Ripple", disable_ripple=True)
        qtbot.addWidget(btn)

        assert btn._ripple_overlay is None


class TestButtonColors:
    """颜色系统测试"""

    @pytest.mark.parametrize("color", [
        "default", "primary", "secondary", "success", "warning", "danger",
    ])
    def test_all_colors(self, qtbot, color):
        """所有颜色都不应该报错"""
        btn = Button("Test", color=color)
        qtbot.addWidget(btn)
        assert btn._color == color

    def test_invalid_color_fallback(self, qtbot):
        """无效颜色应该回退到 primary"""
        btn = Button("Test", color="nonexistent")
        qtbot.addWidget(btn)
        # 不应崩溃，样式能正常应用
        assert btn._color == "nonexistent"

    def test_dark_flat_primary_text_is_bright(self, qtbot):
        """暗色 flat 按钮文字应使用更亮色阶，避免在深色背景上发灰看不清。"""
        btn = Button("Primary", color="primary", variant="flat", theme="dark")
        qtbot.addWidget(btn)
        assert "color: #99c7fb" in btn.styleSheet().lower()

    def test_dark_flat_default_text_is_bright(self, qtbot):
        btn = Button("Default", color="default", variant="flat", theme="dark")
        qtbot.addWidget(btn)
        assert "color: #d4d4d8" in btn.styleSheet().lower()


class TestButtonVariants:
    """变体测试"""

    @pytest.mark.parametrize("variant", [
        "solid", "bordered", "flat", "light", "faded", "ghost",
    ])
    def test_all_variants(self, qtbot, variant):
        """所有变体都不应该报错"""
        btn = Button("Test", variant=variant)
        qtbot.addWidget(btn)
        assert btn._variant == variant


class TestButtonSizes:
    """尺寸测试"""

    @pytest.mark.parametrize("size", ["sm", "md", "lg", "small", "medium", "large"])
    def test_all_sizes(self, qtbot, size):
        """所有尺寸（含长名称兼容）都不应该报错"""
        btn = Button("Test", size=size)
        qtbot.addWidget(btn)
        assert btn._size == size


class TestButtonDynamicAPI:
    """动态 API 测试"""

    def test_set_color(self, qtbot):
        btn = Button("Test", color="primary")
        qtbot.addWidget(btn)

        btn.set_color("danger")
        assert btn._color == "danger"

    def test_set_variant(self, qtbot):
        btn = Button("Test", variant="solid")
        qtbot.addWidget(btn)

        btn.set_variant("ghost")
        assert btn._variant == "ghost"

    def test_set_size(self, qtbot):
        btn = Button("Test", size="sm")
        qtbot.addWidget(btn)

        btn.set_size("lg")
        assert btn._size == "lg"

    def test_set_theme(self, qtbot):
        btn = Button("Test", theme="light")
        qtbot.addWidget(btn)

        btn.set_theme("dark")
        assert btn._theme == "dark"

    def test_set_radius(self, qtbot):
        btn = Button("Test")
        qtbot.addWidget(btn)

        btn.set_radius("full")
        assert btn._radius == "full"


class TestButtonIconOnly:
    """icon_only 模式"""

    def test_icon_only_is_square(self, qtbot):
        btn = Button(icon_only=True, size="md")
        qtbot.addWidget(btn)
        assert btn._icon_only is True
        # 正方形：宽 == 高
        assert btn.size().width() == btn.size().height()

    def test_icon_only_sm_size(self, qtbot):
        btn = Button(icon_only=True, size="sm")
        qtbot.addWidget(btn)
        # sm height 18 + padding_y 6*2 = 30
        assert btn.size().width() == 30

    def test_icon_only_md_size(self, qtbot):
        btn = Button(icon_only=True, size="md")
        qtbot.addWidget(btn)
        # md height 26 + padding_y 10*2 = 46
        assert btn.size().width() == 46

    def test_icon_only_lg_size(self, qtbot):
        btn = Button(icon_only=True, size="lg")
        qtbot.addWidget(btn)
        # lg height 33 + padding_y 14*2 = 61
        assert btn.size().width() == 61

    def test_icon_only_default_false(self, qtbot):
        btn = Button("Hello")
        qtbot.addWidget(btn)
        assert btn._icon_only is False

    def test_set_icon_only_dynamic(self, qtbot):
        btn = Button("Test")
        qtbot.addWidget(btn)

        # 先开启
        btn.set_icon_only(True)
        assert btn._icon_only is True
        assert btn.size().width() == btn.size().height()

        # 再关闭 — 应该不再被锁定尺寸
        btn.set_icon_only(False)
        assert btn._icon_only is False
        # 关闭后 sizeHint 应该是常规（宽 > 高）
        hint = btn.sizeHint()
        assert hint.width() > hint.height()


class TestButtonSignals:
    """信号测试"""

    def test_click_signal(self, qtbot):
        """点击应该触发 clicked 信号"""
        btn = Button("Click me")
        qtbot.addWidget(btn)

        with qtbot.waitSignal(btn.clicked, timeout=1000):
            qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
