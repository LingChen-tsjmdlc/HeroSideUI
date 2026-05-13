"""
HeroUI 风格 padding 挤压动画 (Padding Squeeze Animation)

通过动画 layout 的 contentsMargins 实现"内容从中心向外扩张"的视觉效果,
作为复合组件场景下 transform-scale 的轻量替代:

  展开: padding 从 (base + delta) → base, 内容从压缩状态向外铺开
  收起: padding 从 base → (base + delta), 内容向中心收拢

为什么不直接用 QGraphicsScale / QGraphicsOpacityEffect 做整体缩放?
  1. QGraphicsEffect 在 Qt 上叠加会破坏 backdrop / 阴影 / 自绘 paintEvent
  2. 复合组件(Listbox/Input/Button)被 raster scale 后字会糊、子组件 hover
     动画被冻结
  3. Popover 是 Qt.Tool 顶层窗口,每帧 resize 在 Windows 上很慢且会闪

padding 挤压只动 layout 几何,不缩放像素 —— 文字、子组件 hover、ripple
全部正常工作,且只触发一次 layout pass。

适用场景:
  - Popover 含复合组件(Listbox/Input/...)时的 open/close 视觉补强
  - 任何"内容从中心展开"的视觉,如手风琴 item 内容、tooltip 等

用法::

    # 把动画绑到目标 layout(必须是 QLayout)
    anim = PaddingSqueezeAnimation(
        layout=popover_inner_layout,
        base_margins=(8, 8, 8, 8),  # 静态 padding
        delta=10,                    # 挤压时额外 padding
        duration=180,
    )
    anim.expand()  # 打开播 padding+10 → padding+0
    anim.collapse()  # 关闭播 padding+0 → padding+10
    anim.finished.connect(lambda forward: ...)

设计要点:
  - 不依赖 Qt 自定义 property,直接用 QVariantAnimation 拿浮点 progress
    再换算 margins, 简单清晰
  - 支持随时打断:expand/collapse 总是从"当前 progress"衔接,不会跳变
  - placement_aware 选项:从某一边收/扩(top-origin / bottom-origin),
    用于 popover 在 trigger 上下方时让动画 origin 与 placement 一致
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QObject, QVariantAnimation, QEasingCurve, Signal
from PySide6.QtWidgets import QLayout

# placement_aware 取值
_ORIGIN_CENTER = "center"
_ORIGIN_TOP = "top"      # 上方为锚点(从上往下展开)
_ORIGIN_BOTTOM = "bottom"  # 下方为锚点(从下往上展开)
_VALID_ORIGINS = (_ORIGIN_CENTER, _ORIGIN_TOP, _ORIGIN_BOTTOM)


class PaddingSqueezeAnimation(QObject):
    """通过动画 contentsMargins 实现"内容挤压扩张"的视觉效果。

    参数:
        layout       : 目标 QLayout(动画作用于它的 contentsMargins)
        base_margins : (left, top, right, bottom) —— 静态稳定状态的 padding
        delta        : 挤压幅度(px)。展开起点是 base + delta,终点是 base
        duration     : 动画时长(ms)
        easing       : QEasingCurve.Type
        origin       : 挤压方向:"center"(四周均匀)、"top"(顶部锚定,
                       多余 padding 加到 bottom)、"bottom"(底部锚定,
                       多余 padding 加到 top)。配合 popover placement 用。

    信号:
        finished(bool) : True=展开完成, False=收起完成
    """

    finished = Signal(bool)
    # 每帧 progress 变化时发射(0.0=完全收起, 1.0=完全展开)。供调用方用于
    # 同步触发外部重绘(如 popover 让 paintEvent 也按 progress 算 content_rect,
    # 让外框圆角/阴影跟着缩,而不只是内容 layout 几何)。
    progress_changed = Signal(float)

    def __init__(
        self,
        layout: QLayout,
        base_margins: Tuple[int, int, int, int] = (0, 0, 0, 0),
        delta: int = 8,
        duration: int = 180,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        easing_out: Optional[QEasingCurve.Type] = None,
        origin: str = _ORIGIN_CENTER,
        parent: Optional[QObject] = None,
    ):
        """参数:
            easing     : 展开(expand)曲线,默认 OutCubic
            easing_out : 收起(collapse)曲线,默认 None → 用 easing 反转语义
                         (比如 expand 用 OutBack 时,collapse 建议传 InBack,
                         避免 collapse 开头直接过冲的怪异视觉)
        """
        super().__init__(parent)
        if origin not in _VALID_ORIGINS:
            raise ValueError(f"origin must be one of {_VALID_ORIGINS}, got {origin!r}")

        self._layout = layout
        self._base = tuple(base_margins)
        self._delta = max(0, int(delta))
        self._duration = max(0, int(duration))
        self._easing_in = easing
        self._easing_out = easing_out if easing_out is not None else easing
        self._origin = origin

        # progress: 1.0 = 完全展开(用 base), 0.0 = 完全收起(用 base + delta)
        self._progress: float = 1.0

        self._anim: Optional[QVariantAnimation] = None
        self._forward: bool = True  # 当前动画方向: True=展开, False=收起

    # ============================================================
    # 公共 API
    # ============================================================
    def expand(self, *, animated: bool = True) -> None:
        """从当前 progress 衔接到 1.0(展开完成)。"""
        self._play(target=1.0, forward=True, animated=animated)

    def collapse(self, *, animated: bool = True) -> None:
        """从当前 progress 衔接到 0.0(收起完成)。"""
        self._play(target=0.0, forward=False, animated=animated)

    def set_immediate(self, expanded: bool) -> None:
        """无动画地直接跳到目标状态。"""
        self._stop_anim()
        self._progress = 1.0 if expanded else 0.0
        self._apply_progress()

    def progress(self) -> float:
        return self._progress

    def stop(self) -> None:
        self._stop_anim()

    # ============================================================
    # 内部
    # ============================================================
    def _play(self, target: float, forward: bool, animated: bool) -> None:
        self._stop_anim()
        self._forward = forward
        if not animated or self._duration <= 0:
            self._progress = target
            self._apply_progress()
            self.finished.emit(forward)
            return

        anim = QVariantAnimation(self)
        anim.setStartValue(float(self._progress))
        anim.setEndValue(float(target))
        anim.setDuration(self._duration)
        # 展开用 _easing_in,收起用 _easing_out(默认与 _easing_in 相同)。
        # 场景:expand 用 OutBack 有弹出感,collapse 应该用 InBack/InCubic,
        # 避免 collapse 开头直接"过冲一下再回退"的怪异视觉。
        anim.setEasingCurve(self._easing_in if forward else self._easing_out)
        anim.valueChanged.connect(self._on_step)
        anim.finished.connect(self._on_finished)
        self._anim = anim
        anim.start()

    def _on_step(self, v) -> None:
        try:
            self._progress = float(v)
        except (TypeError, ValueError):
            return
        self._apply_progress()

    def _on_finished(self) -> None:
        # _progress 已经被 _on_step 推到目标值;这里只发信号
        self.finished.emit(self._forward)
        self._anim = None

    def _stop_anim(self) -> None:
        if self._anim is not None:
            try:
                self._anim.stop()
            except RuntimeError:
                pass
            self._anim = None

    def _apply_progress(self) -> None:
        """根据当前 progress(0=收起, 1=展开)计算 margins 并应用到 layout。

        origin 语义("锚点不动,其它三/四边挤入"):
            - center : 四周均匀挤入(每边 extra/2)
            - top    : top 锚定 → top 不动, 其它三边(left/right/bottom)各加 extra/2,
                       视觉是"从 top 向下展开"并两侧收拢
            - bottom : bottom 锚定 → bottom 不动, 其它三边各加 extra/2

        之前 top/bottom 只动单边(只 bottom 或只 top),视觉上"只看到底部在动",
        不像"整体从锚点展开"。改成"三边都加一半"后,水平方向也跟着挤,
        锚点边仍完全不动,整体动画感更贴近 CSS transform-origin 的效果。
        """
        if self._layout is None:
            return
        # 当前额外 padding(progress=1 → 0, progress=0 → delta)
        extra = (1.0 - self._progress) * self._delta
        half = extra / 2.0

        l, t, r, b = self._base
        if self._origin == _ORIGIN_CENTER:
            # 四周均匀加 extra/2
            l_, t_, r_, b_ = l + half, t + half, r + half, b + half
        elif self._origin == _ORIGIN_TOP:
            # 顶部锚定:top 不动, 其它三边各加 extra/2
            l_, t_, r_, b_ = l + half, t, r + half, b + half
        else:  # bottom
            # 底部锚定:bottom 不动, 其它三边各加 extra/2
            l_, t_, r_, b_ = l + half, t + half, r + half, b

        try:
            self._layout.setContentsMargins(int(l_), int(t_), int(r_), int(b_))
        except RuntimeError:
            # layout 已被销毁
            pass

        # 通知调用方 progress 更新(供外部 paintEvent 同步)
        self.progress_changed.emit(float(self._progress))

    def squeeze_extra(self) -> Tuple[int, int, int, int]:
        """返回当前帧"额外挤压量"(在 base_margins 之上的增量),供外部 paintEvent
        用同样的几何算 content_rect,让外框圆角/阴影跟着缩。

        与 ``_apply_progress`` 中加到 layout margins 上的逻辑保持一致 ——
        center 均分四边、top 三边(left/right/bottom 各 extra/2)、bottom 三边
        (left/right/top 各 extra/2)。锚点边永远不动。
        """
        extra = (1.0 - self._progress) * self._delta
        half = extra / 2.0
        if self._origin == _ORIGIN_CENTER:
            return (int(half), int(half), int(half), int(half))
        if self._origin == _ORIGIN_TOP:
            # top 锚定: top 不动, 其它三边各加 extra/2
            return (int(half), 0, int(half), int(half))
        # bottom 锚定: bottom 不动, 其它三边各加 extra/2
        return (int(half), int(half), int(half), 0)
