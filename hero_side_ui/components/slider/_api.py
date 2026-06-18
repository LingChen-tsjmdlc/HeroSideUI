"""Slider 公共 API（setter）Mixin。

把 22 个 `set_xxx` 方法集中放这里，让主体 `slider.py` 仅保留 `__init__` /
UI 装配 / 事件协调三件事。Mixin 不持有任何状态——所有 `self._xxx` 字段
都在 `Slider.__init__` 里建好。

为什么用 Mixin 而非独立函数：
    - setter 大量调用 `self._canvas.update()` / `self._refresh_text_labels()`
      等私有方法，写成函数会变成 `func(slider, ...)` 一长串，可读性差；
    - Mixin 多重继承在 PySide 自绘组件里是项目内常见组合（参见 Tabs/Listbox），
      `super().__init__(parent)` 链路无副作用。

注意：
    - Mixin **不要**写 `__init__`，免得参与 MRO 后被意外调用；
    - `set_value/set_range/set_step` 内部需要 `snap_value/clamp_value`，
      但这些都是 _geometry.py 的纯函数，直接 import 即可。
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ...core import ThemeProvider
from ._geometry import clamp_value, snap_value
from ._icon import _SliderIconLabel
from ._marks import parse_marks

# 类型由 slider.py 暴露；这里只用 Sequence/Callable，不引 ValueT 避免循环导入
__all__ = ["_SliderAPIMixin"]


class _SliderAPIMixin:
    """Slider 的对外 setter 集合。

    依赖宿主类（Slider）已建好的字段：
        _value / _min / _max / _step / _is_range
        _color / _size / _radius / _orientation
        _is_disabled / _hide_value / _hide_thumb / _show_outline
        _disable_thumb_scale / _disable_animation / _show_steps
        _marks / _value_formatter / _fill_offset
        _start_content_widget / _end_content_widget
        _theme_mode / _theme
        _label_text
        _canvas / _label / _value_label / _label_row_widget / _root

    依赖宿主类的方法：
        _refresh_text_labels / _apply_text_styles / _apply_disabled_effect
        _update_canvas_min_size / _setup_ui / _resolve_theme

    依赖宿主类的信号：
        value_changed
    """

    # 这些 attr 仅供 type checker / linter 知道存在；运行时由 Slider.__init__ 建
    _value: object
    _min: float
    _max: float
    _step: float
    _is_range: bool

    # ============================================================
    # 值 / 范围 / 步长
    # ============================================================
    def value(self):
        return self._value

    def set_value(self, value):
        if isinstance(value, (tuple, list)):
            self._is_range = True
            lo, hi = float(value[0]), float(value[1])
            self._value = (
                snap_value(
                    clamp_value(min(lo, hi), self._min, self._max),
                    self._min,
                    self._max,
                    self._step,
                ),
                snap_value(
                    clamp_value(max(lo, hi), self._min, self._max),
                    self._min,
                    self._max,
                    self._step,
                ),
            )
        else:
            self._is_range = False
            self._value = snap_value(
                clamp_value(float(value), self._min, self._max),
                self._min,
                self._max,
                self._step,
            )
        self._refresh_text_labels()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]
        self.value_changed.emit(self._value)  # type: ignore[attr-defined]

    def set_range(self, min_value: float, max_value: float):
        if max_value <= min_value:
            raise ValueError("max_value must be > min_value")
        self._min = float(min_value)
        self._max = float(max_value)
        self.set_value(self._value)

    def set_step(self, step: float):
        if step <= 0:
            raise ValueError("step must be positive")
        self._step = float(step)
        self.set_value(self._value)

    # ============================================================
    # 文字 / 颜色 / 尺寸 / 圆角 / 朝向
    # ============================================================
    def set_label(self, label: str):
        self._label_text = label  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_color(self, color: str):
        self._color = color  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_size(self, size: str):
        self._size = size  # type: ignore[attr-defined]
        self._apply_text_styles()  # type: ignore[attr-defined]
        self._update_canvas_min_size()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_radius(self, radius: str):
        self._radius = radius  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_orientation(self, orientation: str):
        if (
            orientation not in ("horizontal", "vertical")
            or orientation == self._orientation  # type: ignore[attr-defined]
        ):
            return
        self._orientation = orientation  # type: ignore[attr-defined]
        # 先把所有"外部传入的 widget"setParent(None) 解绑 ——
        # 否则下一行临时 QWidget().setLayout(self._root) 销毁旧 layout 时，
        # 这些 widget 会被连锁销毁（C++ 对象 deleted）。它们会在 _setup_ui()
        # 重建时被重新挂回。
        for attr in (
            "_top_end_content_widget",
            "_bottom_start_content_widget",
            "_start_content_widget",
            "_end_content_widget",
        ):
            ext = getattr(self, attr, None)
            if ext is not None:
                ext.hide()
                ext.setParent(None)
        # 把旧 layout 转移到临时 widget 销毁后重新装配
        QWidget().setLayout(self._root)  # type: ignore[attr-defined]
        self._setup_ui()  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    # ============================================================
    # 标志位
    # ============================================================
    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled  # type: ignore[attr-defined]
        self._apply_disabled_effect(disabled)  # type: ignore[attr-defined]

    def set_hide_value(self, hide: bool):
        self._hide_value = hide  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_hide_thumb(self, hide: bool):
        self._hide_thumb = hide  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_show_outline(self, show: bool):
        self._show_outline = show  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_disable_thumb_scale(self, disable: bool):
        self._disable_thumb_scale = disable  # type: ignore[attr-defined]

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable  # type: ignore[attr-defined]

    def set_show_steps(self, show: bool):
        self._show_steps = show  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    # ============================================================
    # marks / formatter / fill_offset
    # ============================================================
    def set_marks(self, marks: Sequence):
        self._marks = parse_marks(marks or [], self._min, self._max)  # type: ignore[attr-defined]
        self._update_canvas_min_size()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_value_formatter(self, fn: Optional[Callable]):
        self._value_formatter = fn  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_fill_offset(self, offset: Optional[float]):
        self._fill_offset = offset  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_show_tooltip(self, enabled: bool):
        """切换 thumb 上方拖拽 tooltip 显示。"""
        self._show_tooltip = bool(enabled)  # type: ignore[attr-defined]
        # 清掉旧的 anchor 和 tooltip
        for a in getattr(self, "_tip_anchors", []) or []:
            a.hide()
            a.setParent(None)
        for t in getattr(self, "_tooltips", []) or []:
            t.close()
            t.hide()
            t.setParent(None)
        self._tip_anchors = []  # type: ignore[attr-defined]
        self._tooltips = []  # type: ignore[attr-defined]
        # 启用则重建（_init_tooltips 内部判 _show_tooltip）
        self._init_tooltips()  # type: ignore[attr-defined]

    def set_enable_wheel(self, enabled: bool):
        """切换是否允许鼠标滚轮调整滑块值（默认关闭）。"""
        self._enable_wheel = bool(enabled)  # type: ignore[attr-defined]

    # ============================================================
    # 插槽 widget
    # ============================================================
    def set_start_content(self, w: Optional[Union[QWidget, str]]):
        """track 起始侧（水平=左 / 垂直=下，靠近 min）的 icon/widget。

        传 str → 自动包为 _SliderIconLabel，跟主题着色。
        传 QWidget → 直接使用。
        """
        if isinstance(w, str):
            w = _SliderIconLabel(w, parent=self)  # type: ignore[arg-type]
        old = self._start_content_widget  # type: ignore[attr-defined]
        band_layout = self._canvas_band.layout()  # type: ignore[attr-defined]
        if old is not None:
            if band_layout is not None:
                band_layout.removeWidget(old)
            old.hide()
            old.setParent(None)
        self._start_content_widget = w  # type: ignore[attr-defined]
        if w is not None and band_layout is not None:
            w.setParent(self._canvas_band)  # type: ignore[attr-defined]
            is_v = self._orientation == "vertical"  # type: ignore[attr-defined]
            # 水平：start 在 layout index 0；垂直："下=min" → start 在末尾
            align = (
                Qt.AlignmentFlag.AlignHCenter if is_v else Qt.AlignmentFlag.AlignVCenter
            )
            if is_v:
                band_layout.addWidget(w, 0, align)
            else:
                band_layout.insertWidget(0, w, 0, align)
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    def set_end_content(self, w: Optional[Union[QWidget, str]]):
        """track 结束侧（水平=右 / 垂直=上，靠近 max）的 icon/widget。

        传 str → 自动包为 _SliderIconLabel，跟主题着色。
        传 QWidget → 直接使用。
        """
        if isinstance(w, str):
            w = _SliderIconLabel(w, parent=self)  # type: ignore[arg-type]
        old = self._end_content_widget  # type: ignore[attr-defined]
        band_layout = self._canvas_band.layout()  # type: ignore[attr-defined]
        if old is not None:
            if band_layout is not None:
                band_layout.removeWidget(old)
            old.hide()
            old.setParent(None)
        self._end_content_widget = w  # type: ignore[attr-defined]
        if w is not None and band_layout is not None:
            w.setParent(self._canvas_band)  # type: ignore[attr-defined]
            is_v = self._orientation == "vertical"  # type: ignore[attr-defined]
            align = (
                Qt.AlignmentFlag.AlignHCenter if is_v else Qt.AlignmentFlag.AlignVCenter
            )
            # 水平：end 在末尾；垂直："上=max" → end 在 index 0
            if is_v:
                band_layout.insertWidget(0, w, 0, align)
            else:
                band_layout.addWidget(w, 0, align)
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    def set_top_end_content(self, w: Optional[QWidget]):
        """右上角插槽（label 行末尾，例如放 Input 直接输入数值）。

        增量更新 _label_row_widget 的内部 layout —— 不重建整个 UI，
        避免把 _canvas / 用户传入的其他外部 widget 一并销毁
        （历史 bug：临时 `QWidget().setLayout(self._root)` 转移会连锁删除 Qt 子对象）。
        """
        # 1) 移除旧 widget
        old = self._top_end_content_widget  # type: ignore[attr-defined]
        row_layout = self._label_row_widget.layout()  # type: ignore[attr-defined]
        if old is not None:
            if row_layout is not None:
                row_layout.removeWidget(old)
            old.hide()
            old.setParent(None)
        self._top_end_content_widget = w  # type: ignore[attr-defined]
        # 2) 挂入新 widget（仅水平方向有"行末尾"语义；垂直方向无视）
        if w is not None and self._orientation == "horizontal" and row_layout is not None:  # type: ignore[attr-defined]
            w.setParent(self._label_row_widget)  # type: ignore[attr-defined]
            row_layout.addWidget(w, 0, Qt.AlignmentFlag.AlignRight)
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    def set_bottom_start_content(self, w: Optional[QWidget]):
        """左下角插槽（轨道下方，例如放 Caption 帮助提示）。

        增量更新 self._root —— 同样不重建整个 UI。
        """
        old = self._bottom_start_content_widget  # type: ignore[attr-defined]
        if old is not None:
            self._root.removeWidget(old)  # type: ignore[attr-defined]
            old.hide()
            old.setParent(None)
        self._bottom_start_content_widget = w  # type: ignore[attr-defined]
        # 仅水平方向有"轨道下方"语义；垂直方向无视
        if w is not None and self._orientation == "horizontal":  # type: ignore[attr-defined]
            w.setParent(self)  # type: ignore[arg-type]
            self._root.addWidget(w, 0, Qt.AlignmentFlag.AlignLeft)  # type: ignore[attr-defined]
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"  # type: ignore[attr-defined]
            self._theme = self._resolve_theme("auto")  # type: ignore[attr-defined]
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":  # type: ignore[attr-defined]
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme  # type: ignore[attr-defined]
            self._theme = theme  # type: ignore[attr-defined]
        self._apply_text_styles()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]
