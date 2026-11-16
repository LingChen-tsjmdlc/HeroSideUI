"""Popover 定位 mixin：12 placement 几何 + 窗口内翻转 + frame margins。"""

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QWidget

from ..._shared.overlays.bounds import overflow, popup_area, register_host
from ...core.shadow_paint import tier_margin
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
        sm = tier_margin(self._shadow)
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

    def _body_global(self) -> QRect:
        """可见主体（扣掉阴影与箭头留白）的全局矩形，供留白穿透与点击外部判断使用。

        Note:
            按窗口当前实际几何算（不用 sizeHint：淡入缩放期间 sizeHint 会缩水）。
        """
        return self._body_local().translated(self.mapToGlobal(QPoint(0, 0)))

    def _body_at(self, pos: QPoint) -> QRect:
        """窗口位于 pos 时，可见主体（不含阴影与箭头留白）的全局矩形。

        Args:
            pos: 浮层左上角的全局坐标。
        """
        ml, mt, mr, mb = self._frame_margins()
        size = self.sizeHint()
        return QRect(
            pos.x() + ml,
            pos.y() + mt,
            max(1, size.width() - ml - mr),
            max(1, size.height() - mt - mb),
        )

    def _layout_for(self, place: str, tr_pos: QPoint, tr_w: int, tr_h: int) -> tuple[QPoint, QRect]:
        """按指定 placement 重排版，返回浮层左上角与可见主体矩形（全局坐标）。

        Args:
            place: 要尝试的 placement。
            tr_pos: trigger 左上角的全局坐标。
            tr_w: trigger 宽度。
            tr_h: trigger 高度。

        Note:
            先把 _actual_placement、外边距和窗口尺寸切到该 placement 再算位置，
            保证箭头所在边的额外边距、窗口尺寸与位置三者一致。
        """
        self._actual_placement = place
        self._outer.setContentsMargins(*self._frame_margins())
        self.adjustSize()
        # adjustSize 在某些平台上只采用当前可用宽度，显式 resize 到 sizeHint 才可靠
        self.resize(self.sizeHint())
        pos = self._compute_pos_for(place, tr_pos, tr_w, tr_h)
        return pos, self._body_at(pos)

    def _calc_position(self, trigger: QWidget) -> QPoint:
        """计算 popover 左上角的全局坐标。

        Args:
            trigger: 作为定位锚点的控件。

        Note:
            可用区域 = 触发控件所在窗口的客户区 ∩ 所在屏幕。先按指定方向排；
            放不下且允许翻转时试相反方向；两边都放不下取越界更少的一边（并列取指定方向）。
            翻转后仍放不下的部分，由 clip_to_host 在窗口边缘处裁掉，不会伸出窗口。
        """
        register_host(self, trigger)
        tr_pos = trigger.mapToGlobal(QPoint(0, 0))
        tr_w, tr_h = trigger.width(), trigger.height()
        area = popup_area(trigger)

        candidates = [self._placement]
        if getattr(self, "_allow_flip", True):
            flipped = self._flip_placement(self._placement)
            if flipped != self._placement:
                candidates.append(flipped)

        best = None  # (越界量, 序号, placement)
        for idx, cand in enumerate(candidates):
            _pos, body = self._layout_for(cand, tr_pos, tr_w, tr_h)
            miss = overflow(body, area)
            if best is None or miss < best[0]:
                best = (miss, idx, cand)
            if miss == 0:
                break
        chosen = best[2]
        pos, _body = self._layout_for(chosen, tr_pos, tr_w, tr_h)
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
