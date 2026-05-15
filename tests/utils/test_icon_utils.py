"""hero_side_ui.utils.icon_utils.load_svg_icon 单元测试

覆盖维度：
    - 内置 heroicons 名能加载并返回非空 QPixmap
    - 外部路径能加载
    - 不存在的 name 返回空的透明 pixmap（不抛异常）
    - size 影响输出 pixmap 尺寸
    - color 着色生效（currentColor 被替换）
    - color="original" 保留 SVG 原始颜色
    - color=None 跟随 ThemeProvider 主题选对比色
    - stroke_width 数值生效

通过像素采样 (`QImage.pixelColor`) 验证着色效果，不依赖具体像素位置 ——
对于 24×24 viewBox 的图标，扫描所有像素找有色像素的 RGB 即可。
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QPixmap, QImage

from hero_side_ui.utils import load_svg_icon
from hero_side_ui import ThemeProvider


# ============================================================
# 辅助：从 QPixmap 里抽样找"非透明的有色像素"
# ============================================================


def _non_transparent_pixels(pix: QPixmap) -> list[QColor]:
    """返回所有 alpha > 200 的像素颜色列表（即真正画出来的部分）。"""
    img: QImage = pix.toImage()
    out = []
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 200:
                out.append(c)
    return out


# ============================================================
# 基础加载
# ============================================================


class TestBuiltinIconLoading:
    """内置 heroicons 应能找到并返回有内容的 pixmap。"""

    @pytest.mark.parametrize("name", [
        "heroicons--check-solid",
        "heroicons--chevron-down",
        "heroicons--x-mark",
        "heroicons--eye-solid",
    ])
    def test_builtin_returns_nonempty_pixmap(self, qtbot, name):
        pix = load_svg_icon(name, size=24, color="#FF0000")
        assert isinstance(pix, QPixmap)
        assert not pix.isNull()
        assert pix.width() == 24 and pix.height() == 24
        # 至少有一些像素被画出来
        assert len(_non_transparent_pixels(pix)) > 0

    @pytest.mark.parametrize("size", [12, 16, 24, 48])
    def test_size_controls_output_dimensions(self, qtbot, size):
        pix = load_svg_icon("heroicons--check-solid", size=size, color="#FF0000")
        assert pix.width() == size
        assert pix.height() == size


class TestMissingIconFallback:
    """不存在的图标名应返回空的透明 pixmap，不抛异常。"""

    def test_unknown_name_returns_transparent_pixmap(self, qtbot):
        pix = load_svg_icon("definitely--does--not--exist", size=24)
        assert isinstance(pix, QPixmap)
        # 函数承诺返回 size×size 的透明 pixmap
        assert pix.width() == 24 and pix.height() == 24
        # 没有任何非透明像素
        assert len(_non_transparent_pixels(pix)) == 0

    def test_unknown_path_returns_transparent_pixmap(self, qtbot, tmp_path):
        nonexistent = tmp_path / "nope.svg"
        pix = load_svg_icon(str(nonexistent), size=16)
        assert not _non_transparent_pixels(pix)


# ============================================================
# 着色
# ============================================================


class TestColoring:
    """color 参数会替换 SVG 里的 currentColor。"""

    def test_color_as_hex_string(self, qtbot):
        pix = load_svg_icon("heroicons--check-solid", size=32, color="#FF0000")
        pixels = _non_transparent_pixels(pix)
        assert pixels, "应该有非透明像素"
        # 主要画的颜色应该接近纯红（R 高、G/B 低）
        # 取颜色样本数最多的 RGB（核心像素，排除抗锯齿边）
        reds = [c for c in pixels if c.red() > 200 and c.green() < 60 and c.blue() < 60]
        assert len(reds) > 0, f"找不到红色像素，样本：{pixels[:5]}"

    def test_color_as_qcolor(self, qtbot):
        pix = load_svg_icon("heroicons--check-solid", size=32, color=QColor("#00FF00"))
        pixels = _non_transparent_pixels(pix)
        greens = [c for c in pixels if c.green() > 200 and c.red() < 60 and c.blue() < 60]
        assert len(greens) > 0

    def test_color_original_does_not_replace(self, qtbot):
        """color="original" 保留 SVG 原始描边 (currentColor 未被替换)。

        QSvgRenderer 对 "currentColor" 的处理是当作黑色降级 —— 所以图标
        会被画成黑色。我们验证：传 "original" 时 pixels 含黑色（R/G/B 都很低）。
        """
        pix = load_svg_icon("heroicons--check-solid", size=32, color="original")
        pixels = _non_transparent_pixels(pix)
        blacks = [c for c in pixels if c.red() < 30 and c.green() < 30 and c.blue() < 30]
        assert len(blacks) > 0


# ============================================================
# 主题感知（color=None）
# ============================================================


class TestThemeAwareColoring:
    """color=None 时根据 ThemeProvider 当前主题选对比色。"""

    @pytest.fixture(autouse=True)
    def reset_provider(self):
        ThemeProvider._reset_for_test()
        yield
        ThemeProvider._reset_for_test()

    def test_light_theme_uses_dark_icon(self, qtbot):
        ThemeProvider.instance().set_mode("light")
        pix = load_svg_icon("heroicons--check-solid", size=32)  # color=None
        pixels = _non_transparent_pixels(pix)
        # 亮色主题 → 深色 icon（#18181b ≈ R/G/B 全 < 50）
        darks = [c for c in pixels if c.red() < 50 and c.green() < 50 and c.blue() < 50]
        assert len(darks) > 0

    def test_dark_theme_uses_light_icon(self, qtbot):
        ThemeProvider.instance().set_mode("dark")
        pix = load_svg_icon("heroicons--check-solid", size=32)  # color=None
        pixels = _non_transparent_pixels(pix)
        # 暗色主题 → 浅色 icon（#fafafa ≈ R/G/B 全 > 230）
        lights = [c for c in pixels if c.red() > 230 and c.green() > 230 and c.blue() > 230]
        assert len(lights) > 0


# ============================================================
# stroke_width 替换
# ============================================================


class TestStrokeWidth:
    """stroke_width 数值生效（视觉上加粗描边 → 黑色/有色像素更多）。"""

    def test_thicker_stroke_paints_more_pixels(self, qtbot):
        thin = load_svg_icon("heroicons--check-solid", size=64, color="#FF0000",
                             stroke_width=1.5)
        thick = load_svg_icon("heroicons--check-solid", size=64, color="#FF0000",
                              stroke_width=4.0)
        thin_count = len(_non_transparent_pixels(thin))
        thick_count = len(_non_transparent_pixels(thick))
        # 加粗后应该明显画得更多
        assert thick_count > thin_count

    def test_stroke_width_none_uses_default(self, qtbot):
        """stroke_width=None 保留 SVG 原始值，不应崩。"""
        pix = load_svg_icon("heroicons--check-solid", size=24, color="#FF0000",
                            stroke_width=None)
        assert not pix.isNull()


# ============================================================
# 外部路径
# ============================================================


class TestExternalPath:
    def test_load_from_explicit_path(self, qtbot, tmp_path):
        # 准备一个最简 SVG
        svg = tmp_path / "rect.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            '<rect x="0" y="0" width="24" height="24" fill="currentColor"/>'
            '</svg>',
            encoding="utf-8",
        )
        pix = load_svg_icon(str(svg), size=24, color="#FF0000")
        assert not pix.isNull()
        pixels = _non_transparent_pixels(pix)
        # 整张图都应该是红色
        assert len(pixels) > 500  # 24*24=576 个像素，大部分应被填上
        reds = [c for c in pixels if c.red() > 200 and c.green() < 60 and c.blue() < 60]
        assert len(reds) > 400
