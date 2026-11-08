"""Popover 定位 mixin：12 placement 几何 + 边界翻转 + frame margins。"""

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget

from ...themes import POPOVER_SHADOWS
from ._constants import ARROW_SIZE


class _PopoverGeometryMixin:
    """Popover 定位/几何 mixin。"""

    # ============================================================
    # 几何
    # ============================================================
    def _frame_margins(self) -> tuple:
        """计算内容 layout 四周需预留给箭头与阴影的边距。

        Returns:
            tuple: (left, top, right, bottom) 像素边距。

        Note:
            仅当 self._arrow 为 True 时，对应方向额外加上 ARROW_SIZE。
        """
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
        """计算绘制用的 frame margins（base + squeeze 增量）。

        Returns:
            tuple: (left, top, right, bottom) 像素边距。

        Note:
            叠加 PaddingSqueezeAnimation 的 squeeze_extra，使圆角与阴影
            随挤压动画一起收缩/展开，呈现"整体出现"而非仅内容铺开。
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
        """计算 popover 在屏幕坐标下的左上角位置（含 auto-flip）。

        Args:
            trigger: 作为定位锚点的控件。

        Returns:
            QPoint: popover 左上角的全局坐标。

        Note:
            越界时自动反向翻转 placement（_allow_flip 为 True 时）；
            多屏配置下使用 trigger 所在屏幕而非主屏，避免误判越界。
        """
        tr_pos = trigger.mapToGlobal(QPoint(0, 0))
        tr_w = trigger.width()
        tr_h = trigger.height()

        # 用 trigger 实际所在的 screen，而不是 primaryScreen——
        # 多屏配置下 primaryScreen 的几何范围可能与 trigger 所在屏不同
        # （副屏 trigger 的全局坐标永远超出主屏 rect → 所有 placement 都被误判越界
        # → 全部 flip，表现为"top 跑下面、bottom 跑上面"）。
        win = trigger.window() if hasattr(trigger, "window") else None
        win_handle = win.windowHandle() if win is not None else None
        scr = win_handle.screen() if win_handle is not None else None
        if scr is None:
            scr = QApplication.screenAt(tr_pos) or QApplication.primaryScreen()
        screen = scr.availableGeometry()

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

    def _compute_pos_for(self, place: str, tr_pos: QPoint, tr_w: int, tr_h: int) -> QPoint:
        """根据 placement 计算 popover 左上角全局坐标。

        Args:
            place: placement 字符串（top/top-start/.../right-end）。
            tr_pos: trigger 左上角的全局坐标。
            tr_w: trigger 宽度。
            tr_h: trigger 高度。

        Returns:
            QPoint: popover 左上角的全局坐标（已扣掉阴影方向边距，
            保证箭头紧贴 trigger）。

        Note:
            箭头与 trigger 之间保留 6px 空气间隙；start/end 变体做
            顶/底对齐偏移。
        """
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
        """将 placement 翻转到相反方向（top↔bottom，left↔right）。

        Args:
            p: 原 placement 字符串。

        Returns:
            str: 翻转后的 placement；无法识别时原样返回。
        """
        if p.startswith("top"):
            return p.replace("top", "bottom")
        if p.startswith("bottom"):
            return p.replace("bottom", "top")
        if p.startswith("left"):
            return p.replace("left", "right")
        if p.startswith("right"):
            return p.replace("right", "left")
        return p
