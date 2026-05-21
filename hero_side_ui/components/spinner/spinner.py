"""HeroUI 风格 Spinner 主组件。

参数与公开 API：

    Spinner(
        variant="default",         # default / simple / gradient / spinner / wave / dots
        color="primary",           # current / white / default / primary / secondary / success / warning / danger
        size="md",                 # sm / md / lg
        label="",                  # 下方/右侧的可选文字
        label_color="foreground",  # foreground / primary / secondary / success / warning / danger
        theme="auto",              # auto / light / dark
        parent=None,
    )

    set_variant / set_color / set_size / set_label / set_label_color / set_theme

注意：Spinner 永远是循环动画（loading 指示器），没有 is_indeterminate 概念。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import PhaseDriver
from ...core import ThemeProvider
from ...themes import SPINNER_SIZES
from ..text import Text
from ._colors import (
    VALID_COLORS,
    VALID_VARIANTS,
    resolve_indicator_color,
)
from ._paint_default import paint_default
from ._paint_dots import paint_dots, paint_wave
from ._paint_gradient import paint_gradient
from ._paint_simple import paint_simple
from ._paint_spinner_bars import paint_spinner


# ============================================================
# 自绘 wrapper（只画 spinner 本身，不含 label）
# ============================================================
class _SpinnerCanvas(QWidget):
    """承担 paintEvent 的"画布"子部件。"""

    def __init__(self, owner: "Spinner", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        owner = self._owner
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cfg = owner._size_cfg()
        indicator = owner._indicator_color()
        variant = owner._variant

        if variant == "default":
            paint_default(
                painter,
                w,
                h,
                indicator,
                border=cfg["border_width"],
                phase_ease=owner._driver_a.value(),
                phase_linear=owner._driver_b.value(),
            )
        elif variant == "simple":
            paint_simple(
                painter,
                w,
                h,
                indicator,
                border=cfg["border_width"],
                phase=owner._driver_a.value(),
            )
        elif variant == "gradient":
            paint_gradient(
                painter,
                w,
                h,
                indicator,
                border=cfg["border_width"],
                phase=owner._driver_a.value(),
            )
        elif variant == "spinner":
            paint_spinner(
                painter,
                w,
                h,
                indicator,
                bar_length=cfg["bar_length"],
                bar_width=cfg["bar_width"],
                phase=owner._driver_a.value(),
            )
        elif variant == "wave":
            paint_wave(
                painter,
                w,
                h,
                indicator,
                dot_size=cfg["dot_size"],
                phase=owner._driver_a.value(),
            )
        elif variant == "dots":
            paint_dots(
                painter,
                w,
                h,
                indicator,
                dot_size=cfg["dot_size"],
                phase=owner._driver_a.value(),
            )


# ============================================================
# Spinner 主组件
# ============================================================
class Spinner(QWidget):
    """HeroUI 风格 loading 指示器，6 种变体。详见模块 docstring。"""

    def __init__(
        self,
        variant: str = "default",
        color: str = "primary",
        size: str = "md",
        label: str = "",
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._variant = self._validate_variant(variant)
        self._color = self._validate_color(color)
        self._size = size if size in SPINNER_SIZES else "md"
        self._label_text = label

        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 驱动器：driver_a 用于"主 phase"，driver_b 仅 default 变体用作第二条圆弧
        self._driver_a = PhaseDriver(owner=self, duration=900)
        self._driver_b = PhaseDriver(owner=self, duration=800)

        self._setup_ui()
        self._apply_durations()
        self._apply_styles()
        self._refresh_label()

        self._driver_a.start()
        if self._variant == "default":
            self._driver_b.start()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ----- 组装 UI -----
    def _setup_ui(self):
        self._canvas = _SpinnerCanvas(owner=self)
        self._label = Text("", selectable=False)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._canvas, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # ----- 派生信息 -----
    def _size_cfg(self) -> dict:
        return SPINNER_SIZES.get(self._size, SPINNER_SIZES["md"])

    def _canvas_diameter(self) -> int:
        cfg = self._size_cfg()
        if self._variant in ("wave", "dots"):
            return int(cfg["diameter_wave_dots"])
        return int(cfg["diameter"])

    def _indicator_color(self) -> QColor:
        return resolve_indicator_color(self._color, self._theme)

    def _label_qcolor(self) -> QColor:
        """label 自动跟随 spinner 主色（铁律 1：组件自管，不让用户决策）。"""
        return resolve_indicator_color(self._color, self._theme)

    # ----- 应用样式 / 文字 -----
    def _apply_styles(self):
        d = self._canvas_diameter()
        self._canvas.setFixedSize(d, d)
        cfg = self._size_cfg()
        # label 走统一 Text：set_size + set_color
        self._label.set_size(cfg["label_font_size"])
        self._label.set_color(self._label_qcolor())
        self._canvas.update()

    def _refresh_label(self):
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

    def _apply_durations(self):
        # HeroUI 各 variant 的官方周期
        if self._variant == "default":
            self._driver_a.set_duration(800)
            self._driver_b.set_duration(800)
        elif self._variant == "simple":
            self._driver_a.set_duration(1000)
        elif self._variant == "gradient":
            self._driver_a.set_duration(1000)
        elif self._variant == "spinner":
            self._driver_a.set_duration(1200)
        elif self._variant == "wave":
            self._driver_a.set_duration(750)
        elif self._variant == "dots":
            self._driver_a.set_duration(1400)

    # ----- 主题 -----
    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用 hook。"""
        self._theme = theme
        self._apply_styles()

    # ----- 校验 -----
    @staticmethod
    def _validate_variant(v: str) -> str:
        return v if v in VALID_VARIANTS else "default"

    @staticmethod
    def _validate_color(c: str) -> str:
        return c if c in VALID_COLORS else "primary"

    # ============================================================
    # 公共 API
    # ============================================================
    def set_variant(self, variant: str):
        if variant not in VALID_VARIANTS:
            return
        if variant == self._variant:
            return
        self._variant = variant
        # 切到/出 default 时管 driver_b
        self._apply_durations()
        if self._variant == "default":
            if not self._driver_b.is_running():
                self._driver_b.start()
        else:
            self._driver_b.stop()
        self._apply_styles()

    def set_color(self, color: str):
        self._color = self._validate_color(color)
        self._apply_styles()  # label 跟随主色刷新

    def set_size(self, size: str):
        if size not in SPINNER_SIZES:
            return
        self._size = size
        self._apply_styles()

    def set_label(self, label: str):
        self._label_text = label
        self._refresh_label()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    # 便捷 getters
    def variant(self) -> str:
        return self._variant

    def color(self) -> str:
        return self._color

    def size(self) -> str:
        return self._size

    def label(self) -> str:
        return self._label_text


__all__ = ["Spinner"]
