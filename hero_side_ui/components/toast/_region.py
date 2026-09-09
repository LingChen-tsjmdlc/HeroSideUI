"""ToastRegion — Toast 的堆叠区（宿主窗口内的 overlay）。

职责：
- 覆盖宿主窗口，空白区鼠标透传，卡片可交互（卡片挂宿主窗口而非 region，
  否则命中测试会整树跳过鼠标透明 region 的子树，卡片内按钮全部收不到点击）
- 6 个 placement 定位；折叠态只露出最新几张，hover 展开全部
- 进出场位移动画、超时/关闭/拖拽的编排；超量时旧卡隐藏保留计时，hover 展开全部

卡片自身的外观与倒计时在 ``toast.py``；全局队列在 ``_provider.py``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QWidget

from ...themes import TOAST_SPEC
from ...utils import safe_delete


@dataclass
class _ToastItem:
    """一条正在显示的 toast 的运行态。"""

    key: str
    card: QWidget
    exiting: bool = False     # 退出动画进行中
    entering: bool = False    # 入场淡入进行中（_relayout 不得踩透明度）
    hiding: bool = False      # 折叠淡出进行中（淡出结束才真正 hide）
    visible: bool = False     # 当前是否显示（折叠态超配额的旧卡隐藏）
    drag_dx: int = 0
    drag_dy: int = 0
    base_geom: QRect = field(default_factory=QRect)
    geo_anim: Optional[QPropertyAnimation] = None
    fade_anim: Optional[QPropertyAnimation] = None


class _HoverWatcher(QObject):
    """监听全局鼠标移动，判断指针是否停在 toast 区域上。

    region 自身鼠标透传，收不到 enter/leave；卡片各自上报又会在展开位移时抖动，
    所以统一按"指针是否落在卡片联合矩形内"判定（等价于 HeroUI 的 region hover）。
    """

    def __init__(self, region: "ToastRegion"):
        super().__init__(region)
        self._region = region

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            self._region._on_global_mouse_move(event.globalPosition().toPoint())
        return False


class ToastRegion(QWidget):
    """宿主窗口内的 Toast 堆叠区。"""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        placement: str = "bottom-right",
        max_visible_toasts: int = TOAST_SPEC["max_visible_toasts"],
        toast_offset: int = 0,
        disable_animation: bool = False,
    ):
        super().__init__(parent)
        self._placement = placement
        self._max_visible = max(1, int(max_visible_toasts))
        self._toast_offset = toast_offset
        self._disable_animation = disable_animation
        self._expanded = False
        self._hovering = False
        self._items: list[_ToastItem] = []
        self._counter = 0

        # 空白区透传鼠标（卡片挂在宿主窗口上，不经 region 命中）；
        # 无宿主的顶层 region 自身要接鼠标，不能透传
        if parent is not None:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._watcher = _HoverWatcher(self)
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(TOAST_SPEC["collapse_delay"])
        self._collapse_timer.timeout.connect(self._collapse_now)

        if parent is not None:
            parent.installEventFilter(self)
        self._sync_geometry()

    @property
    def placement(self) -> str:
        return self._placement

    # ============================================================
    # 增删
    # ============================================================

    def add(self, card, key: Optional[str] = None) -> str:
        """挂载一张卡片，返回它的 key。超配额的旧卡只是隐藏，不销毁。"""
        self._counter += 1
        key = key or f"toast-{self._counter}"
        # 卡片必须挂宿主窗口：Qt 命中测试遇到 WA_TransparentForMouseEvents
        # 的 widget 会整树剪枝（含子件），卡片若在 region 子树内则按钮/拖拽
        # 永远收不到真实鼠标事件。region 几何 == 宿主 rect 且位于 (0,0)，
        # 坐标系不变
        host = self.parent()
        if host is not None and card.parent() is not host:
            card.setParent(host)
        # 先定宽并按新宽度校正高度：标题截断与描述换行都依赖宽度算高度
        card.resize(self._card_width(), max(1, card.height()))
        card.sync_height()
        card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        card.set_placement(self._placement)

        item = _ToastItem(key=key, card=card)
        self._items.append(item)

        card.timeout_reached.connect(lambda: self.dismiss(key))
        card.closed.connect(lambda: self.dismiss(key))
        card.drag_started.connect(lambda: self._on_drag_started(item))
        card.drag_moved.connect(lambda dx, dy: self._on_drag_moved(item, dx, dy))
        card.drag_finished.connect(lambda dx, dy, close: self._on_drag_finished(item, close))
        card.content_changed.connect(lambda: self._on_card_changed(item))

        # 全部立即激活并计时（HeroUI：隐藏的 toast 照样倒计时）；可见性由
        # _relayout 按配额决定。先摆位再显示，避免卡片在旧位置闪现一帧
        # 快速连加时上一张可能仍在入场淡入（半透明）：立即定格为实色。
        # 否则它会在新卡滑上来遮住之前的 300ms 里，把半透明的 icon/标题行
        # 暴露在堆叠缝隙中，看起来像一块突兀的白/黑色矩形。
        # 不依赖 anim.stop() 的 finished 回调（实测不可靠），显式收尾
        for it in self._active_items():
            if it.entering:
                if it.fade_anim is not None:
                    it.fade_anim.stop()
                it.entering = False
                it.card.set_opacity(1.0)
        self._play_enter(item)
        card.show()
        card.start_countdown()
        self._relayout(animate=True)
        self._update_watchers()
        return key

    def dismiss(self, key: str):
        """走退出动画移除指定 toast。"""
        item = self._find(key)
        if item is None or item.exiting:
            return
        item.exiting = True
        item.card.stop_countdown()
        self._play_exit(item)
        self._relayout(animate=True)

    def clear(self):
        """移除全部 toast。"""
        for item in list(self._items):
            if not item.exiting:
                self.dismiss(item.key)

    def keys(self) -> list:
        return [it.key for it in self._items if not it.exiting]

    def card(self, key: str) -> Optional[QWidget]:
        """按 key 取卡片，便于运行中改文案 / 结束 loading。"""
        item = self._find(key)
        return None if item is None else item.card

    # ============================================================
    # 配置
    # ============================================================

    def set_placement(self, placement: str):
        self._placement = placement
        for item in self._items:
            item.card.set_placement(placement)
        self._relayout(animate=False)

    def set_max_visible_toasts(self, count: int):
        self._max_visible = max(1, int(count))
        self._relayout(animate=True)

    def set_toast_offset(self, offset: int):
        self._toast_offset = offset
        self._relayout(animate=False)

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable

    # ============================================================
    # 布局
    # ============================================================

    def _active_items(self) -> list:
        return [it for it in self._items if not it.exiting]

    def _pad(self) -> int:
        """卡片外扩（阴影 + 关闭按钮溢出），取当前所有卡片的最大值。"""
        pads = [it.card.pad_left for it in self._items if not it.exiting]
        return max(pads) if pads else 14

    def _content_width(self) -> int:
        """卡片可见主体的宽度（HeroUI: 356px）。"""
        avail = self.width() - 2 * TOAST_SPEC["margin"] - 2 * self._pad()
        return max(TOAST_SPEC["min_width"], min(TOAST_SPEC["width"], avail))

    def _card_width(self) -> int:
        """卡片 widget 的宽度（主体 + 两侧外扩）。"""
        return self._content_width() + 2 * self._pad()

    def _x_for(self, width: int) -> int:
        margin = TOAST_SPEC["margin"]
        if self._placement.endswith("left"):
            return margin
        if self._placement.endswith("center"):
            return (self.width() - width) // 2
        return self.width() - margin - width

    def _edge_offset(self, index: int, total: int, heights: list) -> int:
        """第 index 条（0=最老）距宿主窗口边缘的距离。"""
        if self._expanded:
            # 每张下方的卡都贡献一份 stack_gap（对齐 HeroUI 每卡 mb-1 的
            # 语义，其 heights 含 margin）；只加一次会被相邻卡差值精确
            # 抵消，展开态卡片会零间距贴合
            n_below = total - 1 - index
            below = sum(heights[index + 1:]) + n_below * TOAST_SPEC["stack_gap"]
            return TOAST_SPEC["stack_gap"] + below + self._toast_offset
        return (total - 1 - index) * TOAST_SPEC["collapsed_step"] + self._toast_offset

    def _folded_y(self, index: int, total: int, card) -> int:
        """折叠堆叠位第 index 张的 y（折叠淡出落点 / 展开揭示起飞点共用）。"""
        off = (total - 1 - index) * TOAST_SPEC["collapsed_step"] + self._toast_offset
        if self._placement.startswith("top"):
            return TOAST_SPEC["margin"] + off - card.pad_top
        return (self.height() - TOAST_SPEC["margin"] - off
                - card.content_height() - card.pad_top)

    def _target_geometry(self, item: _ToastItem, index: int, total: int, heights: list) -> QRect:
        """按 heights（布局开始时统一采集的可见主体高度）定位，避免与
        偏移量用的高度表不是同一份数据、导致相邻卡间距偏离 stack_gap。"""
        width = self._card_width()
        x = self._x_for(width)
        offset = self._edge_offset(index, total, heights)
        card_h = item.card.height()
        if self._placement.startswith("top"):
            content_y = TOAST_SPEC["margin"] + offset
        else:
            content_y = self.height() - TOAST_SPEC["margin"] - offset - heights[index]
        y = content_y - item.card.pad_top
        return QRect(x, y, width, card_h)

    def _relayout(self, animate: bool):
        items = self._active_items()
        total = len(items)
        if total == 0:
            return

        # region 抬到宿主内容之上；卡片是宿主子件，随后逐个 raise 叠更上层
        self.raise_()
        # 折叠态只显示最新 max_visible 张；更旧的隐藏但保留计时（HeroUI
        # visibleToasts 语义：不渲染 ≠ 移除，hover 展开时重新显示）
        visible_from = 0 if self._expanded else max(0, total - self._max_visible)

        # ---- 第一遍：状态（可见性 / 折叠按钮 / 内缩 / 透明度）----
        # 这些操作可能让卡片重算自身高度（结束淡出快照会触发卡片 _relayout），
        # 必须全部完成后再采集高度表，否则定位用的高度与卡片实际高度不一致，
        # 展开态相邻卡片间距会偏离 stack_gap。
        revealed = []
        for index, item in enumerate(items):
            card = item.card
            card.sync_height()
            if index < visible_from:
                item.visible = False
                if item.hiding:
                    pass  # 淡出进行中，等 _finish_hide 回调再隐藏
                elif (animate and not self._disable_animation
                      and not item.entering and not card.isHidden()):
                    # 折叠淡出的卡同步滑回折叠堆叠位再隐藏（与展开时从该位
                    # 起飞对称；只淡出不位移会停在展开位，与其余卡的下浮脱节）
                    item.hiding = True
                    self._animate_move(item, QRect(
                        self._x_for(self._card_width()),
                        self._folded_y(index, total, card),
                        self._card_width(), card.height(),
                    ))
                    self._animate_opacity(
                        item, 0.0, then=lambda it=item: self._finish_hide(it)
                    )
                elif not item.hiding:
                    card.hide()
                revealed.append(False)
                continue
            was_hidden = not item.visible
            item.visible = True
            item.hiding = False
            card.show()
            # 折叠态只有最新一张带关闭按钮：旧卡露出的边条不该带 X，
            # 且旧卡的 X 会被最新卡的命中区挡住
            card.set_folded(not self._expanded and index < total - 1)

            # 折叠态：更早的卡片露出的边略窄（近似 HeroUI scaleX）
            depth = total - 1 - index
            inset = 0.0 if self._expanded else depth * TOAST_SPEC["collapsed_width_step"] / 2.0
            # 内缩量随位移同步渐变，避免位置在滑而卡体宽度瞬跳的割裂感
            if animate and not self._disable_animation and not item.entering:
                card.animate_width_inset(inset)
            else:
                card.set_width_inset(inset)
            # 入场淡入进行中不能踩回 1.0，否则卡片会在入场起点
            # 以不透明状态闪现一两帧（帧级实证 f00 opacity=1.0）
            if not was_hidden and not item.entering:
                card.set_opacity(1.0)
            revealed.append(was_hidden)

        # ---- 第二遍：按统一采集的高度表定位 ----
        heights = [it.card.content_height() for it in items]
        for index, item in enumerate(items):
            if index < visible_from:
                continue
            card = item.card
            target = self._target_geometry(item, index, total, heights)
            item.base_geom = target

            # 折叠态隐藏的卡被展开揭示时不能瞬跳满透明度（突兀弹出）：
            # 位置动画本就从折叠位滑向展开位，这里补上同步淡入
            if (revealed[index] and animate and not self._disable_animation
                    and not item.entering):
                # 起点重置到折叠堆叠位（HeroUI 中隐藏 toast 始终保有折叠
                # transform，展开时从该位滑向展开位）。不重置的话几何冻结
                # 在上次的展开位，第二次展开只剩原位淡入、没有滑动
                card.setGeometry(target.x(), self._folded_y(index, total, card),
                                 target.width(), card.height())
                card.set_opacity(0.0)
                self._animate_opacity(item, 1.0)
            elif not item.entering:
                card.set_opacity(1.0)

            if item.drag_dx or item.drag_dy:
                target = target.translated(item.drag_dx, item.drag_dy)

            if animate and not self._disable_animation:
                self._animate_move(item, target)
            else:
                card.setGeometry(target)

            # 越新的越靠上层
            card.raise_()

    def _animate_move(self, item: _ToastItem, target: QRect):
        card = item.card
        if card.geometry() == target:
            return
        if item.geo_anim is not None:
            item.geo_anim.stop()
        anim = QPropertyAnimation(card, b"geometry", self)
        anim.setDuration(TOAST_SPEC["duration_move"])
        anim.setStartValue(card.geometry())
        anim.setEndValue(target)
        item.geo_anim = anim
        anim.start()

    # ============================================================
    # 进出场动画
    # ============================================================

    def _play_enter(self, item: _ToastItem):
        card = item.card
        if self._disable_animation:
            card.set_opacity(1.0)
            return
        item.entering = True
        items = self._active_items()
        total = len(items)
        index = items.index(item) if item in items else total - 1
        heights = [it.card.content_height() for it in items]
        target = self._target_geometry(item, index, total, heights)
        item.base_geom = target

        enter = TOAST_SPEC["enter_offset"]
        start = QRect(target)
        start.translate(0, -enter if self._placement.startswith("top") else enter)
        card.setGeometry(start)
        card.set_opacity(0.0)
        self._animate_move(item, target)
        self._animate_opacity(item, 1.0, then=lambda: self._enter_done(item))

    def _enter_done(self, item: _ToastItem):
        item.entering = False
        if item in self._items and not item.exiting:
            item.card.set_opacity(1.0)

    def _play_exit(self, item: _ToastItem):
        card = item.card
        # 隐藏中的卡（折叠态超配额）没有可见几何，直接出列
        if not item.visible or self._disable_animation:
            self._finalize_exit(item)
            return
        geo = card.geometry()
        end = QRect(geo)
        if self._placement == "top-center":
            end.translate(0, -geo.height())
        elif self._placement == "bottom-center":
            end.translate(0, geo.height())
        elif self._placement.endswith("right"):
            end.translate(geo.width(), 0)
        else:
            end.translate(-geo.width(), 0)

        if item.geo_anim is not None:
            item.geo_anim.stop()
        anim = QPropertyAnimation(card, b"geometry", self)
        anim.setDuration(TOAST_SPEC["duration_exit"])
        anim.setStartValue(geo)
        anim.setEndValue(end)
        item.geo_anim = anim
        anim.start()
        self._animate_opacity(item, 0.0, then=lambda: self._finalize_exit(item))

    def _animate_opacity(self, item: _ToastItem, target: float, then=None):
        card = item.card
        if item.fade_anim is not None:
            item.fade_anim.stop()
        anim = QPropertyAnimation(card, b"paint_opacity", self)
        anim.setDuration(TOAST_SPEC["duration_exit"])
        anim.setStartValue(card.paint_opacity)
        anim.setEndValue(target)
        if then is not None:
            anim.finished.connect(then)
        item.fade_anim = anim
        anim.start()

    def _finish_hide(self, item: _ToastItem):
        """折叠淡出结束的回调：仍处于隐藏态才真正 hide（中途被重新
        展开时 visible 已翻回 True，这里必须跳过）。"""
        item.hiding = False
        if item not in self._items or item.exiting:
            return
        if not item.visible:
            item.card.hide()

    def _finalize_exit(self, item: _ToastItem):
        if item not in self._items:
            return
        self._items.remove(item)
        safe_delete(item.card)
        self._relayout(animate=True)
        self._update_watchers()

    # ============================================================
    # hover / 展开
    # ============================================================

    def _toasts_rect(self) -> QRect:
        rect = QRect()
        for item in self._active_items():
            if item.visible:
                rect = rect.united(item.card.geometry())
        pad = TOAST_SPEC["stack_gap"]
        return rect.adjusted(-pad, -pad, pad, pad)

    def _on_global_mouse_move(self, pos: QPoint):
        if not self._items:
            return
        local = self.mapFromGlobal(pos)
        inside = self._toasts_rect().contains(local)
        if inside:
            self._collapse_timer.stop()
            if not self._hovering:
                self._set_hovering(True)
        elif self._hovering:
            self._collapse_timer.start()

    def _collapse_now(self):
        self._set_hovering(False)

    def _set_hovering(self, hovering: bool):
        self._hovering = hovering
        self._expanded = hovering
        for item in self._active_items():
            item.card.set_paused(hovering)
        self._relayout(animate=not self._disable_animation)

    # ============================================================
    # 拖拽
    # ============================================================

    def _on_card_changed(self, item: _ToastItem):
        """卡片文案/内容变化导致高度改变，重排堆叠。"""
        if item in self._items and not item.exiting:
            self._relayout(animate=True)

    def _on_drag_started(self, item: _ToastItem):
        # 显式抓取鼠标：拖拽的透明度反馈会走快照模式隐藏子件，若 press
        # 落在子件上（title/desc），隐式 grab 随子件 hide 一起丢失，后续
        # move/release 全部断掉，拖到一半卡死。grab 在卡片上则不受影响
        item.card.grabMouse()
        self._expanded = True
        self._collapse_timer.stop()
        for it in self._active_items():
            it.card.set_paused(True)
        self._relayout(animate=True)

    def _on_drag_moved(self, item: _ToastItem, dx: int, dy: int):
        item.drag_dx, item.drag_dy = dx, dy
        card = item.card
        card.move(item.base_geom.topLeft() + QPoint(dx, dy))
        axis = dy if self._placement.endswith("center") else dx
        limit = (
            TOAST_SPEC["swipe_threshold_y"]
            if self._placement.endswith("center")
            else TOAST_SPEC["swipe_threshold_x"]
        )
        card.set_opacity(max(0.2, 1.0 - abs(axis) / (limit + 20.0)))

    def _on_drag_finished(self, item: _ToastItem, should_close: bool):
        item.card.releaseMouse()
        item.drag_dx = item.drag_dy = 0
        if should_close:
            self.dismiss(item.key)
            return
        item.card.set_opacity(1.0)
        self._on_global_mouse_move(QCursor.pos())
        self._relayout(animate=True)

    # ============================================================
    # 宿主同步
    # ============================================================

    def _sync_geometry(self):
        parent = self.parent()
        if parent is None:
            return
        self.setGeometry(parent.rect())

    def eventFilter(self, obj, event) -> bool:
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self._sync_geometry()
            self._relayout(animate=False)
        return False

    def _update_watchers(self):
        app = QApplication.instance()
        if app is None:
            return
        if self._items:
            app.installEventFilter(self._watcher)
        else:
            app.removeEventFilter(self._watcher)
            self._set_hovering(False)

    def _find(self, key: str) -> Optional[_ToastItem]:
        for item in self._items:
            if item.key == key:
                return item
        return None
