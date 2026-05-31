"""
╔══════════════════════════════════════════════════════════════════════╗
║  实验性功能 — 未集成到组件库(保留供未来讨论)                         ║
║                                                                      ║
║  Superellipse (超椭圆 / Squircle) 路径生成器                         ║
║                                                                      ║
║  使用 Lamé 曲线方程生成 iOS 风格的平滑圆角矩形：                     ║
║      |x/a|^n + |y/b|^n = 1                                           ║
║                                                                      ║
║  ── 为什么没有集成到组件库？──                                       ║
║                                                                      ║
║  2026-06-01 经完整实现 + PS 叠加验证后的决策：                       ║
║                                                                      ║
║    1. 视觉差异在小尺寸组件上不够显著（R=8 时偏差约 24px，            ║
║       但在按钮等小元素上人眼难以分辨）                               ║
║    2. 集成成本高：每个圆角组件的 paintEvent 都需要                   ║
║       drawRoundedRect → squircle_path + drawPath，                   ║
║       QSS 组件（Button/Alert/Accordion）无法使用                     ║
║    3. 混合使用会导致视觉不一致：部分组件"鼓角"、部分标准圆角         ║
║    4. 增加后续每个新组件的维护负担                                   ║
║                                                                      ║
║  ── 什么场景下值得重新启用？──                                       ║
║                                                                      ║
║    - 大尺寸容器类组件：Card / Modal / Dialog / Sheet                 ║
║      （R=14~20+ 时差异明显，22px+ 偏差肉眼可见）                     ║
║    - 品牌 icon/logo 容器                                             ║
║    - 用户明确要求 iOS 风格的项目                                     ║
║                                                                      ║
║  ── 技术细节 ──                                                      ║
║                                                                      ║
║  参数映射：                                                          ║
║    smoothness=0.0 → n=2  (椭圆，退化 = 标准圆角)                     ║
║    smoothness=0.6 → n=5  (iOS 图标风格)                              ║
║    smoothness=1.0 → n=10 (接近矩形但角部圆滑)                        ║
║                                                                      ║
║  算法演进：                                                          ║
║    v1: Figma corner smoothing (贝塞尔过渡 + 裁切圆弧)                ║
║        → 最大偏差 < 1px，PS 叠加验证完全重合 → 废弃                  ║
║    v2 (当前): Superellipse (Lamé 曲线)                               ║
║        → 最大偏差 20-24px (R=14, n=5)，视觉差异明显                  ║
║                                                                      ║
║  参考：                                                              ║
║    - Apple iOS icon shape (since iOS 7)                              ║
║    - "Desperately Seeking Squircles" — Figma Blog                    ║
║    - Piet Hein's Superellipse                                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QPainterPath


def _smoothness_to_n(smoothness: float) -> float:
    """将 smoothness [0,1] 映射为超椭圆指数 n。

    n 越大越接近矩形，越小越接近椭圆。
    """
    s = max(0.0, min(1.0, smoothness))
    # 线性映射: 0→2, 0.6→5, 1.0→10
    return 2.0 + s * 8.0


def _se_point(a: float, b: float, n: float, theta: float) -> QPointF:
    """超椭圆参数方程单点。

    Args:
        a, b: 半轴长 (半宽, 半高)
        n:   指数 (>0)
        θ:   参数角 [0, 2π)

    Returns:
        超椭圆上的点
    """
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    pow_n = 2.0 / n

    x = a * _signed_pow(cos_t, pow_n)
    y = b * _signed_pow(sin_t, pow_n)

    return QPointF(x, y)


def _signed_pow(v: float, p: float) -> float:
    """带符号的幂运算。sign(v) * |v|^p"""
    if abs(v) < 1e-15:
        return 0.0
    return math.copysign(abs(v) ** p, v)


def squircle_path(
    rect: QRectF,
    radius: float,
    smoothness: float = 0.6,
) -> QPainterPath:
    """生成超椭圆 (Squircle) 圆角矩形路径。

    与标准 addRoundedRect 的关键区别：
      - 标准圆角：四边是直线 + 四角是 1/4 圆弧，角部曲率突变 (G1)
      - 超椭圆：整体连续平滑曲线，角部自然外鼓 (G2+)

    Args:
        rect:       矩形区域
        radius:     圆角半径 hint (px)。用于退化回标准圆角的阈值判断；
                     超椭圆本身由 smoothness 控制形状，不直接使用此值
        smoothness: 平滑度/超椭圆指数 [0, 1]
                    0=椭圆(n=2), 0.6=iOS(n=5), 1=近方(n=10)

    Returns:
        QPainterPath 可用于 drawPath() 或 setClipPath()
    """
    # 退化条件：回到 Qt 原生路径
    if radius <= 0:
        p = QPainterPath()
        p.addRect(rect)
        return p

    if smoothness <= 0:
        R = min(radius, rect.width() / 2, rect.height() / 2)
        p = QPainterPath()
        p.addRoundedRect(rect, R, R)
        return p

    w = rect.width()
    h = rect.height()

    # 正方形或接近正方形时用纯超椭圆效果最好
    # 长条形需要混合直线段避免边缘过弯
    aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 1.0

    n = _smoothness_to_n(smoothness)
    cx = rect.x() + w / 2
    cy = rect.y() + h / 2
    a = w / 2  # 半宽
    b = h / 2  # 半高

    if aspect < 3.0:
        # 形状较方正 → 纯超椭圆，自然有平直感
        return _pure_superellipse_path(cx, cy, a, b, n)
    else:
        # 长条形 → 角部超椭圆 + 边缘直线段
        return _hybrid_squircle_path(rect, cx, cy, a, b, n)


def _pure_superellipse_path(
    cx: float,
    cy: float,
    a: float,
    b: float,
    n: float,
) -> QPainterPath:
    """纯超椭圆采样路径。

    在整个周长上均匀采样，用折线逼近曲线。
    采样密度随尺寸和 n 值自适应：n 越大角部越尖锐，需要更密采样。
    """
    # 自适应采样数：基础 256 点 + 按 n 补充角部精度
    base_samples = 256
    extra = int(n * 32)  # n 大时角部弯曲剧烈，加采样
    num_samples = base_samples + extra

    path = QPainterPath()

    # 第一个点
    pt0 = _se_point(a, b, n, 0)
    path.moveTo(cx + pt0.x(), cy + pt0.y())

    # 逐点连线
    for i in range(1, num_samples + 1):
        theta = 2 * math.pi * i / num_samples
        pt = _se_point(a, b, n, theta)
        path.lineTo(cx + pt.x(), cy + pt.y())

    path.closeSubpath()
    return path


def _hybrid_squircle_path(
    rect: QRectF,
    cx: float,
    cy: float,
    a: float,
    b: float,
    n: float,
) -> QPainterPath:
    """混合模式：角部用超椭圆曲线，中间用直线连接。

    适用于长条形组件 (aspect ratio > 3)，防止边缘过度弯曲。
    """
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    # 找超椭圆与「距离边缘一定距离」的水平/垂直线的交点
    # 用这个距离决定直线段和曲段的分界
    blend = min(w, h) * 0.35  # 混合区大小

    # 计算四个角区域的参数范围（简化：用固定角度范围）
    # 更精确的做法是数值求解交点，这里用近似
    corner_angle = min(1.0, blend / max(a, b)) * (math.pi / 4)

    path = QPainterPath()

    # 从上边中点开始，顺时针
    # 上边 (从左到右): θ ≈ π → 0
    start_theta = math.pi
    # 右上角区域
    rt_start = math.pi - corner_angle
    rt_end = -corner_angle  # 即 2π - corner_angle

    # ── 上边直线段 ──
    top_y = cy - b * _signed_pow(math.sin(rt_end), 2.0 / n)
    top_x_right = cx + a * _signed_pow(math.cos(rt_end), 2.0 / n)
    top_x_left = cx + a * _signed_pow(math.cos(math.pi - rt_end), 2.0 / n)

    path.moveTo(top_x_left, top_y)
    path.lineTo(top_x_right, top_y)

    # ── 右上角超椭圆弧 ──
    _append_arc(path, cx, cy, a, b, n, rt_end, rt_start - 2 * math.pi)

    # ── 右边直线段 ──
    right_x = cx + a * _signed_pow(math.cos(math.pi / 2 - corner_angle), 2.0 / n)
    right_y_top = cy + b * _signed_pow(math.sin(math.pi / 2 - corner_angle), 2.0 / n)
    right_y_bot = cy + b * _signed_pow(math.sin(corner_angle - math.pi / 2), 2.0 / n)
    path.lineTo(right_x, right_y_bot)

    # ── 右下角 ──
    _append_arc(
        path, cx, cy, a, b, n, math.pi / 2 - corner_angle, corner_angle - math.pi / 2
    )

    # ── 下边直线段 ──
    bot_y = cy + b * _signed_pow(math.sin(corner_angle), 2.0 / n)
    bot_x_left = cx - a * _signed_pow(math.cos(corner_angle), 2.0 / n)
    path.lineTo(bot_x_left, bot_y)

    # ── 左下角 ──
    _append_arc(path, cx, cy, a, b, n, math.pi - corner_angle, math.pi + corner_angle)

    # ── 左边直线段 ──
    left_x = cx - a * _signed_pow(math.cos(math.pi - corner_angle), 2.0 / n)
    path.lineTo(left_x, top_y)

    # ── 左上角 ──
    _append_arc(
        path, cx, cy, a, b, n, -math.pi / 2 + corner_angle, -corner_angle - math.pi / 2
    )

    path.closeSubpath()
    return path


def _append_arc(
    path: QPainterPath,
    cx: float,
    cy: float,
    a: float,
    b: float,
    n: float,
    theta_start: float,
    theta_end: float,
) -> None:
    """向 path 追加一段超椭圆弧。theta_start → theta_end，顺时针。"""
    # 归一化到正区间
    while theta_end <= theta_start:
        theta_end += 2 * math.pi

    arc_len = abs(theta_end - theta_start)
    n_seg = max(16, int(arc_len * 48 / (math.pi / 2)))  # 每 π/2 至少 48 段

    for i in range(1, n_seg + 1):
        t = theta_start + (theta_end - theta_start) * i / n_seg
        pt = _se_point(a, b, n, t)
        path.lineTo(cx + pt.x(), cy + pt.y())
