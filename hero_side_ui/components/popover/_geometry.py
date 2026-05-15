"""Popover 弹层定位计算 mixin（私有）。

负责：
- 计算 popover 相对 trigger 的目标位置（_calc_position）
- 12 种 placement 的具体几何（_compute_pos_for）
- 边界翻转（_flip_placement，避免飞出屏幕）
- frame margins（阴影 + 边距）
"""

from ...themes import POPOVER_SHADOWS

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QApplication, QWidget

from ._constants import ARROW_INSET, ARROW_SIZE


class _PopoverGeometryMixin:
    """Popover 定位/几何 mixin。"""

    # ============================================================
    # 几何
    # ============================================================
    def _frame_margins(self) -> tuple:
        """内 layout 在四个方向需要让出多少空间给 arrow 和阴影。"""
        cfg = POPOVER_SHADOWS.get(self._shadow, POPOVER_SHADOWS["md"])
        sm = cfg["blur"] + abs(cfg["offset_y"])
        # arrow 占用一边（仅在 self._arrow=True 时保留空间）
        arrow = ARROW_SIZE if self._arrow else 0
        place = self._actual_placement
        m = [sm, sm, sm, sm]  # left, top, right, bottom
        if place.startswith("top"):
            m[3] += arrow
        elif place.startswith("bottom"):
            m[1] += arrow
        elif place.startswith("left"):
            m[2] += arrow
        elif place.startswith("right"):
            m[0] += arrow
        return tuple(m)

    def _effective_frame_margins(self) -> tuple:
        """paint 用的 frame margins = base + 当前 squeeze 增量。

        让 paintEvent 画的圆角 + 阴影 + 箭头位置都跟着 squeeze 动画走 ——
        实现"整个 popover(含底色)整体挤压扩张"的视觉,不只是内容 layout 几何。
        非动画期间 squeeze 处于完全展开态(extra 全 0),返回值 == _frame_margins。
        """
        base = self._frame_margins()
        try:
            extra = self._squeeze.squeeze_extra()
        except Exception:
            return base
        return (
            base[0] + extra[0],
            base[1] + extra[1],
            base[2] + extra[2],
            base[3] + extra[3],
        )

    def _calc_position(self, trigger: QWidget) -> QPoint:
        """计算 popover 在屏幕坐标下的左上角位置（含 auto-flip）。"""
        tr_pos = trigger.mapToGlobal(QPoint(0, 0))
        tr_w = trigger.width()
        tr_h = trigger.height()

        screen = QApplication.primaryScreen().availableGeometry()

        # 先按用户指定方向算
        place = self._placement
        pos = self._compute_pos_for(place, tr_pos, tr_w, tr_h)

        # 检查是否越界，越界则反向
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        rect = (pos.x(), pos.y(), my_w, my_h)
        if getattr(self, "_allow_flip", True) and (
            rect[0] < screen.left()
            or rect[1] < screen.top()
            or rect[0] + rect[2] > screen.right()
            or rect[1] + rect[3] > screen.bottom()
        ):
            flipped = self._flip_placement(place)
            new_pos = self._compute_pos_for(flipped, tr_pos, tr_w, tr_h)
            self._actual_placement = flipped
            self._outer.setContentsMargins(*self._frame_margins())
            self.adjustSize()
            return new_pos

        self._actual_placement = place
        self._outer.setContentsMargins(*self._frame_margins())
        return pos

    def _compute_pos_for(
        self, place: str, tr_pos: QPoint, tr_w: int, tr_h: int
    ) -> QPoint:
        """根据 placement 计算 popover 左上角（已扣掉 shadow 方向的 margin
        以保证 arrow 紧贴 trigger）。"""
        my_w = self.sizeHint().width()
        my_h = self.sizeHint().height()
        x, y = tr_pos.x(), tr_pos.y()

        # frame_margins: (left, top, right, bottom)。我们 sizeHint 包含了
        # 这些 margin，但实际 content_rect 距离 widget 边缘还有 margin。
        # 为了让 arrow 紧贴 trigger，要把 widget 位置朝 trigger 的反方向 +margin。
        ml, mt, mr, mb = self._frame_margins()
        # arrow 尖与 trigger 之间保留 6px 空气
        gap = 6

        if place == "top":
            return QPoint(x + (tr_w - my_w) // 2, y - my_h + mb - gap)
        if place == "top-start":
            return QPoint(x - ml, y - my_h + mb - gap)
        if place == "top-end":
            return QPoint(x + tr_w - my_w + mr, y - my_h + mb - gap)

        if place == "bottom":
            return QPoint(x + (tr_w - my_w) // 2, y + tr_h - mt + gap)
        if place == "bottom-start":
            return QPoint(x - ml, y + tr_h - mt + gap)
        if place == "bottom-end":
            return QPoint(x + tr_w - my_w + mr, y + tr_h - mt + gap)

        if place == "left":
            return QPoint(x - my_w + mr - gap, y + (tr_h - my_h) // 2)
        if place == "left-start":
            # popover 顶对齐 trigger 顶（视觉左下方向延伸）
            return QPoint(x - my_w + mr - gap, y - mt)
        if place == "left-end":
            # popover 底对齐 trigger 底（视觉左上方向延伸）
            return QPoint(x - my_w + mr - gap, y + tr_h - my_h + mb)

        if place == "right":
            return QPoint(x + tr_w - ml + gap, y + (tr_h - my_h) // 2)
        if place == "right-start":
            return QPoint(x + tr_w - ml + gap, y - mt)
        if place == "right-end":
            return QPoint(x + tr_w - ml + gap, y + tr_h - my_h + mb)

        return QPoint(x, y + tr_h)

    @staticmethod
    def _flip_placement(p: str) -> str:
        if p.startswith("top"):
            return p.replace("top", "bottom")
        if p.startswith("bottom"):
            return p.replace("bottom", "top")
        if p.startswith("left"):
            return p.replace("left", "right")
        if p.startswith("right"):
            return p.replace("right", "left")
        return p

