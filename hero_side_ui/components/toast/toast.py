"""HeroSideUI Toast — 单条轻提示卡片（HeroUI v2 toast.ts）。

结构：icon + (title / description) + end_content，右上角关闭按钮常显；
倒计时可显示进度覆层（覆盖整卡从左推进），支持拖拽关闭。

单卡只负责绘制 / 内容 / 倒计时；堆叠定位与进出场编排见 ``_region.py``，
全局队列见 ``_provider.py``。
"""

from __future__ import annotations

from typing import Callable, Optional

import shiboken6
from PySide6.QtCore import (
    QElapsedTimer,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Property,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import (
    RADIUS,
    TOAST_SEVERITY_ICONS,
    TOAST_SHADOWS,
    TOAST_SPEC,
)
from ...utils import load_svg_icon, safe_delete
from ..button import Button
from ..spinner import Spinner
from ..text import Text
from ._styling import build_toast_styles

# Button / Spinner 不接受 foreground，回落到 default
_LEGACY_COLOR = {"foreground": "default"}


class Toast(QWidget):
    """HeroUI 风格 Toast 卡片。通常由 ``add_toast()`` 创建并交给 ToastRegion 管理。"""

    closed = Signal()           # 用户点关闭按钮
    timeout_reached = Signal()  # 倒计时结束，请求外层走退出动画
    hover_changed = Signal(bool)
    drag_started = Signal()
    drag_moved = Signal(int, int)
    drag_finished = Signal(int, int, bool)  # dx, dy, should_close
    content_changed = Signal()  # 文案/内容变化，请求外层重排堆叠

    def __init__(
        self,
        title: str = "",
        description: str = "",
        color: str = "default",
        variant: str = "flat",
        radius: str = "md",
        shadow: str = "sm",
        severity: Optional[str] = None,
        icon: Optional[str] = None,
        hide_icon: bool = False,
        hide_close_button: bool = False,
        end_content: Optional[QWidget] = None,
        timeout: Optional[int] = None,
        should_show_timeout_progress: bool = False,
        is_loading: bool = False,
        on_close: Optional[Callable[[], None]] = None,
        disable_animation: bool = False,
        placement: str = "bottom-right",
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroToast")

        self._title_text = title
        self._color = color
        self._variant = variant
        self._radius = radius
        self._shadow = shadow
        self._severity = severity
        self._icon_src = icon
        self._hide_icon = hide_icon
        self._hide_close = hide_close_button
        self._folded = False
        self._show_progress = should_show_timeout_progress
        self._loading = is_loading
        self._on_close = on_close
        self._disable_animation = disable_animation
        self._placement = placement
        self._end_content: Optional[QWidget] = None
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # timeout=None → 预设值；<=0 表示不自动关闭
        self._timeout = TOAST_SPEC["timeout"] if timeout is None else int(timeout)

        self._width_inset = 0.0   # 折叠堆叠时背景左右内缩（每侧）
        self._progress = 0.0      # 0..1 倒计时进度
        self._styles = build_toast_styles(variant, color, self._theme)

        self._clock = QElapsedTimer()
        self._elapsed_before = 0
        self._paused = False
        self._timer = QTimer(self)
        self._timer.setInterval(TOAST_SPEC["tick_interval"])
        self._timer.timeout.connect(self._on_tick)

        self._drag_origin: Optional[QPoint] = None
        self._drag_delta = QPoint()

        self._build_ui(description)
        self._apply_styles()
        self._relayout()

        if end_content is not None:
            self.set_end_content(end_content)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 构建
    # ============================================================

    def _build_ui(self, description: str):
        spec = TOAST_SPEC
        pad = self._shadow_pad()

        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(
            pad + spec["padding_x"], pad + spec["padding_y"],
            pad + spec["padding_x"], pad + spec["padding_y"],
        )
        self._root.setSpacing(TOAST_SPEC["content_gap"])

        # icon（loading 时换成 Spinner）
        self._icon_label = Text(size="md", theme=self._theme)
        self._icon_label.setFixedSize(spec["icon"], spec["icon"])
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._root.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignTop)

        self._spinner = Spinner(
            size="sm",
            color=_LEGACY_COLOR.get(self._color, self._color),
            theme=self._theme,
            parent=self,
        )
        self._spinner.setFixedSize(spec["icon"], spec["icon"])
        self._spinner.setVisible(self._loading)

        # title / description（文字不可选：HeroUI toast 无文字选择，且
        # Text 吃掉 press 会让整卡拖拽收不到事件）
        self._text_col = QVBoxLayout()
        self._text_col.setSpacing(0)
        self._title_label = Text(
            "", size=TOAST_SPEC["title_size"], weight="medium", theme=self._theme,
            selectable=False,
        )
        self._title_label.setWordWrap(False)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._desc_label = Text(
            description, size=TOAST_SPEC["desc_size"], weight="normal",
            theme=self._theme, selectable=False,
        )
        self._desc_label.setWordWrap(True)
        self._text_col.addWidget(self._title_label)
        self._text_col.addWidget(self._desc_label)
        self._root.addLayout(self._text_col, 1)
        # 先挂父再定显隐：无父 widget 调 setVisible(True) 会被 Windows 当成
        # 顶层窗口，闪出一帧带标题栏的原生窗口（widget_utils 记载的坑）
        self._desc_label.setVisible(bool(description))

        # 关闭按钮：绝对定位在内容右上角，常显（对齐 HeroUI closeIcon）
        self._close_btn = Button(
            icon_only=True,
            icon="heroicons--x-mark-16-solid",
            icon_size=TOAST_SPEC["close_icon"],
            variant="light",
            radius="full",
            size="sm",
            color=_LEGACY_COLOR.get(self._color, self._color),
            theme=self._theme,
            parent=self,
        )
        # icon_only 边长必须走 set_icon_only_side：裸 setFixedSize 会被
        # Button._apply_styles（主题切换/setter 触发）冲回自动计算的边长
        self._close_btn.set_icon_only_side(TOAST_SPEC["close"])
        self._close_btn.clicked.connect(self._on_close_clicked)
        self._close_btn.setVisible(not self._hide_close)

        # 整卡透明度（进出场 / 折叠 / 拖拽）：快照 + painter 透明度实现。
        # 卡片禁止挂 QGraphicsEffect——Button 等子件自带 effect，父子嵌套
        # 会触发 "one painter at a time" 告警洪水。
        self._paint_opacity = 1.0
        self._fade_pixmap: Optional[QPixmap] = None
        self._snapshot_visible: list = []
        self._inset_anim: Optional[QPropertyAnimation] = None
        self._content_children: list = [
            self._icon_label, self._spinner, self._title_label,
            self._desc_label, self._close_btn,
        ]

    # ============================================================
    # 几何
    # ============================================================

    def _shadow_pad(self) -> int:
        """卡片四周为阴影（及关闭按钮外溢）预留的空间。"""
        cfg = TOAST_SHADOWS.get(self._shadow, TOAST_SHADOWS["sm"])
        overhang = TOAST_SPEC["close"] // 2 + 2
        return max(cfg["blur"] + abs(cfg["offset_y"]) + 2, overhang)

    @property
    def pad_top(self) -> int:
        return self._shadow_pad()

    @property
    def pad_bottom(self) -> int:
        return self._shadow_pad()

    @property
    def pad_left(self) -> int:
        return self._shadow_pad()

    def content_height(self) -> int:
        """卡片可见主体高度（不含阴影留白），供外层堆叠计算。"""
        return max(0, self.height() - 2 * self._shadow_pad())

    def _content_rect(self) -> QRectF:
        pad = self._shadow_pad()
        return QRectF(
            pad + self._width_inset,
            pad,
            max(0.0, self.width() - 2 * pad - 2 * self._width_inset),
            max(0.0, self.height() - 2 * pad),
        )

    def _resolve_radius(self) -> float:
        if self._radius == "full":
            return self.content_height() / 2.0
        return float(RADIUS.get(self._radius, RADIUS["md"]).rstrip("px"))

    def sizeHint(self):
        return QSize(
            TOAST_SPEC["width"] + 2 * self._shadow_pad(),
            self.height() if self.height() > 0 else 64,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        """按内容重算高度、标题截断、关闭按钮与 Spinner 位置。

        高度手动累加而不用 layout sizeHint：wordWrap QLabel 的 sizeHint 有
        "尽量方形"倾向，长描述会被虚增一截；描述行高必须按实际可用宽走
        heightForWidth。layout margins 已含阴影外扩（pad + padding）。
        """
        if self._fade_pixmap is not None:
            return
        pad = self._shadow_pad()

        # 显隐用 isHidden() 判定（只看自身 hide 标志）；isVisible() 在父未
        # show 的构造期恒 False，会把 title/desc 高度算成 0
        title_h = (
            self._title_label.sizeHint().height()
            if not self._title_label.isHidden() else 0
        )
        if not self._desc_label.isHidden():
            desc_h = max(
                self._desc_label.heightForWidth(self._text_avail_width()),
                self._desc_label.fontMetrics().height(),
            )
        else:
            desc_h = 0
        end_h = (
            self._end_content.sizeHint().height()
            if self._end_content is not None else 0
        )
        content_h = max(TOAST_SPEC["icon"], title_h + desc_h, end_h)
        self.setFixedHeight(content_h + 2 * (TOAST_SPEC["padding_y"] + pad))

        self._apply_title_elide()

        rect = self._content_rect()
        btn = self._close_btn
        # 用户指定位置：X 相对内容区右上角左移 8px、下移 8px
        # （按钮中心距右缘/顶缘 12px，24px 按钮的右缘与顶缘恰与内容区平齐）
        btn.move(
            int(rect.right() - btn.width() // 2 - 12),
            int(rect.top() - btn.height() // 2 + 12),
        )
        btn.raise_()
        self._spinner.move(self._icon_label.x(), self._icon_label.y())

    def _text_avail_width(self) -> int:
        """文本列真实宽度（标题截断与描述换行估算共用）。

        构造期尚未被 region 定宽（width 还是 Qt 默认 100）：按临时宽度算
        elide 会得到空串，故回落到 sizeHint 宽；region resize 后
        resizeEvent 会按真实宽度重算。
        """
        w = max(self.width(), self.sizeHint().width())
        pad = self._shadow_pad()
        rect_w = max(0.0, w - 2 * pad - 2 * self._width_inset)
        icon_w = (
            0 if self._hide_icon
            else TOAST_SPEC["icon"] + TOAST_SPEC["content_gap"]
        )
        # 左右各有一份 padding_x：此前漏减右侧一份，elide 判定的可用宽
        # 比文本列实际宽 12px，长标题不触发截断、钻进关闭按钮区
        avail = int(rect_w) - icon_w - 2 * TOAST_SPEC["padding_x"]
        # end_content 占据文本列右侧（含一处列间距），一并扣除
        end = self._end_content
        if end is not None:
            avail -= end.sizeHint().width() + TOAST_SPEC["content_gap"]
        return max(0, avail)

    def _apply_title_elide(self):
        """标题单行截断（HeroUI: title truncate）。"""
        fm = self._title_label.fontMetrics()
        avail = max(1, self._text_avail_width())
        text = self._title_text
        if not text:
            self._title_label.setText("")
        elif fm.horizontalAdvance(text) <= avail:
            self._title_label.setText(text)
        else:
            # 部分平台字体下 fm.elidedText 会返回空串或别的省略形式，需自算兜底
            elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, avail)
            if not elided.endswith("…"):
                elided = self._elide_right(fm, text, avail)
            self._title_label.setText(elided)
        self._apply_child_visible(self._title_label, bool(text))

    def _elide_right(self, fm, text: str, avail: int) -> str:
        """二分出可容纳的最长前缀，追加省略号。"""
        dots = "…"
        dot_w = fm.horizontalAdvance(dots)
        if dot_w >= avail:
            return dots
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fm.horizontalAdvance(text[:mid]) + dot_w <= avail:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + dots

    # ============================================================
    # 绘制
    # ============================================================

    def paintEvent(self, event):
        # 淡入淡出期间：子件已隐藏，改画半透明快照
        if self._fade_pixmap is not None:
            if self._paint_opacity <= 0.001:
                return
            painter = QPainter(self)
            painter.setOpacity(self._paint_opacity)
            painter.drawPixmap(0, 0, self._fade_pixmap)
            return

        cfg = TOAST_SHADOWS.get(self._shadow, TOAST_SHADOWS["sm"])
        rect = self._content_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = self._resolve_radius()

        # 1) 阴影：多层半透明，越外越淡
        if cfg["layers"] > 0:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(cfg["layers"]):
                t = (i + 1) / cfg["layers"]
                grow = cfg["blur"] * (1 - t) + 1
                off = cfg["offset_y"] * (1 - t)
                painter.setBrush(QColor(0, 0, 0, int(cfg["alpha"] * t)))
                painter.drawRoundedRect(
                    rect.adjusted(-grow, -grow + off, grow, grow + off), radius, radius
                )
            painter.restore()

        # 2) 主体背景 + 边框
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._styles["base_bg"]))
        painter.drawRoundedRect(rect, radius, radius)

        bw = self._styles["border_width"]
        if bw > 0 and self._styles["border_color"]:
            painter.setPen(QColor(self._styles["border_color"]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                rect.adjusted(bw / 2, bw / 2, -bw / 2, -bw / 2),
                max(0.0, radius - bw / 2),
                max(0.0, radius - bw / 2),
            )

        # 3) 倒计时进度覆层（HeroUI: inset-0 半透明色块从左推进）
        if self._show_progress and self._progress > 0.0:
            painter.save()
            clip = QPainterPath()
            clip.addRoundedRect(rect, radius, radius)
            painter.setClipPath(clip)
            color = QColor(self._styles["progress_color"])
            color.setAlphaF(TOAST_SPEC["progress_alpha"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(
                QRectF(
                    rect.left(),
                    rect.top(),
                    rect.width() * min(1.0, self._progress),
                    rect.height(),
                )
            )
            painter.restore()

    # ============================================================
    # 样式
    # ============================================================

    def _apply_styles(self):
        self._styles = build_toast_styles(self._variant, self._color, self._theme)
        s = self._styles
        self._title_label.set_color(s["title_color"])
        self._desc_label.set_color(s["desc_color"])
        self._close_btn.set_icon_color(s["close_color"])
        self._refresh_icon()
        self.update()

    def _resolve_icon_name(self) -> Optional[str]:
        if self._icon_src:
            return self._icon_src
        key = self._severity or self._color
        return TOAST_SEVERITY_ICONS.get(key, TOAST_SEVERITY_ICONS["default"])

    def _refresh_icon(self):
        if self._hide_icon or self._loading:
            self._icon_label.hide()
            return
        self._icon_label.show()
        name = self._resolve_icon_name()
        if not name:
            return
        size = TOAST_SPEC["icon"]
        pix = load_svg_icon(name, size=size, color=self._styles["icon_color"])
        self._icon_label.setPixmap(
            pix.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ============================================================
    # 倒计时
    # ============================================================

    def start_countdown(self):
        """开始自动关闭倒计时（timeout<=0 或 loading 时不启动）。"""
        if self._timeout <= 0 or self._loading:
            return
        self._elapsed_before = 0
        self._paused = False
        self._clock.start()
        self._timer.start()

    def set_paused(self, paused: bool):
        """暂停 / 恢复倒计时（hover 或区域展开时由外层调用）。"""
        if self._timeout <= 0 or self._loading:
            return
        if paused == self._paused:
            return
        if paused:
            self._elapsed_before += self._clock.elapsed()
            self._timer.stop()
        else:
            self._clock.restart()
            self._timer.start()
        self._paused = paused

    def stop_countdown(self):
        self._timer.stop()
        self._paused = False

    def _on_tick(self):
        elapsed = self._elapsed_before + (0 if self._paused else self._clock.elapsed())
        if self._timeout <= 0:
            return
        self._progress = min(1.0, elapsed / self._timeout)
        if self._show_progress:
            self.update()
        if elapsed >= self._timeout:
            self._timer.stop()
            self.timeout_reached.emit()

    # ============================================================
    # 交互
    # ============================================================

    def enterEvent(self, event):
        self.hover_changed.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._drag_origin is not None:
            super().leaveEvent(event)
            return
        self.hover_changed.emit(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._drag_delta = QPoint()
            self.drag_started.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is None:
            super().mouseMoveEvent(event)
            return
        self._drag_delta = event.globalPosition().toPoint() - self._drag_origin
        self.drag_moved.emit(self._drag_delta.x(), self._drag_delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_origin is None:
            super().mouseReleaseEvent(event)
            return
        dx, dy = self._drag_delta.x(), self._drag_delta.y()
        self._drag_origin = None
        self._drag_delta = QPoint()
        self.drag_finished.emit(dx, dy, self._should_close_by_drag(dx, dy))
        super().mouseReleaseEvent(event)

    def _should_close_by_drag(self, dx: int, dy: int) -> bool:
        """按 placement 判定拖拽是否越过阈值（HeroUI SWIPE_THRESHOLD）。"""
        if self._placement == "top-center":
            return dy <= -TOAST_SPEC["swipe_threshold_y"]
        if self._placement == "bottom-center":
            return dy >= TOAST_SPEC["swipe_threshold_y"]
        if "right" in self._placement:
            return dx >= TOAST_SPEC["swipe_threshold_x"]
        return dx <= -TOAST_SPEC["swipe_threshold_x"]

    def _on_close_clicked(self):
        self.stop_countdown()
        if self._on_close:
            self._on_close()
        self.closed.emit()

    # ============================================================
    # 对外控制
    # ============================================================

    def _alive(self) -> bool:
        """卡片被关闭销毁后，外部回调（如异步完成）仍可能调用 setter。"""
        return shiboken6.isValid(self)

    def set_opacity(self, value: float):
        self._set_paint_opacity(value)

    # ============================================================
    # 整卡淡入淡出（快照模式，替代 QGraphicsOpacityEffect）
    # ============================================================

    def _get_paint_opacity(self) -> float:
        return self._paint_opacity

    def _set_paint_opacity(self, value: float):
        value = max(0.0, min(1.0, float(value)))
        if abs(value - self._paint_opacity) < 0.001:
            return
        self._paint_opacity = value
        if value >= 0.999:
            self._end_fade_snapshot()
        else:
            self._take_fade_snapshot()
        self.update()

    paint_opacity = Property(float, _get_paint_opacity, _set_paint_opacity)

    def _take_fade_snapshot(self):
        """把当前完整外观（含子件）渲染成快照，然后隐藏子件。"""
        if self._fade_pixmap is not None:
            return
        if self.width() <= 0 or self.height() <= 0:
            return
        pm = QPixmap(self.size())
        pm.fill(Qt.GlobalColor.transparent)
        # 禁用默认的 DrawWindowBackground：它会把窗口底色（palette window，
        # 亮色=白/暗色=黑）整矩形不透明地画进快照，四周阴影留白区变成一圈
        # 实色底，半透明绘制时就是用户看到的「主题色矩形块（像边距一样）」
        self.render(pm, QPoint(), QRect(), QWidget.RenderFlag.DrawChildren)
        self._fade_pixmap = pm
        # 只隐藏快照前可见的子件；故意隐藏的（Spinner/icon）恢复时不能被强拉出来
        self._snapshot_visible = [
            w for w in self._content_children if not w.isHidden()
        ]
        for w in self._snapshot_visible:
            w.hide()
        self.update()

    def _apply_child_visible(self, w, visible: bool):
        """快照淡入淡出期间子件显隐由快照接管：只记录意图，不动 widget。

        否则中途 setVisible(True) 的子件（如 set_folded 恢复关闭按钮）会
        以全不透明叠在半透明快照上，入场卡上出现实心 X。"""
        if self._fade_pixmap is not None:
            if visible and w not in self._snapshot_visible:
                self._snapshot_visible.append(w)
            elif not visible and w in self._snapshot_visible:
                self._snapshot_visible.remove(w)
            return
        w.setVisible(visible)

    def _end_fade_snapshot(self):
        """结束快照：恢复快照前可见的子件。"""
        if self._fade_pixmap is None:
            return
        self._fade_pixmap = None
        for w in self._snapshot_visible:
            w.show()
        self._snapshot_visible = []
        self._relayout()
        self.update()

    def set_width_inset(self, inset: float):
        """折叠堆叠时让背景左右内缩（近似 HeroUI scaleX），不触发文字重排。"""
        if abs(inset - self._width_inset) < 0.01:
            return
        self._width_inset = inset
        self.update()

    def _get_width_inset(self) -> float:
        return self._width_inset

    def _set_width_inset_prop(self, value: float):
        self.set_width_inset(value)

    width_inset = Property(float, _get_width_inset, _set_width_inset_prop)

    def animate_width_inset(self, target: float):
        """内缩量随位移同步渐变（折叠/展开切换时 scaleX 连续，不瞬跳）。"""
        if abs(target - self._width_inset) < 0.01:
            return
        if self._inset_anim is not None:
            self._inset_anim.stop()
        anim = QPropertyAnimation(self, b"width_inset", self)
        anim.setDuration(TOAST_SPEC["duration_move"])
        anim.setStartValue(self._width_inset)
        anim.setEndValue(float(target))
        self._inset_anim = anim
        anim.start()

    def sync_height(self):
        """宽度变化后立即按新宽度重算高度（入列前调用，避免显示时高度跳变）。"""
        self._relayout()

    def set_placement(self, placement: str):
        self._placement = placement

    def set_loading(self, loading: bool):
        """loading 时图标换 Spinner 并停掉倒计时（对齐 HeroUI promise 行为）。"""
        if not self._alive():
            return
        self._loading = loading
        self._apply_child_visible(self._spinner, loading)
        if loading:
            self.stop_countdown()
        else:
            self.start_countdown()
        self._refresh_icon()
        self._relayout()
        self.content_changed.emit()

    def set_title(self, title: str):
        if not self._alive():
            return
        self._title_text = title
        self._apply_title_elide()
        self._relayout()
        self.content_changed.emit()

    def set_description(self, description: str):
        if not self._alive():
            return
        self._desc_label.setText(description)
        self._apply_child_visible(self._desc_label, bool(description))
        self._relayout()
        self.content_changed.emit()

    def set_end_content(self, widget: Optional[QWidget]):
        if not self._alive():
            return
        if self._end_content is not None:
            self._root.removeWidget(self._end_content)
            if self._end_content in self._content_children:
                self._content_children.remove(self._end_content)
            safe_delete(self._end_content)
        self._end_content = widget
        if widget is not None:
            widget.setParent(self)
            self._root.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
            widget.show()
            self._content_children.append(widget)
        self._relayout()
        self.content_changed.emit()

    def set_color(self, color: str):
        if not self._alive():
            return
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        if not self._alive():
            return
        self._variant = variant
        self._apply_styles()

    def set_radius(self, radius: str):
        if not self._alive():
            return
        self._radius = radius
        self.update()

    def set_shadow(self, shadow: str):
        if not self._alive():
            return
        self._shadow = shadow
        self._relayout()
        self.update()

    def set_hide_icon(self, hide: bool):
        if not self._alive():
            return
        self._hide_icon = hide
        self._refresh_icon()
        self._relayout()

    def set_hide_close_button(self, hide: bool):
        if not self._alive():
            return
        self._hide_close = hide
        self._refresh_close_visibility()

    def set_folded(self, folded: bool):
        """折叠堆叠时隐藏非最新卡的关闭按钮：露出边条不该带出 X，
        且旧卡的 X 会被最新卡的整体命中区挡住、点了没反应。"""
        if not self._alive():
            return
        self._folded = folded
        self._refresh_close_visibility()

    def _refresh_close_visibility(self):
        self._apply_child_visible(
            self._close_btn, not self._hide_close and not self._folded
        )

    def set_show_timeout_progress(self, show: bool):
        if not self._alive():
            return
        self._show_progress = show
        self.update()

    def set_theme(self, theme: str):
        if not self._alive():
            return
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = ThemeProvider.instance().current_theme
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_provider_theme(self._theme)

    def _apply_provider_theme(self, theme: str):
        self._theme = theme
        self._title_label.set_theme(theme)
        self._desc_label.set_theme(theme)
        self._close_btn.set_theme(theme)
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme
