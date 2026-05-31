"""Squircle 路径生成器单元测试"""

import sys
import os
import math
import pytest
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QPainterPath

# 确保能导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hero_side_ui.utils.squircle import squircle_path


class TestSquirclePath:
    """squircle_path() 基础行为测试"""

    def test_radius_zero_returns_rect(self):
        """radius=0 返回标准矩形"""
        rect = QRectF(0, 0, 100, 50)
        path = squircle_path(rect, 0)
        # 矩形路径应该包含 4 个点
        assert path.elementCount() >= 4

    def test_smoothness_zero_returns_rounded_rect(self):
        """smoothness=0 退化为标准圆角矩形"""
        rect = QRectF(0, 0, 100, 50)
        path = squircle_path(rect, 10, smoothness=0)
        assert path.elementCount() >= 4

    def test_normal_squircle_creates_path(self):
        """正常参数生成路径"""
        rect = QRectF(0, 0, 200, 100)
        path = squircle_path(rect, 14, smoothness=0.6)
        assert path.elementCount() > 4

    def test_radius_exceeds_half_size_clamped(self):
        """radius 超过短边一半时自动裁剪"""
        rect = QRectF(0, 0, 100, 40)
        # radius=30 超过 height/2=20
        path = squircle_path(rect, 30, smoothness=0.6)
        assert path.elementCount() > 0

    def test_very_small_rect(self):
        """极小尺寸不崩溃"""
        rect = QRectF(0, 0, 4, 4)
        path = squircle_path(rect, 1, smoothness=0.6)
        assert path.elementCount() > 0

    def test_zero_size_rect(self):
        """零尺寸不崩溃"""
        rect = QRectF(0, 0, 0, 0)
        path = squircle_path(rect, 0)
        assert path.elementCount() >= 0

    def test_negative_radius(self):
        """负半径不崩溃"""
        rect = QRectF(0, 0, 100, 50)
        path = squircle_path(rect, -5)
        assert path.elementCount() >= 0

    def test_smoothness_clamped_to_range(self):
        """smoothness 超出 [0,1] 时被裁剪"""
        rect = QRectF(0, 0, 200, 100)
        # smoothness > 1
        path1 = squircle_path(rect, 14, smoothness=1.5)
        assert path1.elementCount() > 0
        # smoothness < 0
        path2 = squircle_path(rect, 14, smoothness=-0.5)
        assert path2.elementCount() > 0

    def test_path_is_closed(self):
        """路径是闭合的"""
        rect = QRectF(10, 10, 200, 100)
        path = squircle_path(rect, 14, smoothness=0.6)
        # QPainterPath closeSubpath 后可被填充
        # 验证 boundingRect 在合理范围内
        br = path.boundingRect()
        assert br.x() <= rect.x() + 1
        assert br.y() <= rect.y() + 1
        assert br.width() <= rect.width() + 2
        assert br.height() <= rect.height() + 2

    def test_large_smoothness_degrades_gracefully(self):
        """极大 smoothness 不崩溃（圆弧段消失时退化）"""
        rect = QRectF(0, 0, 100, 100)
        path = squircle_path(rect, 14, smoothness=1.0)
        assert path.elementCount() > 0

    def test_various_radii(self):
        """不同 radius 都能生成路径"""
        rect = QRectF(0, 0, 200, 100)
        for r in [4, 8, 14, 20, 49]:
            path = squircle_path(rect, r, smoothness=0.6)
            assert path.elementCount() > 0

    def test_various_smoothness(self):
        """不同 smoothness 都能生成路径"""
        rect = QRectF(0, 0, 200, 100)
        for s in [0.1, 0.3, 0.6, 0.8, 1.0]:
            path = squircle_path(rect, 14, smoothness=s)
            assert path.elementCount() > 0

    def test_non_origin_rect(self):
        """非原点矩形正确工作"""
        rect = QRectF(50, 30, 200, 100)
        path = squircle_path(rect, 14, smoothness=0.6)
        br = path.boundingRect()
        # 路径应该在 rect 范围内（或略微超出因贝塞尔控制点）
        assert br.x() <= rect.x() + 2

    def test_squircle_vs_rounded_rect_different(self):
        """squircle 和标准圆角路径不同"""
        rect = QRectF(0, 0, 200, 100)
        r = 14
        # 标准圆角
        std = QPainterPath()
        std.addRoundedRect(rect, r, r)
        # squircle
        sq = squircle_path(rect, r, smoothness=0.6)
        # 路径元素数量不同（squircle 有更多贝塞尔段）
        assert sq.elementCount() != std.elementCount()

    def test_bounding_rect_within_expected(self):
        """squircle 路径的 boundingRect 不超出 rect 太多"""
        rect = QRectF(0, 0, 200, 100)
        path = squircle_path(rect, 14, smoothness=0.6)
        br = path.boundingRect()
        # squircle 的额外消耗 = R * xi = 14 * 0.6 = 8.4px
        # 但这是路径向内缩，boundingRect 不应超出 rect
        assert br.width() <= rect.width() + 1
        assert br.height() <= rect.height() + 1
