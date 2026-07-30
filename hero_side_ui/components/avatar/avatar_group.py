"""HeroSideUI AvatarGroup — HeroUI v2 AvatarGroup PySide6 复刻。

组件来源: https://github.com/heroui-inc/heroui/tree/main/packages/components/avatar
样式来源: packages/core/theme/src/components/avatar.ts (avatarGroup slot)

行为:
- 子 Avatar 绝对定位横向重叠堆叠（越靠后的头像 z 越高，压在前面之上）。
- hover 其中一个 → 该头像向左平移 hover_shift 让开缝隙（带动画），移出后复位。
- 最多显示 max 个，超出以 "+N" 计数头像收尾（total 可覆盖 N）。
- 组级 color/radius/size/is_bordered/is_disabled 下发给所有子 Avatar。
- is_grid 时改为网格排布（正间距，不重叠）。
- render_count 可自定义计数控件工厂。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtWidgets import QGridLayout, QWidget

from ...themes import (
    AVATAR_GROUP_GRID_COLS,
    AVATAR_GROUP_GRID_GAP,
    AVATAR_GROUP_HOVER_SHIFT,
    AVATAR_GROUP_OVERLAP,
)
from .avatar import Avatar


class AvatarGroup(QWidget):
    """HeroUI v2 风格 AvatarGroup 头像组。用法::

        AvatarGroup([
            Avatar(src=url1), Avatar(src=url2), Avatar(name="张三"),
        ], color="primary", is_bordered=True, max=3)

        # 网格排布
        AvatarGroup(avatars, is_grid=True, max=7)

    Args:
        avatars:     Avatar 实例列表
        max:         最多显示数量（默认 5），超出以 "+N" 计数收尾
        total:       手动指定"未显示数量"，覆盖自动计算
        color/radius/size/is_bordered/is_disabled:
                     组级默认，下发给子 Avatar
        is_grid:     网格排布（正间距，不重叠）
        render_count: 自定义计数控件工厂 fn(count)->QWidget
        disable_animation: 关闭 hover 平移动画
        theme:       auto / light / dark
    """

    def __init__(
        self,
        avatars: Optional[List[Avatar]] = None,
        max: int = 5,
        total: Optional[int] = None,
        color: Optional[str] = None,
        radius: Optional[str] = None,
        size: Optional[str] = None,
        is_bordered: bool = False,
        is_disabled: bool = False,
        is_grid: bool = False,
        render_count: Optional[Callable[[int], QWidget]] = None,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroAvatarGroup")

        self._avatars: List[Avatar] = list(avatars or [])
        self._max = max
        self._total = total
        self._color = color
        self._radius = radius
        self._size = size
        self._is_bordered = is_bordered
        self._is_disabled = is_disabled
        self._is_grid = is_grid
        self._render_count = render_count
        self._disable_animation = disable_animation
        self._theme = theme

        self._count_widget: Optional[QWidget] = None
        # 堆叠模式下：item -> 其在原位的 x 基准值；以及 item -> hover 平移动画
        self._items: List[QWidget] = []
        self._base_x: Dict[QWidget, int] = {}
        self._anims: Dict[QWidget, QPropertyAnimation] = {}

        self._build()

    # ============================================================
    def _apply_group_props(self, av: Avatar):
        """把组级默认下发给子 Avatar。"""
        if self._color is not None:
            av.set_color(self._color)
        if self._radius is not None:
            av.set_radius(self._radius)
        if self._size is not None:
            av.set_size(self._size)
        av.set_bordered(self._is_bordered)
        av.set_disabled(self._is_disabled)
        if self._theme != "auto":
            av.set_theme(self._theme)

    def _remaining_count(self) -> int:
        if self._total is not None:
            return self._total
        if self._max is not None:
            return len(self._avatars) - self._max
        return -1

    def _visible_avatars(self) -> List[Avatar]:
        if self._max is None:
            return self._avatars
        return self._avatars[: self._max]

    def _build(self):
        if self._is_grid:
            self._build_grid()
        else:
            self._build_stack()

    # ============================================================
    # 堆叠模式（绝对定位重叠 + hover 平移）
    # ============================================================
    def _build_stack(self):
        # 分别收集头像与可选计数控件：头像重叠堆叠，计数控件另作小间距排在末尾
        avatars: List[Avatar] = []
        for av in self._visible_avatars():
            av.setParent(self)
            self._apply_group_props(av)
            avatars.append(av)

        rc = self._remaining_count()
        self._count_widget = None
        if rc > 0:
            self._count_widget = self._make_count(rc)
            self._count_widget.setParent(self)

        # items = 头像 + 计数（计数不参与 hover/overlap，但纳入 z-order 与总尺寸）
        items: List[QWidget] = list(avatars)
        if self._count_widget is not None:
            items.append(self._count_widget)
        self._items = items

        def _avatar_side(av):
            # 直接问 Avatar 自身几何（box + 描边外圈），不依赖 width() 时序，
            # 避免读到样式应用前的旧尺寸导致 total_h 偏小、头像被裁。
            if isinstance(av, Avatar):
                return av._box_side() + 2 * av._outer_margin()
            return av.width() if av.width() > 0 else av.sizeHint().width()

        # 整组高度仅由头像决定（头像方形，用真实外径）；计数控件在其中居中，
        # 绝不让计数控件的 sizeHint 反过来撑高整个 group。
        avatar_side = 0
        for av in avatars:
            avatar_side = max(avatar_side, _avatar_side(av))
        total_h = avatar_side

        # 左侧留出 hover 平移空间，避免第一个头像左移越界
        self._left_pad = AVATAR_GROUP_HOVER_SHIFT

        # 头像重叠排布：x 递进 step = 外径 - 重叠量；y 纵向居中
        # right_edge 单独记真实最右缘（x 累加会比末个头像右缘少一个 overlap）
        x = self._left_pad
        right_edge = self._left_pad
        for av in avatars:
            side = _avatar_side(av)
            y = (total_h - side) // 2
            self._base_x[av] = x
            av.move(x, y)
            av.show()
            right_edge = x + side
            x += side - AVATAR_GROUP_OVERLAP
            anim = QPropertyAnimation(av, b"pos", self)
            anim.setDuration(250)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anims[av] = anim
            av.installEventFilter(self)

        # 计数控件排布：
        # - 默认计数是 Avatar → 参与重叠堆叠（同头像 step，纵向居中）
        # - 自定义 render_count 返回的普通控件 → 紧随头像右缘 + 小间距(ms-2)，不重叠
        if self._count_widget is not None:
            cwidget = self._count_widget
            cwidget.adjustSize()  # 定成真实单行尺寸，避免 0×0 或换行撑高
            cw = cwidget.width() if cwidget.width() > 0 else cwidget.sizeHint().width()
            ch = cwidget.height() if cwidget.height() > 0 else cwidget.sizeHint().height()
            if isinstance(cwidget, Avatar):
                cx = x  # 延续重叠 step
            else:
                cx = right_edge + AVATAR_GROUP_OVERLAP
            cy = (total_h - ch) // 2
            self._base_x[cwidget] = cx
            cwidget.move(cx, cy)
            cwidget.show()
            right_edge = cx + cw

        total_w = right_edge
        self.setFixedSize(total_w, total_h)

        # z-order：越靠后的头像 z 越高（压在前面之上）→ 正序 raise，最后一个最顶
        for w in items:
            w.raise_()

    def eventFilter(self, obj, event):
        # 仅堆叠模式处理 hover 平移
        if not self._is_grid and obj in self._base_x:
            if event.type() == QEvent.Type.Enter:
                self._hover_shift(obj, enter=True)
            elif event.type() == QEvent.Type.Leave:
                self._hover_shift(obj, enter=False)
        return super().eventFilter(obj, event)

    def _hover_shift(self, w: QWidget, enter: bool):
        base = self._base_x.get(w)
        if base is None:
            return
        w.raise_()  # hover 的浮到最上层
        target_x = base - AVATAR_GROUP_HOVER_SHIFT if enter else base
        if self._disable_animation:
            w.move(target_x, w.y())
            if not enter:
                self._restore_z_order()
            return
        anim = self._anims.get(w)
        if anim is None:
            w.move(target_x, w.y())
            return
        anim.stop()
        # 断开旧的一次性回调，避免重复连接累积
        try:
            anim.finished.disconnect(self._restore_z_order)
        except (RuntimeError, TypeError):
            pass
        anim.setStartValue(w.pos())
        anim.setEndValue(QPoint(target_x, w.y()))
        if not enter:
            anim.finished.connect(self._restore_z_order)
        anim.start()

    def _restore_z_order(self):
        # 复位到自然堆叠：越靠后的头像 z 越高（正序 raise）
        for w in self._items:
            w.raise_()

    # ============================================================
    # 网格模式
    # ============================================================
    def _build_grid(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AVATAR_GROUP_GRID_GAP)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        items: List[QWidget] = []
        for av in self._visible_avatars():
            av.setParent(self)
            self._apply_group_props(av)
            items.append(av)

        rc = self._remaining_count()
        if rc > 0:
            self._count_widget = self._make_count(rc)
            self._count_widget.setParent(self)
            items.append(self._count_widget)

        cols = AVATAR_GROUP_GRID_COLS
        for idx, w in enumerate(items):
            layout.addWidget(w, idx // cols, idx % cols)
            w.show()

        self._items = items
        self._layout = layout

    def _make_count(self, count: int) -> QWidget:
        """计数收尾控件：默认一个 name='+N' 的 Avatar。"""
        if self._render_count is not None:
            return self._render_count(count)
        av = Avatar(
            name=f"+{count}",
            color=self._color or "default",
            radius=self._radius or "full",
            size=self._size or "md",
            is_bordered=self._is_bordered,
            is_disabled=self._is_disabled,
            theme=self._theme,
            parent=self,
        )
        return av

    # ============================================================
    # 公共访问器
    # ============================================================
    def avatars(self) -> List[Avatar]:
        return list(self._avatars)

    def remaining_count(self) -> int:
        return self._remaining_count()

    def count_widget(self) -> Optional[QWidget]:
        return self._count_widget


__all__ = ["AvatarGroup"]
