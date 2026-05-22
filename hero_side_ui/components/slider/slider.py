"""HeroSideUI Slider 组件 — 滑块。

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/slider.ts

结构:
    Slider (QWidget)
        ├── label_row (label 左 / value 右; vertical 时纵向居中)
        └── _SliderCanvas (track + filler + step + thumb + mark 全部自绘) 鼠标事件转发回 Slider 处理拖拽
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation.tween import stop_tween, tween_value
from ...core import ThemeProvider
from ...themes import SLIDER_SIZES
from ..text import Text
from ._geometry import (
    HALO_EXTRA,
    RING_GAP,
    RING_WIDTH,
    clamp_value,
    hit_thumb,
    marks_band_size,
    ratio_at_pos,
    snap_value,
    thumb_centers,
    track_geom,
    value_at_ratio,
)
from ._marks import format_value, parse_marks
from ._paint import _SliderCanvas
from ._icon import _SliderIconLabel
from ._api import _SliderAPIMixin
from ._tooltip import _SliderTooltipMixin

# 类型别名（对外语义，docs/tests 引用）
NumPair = Tuple[float, float]
ValueT = Union[float, NumPair]
MarkT = Union[float, Tuple[float, str], dict]

# 仅本模块用的常量
_KEY_PAGE_FRAC = 0.1  # PageUp/PageDown = 10% range
_DRAG_PRESS_DURATION = 120  # 拖拽 scale 动画时长 (ms)


class Slider(_SliderAPIMixin, _SliderTooltipMixin, QWidget):
    """HeroUI 风格的 Slider 组件

    用法:
        s = Slider(label="Volume", value=40, min_value=0, max_value=100, step=1, color="primary", size="md")
        s.value_changed.connect(lambda v: print(v))

    Range 模式（双 thumb）:
        s = Slider(value=(20, 80), min_value=0, max_value=100)

    Marks（吸附点 + 文字）:
        s = Slider(marks=[
            {"value": 20, "label": "20°C"},
            {"value": 50, "label": "50°C"},
            {"value": 80, "label": "80°C"},
        ])
    """

    # 信号
    value_changed = Signal(object)  # float 或 (float, float)
    change_end = Signal(object)  # 鼠标抬起 / 键盘抬起 / 滚轮单步结束发射
    valueChanged = value_changed  # 兼容别名

    def __init__(
        self,
        value: Optional[ValueT] = None,
        min_value: float = 0.0,
        max_value: float = 100.0,
        step: float = 1.0,
        label: str = "",
        color: str = "primary",
        size: str = "md",
        radius: str = "full",
        orientation: str = "horizontal",
        is_disabled: bool = False,
        hide_value: bool = False,
        hide_thumb: bool = False,
        show_outline: bool = False,
        disable_thumb_scale: bool = False,
        disable_animation: bool = False,
        show_steps: bool = False,
        marks: Optional[Sequence[MarkT]] = None,
        start_content: Optional[Union[QWidget, str]] = None,
        end_content: Optional[Union[QWidget, str]] = None,
        top_end_content: Optional[QWidget] = None,
        bottom_start_content: Optional[QWidget] = None,
        value_formatter: Optional[Callable[[ValueT], str]] = None,
        fill_offset: Optional[float] = None,
        show_tooltip: bool = False,
        tooltip_props: Optional[dict] = None,
        enable_wheel: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---- 范围 / 步长 ----
        if max_value <= min_value:
            raise ValueError(
                f"Slider: max_value({max_value}) must be > min_value({min_value})"
            )
        if step <= 0:
            raise ValueError(f"Slider: step({step}) must be positive")
        self._min = float(min_value)
        self._max = float(max_value)
        self._step = float(step)

        # ---- value（单 / range）----
        if value is None:
            value = self._min
        self._is_range = isinstance(value, (tuple, list))
        if self._is_range:
            lo, hi = float(value[0]), float(value[1])
            self._value: ValueT = (
                snap_value(
                    clamp_value(lo, self._min, self._max),
                    self._min,
                    self._max,
                    self._step,
                ),
                snap_value(
                    clamp_value(hi, self._min, self._max),
                    self._min,
                    self._max,
                    self._step,
                ),
            )
        else:
            self._value = snap_value(
                clamp_value(float(value), self._min, self._max),
                self._min,
                self._max,
                self._step,
            )

        # ---- 视觉参数 ----
        self._label_text = label
        self._color = color
        self._size = size
        self._radius = radius
        self._orientation = (
            orientation if orientation in ("horizontal", "vertical") else "horizontal"
        )
        self._is_disabled = is_disabled
        self._hide_value = hide_value
        self._hide_thumb = hide_thumb
        self._show_outline = show_outline
        self._disable_thumb_scale = disable_thumb_scale
        self._disable_animation = disable_animation
        self._show_steps = show_steps
        self._fill_offset = fill_offset
        self._value_formatter = value_formatter

        self._marks: List[Tuple[float, str]] = parse_marks(
            marks or [], self._min, self._max
        )

        # start/end_content 接受 str（icon name）或 QWidget（自定义控件）。
        # str 路径走内置 _SliderIconLabel：load_svg_icon 自动跟主题着色，零样板。
        self._start_content_widget = self._coerce_side_content(start_content)
        self._end_content_widget = self._coerce_side_content(end_content)
        self._top_end_content_widget = top_end_content
        self._bottom_start_content_widget = bottom_start_content

        # ---- tooltip 状态（实际 anchor / Tooltip 实例由 _init_tooltips() 创建）----
        self._show_tooltip = bool(show_tooltip)
        self._tooltip_props = tooltip_props

        # 默认不允许滚轮触发滑动，避免误操作页面滚动时改变滑块值
        self._enable_wheel = bool(enable_wheel)

        # ---- 主题 ----
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # ---- 运行时状态 ----
        self._hover = False
        self._hovered_idx = -1  # 当前鼠标悬停的 thumb 索引（-1 = 无）
        self._dragging_idx = -1
        self._drag_press_t = [0.0, 0.0]
        self._drag_anim_runners = [None, None]
        self._focused_idx = 0  # range 模式下键盘焦点在哪个 thumb

        # ---- 输入策略 ----
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        if not is_disabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        # ---- UI 装配 ----
        self._setup_ui()
        self._refresh_text_labels()
        self._apply_disabled_effect(is_disabled)
        self._init_tooltips()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # cfg
    # ============================================================
    def _cfg(self) -> dict:
        return SLIDER_SIZES.get(self._size, SLIDER_SIZES["md"])

    # ============================================================
    # UI 装配
    # ============================================================
    def _setup_ui(self):
        is_v = self._orientation == "vertical"

        if is_v:
            self._root = QHBoxLayout(self)
        else:
            self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(8)

        # label / value 行
        self._label_row_widget = QWidget(self)
        row = (
            QVBoxLayout(self._label_row_widget)
            if is_v
            else QHBoxLayout(self._label_row_widget)
        )
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self._label = Text("", selectable=False, theme=self._theme_mode)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._value_label = Text("", selectable=False, theme=self._theme_mode)
        self._value_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        if is_v:
            row.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)
            row.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignHCenter)
        else:
            row.addWidget(self._label, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
            row.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignRight)
            # top_end_content：右上角插槽（如 Input 输入数字）
            # 与 value_label 并存；如果用户希望只显示插槽，可同时传 hide_value=True
            if self._top_end_content_widget is not None:
                self._top_end_content_widget.setParent(self._label_row_widget)
                row.addWidget(
                    self._top_end_content_widget, 0, Qt.AlignmentFlag.AlignRight
                )
                self._top_end_content_widget.show()

        # 自绘画布
        self._canvas = _SliderCanvas(self)
        self._update_canvas_min_size()

        # canvas_band：把 [start_content | canvas | end_content] 包成一行/一列，
        # 让 icon 真正参与 layout（旧实现是 setParent(self)+show()，不挂 layout，
        # icon 浮在 0,0 角永远看不到 —— 实质等于没实现）。
        self._canvas_band = QWidget(self)
        if is_v:
            band = QVBoxLayout(self._canvas_band)
            band.setContentsMargins(0, 0, 0, 0)
            band.setSpacing(6)
            # 垂直方向：HeroUI 的 "下=min / 上=max" 视觉
            # → end_content 靠近 max（顶），start_content 靠近 min（底）
            if self._end_content_widget is not None:
                self._end_content_widget.setParent(self._canvas_band)
                band.addWidget(
                    self._end_content_widget, 0, Qt.AlignmentFlag.AlignHCenter
                )
                self._end_content_widget.show()
            band.addWidget(self._canvas, 1)
            if self._start_content_widget is not None:
                self._start_content_widget.setParent(self._canvas_band)
                band.addWidget(
                    self._start_content_widget, 0, Qt.AlignmentFlag.AlignHCenter
                )
                self._start_content_widget.show()
        else:
            band = QHBoxLayout(self._canvas_band)
            band.setContentsMargins(0, 0, 0, 0)
            band.setSpacing(6)
            if self._start_content_widget is not None:
                self._start_content_widget.setParent(self._canvas_band)
                band.addWidget(
                    self._start_content_widget, 0, Qt.AlignmentFlag.AlignVCenter
                )
                self._start_content_widget.show()
            band.addWidget(self._canvas, 1)
            if self._end_content_widget is not None:
                self._end_content_widget.setParent(self._canvas_band)
                band.addWidget(
                    self._end_content_widget, 0, Qt.AlignmentFlag.AlignVCenter
                )
                self._end_content_widget.show()

        if is_v:
            self._root.addWidget(self._canvas_band, 1)
            self._root.addWidget(self._label_row_widget, 0)
        else:
            self._root.addWidget(self._label_row_widget, 0)
            self._root.addWidget(self._canvas_band, 0)
            # bottom_start_content：轨道下方的左下提示（如 Text 帮助文字）
            if self._bottom_start_content_widget is not None:
                self._bottom_start_content_widget.setParent(self)
                self._root.addWidget(
                    self._bottom_start_content_widget, 0, Qt.AlignmentFlag.AlignLeft
                )
                self._bottom_start_content_widget.show()

        self._apply_text_styles()
        self._update_size_policy()

    def _apply_text_styles(self):
        cfg = self._cfg()
        self._label.set_size(cfg["label_font_size"])
        self._label.set_weight("medium")
        self._value_label.set_size(cfg["value_font_size"])
        self._value_label.set_weight("normal")

    def _update_size_policy(self):
        if self._orientation == "vertical":
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _update_canvas_min_size(self):
        cfg = self._cfg()
        thumb = cfg["thumb"]
        # 上下留白取 ring 与 hover 光晕较大者，避免裁剪
        pad = max(RING_WIDTH + RING_GAP, HALO_EXTRA)
        if self._orientation == "vertical":
            w = thumb + pad * 2
            if self._marks:
                w += marks_band_size(cfg)
            self._canvas.setMinimumSize(w, 80)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
        else:
            h = thumb + pad * 2
            if self._marks:
                h += marks_band_size(cfg)
            self._canvas.setFixedHeight(h)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )

    # ============================================================
    # 文字刷新
    # ============================================================
    def _refresh_text_labels(self):
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

        if self._hide_value:
            self._value_label.setText("")
            self._value_label.hide()
        else:
            self._value_label.setText(
                format_value(
                    self._value, self._is_range, self._step, self._value_formatter
                )
            )
            self._value_label.show()

        self._label_row_widget.setVisible(
            bool(self._label_text) or not self._hide_value
        )

    # ============================================================
    # 拖拽 scale-80 动画
    # ============================================================
    def _animate_press(self, idx: int, target: float):
        if self._disable_animation or self._disable_thumb_scale:
            stop_tween(self, f"_drag_runner_{idx}")
            self._drag_press_t[idx] = target
            self._canvas.update()
            return
        tween_value(
            self,
            f"_drag_runner_{idx}",
            float(self._drag_press_t[idx]),
            float(target),
            lambda v, i=idx: self._on_press_step(i, v),
            duration=_DRAG_PRESS_DURATION,
        )

    def _on_press_step(self, idx: int, v):
        self._drag_press_t[idx] = float(v)
        self._canvas.update()

    # ============================================================
    # 写入 thumb 值（拖拽/键盘/滚轮 共享入口）
    # ============================================================
    def _set_thumb_value(
        self, idx: int, raw: float, animate_signal: bool = True
    ) -> bool:
        new_v = snap_value(
            clamp_value(raw, self._min, self._max), self._min, self._max, self._step
        )
        if self._is_range:
            lo, hi = self._value  # type: ignore[misc]
            if idx == 0:
                lo = min(new_v, hi)
            else:
                hi = max(new_v, lo)
            new_value: ValueT = (lo, hi)
        else:
            new_value = new_v
        if new_value == self._value:
            return False
        self._value = new_value
        self._refresh_text_labels()
        self._canvas.update()
        if animate_signal:
            self.value_changed.emit(self._value)
        return True

    # ============================================================
    # canvas 鼠标事件（由 _SliderCanvas 转发）
    # ============================================================
    def _track_geom_q(self):
        return track_geom(
            self._cfg(),
            self._orientation,
            self._canvas.width(),
            self._canvas.height(),
            bool(self._marks),
        )

    def _canvas_mouse_press(self, event):
        if self._is_disabled or event.button() != Qt.MouseButton.LeftButton:
            return
        pt = event.position()
        cfg = self._cfg()
        track = self._track_geom_q()
        centers = thumb_centers(
            track, self._orientation, self._min, self._max, self._value, self._is_range
        )
        idx = hit_thumb(pt, centers, cfg["thumb"], self._hide_thumb)
        if idx == -1:
            # 点 track：跳到该位置（单 thumb），或最近的 thumb 跟过来（range）
            r = ratio_at_pos(pt, track, self._orientation)
            target_v = value_at_ratio(r, self._min, self._max)
            if self._is_range:
                lo, hi = self._value  # type: ignore[misc]
                idx = 0 if abs(target_v - lo) <= abs(target_v - hi) else 1
            else:
                idx = 0
            self._set_thumb_value(idx, target_v)
        self._dragging_idx = idx
        self._focused_idx = idx
        self._animate_press(idx, 1.0)
        self._tooltip_show(idx)
        self.setFocus()
        event.accept()

    def _canvas_mouse_move(self, event):
        if self._is_disabled:
            return
        # 拖拽中：跟拖动；非拖拽：实时更新 _hovered_idx 用于 tooltip 触发
        if self._dragging_idx != -1:
            track = self._track_geom_q()
            r = ratio_at_pos(event.position(), track, self._orientation)
            v = value_at_ratio(r, self._min, self._max)
            self._set_thumb_value(self._dragging_idx, v)
            self._tooltip_update(self._dragging_idx)
            event.accept()
            return
        cfg = self._cfg()
        track = self._track_geom_q()
        centers = thumb_centers(
            track, self._orientation, self._min, self._max, self._value, self._is_range
        )
        new_idx = hit_thumb(event.position(), centers, cfg["thumb"], self._hide_thumb)
        if new_idx != self._hovered_idx:
            old_idx = self._hovered_idx
            self._hovered_idx = new_idx
            self._canvas.update()
            # hover 进入 thumb → 显示 tooltip；离开 → 隐藏。拖拽期间不干预 drag tooltip。
            if old_idx != -1:
                self._tooltip_hide(old_idx)
            if new_idx != -1:
                self._tooltip_show(new_idx)

    def _canvas_mouse_release(self, event):
        if self._dragging_idx == -1 or event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._dragging_idx
        self._dragging_idx = -1
        self._animate_press(idx, 0.0)
        # 释放后：如果鼠标仍悬停在该 thumb 上 → 保持 tooltip。否则隐藏。
        if self._hovered_idx != idx:
            self._tooltip_hide(idx)
        self.change_end.emit(self._value)
        event.accept()

    # ============================================================
    # 键盘 / 滚轮 / hover
    # ============================================================
    def keyPressEvent(self, event):
        if self._is_disabled:
            return super().keyPressEvent(event)
        idx = self._focused_idx if self._is_range else 0
        cur = self._value[idx] if self._is_range else self._value  # type: ignore[index]

        page = max(self._step, (self._max - self._min) * _KEY_PAGE_FRAC)
        delta = 0.0
        is_v = self._orientation == "vertical"
        key = event.key()

        # 水平: Left/Right；垂直: Down/Up（向上 = 增大，对齐"下=min/上=max"）
        if (not is_v and key == Qt.Key.Key_Right) or (is_v and key == Qt.Key.Key_Up):
            delta = self._step
        elif (not is_v and key == Qt.Key.Key_Left) or (is_v and key == Qt.Key.Key_Down):
            delta = -self._step
        elif key == Qt.Key.Key_PageUp:
            delta = page
        elif key == Qt.Key.Key_PageDown:
            delta = -page
        elif key == Qt.Key.Key_Home:
            self._set_thumb_value(idx, self._min)
            self.change_end.emit(self._value)
            event.accept()
            return
        elif key == Qt.Key.Key_End:
            self._set_thumb_value(idx, self._max)
            self.change_end.emit(self._value)
            event.accept()
            return
        elif key == Qt.Key.Key_Tab and self._is_range:
            self._focused_idx = 1 - self._focused_idx
            self._canvas.update()
            event.accept()
            return
        else:
            return super().keyPressEvent(event)

        if delta != 0.0:
            self._set_thumb_value(idx, cur + delta)
            self.change_end.emit(self._value)
            event.accept()

    def wheelEvent(self, event):
        if self._is_disabled or not self._enable_wheel:
            return super().wheelEvent(event)
        d = event.angleDelta().y()
        if d == 0:
            return
        idx = self._focused_idx if self._is_range else 0
        cur = self._value[idx] if self._is_range else self._value  # type: ignore[index]
        sign = 1 if d > 0 else -1
        self._set_thumb_value(idx, cur + sign * self._step)
        self.change_end.emit(self._value)
        event.accept()

    def enterEvent(self, event):
        self._hover = True
        self._canvas.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        if self._hovered_idx != -1:
            old_idx = self._hovered_idx
            self._hovered_idx = -1
            if self._dragging_idx == -1:
                self._tooltip_hide(old_idx)
        self._canvas.update()
        super().leaveEvent(event)

    def _canvas_leave(self):
        """canvas 子 widget 鼠标离开 → 清 hovered_idx + 隐 tooltip。"""
        if self._hovered_idx != -1:
            old_idx = self._hovered_idx
            self._hovered_idx = -1
            self._canvas.update()
            # 拖拽中不隐（drag 期 tooltip 跟值）
            if self._dragging_idx == -1:
                self._tooltip_hide(old_idx)

    # ============================================================
    # 禁用 / 主题
    # ============================================================
    def _apply_disabled_effect(self, disabled: bool):
        if disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setGraphicsEffect(None)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用（auto 模式）"""
        self._theme = theme
        self._apply_text_styles()
        self._tooltip_apply_theme(theme)
        # str 路径生成的 icon 跟随主题重新着色（load_svg_icon color=None 看主题）
        for w in (self._start_content_widget, self._end_content_widget):
            if isinstance(w, _SliderIconLabel):
                w.apply_theme()
        self._canvas.update()

    # ============================================================
    # 内部 helper：side_content 归一化（str → _SliderIconLabel）
    # ============================================================
    def _coerce_side_content(self, x):
        """start_content / end_content 输入归一化。

        - None  → None
        - str   → _SliderIconLabel(icon_name=...)，跟主题自动着色
        - QWidget → 原样返回（用户自定义控件）
        """
        if x is None or isinstance(x, QWidget):
            return x
        if isinstance(x, str):
            return _SliderIconLabel(x, parent=self)
        raise TypeError(
            f"Slider start/end_content 只接受 None / str(icon name) / QWidget，"
            f"got {type(x).__name__}"
        )
