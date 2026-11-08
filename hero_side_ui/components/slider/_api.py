"""Slider 公共 setter Mixin：22 个 set_xxx 方法，不持有状态。

Mixin 不写 __init__ 以免参与 MRO 被意外调用；宿主字段与方法在 Slider
主类建好后由本 Mixin 调用。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

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

    Note:
        依赖宿主已建好的 _value/_color/_canvas 等字段、_refresh_text_labels
        等方法与 value_changed 信号。
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
        """返回当前滑块值。"""
        return self._value

    def set_value(self, value):
        """设置滑块值，按范围与步长归一化后刷新并派发 value_changed。

        Args:
            value: 单值或 (lo, hi) 序列；序列自动切到 range 模式。

        Note:
            单值会 clamp 到 [min, max] 再 snap 到 step；range 会先排序两端。
        """
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
        """重设取值范围并用新范围重新归一化当前值。

        Args:
            min_value: 新的最小值。
            max_value: 新的最大值。

        Note:
            max_value <= min_value 时抛出 ValueError，不修改状态。
        """
        if max_value <= min_value:
            raise ValueError("max_value must be > min_value")
        self._min = float(min_value)
        self._max = float(max_value)
        self.set_value(self._value)

    def set_step(self, step: float):
        """重设步长并用新步长重新归一化当前值。

        Args:
            step: 新的步长。

        Note:
            step <= 0 时抛出 ValueError，不修改状态。
        """
        if step <= 0:
            raise ValueError("step must be positive")
        self._step = float(step)
        self.set_value(self._value)

    # ============================================================
    # 文字 / 颜色 / 尺寸 / 圆角 / 朝向
    # ============================================================
    def set_label(self, label: str):
        """设置 label 文案并刷新文字标签。"""
        self._label_text = label  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_color(self, color: str):
        """设置语义色并触发画布重绘。"""
        self._color = color  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_size(self, size: str):
        """设置尺寸档位并刷新文字样式、画布最小尺寸与重绘。"""
        self._size = size  # type: ignore[attr-defined]
        self._apply_text_styles()  # type: ignore[attr-defined]
        self._update_canvas_min_size()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_radius(self, radius: str):
        """设置圆角档位并触发画布重绘。"""
        self._radius = radius  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_orientation(self, orientation: str):
        """切换水平 / 垂直方向并重建 UI。

        Args:
            orientation: 目标方向，horizontal 或 vertical。

        Note:
            非法值或与当前方向相同则直接返回；重建前先把外部传入的插槽
            widget 解绑，否则旧 layout 销毁时会连锁删除这些 Qt 对象。
        """
        if (
            orientation not in ("horizontal", "vertical") or orientation == self._orientation  # type: ignore[attr-defined]
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
        """设置禁用态并下发禁用视觉效果。"""
        self._is_disabled = disabled  # type: ignore[attr-defined]
        self._apply_disabled_effect(disabled)  # type: ignore[attr-defined]

    def set_hide_value(self, hide: bool):
        """设置是否隐藏数值文字并刷新标签。"""
        self._hide_value = hide  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_hide_thumb(self, hide: bool):
        """设置是否隐藏 thumb 并触发画布重绘。"""
        self._hide_thumb = hide  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_show_outline(self, show: bool):
        """设置是否显示 thumb 外圈并触发画布重绘。"""
        self._show_outline = show  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_disable_thumb_scale(self, disable: bool):
        """设置是否关闭拖拽时 thumb 的缩放动画。"""
        self._disable_thumb_scale = disable  # type: ignore[attr-defined]

    def set_disable_animation(self, disable: bool):
        """设置是否关闭动画。"""
        self._disable_animation = disable  # type: ignore[attr-defined]

    def set_show_steps(self, show: bool):
        """设置是否显示 step 标记并触发画布重绘。"""
        self._show_steps = show  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    # ============================================================
    # marks / formatter / fill_offset
    # ============================================================
    def set_marks(self, marks: Sequence):
        """解析并设置 marks，刷新画布最小尺寸与重绘。"""
        self._marks = parse_marks(marks or [], self._min, self._max)  # type: ignore[attr-defined]
        self._update_canvas_min_size()  # type: ignore[attr-defined]
        self._canvas.update()  # type: ignore[attr-defined]

    def set_value_formatter(self, fn: Callable | None):
        """设置自定义数值格式化回调并刷新标签。"""
        self._value_formatter = fn  # type: ignore[attr-defined]
        self._refresh_text_labels()  # type: ignore[attr-defined]

    def set_fill_offset(self, offset: float | None):
        """设置 filler 起点偏移并触发画布重绘。"""
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
    def set_start_content(self, w: QWidget | str | None):
        """设置 track 起始侧内容（水平=左/垂直=下，靠近 min）。"""
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
            align = Qt.AlignmentFlag.AlignHCenter if is_v else Qt.AlignmentFlag.AlignVCenter
            if is_v:
                band_layout.addWidget(w, 0, align)
            else:
                band_layout.insertWidget(0, w, 0, align)
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    def set_end_content(self, w: QWidget | str | None):
        """设置 track 结束侧内容（水平=右/垂直=上，靠近 max）。"""
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
            align = Qt.AlignmentFlag.AlignHCenter if is_v else Qt.AlignmentFlag.AlignVCenter
            # 水平：end 在末尾；垂直："上=max" → end 在 index 0
            if is_v:
                band_layout.insertWidget(0, w, 0, align)
            else:
                band_layout.addWidget(w, 0, align)
            w.show()
        self._canvas.update()  # type: ignore[attr-defined]

    def set_top_end_content(self, w: QWidget | None):
        """设置右上角插槽（label 行末尾，如放 Input 直输数值）。

        Note:
            增量更新 layout 不重建 UI，避免连锁删除 Qt 子对象。
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

    def set_bottom_start_content(self, w: QWidget | None):
        """设置左下角插槽（轨道下方，例如放 Caption 帮助提示）。

        Note:
            增量更新 self._root，不重建整个 UI。
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
        """切换主题模式并刷新文字样式与画布。

        Args:
            theme: 目标模式；auto 重新注册 ThemeProvider，其他值注销注册。
        """
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
