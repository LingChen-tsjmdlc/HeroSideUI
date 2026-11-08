"""Spinner 主组件：variant/color/size/label/label_color/theme。"""

from __future__ import annotations

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

    def __init__(self, owner: Spinner, parent: QWidget | None = None):
        """绑定持有者 Spinner 并创建画布。

        Args:
            owner: 提供尺寸、颜色与相位数据的 Spinner 实例。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self._owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        """按 variant 把绘制分派到对应的 paint_* 函数。

        Args:
            event: Qt 绘制事件，本实现不读取。

        Note:
            宽高非正时直接返回；仅 default 变体读取第二条驱动器 _driver_b。
        """
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
        parent: QWidget | None = None,
    ):
        """按变体与外观配置创建 loading 指示器。

        Args:
            variant: 变体名，共 6 种。
            color: 颜色名。
            size: 尺寸档位。
            label: 可选标签文字，空字符串表示不显示。
            theme: 主题模式，auto 时跟随系统主题。
            parent: 父级 QWidget。

        Note:
            variant、color、size 的非法值分别回退到 default、primary、md；auto 主题会向 ThemeProvider 注册接收广播。
        """
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
        """创建画布与标签并装入居中纵向布局。"""
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
        """返回当前尺寸档位的配置字典。"""
        return SPINNER_SIZES.get(self._size, SPINNER_SIZES["md"])

    def _canvas_diameter(self) -> int:
        """返回画布直径；wave/dots 变体使用专用直径档位。"""
        cfg = self._size_cfg()
        if self._variant in ("wave", "dots"):
            return int(cfg["diameter_wave_dots"])
        return int(cfg["diameter"])

    def _indicator_color(self) -> QColor:
        """返回当前颜色与主题对应的主色 QColor。"""
        return resolve_indicator_color(self._color, self._theme)

    def _label_qcolor(self) -> QColor:
        """label 自动跟随 spinner 主色（铁律 1：组件自管，不让用户决策）。"""
        return resolve_indicator_color(self._color, self._theme)

    # ----- 应用样式 / 文字 -----
    def _apply_styles(self):
        """按当前尺寸刷新画布固定尺寸、标签字号与颜色。"""
        d = self._canvas_diameter()
        self._canvas.setFixedSize(d, d)
        cfg = self._size_cfg()
        # label 走统一 Text：set_size + set_color
        self._label.set_size(cfg["label_font_size"])
        self._label.set_color(self._label_qcolor())
        self._canvas.update()

    def _refresh_label(self):
        """按标签文字刷新文本与可见性。"""
        self._label.setText(self._label_text or "")
        self._label.setVisible(bool(self._label_text))

    def _apply_durations(self):
        """按变体设置各相位驱动器的周期。"""
        # HeroUI 各 variant 的官方周期
        if self._variant == "default":
            self._driver_a.set_duration(800)
            self._driver_b.set_duration(800)
        elif self._variant == "simple" or self._variant == "gradient":
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
        """把主题模式解析为具体主题名。

        Args:
            mode: light、dark 或 auto。

        Returns:
            具体主题名；auto 时取 ThemeProvider 当前主题。

        Note:
            mode 非 light/dark 时一律按 auto 处理，未做校验。
        """
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
        """校验变体名并返回可用的变体。

        Args:
            v: 待校验的变体名。

        Returns:
            校验后的变体名。

        Note:
            v 不在 VALID_VARIANTS 时回退到 default，未做报错。
        """
        return v if v in VALID_VARIANTS else "default"

    @staticmethod
    def _validate_color(c: str) -> str:
        """校验颜色名并返回可用的颜色。

        Args:
            c: 待校验的颜色名。

        Returns:
            校验后的颜色名。

        Note:
            c 不在 VALID_COLORS 时回退到 primary，未做报错。
        """
        return c if c in VALID_COLORS else "primary"

    # ============================================================
    # 公共 API
    # ============================================================
    def set_variant(self, variant: str):
        """切换变体并同步驱动器与样式。

        Args:
            variant: 目标变体名。

        Note:
            非法或同名变体直接返回；切入 default 时启动 _driver_b，切出时停止。
        """
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
        """设置颜色并刷新标签配色。

        Args:
            color: 目标颜色名。

        Note:
            非法颜色名由 _validate_color 回退到 primary。
        """
        self._color = self._validate_color(color)
        self._apply_styles()  # label 跟随主色刷新

    def set_size(self, size: str):
        """设置尺寸档位并刷新样式。

        Args:
            size: 目标尺寸档位。

        Note:
            size 不在 SPINNER_SIZES 时直接返回，不改动当前尺寸。
        """
        if size not in SPINNER_SIZES:
            return
        self._size = size
        self._apply_styles()

    def set_label(self, label: str):
        """设置标签文字并刷新可见性。

        Args:
            label: 标签文字，空字符串表示隐藏标签。
        """
        self._label_text = label
        self._refresh_label()

    def set_theme(self, theme: str):
        """设置主题模式并刷新样式。

        Args:
            theme: 主题名或 auto。

        Note:
            auto 会向 ThemeProvider 注册，从 auto 切到固定主题时注销；非 auto 值原样作为主题名，未做校验。
        """
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
        """返回当前变体名。"""
        return self._variant

    def color(self) -> str:
        """返回当前颜色名。"""
        return self._color

    def size(self) -> str:
        """返回当前尺寸档位。"""
        return self._size

    def label(self) -> str:
        """返回当前标签文字。"""
        return self._label_text


__all__ = ["Spinner"]
