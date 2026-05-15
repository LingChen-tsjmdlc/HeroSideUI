"""hero_side_ui.utils.color_utils 单元测试

测的是两个纯函数：
    - hex_to_rgba: HEX 字符串 → CSS rgba() 字符串
    - aligned_color_pair: 处理 alpha=0 端的 RGB 对齐，避免色彩 lerp 经过深灰

这层是纯函数，零 Qt widget 依赖；唯一用到 Qt 的是 ``QColor`` 数据类型。
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from hero_side_ui.utils import hex_to_rgba, aligned_color_pair


# ============================================================
# hex_to_rgba
# ============================================================


class TestHexToRgba:
    @pytest.mark.parametrize(
        "hex_in, alpha, expected",
        [
            # 带 # / 不带 # 都接受
            ("#006FEE", 0.5, "rgba(0, 111, 238, 0.5)"),
            ("006FEE", 0.5, "rgba(0, 111, 238, 0.5)"),
            # 边界 alpha
            ("#FFFFFF", 0.0, "rgba(255, 255, 255, 0.0)"),
            ("#000000", 1.0, "rgba(0, 0, 0, 1.0)"),
            # 全大写 / 全小写都行
            ("#abcdef", 0.25, "rgba(171, 205, 239, 0.25)"),
            ("#ABCDEF", 0.25, "rgba(171, 205, 239, 0.25)"),
        ],
    )
    def test_valid_inputs(self, hex_in, alpha, expected):
        assert hex_to_rgba(hex_in, alpha) == expected

    def test_output_format_has_three_components_then_alpha(self):
        result = hex_to_rgba("#102030", 0.3)
        # 解析: "rgba(" + "16, 32, 48, 0.3" + ")"
        assert result.startswith("rgba(") and result.endswith(")")
        body = result[5:-1]
        parts = [p.strip() for p in body.split(",")]
        assert len(parts) == 4
        assert parts == ["16", "32", "48", "0.3"]


# ============================================================
# aligned_color_pair
# ============================================================


class TestAlignedColorPair:
    """让 alpha=0 一端的 RGB 等于另一端，避免 lerp 经过 (0,0,0) 深灰。"""

    def test_start_transparent_inherits_end_rgb(self):
        start = QColor(0, 0, 0, 0)  # 透明黑
        end = QColor(0, 111, 238, 255)  # primary
        s, e = aligned_color_pair(start, end)

        # 透明端 RGB 被改写为 end 的 RGB
        assert (s.red(), s.green(), s.blue()) == (end.red(), end.green(), end.blue())
        assert s.alpha() == 0
        # 不透明端原样返回
        assert e.name() == end.name()
        assert e.alpha() == 255

    def test_end_transparent_inherits_start_rgb(self):
        start = QColor(0, 111, 238, 255)
        end = QColor(0, 0, 0, 0)
        s, e = aligned_color_pair(start, end)

        assert (e.red(), e.green(), e.blue()) == (start.red(), start.green(), start.blue())
        assert e.alpha() == 0
        assert s.name() == start.name()
        assert s.alpha() == 255

    def test_both_opaque_returns_copies_unchanged(self):
        start = QColor("#006FEE")
        end = QColor("#f31260")
        s, e = aligned_color_pair(start, end)
        assert s.name() == start.name()
        assert e.name() == end.name()
        assert s.alpha() == 255 and e.alpha() == 255

    def test_both_transparent_returns_as_is(self):
        """两端都是 alpha=0：原样返回，不做改写（语义上没有"色相"可继承）。"""
        start = QColor(10, 20, 30, 0)
        end = QColor(100, 110, 120, 0)
        s, e = aligned_color_pair(start, end)
        # RGB 各自保持原值
        assert (s.red(), s.green(), s.blue()) == (10, 20, 30)
        assert (e.red(), e.green(), e.blue()) == (100, 110, 120)
        assert s.alpha() == 0 and e.alpha() == 0

    def test_does_not_mutate_inputs(self):
        """函数应返回新 QColor，不修改入参。"""
        start = QColor(0, 0, 0, 0)
        end = QColor("#006FEE")
        start_copy = QColor(start)
        end_copy = QColor(end)

        aligned_color_pair(start, end)

        # 入参未被修改
        assert (start.red(), start.green(), start.blue(), start.alpha()) == (
            start_copy.red(), start_copy.green(), start_copy.blue(), start_copy.alpha()
        )
        assert end.name() == end_copy.name()

    def test_returns_independent_qcolor(self):
        """返回的 QColor 与入参不共享对象（防止后续修改污染）。"""
        start = QColor(0, 0, 0, 0)
        end = QColor("#006FEE")
        s, e = aligned_color_pair(start, end)
        assert s is not start
        assert e is not end
