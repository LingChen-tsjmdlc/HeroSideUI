"""
HeroSideUI 全局滚动条样式管理器 (ScrollStyle)

为整个应用提供统一的细线条滚动条样式，支持 hover 时**带动画过渡**地变粗 + 变色，
并在 ThemeProvider 主题切换时自动跟随。

设计参照 HeroUI 的"细线 + hover 加粗 + hover 加深"风格：
    - 默认细 6px，hover 加粗 +2px = 8px（ease-out，duration 默认 150ms）
    - 默认色用 default 色阶 300 (亮) / 700 (暗)，hover 加深到 400 / 600
    - 颜色支持 default / primary / secondary / success / warning / danger（同 Button 等组件）

实现两层架构：
    1) **静态层**：`apply_global()` 注入 QApplication QSS（无 :hover 选择器，
       只设默认状态）。这层让所有 QScrollBar 都先有正确的"细 + 暗"初始外观。
    2) **动画层**：QApplication eventFilter 拦截所有 QScrollBar 的 Enter/Leave 事件，
       为每条 bar 启动 QVariantAnimation 在 0→1 间插值。回调里把 thickness 和
       handle 颜色按进度算出，setStyleSheet 局部覆盖到那条 bar 上，达成丝滑过渡。

为什么不用 QSS `:hover`？
    - Qt QSS 的 `QScrollBar:hover { width: ... }` 不会触发布局重算（width 只在
      widget 创建时被读一次）
    - QSS 不支持 transition（CSS 的过渡能力，Qt 没实现）
    - 所以必须用 Python 动画驱动，逐帧重设 stylesheet

用法：
    from hero_side_ui import ScrollStyle, ThemeProvider
    ThemeProvider.instance()
    ScrollStyle.instance().apply_global()  # 一行接入

    # 配置
    ScrollStyle.instance().set_thickness(8)
    ScrollStyle.instance().set_hover_thickness_delta(3)
    ScrollStyle.instance().set_color("primary")
    ScrollStyle.instance().set_duration(200)  # 动画时长（ms）

主题联动：
    ScrollStyle 监听 ThemeProvider.theme_changed，主题切换时自动重新 apply_global()
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QObject, QEvent, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QScrollBar

from ..themes import HEROUI_COLORS
from ..animation.tween import tween_value, stop_tween
from .theme_provider import ThemeProvider


VALID_COLORS = ("neutral", "default", "primary", "secondary", "success", "warning", "danger")


class ScrollStyle(QObject):
    """全局滚动条样式管理器（单例）

    线程不安全，仅在 GUI 主线程使用。
    """

    _instance: Optional["ScrollStyle"] = None

    @classmethod
    def instance(cls) -> "ScrollStyle":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        # 默认配置
        self._thickness: int = 6
        self._hover_thickness_delta: int = 2
        # 全局默认色：neutral（纯灰，无色相偏移；比 default/zinc 更"中性"）
        # Textarea 等组件会用 set_bar_color 覆盖成自己的语义色
        self._color: str = "neutral"
        self._min_handle_length: int = 24
        self._track_padding: int = 4
        self._duration: int = 150           # hover 过渡时长 (ms)
        self._easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic
        # handle 阴影（用 1px border 模拟）：normal alpha=满，hover alpha 渐变到 0
        # 当前默认是"轻量阴影"——视觉上若隐若现，不喧宾夺主
        self._shadow_alpha_light: int = 15    # 亮色：约 6%（之前 30 偏重，减半到 15）
        self._shadow_alpha_dark: int = 50     # 暗色：约 20%（之前 100 偏重，减半到 50）

        self._applied: bool = False
        self._app_filter_installed: bool = False

        # 订阅主题变化
        try:
            ThemeProvider.instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ============================================================
    # 配置 setter
    # ============================================================
    def set_thickness(self, px: int):
        self._thickness = max(2, int(px))
        self._reapply_if_active()

    def set_hover_thickness_delta(self, delta_px: int):
        self._hover_thickness_delta = max(0, int(delta_px))
        self._reapply_if_active()

    def set_color(self, color: str):
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        self._color = color
        self._reapply_if_active()

    def set_min_handle_length(self, px: int):
        self._min_handle_length = max(8, int(px))
        self._reapply_if_active()

    def set_track_padding(self, px: int):
        self._track_padding = max(0, int(px))
        self._reapply_if_active()

    def set_duration(self, ms: int):
        """hover 进出过渡时长（ms）。0 = 无动画，瞬间切换。"""
        self._duration = max(0, int(ms))

    def set_easing(self, easing: QEasingCurve.Type):
        self._easing = easing

    def set_shadow_alpha(self, *, light: Optional[int] = None, dark: Optional[int] = None):
        """设置 handle 阴影（border 模拟）的 alpha 强度（0-255）

        normal 状态用此 alpha；hover 时渐变到 0（border 消失）。

        Args:
            light: 亮色模式 alpha；默认 30（约 12%）
            dark:  暗色模式 alpha；默认 100（约 40%）
        """
        if light is not None:
            self._shadow_alpha_light = max(0, min(255, int(light)))
        if dark is not None:
            self._shadow_alpha_dark = max(0, min(255, int(dark)))
        self._reapply_if_active()

    # ============================================================
    # 取值
    # ============================================================
    @property
    def thickness(self) -> int:
        return self._thickness

    @property
    def hover_thickness(self) -> int:
        return self._thickness + self._hover_thickness_delta

    @property
    def color(self) -> str:
        return self._color

    # ============================================================
    # 单条 bar 颜色覆盖（典型用例: Textarea 让滚动条跟随自己的 color 属性）
    # ============================================================
    def set_bar_color(self, bar: QScrollBar, color: Optional[str]):
        """给单条 QScrollBar 注册一个颜色意图，覆盖全局 self._color

        Args:
            bar: 目标 QScrollBar 实例（如 textarea.plain_text_edit.verticalScrollBar()）
            color: 颜色名（"primary" / "default" / ...）；传 None 撤销覆盖回到全局色

        生效时机：
            - 立即重新计算该 bar 的当前 stylesheet（不动画）
            - 之后 hover 进出动画也会读这个 color

        使用模式（在组件 _apply_styles 末尾）：
            from hero_side_ui import ScrollStyle
            ScrollStyle.instance().set_bar_color(
                self.plain_text_edit.verticalScrollBar(), self._color
            )
        """
        if color is not None and color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        bar.setProperty("_hs_scroll_color", color)
        # 立刻重设 stylesheet 让新色当前进度可见（不带动画）
        if self._applied:
            cur = float(getattr(bar, "_hs_scroll_progress", 0.0) or 0.0)
            self._reapply_bar_style(bar, cur)

    def _resolve_bar_color(self, bar: QScrollBar) -> str:
        """查 bar 上注册的颜色意图，没有则返回全局色"""
        c = bar.property("_hs_scroll_color")
        if c is None or c == "":
            return self._color
        if c not in VALID_COLORS:
            return self._color
        return c

    def _bar_uses_custom_color(self, bar: QScrollBar) -> bool:
        c = bar.property("_hs_scroll_color")
        return c is not None and c != "" and c in VALID_COLORS and c != self._color

    def _reapply_bar_style(self, bar: QScrollBar, progress: float):
        """根据当前进度重新画该 bar（用其专属或全局色）"""
        is_dark = self._is_dark()
        color = self._resolve_bar_color(bar)
        normal, hover = self._resolve_handle_colors(color, is_dark)
        if progress <= 0.0 and not self._bar_uses_custom_color(bar):
            # 进度 0 + 全局色 → 直接清局部 stylesheet 让全局静态层接管
            try:
                bar.setStyleSheet("")
            except RuntimeError:
                pass
            setattr(bar, "_hs_scroll_progress", 0.0)
            return
        # 自定义色 或 进度>0 → setStyleSheet 让其生效
        self._apply_progress_to_bar(bar, progress, normal, hover)
        setattr(bar, "_hs_scroll_progress", progress)

    # ============================================================
    # 颜色 ramp：亮色 300→400，暗色 700→600
    # ============================================================
    def _resolve_handle_colors(self, color: str, is_dark: bool) -> Tuple[QColor, QColor]:
        ramp = HEROUI_COLORS.get(color, HEROUI_COLORS["default"])
        if is_dark:
            return QColor(ramp[700]), QColor(ramp[600])
        return QColor(ramp[300]), QColor(ramp[400])

    def _is_dark(self) -> bool:
        try:
            return ThemeProvider.instance().current_theme == "dark"
        except Exception:
            return False

    # ============================================================
    # QSS 构造（用于全局静态层 + 每条 bar 的动画层）
    # ============================================================
    def _build_bar_qss(self, *, thickness: int, handle_color: QColor,
                       border_color: Optional[QColor] = None,
                       color: Optional[str] = None) -> str:
        """根据当前 thickness（瞬时插值值）和 handle 颜色生成单条 QScrollBar 的 QSS

        被动画层每帧调用 —— 进度变化 → thickness 与 color 各自插值 → 重生成 QSS。

        ⚠️ 关键技巧：QScrollBar 的实际 width 始终保持 hover_thickness（最大值），
        通过 handle 的左右 margin 来视觉上"瘦身"成 thickness。这样动画里只需要
        改 margin 就能"加粗"，不必触发 layout 重算（QSS width 不能动态生效）。

        Args:
            thickness: 当前视觉粗细
            handle_color: 当前 handle 填充色
            border_color: 当前 border 颜色（含 alpha），None = 不画 border
                          —— 用 alpha 渐变模拟"hover 时阴影消失"
        """
        ht = self.hover_thickness  # widget 实际 width 永远 = 最大值
        margin_lr = max(0, (ht - thickness) // 2)
        radius = max(1, thickness // 2)
        m = self._track_padding
        min_len = self._min_handle_length

        c = handle_color.name(QColor.NameFormat.HexArgb) if handle_color.alpha() < 255 else handle_color.name()

        # border 段（仅当 border_color 有效且 alpha > 0 时画）
        if border_color is not None and border_color.alpha() > 0:
            bc = f"rgba({border_color.red()},{border_color.green()},{border_color.blue()},{border_color.alpha()})"
            border_decl = f"border: 1px solid {bc};"
        else:
            border_decl = "border: none;"

        return f"""
