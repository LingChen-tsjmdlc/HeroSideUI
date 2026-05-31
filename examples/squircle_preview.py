"""Squircle 对比 Demo — Superellipse (超椭圆) vs 标准 G1 圆角

新算法: |x/a|^n + |y/b|^n = 1
  n=2 → 椭圆(最圆) | n=5 → iOS 风格 | n=10 → 近方(锐)

关键改进:
  - 偏差量级: 旧版 <1px → 新版 20~40px（肉眼明显可见）
  - 用实际组件尺寸 (R=12~20) 展示
  - 右上角大图放大 + 纯描边叠加
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
)
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QLinearGradient,
)

from hero_side_ui.utils.squircle import squircle_path

# ─── 配色 ──────────────────────────────────────────────
BG = "#0f0f11"
CARD_BG = "#1e1e22"
G1_COLOR = QColor(255, 95, 86)     # 红 — 标准
G2_COLOR = QColor(64, 169, 255)    # 蓝 — 超椭圆
TEXT_COLOR = QColor(200, 200, 200)
HINT_DIM = QColor(150, 150, 150)


def _font(size: int, bold: bool = False) -> QFont:
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    f = QFont("Segoe UI", size)
    f.setWeight(w)
    return f


# ════════════════════════════════════════════════════════
#  1. 实际组件尺寸对比 — 按钮/卡片级别
# ════════════════════════════════════════════════════════
class RealComponentCompare(QWidget):
    """用真实 UI 组件尺寸对比：按钮(R=8)、卡片(R=14)、大卡(R=20)"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(700, 260)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setFont(_font(11, True))
        p.setPen(TEXT_COLOR)
        p.drawText(10, 18, "真实组件尺寸 — 超椭圆 vs 标准圆角")

        configs = [
            ("按钮", 8, 120, 44),
            ("卡片", 14, 220, 160),
            ("大卡片", 20, 280, 180),
        ]

        x_start = 20
        y_off = 38

        for i, (label, r, cw, ch) in enumerate(configs):
            x = x_start + i * (cw + 24)
            rect = QRectF(x, y_off, cw, ch)

            g1 = QPainterPath()
            g1.addRoundedRect(rect, r, r)
            g2 = squircle_path(rect, r, 0.6)

            # 先画 G2 底
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(G2_COLOR.red(), G2_COLOR.green(), G2_COLOR.blue(), 30))
            p.drawPath(g2)

            # G1 描边 (红)
            p.setPen(QPen(G1_COLOR, 2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(g1)

            # G2 描边 (蓝)
            p.setPen(QPen(G2_COLOR, 2.5))
            p.drawPath(g2)

            # 标签
            p.setFont(_font(9, True))
            p.setPen(TEXT_COLOR)
            p.drawText(QRectF(x, y_off + ch + 6, cw, 20),
                       Qt.AlignmentFlag.AlignCenter,
                       f"{label} R={r}")
        p.end()


# ════════════════════════════════════════════════════════
#  2. 右上角大图局部放大
# ════════════════════════════════════════════════════════
class BigZoomCorner(QWidget):
    """右上角区域裁切放大，G1 vs G2 并排"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(700, 400)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setFont(_font(11, True))
        p.setPen(TEXT_COLOR)
        p.drawText(10, 18, "右上角放大 4× — 注意蓝线在角落处「鼓出来」")

        # 用 R=14 的卡片尺寸（最常用）
        full_w, full_h = 300, 200
        R = 14
        n_samples = 500

        # 构建两个路径
        rect_full = QRectF(0, 0, full_w, full_h)
        g1 = QPainterPath()
        g1.addRoundedRect(rect_full, R, R)
        g2 = squircle_path(rect_full, R, 0.6)

        zoom = 4.0
        zoom_w = int(full_w * zoom)
        zoom_h = int(full_h * zoom)
        margin_x = 30
        y_top = 35

        for idx, (label, color, path) in enumerate([
            ("G1 标准 border-radius", G1_COLOR, g1),
            ("G2 超椭圆 (n=5)", G2_COLOR, g2),
        ]):
            zx = margin_x + idx * (zoom_w + 50)

            # 放大背景
            p.setPen(QPen(QColor("#333"), 1))
            p.setBrush(QColor("#14141a"))
            p.drawRect(zx, y_top, zoom_w, zoom_h)

            # 放大绘制
            p.save()
            p.setClipRect(zx, y_top, zoom_w, zoom_h)
            p.translate(zx, y_top)
            p.scale(zoom, zoom)

            p.setPen(QPen(color, 1.5 / zoom))  # 缩放后线宽
            p.setBrush(QColor(color.red(), color.green(), color.blue(), 15))
            p.drawPath(path)

            # 边框参考线
            p.setPen(QPen(QColor(255, 255, 255, 25), 0.5 / zoom, Qt.PenStyle.DashLine))
            p.drawRect(rect_full)

            p.restore()

            # 标签
            p.setFont(_font(9, True))
            p.setPen(color)
            p.drawText(zx, y_top + zoom_h + 18, label)

        # 下方：叠加小图
        mini_s = 140
        mini_scale = mini_s / max(full_w, full_h)
        mx = margin_x + 0 * (zoom_w + 50)
        my = y_top + zoom_h + 45

        p.save()
        p.translate(mx, my)
        p.scale(mini_scale, mini_scale)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#222"))
        p.drawRect(rect_full)

        p.setPen(QPen(G1_COLOR, 3 / mini_scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(g1)

        p.setPen(QPen(G2_COLOR, 3 / mini_scale))
        p.drawPath(g2)

        # 黄色放大区标注
        crop_pct = 0.35
        cx0 = int(full_w * (1 - crop_pct))
        cy0 = 0
        cw_crop = int(full_w * crop_pct)
        ch_crop = int(full_h * crop_pct)
        p.setPen(QPen(QColor(255, 220, 0), 2 / mini_scale))
        p.setBrush(QColor(255, 220, 0, 20))
        p.drawRect(QRectF(cx0, cy0, cw_crop, ch_crop))

        p.restore()

        p.setFont(_font(8))
        p.setPen(QColor(255, 220, 0))
        p.drawText(mx, my + mini_s + 14, "黄框 = 上方放大区域")

        # 叠加图例
        p.setFont(_font(9))
        p.setPen(G1_COLOR)
        p.drawText(mx + mini_s + 20, my + 20, "━ G1 标准")
        p.setPen(G2_COLOR)
        p.drawText(mx + mini_s + 20, my + 36, "━ G2 超椭圆")

        p.end()


# ════════════════════════════════════════════════════════
#  3. 纯描边叠加 — 只看线条偏移
# ════════════════════════════════════════════════════════
class OutlineOverlay(QWidget):
    """同一位置画两根线，直线段重合，角部分开"""

    def __init__(self, radius=14):
        super().__init__()
        self.r = radius
        self.setFixedSize(320, 340)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        sz = 240
        x0 = (self.width() - sz) // 2
        y0 = 42
        rect = QRectF(x0, y0, sz, sz)

        g1 = QPainterPath()
        g1.addRoundedRect(rect, self.r, self.r)
        g2 = squircle_path(rect, self.r, 0.6)

        # G1 粗红线
        p.setPen(QPen(G1_COLOR, 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(g1)

        # G2 粗蓝线 — 完全重叠
        p.setPen(QPen(G2_COLOR, 3))
        p.drawPath(g2)

        # 标题
        p.setFont(_font(10, True))
        p.setPen(TEXT_COLOR)
        p.drawText(QRectF(0, 0, self.width(), 35),
                   Qt.AlignmentFlag.AlignCenter,
                   f"描边叠加 R={self.r} — 角部双色分离")

        # 图例
        ly = y0 + sz + 16
        p.setFont(_font(9))
        p.setPen(G1_COLOR)
        p.drawText(x0, ly, "━ G1 标准圆角")
        p.setPen(G2_COLOR)
        p.drawText(x0 + 130, ly, "━ G2 超椭圆")

        p.setPen(HINT_DIM)
        p.setFont(_font(8))
        p.drawText(x0, ly + 18,
                   "四条边完全重合 → 四个角蓝线向外鼓出 → 这就是 iOS 的感觉")

        p.end()


# ════════════════════════════════════════════════════════
#  4. n 指数梯度 — 从椭圆到近方的连续变化
# ════════════════════════════════════════════════════════
class ExponentGradient(QWidget):
    """n = 2 → 3 → 5 → 7 → 10 的形状变化"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(680, 190)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setFont(_font(11, True))
        p.setPen(TEXT_COLOR)
        p.drawText(10, 18, "指数梯度 (n) — 同一个矩形，只变 n 值")

        items = [
            (0.0, "n=2\n椭圆"),
            (0.2, "n≈3.6\n圆润"),
            (0.6, "n=5\niOS 风格"),
            (0.75, "n≈8\n较锐"),
            (1.0, "n=10\n近方"),
        ]

        n_items = len(items)
        gap = 12
        margin = 10
        card_w = (self.width() - 2 * margin - (n_items - 1) * gap) / n_items
        card_h = 130
        y_off = 38

        for i, (s, label) in enumerate(items):
            x = margin + i * (card_w + gap)
            rect = QRectF(x, y_off, card_w, card_h)
            path = squircle_path(rect, min(card_w, card_h) / 3, s)

            grad = QLinearGradient(x, y_off, x, y_off + card_h)
            grad.setColorAt(0, QColor(80, 140, 230))
            grad.setColorAt(1, QColor(25, 28, 40))

            p.setPen(QPen(QColor(100, 170, 255), 2))
            p.setBrush(QBrush(grad))
            p.drawPath(path)

            p.setPen(QColor("#ddd"))
            p.setFont(_font(8))
            p.drawText(QRectF(x, y_off, card_w, card_h),
                       Qt.AlignmentFlag.AlignCenter, label)
        p.end()


# ════════════════════════════════════════════════════════
#  5. 渐变填充对比 — 最直观的整体形状差异
# ════════════════════════════════════════════════════════
class GradientShapePair(QWidget):
    """两个渐变填充的形状并排，一眼看出整体轮廓不同"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(680, 240)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setFont(_font(11, True))
        p.setPen(TEXT_COLOR)
        p.drawText(10, 18, "整体轮廓对比 — 填充后一目了然")

        w, h = 280, 180
        gap = 60
        y_off = 35
        r = 20

        for idx, (label, color, s) in enumerate([
            ("标准 G1 圆角矩形", G1_COLOR, None),
            ("超椭圆 Squircle (n=5)", G2_COLOR, 0.6),
        ]):
            x = 28 + idx * (w + gap)
            rect = QRectF(x, y_off, w, h)

            if s is None:
                path = QPainterPath()
                path.addRoundedRect(rect, r, r)
            else:
                path = squircle_path(rect, r, s)

            grad = QLinearGradient(x, y_off, x + w, y_off + h)
            grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 180))
            grad.setColorAt(1, QColor(15, 15, 20))

            p.setPen(QPen(color, 2.5))
            p.setBrush(QBrush(grad))
            p.drawPath(path)

            p.setPen(color)
            p.setFont(_font(9, True))
            p.drawText(QRectF(x, y_off, w, h),
                       Qt.AlignmentFlag.AlignCenter, label)
        p.end()


# ════════════════════════════════════════════════════════
#  主窗口
# ════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    content = QWidget()
    content.setStyleSheet(f"background: {BG};")
    layout = QVBoxLayout(content)
    layout.setSpacing(22)
    layout.setContentsMargins(22, 22, 22, 22)

    title = QLabel("Superellipse (超椭圆) vs 标准 G1 圆角")
    title.setStyleSheet(
        "color: white; font-size: 17px; font-weight: bold; padding: 8px;"
    )
    layout.addWidget(title)

    hint = QLabel(
        "红 = 标准 border-radius (G1)  │  "
        "蓝 = 超椭圆 Squircle (n=5, iOS 风格)  │  "
        "算法从 Figma corner smoothing 替换为 Lamé 曲线"
    )
    hint.setStyleSheet("color: #888; font-size: 10px; padding: 2px 6px;")
    layout.addWidget(hint)

    # ① 整体填充轮廓对比
    layout.addWidget(GradientShapePair())

    # ② 真实组件尺寸
    layout.addWidget(RealComponentCompare())

    # ③ 右上角大图放大
    layout.addWidget(BigZoomCorner())

    # ④ 纯描边叠加 (多半径)
    row = QHBoxLayout()
    row.setSpacing(8)
    for r in [8, 14, 20]:
        row.addWidget(OutlineOverlay(r))
    layout.addLayout(row)

    # ⑤ 指数梯度
    layout.addWidget(ExponentGradient())

    scroll = QScrollArea()
    scroll.setWidget(content)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(
        f"QScrollArea {{ background: {BG}; border: none; }}"
        "QScrollBar:vertical { width: 8px; background: #1a1a1e; }"
        "QScrollBar::handle:vertical { background: #444; border-radius: 4px; min-height: 30px; }"
    )

    w = QWidget()
    w.setStyleSheet(f"background: {BG};")
    outer = QVBoxLayout(w)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(scroll)

    w.resize(720, 920)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
