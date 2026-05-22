"""Slider 的 thumb tip 显隐辅助（仅当 show_tooltip=True 时启用）。

不复用通用 Tooltip——后者顶层窗口模式会闪一帧 Windows 原生装饰，
embedded 模式 reparent 链也不可靠。改用 _SliderThumbTip：永远是 canvas
的直系子 widget，自绘背景 + 文字 + 箭头。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget

from ._geometry import thumb_centers
from ._marks import format_value
from ._thumb_tip import _SliderThumbTip

__all__ = ["_SliderTooltipMixin"]


class _SliderTooltipMixin:
    """Slider 的 thumb tip 显隐辅助。

    依赖宿主 Slider 已有字段：
        _show_tooltip / _tooltip_props / _canvas / _is_range
        _value / _min / _max / _value_formatter / _step
        _orientation / _hide_thumb / _theme_mode
    """

    # ------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------
    def _init_tooltips(self) -> None:
        # _tip_anchors 保留为空 list（_api.py 重建逻辑兼容）
        self._tip_anchors: list[QWidget] = []
        self._tooltips: list[_SliderThumbTip] = []
        if not getattr(self, "_show_tooltip", False):
            return
        n = 2 if self._is_range else 1  # type: ignore[attr-defined]
        props = dict(self._tooltip_props or {})  # type: ignore[attr-defined]
        color = props.get("color", "default")
        size = props.get("size", "md")
        theme = props.get("theme", self._theme_mode)  # type: ignore[attr-defined]
        disable_anim = bool(props.get("disable_animation", False))
        for _ in range(n):
            tip = _SliderThumbTip(
                self._canvas,  # type: ignore[attr-defined]
                color=color,
                size=size,
                theme=theme,
                disable_animation=disable_anim,
            )
            self._tooltips.append(tip)

    # ------------------------------------------------------------
    # 显隐控制
    # ------------------------------------------------------------
    def _tooltip_show(self, idx: int) -> None:
        if not self._tooltips or idx < 0 or idx >= len(self._tooltips):
            return
        tip = self._tooltips[idx]
        tip.set_text(self._tooltip_text_for(idx))
        tip.show_at(self._thumb_top_center(idx))

    def _tooltip_hide(self, idx: Optional[int] = None) -> None:
        if not self._tooltips:
            return
        if idx is None:
            for tip in self._tooltips:
                tip.fade_out()
        elif 0 <= idx < len(self._tooltips):
            self._tooltips[idx].fade_out()

    def _tooltip_update(self, idx: int) -> None:
        """drag 期间值改变 → 更新文字 + 重新定位。"""
        if not self._tooltips or idx < 0 or idx >= len(self._tooltips):
            return
        tip = self._tooltips[idx]
        tip.set_text(self._tooltip_text_for(idx))
        tip.show_at(self._thumb_top_center(idx))

    # ------------------------------------------------------------
    # 几何 / 文字
    # ------------------------------------------------------------
    def _thumb_top_center(self, idx: int) -> QPointF:
        """thumb 顶部中心（canvas 坐标系），tip 底部箭头尖端对齐到这里上方。"""
        from ._geometry import track_geom

        cfg = self._cfg()  # type: ignore[attr-defined]
        canvas = self._canvas  # type: ignore[attr-defined]
        track = track_geom(
            cfg,
            self._orientation,  # type: ignore[attr-defined]
            canvas.width(),
            canvas.height(),
            bool(getattr(self, "_marks", None)),
        )
        centers = thumb_centers(
            track,
            self._orientation,  # type: ignore[attr-defined]
            self._min,  # type: ignore[attr-defined]
            self._max,  # type: ignore[attr-defined]
            self._value,  # type: ignore[attr-defined]
            self._is_range,  # type: ignore[attr-defined]
        )
        if idx >= len(centers):
            return QPointF(0, 0)
        c = centers[idx]
        thumb = cfg["thumb"]
        return QPointF(c.x(), c.y() - thumb / 2.0)

    def _tooltip_text_for(self, idx: int) -> str:
        v = self._value  # type: ignore[attr-defined]
        if self._is_range:  # type: ignore[attr-defined]
            single = v[idx]
            return format_value(
                single,
                False,
                self._step,  # type: ignore[attr-defined]
                None,
            )
        return format_value(
            v,
            False,
            self._step,  # type: ignore[attr-defined]
            self._value_formatter,  # type: ignore[attr-defined]
        )

    # ------------------------------------------------------------
    # 主题同步
    # ------------------------------------------------------------
    def _tooltip_apply_theme(self, theme: str) -> None:
        for tip in getattr(self, "_tooltips", []) or []:
            tip.set_theme(theme)
