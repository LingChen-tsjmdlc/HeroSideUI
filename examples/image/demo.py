"""Image 组件示例 — 对齐 HeroUI Image 页面全部示例。

示例:
 1. Default        — 基本用法
 2. Sizes          — width/height 几档（含只设一边按比例自适应）
 3. Radius         — none/sm/md/lg/full
 4. Shadow         — none/sm/md/lg
 5. Zoomed         — hover 放大 zoom_factor
 6. Blurred        — 模糊副本背景
 7. ObjectFit      — cover/contain/fill/none/scale-down
 8. AnimatedLoad   — Skeleton → loaded 切换
 9. Fallback       — 加载失败显示备用图
10. removeWrapper  — 去掉 wrapper

远程图源使用 https://uapis.cn/api/v1/random/image —— 该接口每次请求会返回
随机一张图片。
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QSizePolicy

from hero_side_ui import (
    Image,
    Button,
    Caption,
)
from _base import DemoBase

# 开启组件内部的加载失败警告日志，控制台可见
logging.basicConfig(
    level=logging.WARNING, format="[%(name)s] %(levelname)s: %(message)s"
)

# 远程随机图 API（用户指定）
RANDOM_IMG = "https://uapis.cn/api/v1/random/image"
# 必获必必 Bing 每日一图，Fallback 示例中用作 fallback_src
BING_DAILY = "https://uapis.cn/api/v1/image/bing-daily"
# 故意篝改接口路径——模拟“上一个随机图 API 获取失败”
BAD_URL = "https://uapis.cn/api/v1/random/image_BROKEN_PATH_404"


def _label(text: str) -> Caption:
    """带样式的小说明文本。"""
    cap = Caption(text)
    return cap


def _row(*widgets: QWidget, spacing: int = 16) -> QWidget:
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    # 顶端对齐：阴影越大 wrapper 越高，避免被居中后整图下沉
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    for w in widgets:
        lay.addWidget(w, 0, Qt.AlignmentFlag.AlignTop)
    box.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    return box


def _column(*widgets: QWidget, spacing: int = 6) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
    for w in widgets:
        lay.addWidget(w)
    return box


# ============================================================
# 1. Default
# ============================================================
def _make_default() -> QWidget:
    # 不传 width/height —— 加载完成后按原图尺寸与比例展示
    img = Image(src=RANDOM_IMG)
    return img


# ============================================================
# 2. Sizes
# ============================================================
def _make_sizes() -> QWidget:
    s1 = Image(src=RANDOM_IMG, width=120, height=80)
    s2 = Image(src=RANDOM_IMG, width=200, height=130)
    s3 = Image(src=RANDOM_IMG, width=280, height=180)
    # 只设一边：加载完成后另一边按原图比例自动推算
    only_w = Image(src=RANDOM_IMG, width=180)
    only_h = Image(src=RANDOM_IMG, height=120)
    return _row(
        _column(s1, _label("120 × 80")),
        _column(s2, _label("200 × 130")),
        _column(s3, _label("280 × 180")),
        _column(only_w, _label("只设 width=180")),
        _column(only_h, _label("只设 height=120")),
    )


# ============================================================
# 3. Radius
# ============================================================
def _make_radius() -> QWidget:
    radii = ["none", "sm", "md", "lg", "full"]
    children = []
    for r in radii:
        img = Image(src=RANDOM_IMG, width=120, height=120, radius=r)
        children.append(_column(img, _label(f"radius={r}")))
    return _row(*children)


# ============================================================
# 4. Shadow
# ============================================================
def _make_shadow() -> QWidget:
    shadows = ["none", "sm", "md", "lg"]
    children = []
    for s in shadows:
        img = Image(src=RANDOM_IMG, width=160, height=110, radius="lg", shadow=s)
        children.append(_column(img, _label(f"shadow={s}")))
    # wrapper 自身已包一圈阴影 margin，这里只负责控制 item 间距
    return _row(*children, spacing=24)


# ============================================================
# 5. Zoomed
# ============================================================
def _make_zoomed() -> QWidget:
    # 三个不同 zoom_factor——默认 1.25 / 轻微 1.1 / 强烈 1.5
    z1 = Image(src=RANDOM_IMG, width=200, height=140, radius="lg", is_zoomed=True)
    z2 = Image(
        src=RANDOM_IMG,
        width=200,
        height=140,
        radius="lg",
        is_zoomed=True,
        zoom_factor=1.10,
    )
    z3 = Image(
        src=RANDOM_IMG,
        width=200,
        height=140,
        radius="lg",
        is_zoomed=True,
        zoom_factor=1.50,
    )
    return _row(
        _column(z1, _label("hover → 1.25（默认）")),
        _column(z2, _label("hover → 1.10")),
        _column(z3, _label("hover → 1.50")),
    )


# ============================================================
# 6. Blurred
# ============================================================
def _make_blurred() -> QWidget:
    # 三档 blur_amount：0.5 温和 / 1.0 默认 / 2.0 加强
    b1 = Image(
        src=RANDOM_IMG,
        width=200,
        height=140,
        radius="lg",
        is_blurred=True,
        blur_amount=0.5,
    )
    b2 = Image(
        src=RANDOM_IMG,
        width=200,
        height=140,
        radius="lg",
        is_blurred=True,
        blur_amount=1.0,
    )
    b3 = Image(
        src=RANDOM_IMG,
        width=200,
        height=140,
        radius="lg",
        is_blurred=True,
        blur_amount=2.0,
    )
    return _row(
        _column(b1, _label("blur_amount=0.5（温和）")),
        _column(b2, _label("blur_amount=1.0（默认）")),
        _column(b3, _label("blur_amount=2.0（加强）")),
    )


# ============================================================
# 7. ObjectFit —— 裁剪模式
# ============================================================
def _make_object_fit() -> QWidget:
    fits = ["cover", "contain", "fill", "none", "scale-down"]
    children = []
    for f in fits:
        img = Image(
            src=RANDOM_IMG,
            width=180,
            height=120,
            radius="lg",
            object_fit=f,
        )
        children.append(_column(img, _label(f"object_fit={f}")))
    return _row(*children)


# ============================================================
# 7. AnimatedLoad —— Skeleton → loaded 切换
# ============================================================
def _make_animated_load() -> QWidget:
    """演示 Skeleton 动画——初次与重新加载都强制延长 3s 让动画清晰可见。"""
    # 初次构造时锁定 loading，3s 后释放
    img = Image(src=RANDOM_IMG, width=300, height=200, radius="lg", is_loading=True)
    QTimer.singleShot(3000, lambda: img.set_is_loading(False))

    btn = Button(text="重新加载", variant="flat", color="primary", size="sm")

    def _reload():
        # 显式锁定 loading 3s，演示 Skeleton 动画
        img.set_is_loading(True)
        img.set_src(RANDOM_IMG)
        QTimer.singleShot(3000, lambda: img.set_is_loading(False))

    btn.clicked.connect(_reload)
    return _column(
        img,
        btn,
        _label("演示用：刻意延长 3s 让 Skeleton 动画清晰可见"),
    )


# ============================================================
# 8. Fallback —— 加载失败时显示 fallback_src
# ============================================================
def _make_fallback() -> QWidget:
    # 主 src 故意用一个伪造路径，模拟上一个随机图 API 出错
    bad = Image(
        src=BAD_URL,
        fallback_src=BING_DAILY,
        width=260,
        height=180,
        radius="lg",
    )
    bad.failed.connect(
        lambda: print(f"[demo] 主图加载失败，已切换到 fallback_src: {BING_DAILY}")
    )
    return _column(bad, _label("主图加载失败 → 展示 fallback_src（Bing 每日一图）"))


# ============================================================
# 9. removeWrapper
# ============================================================
def _make_remove_wrapper() -> QWidget:
    img = Image(src=RANDOM_IMG, width=260, height=180, radius="lg", remove_wrapper=True)
    return _column(img, _label("remove_wrapper=True，无 skeleton/zoom/blur/shadow"))


# ============================================================
# Demo 主类
# ============================================================
class ImageDemo(DemoBase):
    component_name = "Image"

    def build_content(self, layout, labels_bag):
        layout.addWidget(self._section_title("Default"))
        layout.addWidget(_make_default())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Sizes"))
        layout.addWidget(_make_sizes())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Radius"))
        layout.addWidget(_make_radius())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Shadow"))
        layout.addWidget(_make_shadow())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Zoomed"))
        layout.addWidget(_make_zoomed())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Blurred"))
        layout.addWidget(_make_blurred())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Object Fit"))
        layout.addWidget(_make_object_fit())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Animated Load"))
        layout.addWidget(_make_animated_load())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Fallback"))
        layout.addWidget(_make_fallback())
        layout.addSpacing(24)

        layout.addWidget(self._section_title("Remove Wrapper"))
        layout.addWidget(_make_remove_wrapper())


if __name__ == "__main__":
    ImageDemo.run()