QScrollBar:vertical {{
    background: transparent;
    width: {ht}px;
    margin: {m}px 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {c};
    {border_decl}
    border-radius: {radius}px;
    min-height: {min_len}px;
    margin-left: {margin_lr}px;
    margin-right: {margin_lr}px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {ht}px;
    margin: 0 {m}px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {c};
    {border_decl}
    border-radius: {radius}px;
    min-width: {min_len}px;
    margin-top: {margin_lr}px;
    margin-bottom: {margin_lr}px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    background: none; border: none; width: 0; height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
        """.strip()

    def build_qss(self, color: Optional[str] = None, is_dark: Optional[bool] = None) -> str:
        """对外公开的 QSS 生成方法（默认 normal 状态，无 hover 信息）

        组件想要把这套样式应用到自己的 widget 上时调用此方法。例如：
            qss = ScrollStyle.instance().build_qss(color="primary")
            my_widget.setStyleSheet(my_widget.styleSheet() + qss)

        注意：通过 build_qss 出来的 QSS 没有 hover 动画（无法靠 QSS 实现）。
        如果想让该 widget 也有 hover 过渡，让 ScrollStyle.apply_global() 全局生效即可，
        animation_filter 会自动作用到该 widget 内的 QScrollBar。
        """
        c = color if color is not None else self._color
        is_d = is_dark if is_dark is not None else self._is_dark()
        normal, _hover = self._resolve_handle_colors(c, is_d)
        # border 阴影仅在使用全局色（默认 neutral）时画；显式传语义色不带阴影
        if c == self._color:
            max_alpha = self._shadow_alpha_dark if is_d else self._shadow_alpha_light
            border = QColor(0, 0, 0, max_alpha) if max_alpha > 0 else None
        else:
            border = None
        return self._build_bar_qss(thickness=self._thickness, handle_color=normal,
                                   border_color=border)

    # ============================================================
    # 全局应用 / 取消
    # ============================================================
    def apply_global(self):
        """注入静态 QSS 到 QApplication + 安装 hover 动画 eventFilter"""
        app = QApplication.instance()
        if app is None:
            return

        # ---- 静态层：默认状态的 QSS ----
        existing = app.styleSheet() or ""
        marker_start = "/* HEROSIDEUI_SCROLLSTYLE_BEGIN */"
        marker_end = "/* HEROSIDEUI_SCROLLSTYLE_END */"
        cleaned = existing
        if marker_start in cleaned and marker_end in cleaned:
            before = cleaned.split(marker_start, 1)[0]
            after = cleaned.split(marker_end, 1)[1]
            cleaned = (before + after).rstrip()

        normal_color, _hover = self._resolve_handle_colors(self._color, self._is_dark())
        # 静态层（normal 状态）：handle 带满 alpha 的 border 阴影
        max_alpha = self._shadow_alpha_dark if self._is_dark() else self._shadow_alpha_light
        static_border = QColor(0, 0, 0, max_alpha) if max_alpha > 0 else None
        static_qss = self._build_bar_qss(
            thickness=self._thickness,
            handle_color=normal_color,
            border_color=static_border,
        )
        block = f"\n{marker_start}\n{static_qss}\n{marker_end}\n"
        app.setStyleSheet((cleaned + block).lstrip())

        # ---- 动画层：装 eventFilter（仅装一次）----
        if not self._app_filter_installed:
            app.installEventFilter(self)
            self._app_filter_installed = True

        self._applied = True

        # 主题/配置变化后，已经被 hover 过的 bar 上还残留旧 stylesheet，要清掉让其回到全局静态值
        # 但有自定义色（_hs_scroll_color）的 bar 要按其自定义色重新 reapply 当前进度
        for bar in app.findChildren(QScrollBar):
            cur = float(getattr(bar, "_hs_scroll_progress", 0.0) or 0.0)
            self._reapply_bar_style(bar, cur)

    def remove_global(self):
        app = QApplication.instance()
        if app is None:
            return
        existing = app.styleSheet() or ""
        marker_start = "/* HEROSIDEUI_SCROLLSTYLE_BEGIN */"
        marker_end = "/* HEROSIDEUI_SCROLLSTYLE_END */"
        if marker_start in existing and marker_end in existing:
            before = existing.split(marker_start, 1)[0]
            after = existing.split(marker_end, 1)[1]
            app.setStyleSheet((before + after).strip())
        if self._app_filter_installed:
            app.removeEventFilter(self)
            self._app_filter_installed = False
        self._applied = False

    # ============================================================
    # 动画层：QApplication eventFilter
    # ============================================================
    def eventFilter(self, obj, event):
        # 只关心 QScrollBar 的 Enter/Leave
        if isinstance(obj, QScrollBar):
            t = event.type()
            if t == QEvent.Type.Enter:
                self._animate_bar(obj, to_hover=True)
            elif t == QEvent.Type.Leave:
                self._animate_bar(obj, to_hover=False)
        return super().eventFilter(obj, event)

    def _animate_bar(self, bar: QScrollBar, *, to_hover: bool):
        """对单条 bar 启动 thickness + color 的过渡动画（颜色优先用 bar 自己的覆盖色）"""
        is_dark = self._is_dark()
        color = self._resolve_bar_color(bar)
        normal_color, hover_color = self._resolve_handle_colors(color, is_dark)

        progress_attr = "_hs_scroll_progress"
        runner_attr = "_hs_scroll_anim_runner"
        cur = float(getattr(bar, progress_attr, 0.0) or 0.0)
        tgt = 1.0 if to_hover else 0.0

        # 0 时长直接跳
        if self._duration <= 0 or cur == tgt:
            self._apply_progress_to_bar(bar, tgt, normal_color, hover_color)
            setattr(bar, progress_attr, tgt)
            return

        def _on_step(p: float):
            self._apply_progress_to_bar(bar, p, normal_color, hover_color)
            setattr(bar, progress_attr, p)

        tween_value(
            owner=bar,
            runner_attr=runner_attr,
            start=cur,
            end=float(tgt),
            on_step=_on_step,
            duration=self._duration,
            easing=self._easing,
        )

    def _apply_progress_to_bar(self, bar: QScrollBar, progress: float,
                               normal_color: QColor, hover_color: QColor):
        """根据进度 0..1 给该 bar 重新 setStyleSheet"""
        t = self._thickness
        ht = self.hover_thickness
        # 厚度插值
        thickness_now = t + (ht - t) * progress
        # 颜色插值（QColor 线性混合）
        c = QColor(
            int(normal_color.red() + (hover_color.red() - normal_color.red()) * progress),
            int(normal_color.green() + (hover_color.green() - normal_color.green()) * progress),
            int(normal_color.blue() + (hover_color.blue() - normal_color.blue()) * progress),
        )
        # border 阴影：仅在 bar **使用全局色**（neutral）时才有，
        # 自定义语义色（primary/success/...）色阶本身鲜明，不需要描边
        if self._bar_uses_custom_color(bar):
            border_color = None
        else:
            is_dark = self._is_dark()
            max_alpha = self._shadow_alpha_dark if is_dark else self._shadow_alpha_light
            # alpha 反向插值：progress=0 满 alpha；progress=1 alpha=0
            border_alpha = int(round(max_alpha * (1.0 - progress)))
            border_color = QColor(0, 0, 0, border_alpha) if border_alpha > 0 else None

        bar.setStyleSheet(self._build_bar_qss(
            thickness=int(round(thickness_now)),
            handle_color=c,
            border_color=border_color,
        ))

    def _reset_bar_to_normal(self, bar: QScrollBar, *, animate: bool):
        """把单条 bar 重置回 normal 状态（清除局部 stylesheet 让全局生效）"""
        # 停掉它身上的动画
        stop_tween(bar, "_hs_scroll_anim_runner")
        # 清局部 stylesheet → 让全局 QApplication QSS 接管
        try:
            bar.setStyleSheet("")
        except RuntimeError:
            pass  # bar 可能已销毁
        # 进度回到 0
        try:
            setattr(bar, "_hs_scroll_progress", 0.0)
        except Exception:
            pass

    # ============================================================
    # 内部
    # ============================================================
    def _reapply_if_active(self):
        if self._applied:
            self.apply_global()

    def _on_theme_changed(self, _theme: str):
        if self._applied:
            self.apply_global()
