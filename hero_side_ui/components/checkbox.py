"""
HeroSideUI Checkbox Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/checkbox.ts

结构:
    Checkbox (继承 QCheckBox)
        ├── 自绘 box (before: 边框 / after: 填充背景)
        ├── QSvgRenderer 绘制 check icon
        └── 原生 QCheckBox 文字 label (paintEvent 自己画以支持 line-through)

特性对齐 HeroUI:
    - 6 种颜色 (default / primary / secondary / success / warning / danger)
    - 3 种尺寸 (sm / md / lg)
    - 5 种圆角 (none / sm / md / lg / full)
    - lineThrough：选中时 label 文字加下划线（从 0 扩展到 100%），label 透明度 0.6
    - isDisabled / isInvalid / isIndeterminate
    - disableAnimation
    - 主题: light / dark
    - 按压缩放 (scale-95) + after 填充从 scale 0.5 → 1、opacity 0 → 1 过渡

CheckboxGroup:
    - label / description / errorMessage
    - orientation (horizontal / vertical)
    - 统一 color / size / radius / theme 应用到子 Checkbox
    - is_required / is_invalid
    - value / default_value (选中的 checkbox value 列表)
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    QRectF,
    QByteArray,
    QSize,
    QTimer,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QPen,
    QFontMetrics,
)
from PySide6.QtSvg import QSvgRenderer
from typing import Optional, List

from ..themes import HEROUI_COLORS, RADIUS, FONT_FAMILY, CHECKBOX_SIZES
from ..utils import hex_to_rgba
from ..core import ThemeProvider

# ============================================================
# 内部资源：check / minus (indeterminate) svg
# ============================================================
_CHECK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="none" stroke="currentColor" stroke-linecap="round" '
    'stroke-linejoin="round" stroke-width="3" d="M4.5 12.75l6 6 9-13.5"/>'
    "</svg>"
)

_MINUS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="none" stroke="currentColor" stroke-linecap="round" '
    'stroke-linejoin="round" stroke-width="3" d="M5 12h14"/>'
    "</svg>"
)


def _render_icon_svg(svg_tpl: str, color: QColor) -> QSvgRenderer:
    data = svg_tpl.replace("currentColor", color.name())
    return QSvgRenderer(QByteArray(data.encode("utf-8")))


# ============================================================
# Checkbox
# ============================================================
class Checkbox(QCheckBox):
    """HeroUI 风格的 Checkbox 组件

    继承 QCheckBox，保留原生 API (stateChanged / toggled / setChecked / isChecked)。
    外观由 paintEvent 全自绘（忽略系统风格），以完美对齐 HeroUI。

    参数:
        text: label 文字（可为空）
        is_selected: 初始选中状态 (映射到 QCheckBox.checked)
        color: default / primary / secondary / success / warning / danger
        size: sm / md / lg
        radius: none / sm / md / lg / full（None = 跟随 size 默认）
        line_through: 选中时给 label 加下划线
        is_disabled: 禁用
        is_invalid: 无效态 (边框变红)
        is_indeterminate: 未定态 (填充 minus 图标)
        disable_animation: 禁用动画
        theme: light / dark
        value: 在 CheckboxGroup 中标识该 checkbox 的值
    """

    def __init__(
        self,
        text: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        radius: Optional[str] = None,
        line_through: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_indeterminate: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        value: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)

        self._color = color
        self._size = size
        self._radius = radius
        self._line_through = line_through
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_indeterminate = is_indeterminate
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._value = value if value is not None else text

        # 动画驱动值
        self._fill_progress = 0.0  # after 填充: 0 = 未选中, 1 = 选中（scale+opacity）
        self._line_progress = 0.0  # lineThrough 下划线宽度: 0 → 1
        self._press_progress = 0.0  # 按压缩放: 0 = 1.0, 1 = 0.95
        self._check_draw = 0.0  # check 图标描边进度: 0 → 1（勾选时从 0 按路径描到 1）
        self._hover = False

        # 初始状态
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setEnabled(not is_disabled)
        if is_selected and not disable_animation:
            self._fill_progress = 1.0
            self._check_draw = 1.0
            if line_through:
                self._line_progress = 1.0

        # 动画
        self._fill_anim = QPropertyAnimation(self, b"fill_progress")
        self._fill_anim.setDuration(200)
        self._fill_anim.setEasingCurve(QEasingCurve.Type.Linear)

        self._line_anim = QPropertyAnimation(self, b"line_progress")
        self._line_anim.setDuration(200)
        self._line_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"press_progress")
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # check 描边动画（选中时用；取消时不用，图标直接跟 fill_progress 淡出）
        self._check_anim = QPropertyAnimation(self, b"check_draw")
        self._check_anim.setDuration(500)
        self._check_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 原生 stateChanged 驱动我们的动画
        self.stateChanged.connect(self._on_state_changed)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        # 让自绘接管外观
        self.setStyleSheet("QCheckBox { background: transparent; border: none; }")

        # 初次尺寸
        self._refresh_geometry()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Qt 属性（供 QPropertyAnimation 驱动）
    # ============================================================
    def _get_fill(self) -> float:
        return self._fill_progress

    def _set_fill(self, v: float):
        self._fill_progress = v
        self.update()

    fill_progress = Property(float, _get_fill, _set_fill)

    def _get_line(self) -> float:
        return self._line_progress

    def _set_line(self, v: float):
        self._line_progress = v
        self.update()

    line_progress = Property(float, _get_line, _set_line)

    def _get_press(self) -> float:
        return self._press_progress

    def _set_press(self, v: float):
        self._press_progress = v
        self.update()

    press_progress = Property(float, _get_press, _set_press)

    def _get_check_draw(self) -> float:
        return self._check_draw

    def _set_check_draw(self, v: float):
        self._check_draw = v
        self.update()

    check_draw = Property(float, _get_check_draw, _set_check_draw)

    # ============================================================
    # 状态变化 / 动画
    # ============================================================
    def _on_state_changed(self, state):
        """Qt stateChanged → 驱动动画

        PySide6 的 stateChanged 在不同版本可能发射 int(0/1/2) 或 Qt.CheckState 枚举，
        统一用 isChecked() 读取当前状态最稳。
        """
        checked = self.isChecked()

        if self._disable_animation:
            self._fill_progress = 1.0 if checked else 0.0
            self._check_draw = 1.0 if checked else 0.0
            self._line_progress = 1.0 if (checked and self._line_through) else 0.0
            self.update()
            return

        self._fill_anim.stop()
        self._fill_anim.setStartValue(self._fill_progress)
        self._fill_anim.setEndValue(1.0 if checked else 0.0)
        self._fill_anim.start()

        # check 描边：勾选 → 0 → 1（画对勾的过程）；取消 → 直接跳 0（让图标跟 fill 淡出）
        self._check_anim.stop()
        if checked:
            # 立即清零；延迟 100ms 再开始描，让背景先铺开
            self._check_draw = 0.0
            self.update()
            QTimer.singleShot(100, self._start_check_draw)
        else:
            # 取消：立刻置 1（整条对勾可见），然后跟随 fill opacity 淡出
            self._check_draw = 1.0

        if self._line_through:
            self._line_anim.stop()
            self._line_anim.setStartValue(self._line_progress)
            self._line_anim.setEndValue(1.0 if checked else 0.0)
            self._line_anim.start()

    def _start_check_draw(self):
        """延迟 100ms 后启动 check 描边动画；如果此刻已不再是选中，则不启动"""
        if not self.isChecked() or self._is_indeterminate:
            return
        self._check_anim.stop()
        self._check_anim.setStartValue(self._check_draw)
        self._check_anim.setEndValue(1.0)
        self._check_anim.start()

    # ============================================================
    # 按压缩放
    # ============================================================
    def mousePressEvent(self, event):
        if self.isEnabled() and not self._disable_animation:
            self._press_anim.stop()
            self._press_anim.setStartValue(self._press_progress)
            self._press_anim.setEndValue(1.0)
            self._press_anim.setDuration(80)
            self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and not self._disable_animation:
            self._press_anim.stop()
            self._press_anim.setStartValue(self._press_progress)
            self._press_anim.setEndValue(0.0)
            self._press_anim.setDuration(150)
            self._press_anim.start()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ============================================================
    # 几何计算 (基于 size)
    # ============================================================
    def _size_config(self) -> dict:
        return CHECKBOX_SIZES.get(self._size, CHECKBOX_SIZES["md"])

    def _refresh_geometry(self):
        cfg = self._size_config()
        font = QFont(FONT_FAMILY.split(",")[0].strip().strip("'\""))
        font.setPixelSize(cfg["label_font_size"])
        self.setFont(font)

        # 让 QCheckBox 的 sizeHint 足够容纳 box + gap + text
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.text())
        text_h = fm.height()
        total_w = cfg["box"] + cfg["gap"] + text_w
        total_h = max(cfg["box"], text_h)
        # 外围 padding 2px（HeroUI 的 p-2 tap 热区）
        pad = 2
        self.setMinimumSize(total_w + pad * 2, total_h + pad * 2)
        self.updateGeometry()

    def setText(self, text: str):
        super().setText(text)
        self._refresh_geometry()

    def sizeHint(self) -> QSize:
        cfg = self._size_config()
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self.text())
        text_h = fm.height()
        total_w = cfg["box"] + cfg["gap"] + text_w + 4
        total_h = max(cfg["box"], text_h) + 4
        return QSize(total_w, total_h)

    # ============================================================
    # 色彩决策
    # ============================================================
    def _palette(self):
        """返回 (border_color, fill_color, icon_color, label_color,
        hover_bg_color, disabled_opacity)"""
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])

        # 无效态：边框 danger
        invalid_border = None
        if self._is_invalid:
            invalid_border = QColor(HEROUI_COLORS["danger"][500])

        # 未选中边框: default (通常 default-300 / 暗色 default-100-20%)
        border = QColor(dc[400] if is_dark else dc[300])

        # hover 前景（wrapper hover 伪加一层 default-100 底色）
        hover_bg = QColor(dc[700] if is_dark else dc[100])
        hover_bg.setAlpha(200 if is_dark else 255)  # 暗色稍透明

        # 选中填充色 = 主色 500；default 特殊处理
        if self._color == "default":
            fill = QColor(dc[300] if is_dark else dc[500])
            icon = QColor(dc[900] if is_dark else "#ffffff")
        else:
            fill = QColor(colors[500])
            # warning 的 foreground 偏黑
            if self._color == "warning":
                icon = QColor("#000000")
            else:
                icon = QColor("#ffffff")

        # label: 默认前景色
        if is_dark:
            label = QColor("#ecedee")
        else:
            label = QColor("#11181c")

        if self._is_invalid:
            label = QColor(HEROUI_COLORS["danger"][500])

        if invalid_border is not None:
            border = invalid_border

        return border, fill, icon, label, hover_bg

    # ============================================================
    # 圆角计算
    # ============================================================
    def _resolve_box_radius(self, box_size: int) -> float:
        if self._radius is None:
            # 默认 md = 8px
            return float(RADIUS["md"].replace("px", ""))
        if self._radius == "full":
            return box_size / 2.0
        if self._radius == "none":
            return 0.0
        key_map = {"sm": 4, "md": 8, "lg": 14}
        return float(key_map.get(self._radius, 8))

    # ============================================================
    # paintEvent — 完整自绘
    # ============================================================
    def paintEvent(self, event):
        cfg = self._size_config()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        border_color, fill_color, icon_color, label_color, hover_bg = self._palette()

        box_size = cfg["box"]
        bw = cfg["border_width"]
        gap = cfg["gap"]
        r = self._resolve_box_radius(box_size)

        # 整体容器垂直居中
        total_h = self.height()
        box_y = (total_h - box_size) // 2
        box_x = 2  # 左侧留 2px 呼吸

        # ---- 按压缩放（整个 box 居中缩放）----
        press_scale = 1.0 - 0.05 * self._press_progress  # 按压时 0.95
        if press_scale < 1.0:
            painter.save()
            cx = box_x + box_size / 2.0
            cy = box_y + box_size / 2.0
            painter.translate(cx, cy)
            painter.scale(press_scale, press_scale)
            painter.translate(-cx, -cy)

        # ---- 1) hover 底色（before:bg-default-100）----
        if self._hover and not self._is_disabled:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hover_bg)
            # 比 box 稍小，不遮挡边框
            painter.drawRoundedRect(QRectF(box_x, box_y, box_size, box_size), r, r)
            painter.restore()

        # ---- 2) before: 边框（未选中时可见；选中时被 fill 覆盖）----
        # HeroUI: before 始终在 (可以视作描边)；after 选中时覆盖在上面
        painter.save()
        pen = QPen(border_color, bw)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        half = bw / 2.0
        painter.drawRoundedRect(
            QRectF(
                box_x + half,
                box_y + half,
                box_size - bw,
                box_size - bw,
            ),
            max(0.0, r - half),
            max(0.0, r - half),
        )
        painter.restore()

        # ---- 3) after: 选中填充（scale 0.5 → 1 + opacity 0 → 1）----
        checked = self.isChecked() or self._is_indeterminate
        p = (
            1.0
            if (self._is_indeterminate and not self.isChecked())
            else self._fill_progress
        )
        if self._is_indeterminate:
            # indeterminate: 不管 checked，总是画满
            p = 1.0

        if p > 0.001:
            painter.save()
            # scale 从 0.5 → 1 对应 p 从 0 → 1
            s = 0.5 + 0.5 * p
            opacity = p
            painter.setOpacity(opacity)
            cx = box_x + box_size / 2.0
            cy = box_y + box_size / 2.0
            painter.translate(cx, cy)
            painter.scale(s, s)
            painter.translate(-cx, -cy)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(QRectF(box_x, box_y, box_size, box_size), r, r)
            painter.restore()

            # ---- 4) 图标 ----
            ic_w = cfg["icon_w"]
            ic_h = cfg["icon_h"]
            ic_x = box_x + (box_size - ic_w) / 2.0
            ic_y = box_y + (box_size - ic_h) / 2.0

            if self._is_indeterminate:
                # minus: 直接 SVG 渲染 + 跟随 fill 淡入
                painter.save()
                painter.setOpacity(opacity)
                svg = _render_icon_svg(_MINUS_SVG, icon_color)
                svg.render(painter, QRectF(ic_x, ic_y, ic_w, ic_h))
                painter.restore()
            else:
                # check: 手绘两段线，按 _check_draw 进度描出
                self._draw_animated_check(
                    painter,
                    ic_x,
                    ic_y,
                    ic_w,
                    ic_h,
                    icon_color,
                    opacity,
                    cfg,
                )

        if press_scale < 1.0:
            painter.restore()

        # ---- 5) label 文字 ----
        text = self.text()
        if text:
            painter.save()
            fm = QFontMetrics(self.font())
            # label 跟随选中态 opacity 0.6
            label_opacity = 1.0
            if self._line_through and self.isChecked():
                # 选中时 opacity 0.6（随进度）
                label_opacity = 1.0 - 0.4 * self._line_progress
            if self._is_disabled:
                label_opacity *= 0.5
            painter.setOpacity(label_opacity)
            painter.setPen(QPen(label_color))
            painter.setFont(self.font())

            text_x = box_x + box_size + gap
            text_w = self.width() - text_x - 2
            text_rect = QRectF(text_x, 0, text_w, self.height())
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                text,
            )

            # 下划线（line-through）— 以文字中点为中心双向展开
            if self._line_through and self._line_progress > 0.001:
                pw = max(1, cfg["border_width"] // 2)
                full_width = fm.horizontalAdvance(text)
                line_width = full_width * self._line_progress
                # 线在文字垂直中线
                line_y = self.height() / 2.0
                # 中心点 = 文字矩形中心
                center_x = text_x + full_width / 2.0
                x1 = center_x - line_width / 2.0
                x2 = center_x + line_width / 2.0
                painter.setPen(QPen(label_color, pw))
                painter.drawLine(
                    int(x1),
                    int(line_y),
                    int(x2),
                    int(line_y),
                )
            painter.restore()

        # ---- 6) 禁用蒙层 ----
        if self._is_disabled:
            painter.save()
            painter.setOpacity(0.5)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
            painter.restore()

        painter.end()

    # ============================================================
    # 动画 check 图标（手绘对勾）
    # ============================================================
    def _draw_animated_check(
        self,
        painter: QPainter,
        x: float,
        y: float,
        w: float,
        h: float,
        color: QColor,
        opacity: float,
        cfg: dict,
    ):
        """按 self._check_draw 进度从起点开始"描"出对勾

        对勾路径 (24×24 viewBox):
            A(4.5, 12.75) --AB--> B(10.5, 18.75) --BC--> C(19.5, 5.25)
        先画短下斜段 AB，再画长上斜段 BC。
        """
        import math

        progress = max(0.0, min(1.0, self._check_draw))
        if progress <= 0.001:
            return

        sx = w / 24.0
        sy = h / 24.0
        ax, ay = x + 4.5 * sx, y + 12.75 * sy
        bx, by = x + 10.5 * sx, y + 18.75 * sy
        cx, cy = x + 19.5 * sx, y + 5.25 * sy

        len_ab = math.hypot(bx - ax, by - ay)
        len_bc = math.hypot(cx - bx, cy - by)
        total = len_ab + len_bc
        if total <= 0.0:
            return

        target = total * progress

        painter.save()
        painter.setOpacity(opacity)

        # 笔宽：参考 SVG stroke-width=3（viewBox 24）等比缩放，最小 1.5
        pen_w = max(1.5, 3.0 * min(sx, sy))
        pen = QPen(color, pen_w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        from PySide6.QtCore import QPointF

        if target <= len_ab:
            t = target / len_ab if len_ab > 0 else 0
            end_x = ax + (bx - ax) * t
            end_y = ay + (by - ay) * t
            painter.drawLine(QPointF(ax, ay), QPointF(end_x, end_y))
        else:
            painter.drawLine(QPointF(ax, ay), QPointF(bx, by))
            remaining = target - len_ab
            t = remaining / len_bc if len_bc > 0 else 0
            end_x = bx + (cx - bx) * t
            end_y = by + (cy - by) * t
            painter.drawLine(QPointF(bx, by), QPointF(end_x, end_y))

        painter.restore()

    # ============================================================
    # 公共 API (运行时切换)
    # ============================================================
    def set_color(self, color: str):
        self._color = color
        self.update()

    def set_size(self, size: str):
        self._size = size
        self._refresh_geometry()
        self.update()

    def set_radius(self, radius: Optional[str]):
        self._radius = radius
        self.update()

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
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_line_through(self, enabled: bool):
        self._line_through = enabled
        # 状态同步
        if self.isChecked():
            self._line_progress = 1.0 if enabled else 0.0
        self.update()

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self.update()

    def set_is_indeterminate(self, indeterminate: bool):
        self._is_indeterminate = indeterminate
        self.update()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable

    def is_selected(self) -> bool:
        """别名: isChecked()"""
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        """别名: setChecked()"""
        self.setChecked(selected)

    def value(self) -> str:
        """在 CheckboxGroup 中使用的值标识"""
        return self._value

    def set_value(self, value: str):
        self._value = value


# ============================================================
# CheckboxGroup
# ============================================================
class CheckboxGroup(QWidget):
    """多选组

    统一管理多个 Checkbox 的 color / size / radius / theme / orientation，
    提供 label / description / errorMessage / isRequired / isInvalid，
    并通过 value_changed 信号汇报已选值列表。

    用法:
        group = CheckboxGroup(label="Select your tech", color="primary")
        group.add_checkbox(Checkbox("React", value="react"))
        group.add_checkbox(Checkbox("Vue", value="vue"))
        group.value_changed.connect(lambda vals: print(vals))
    """

    value_changed = Signal(list)

    def __init__(
        self,
        label: str = "",
        description: str = "",
        error_message: str = "",
        orientation: str = "vertical",
        color: str = "primary",
        size: str = "md",
        radius: Optional[str] = None,
        line_through: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        default_value: Optional[List[str]] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._label_text = label
        self._description = description
        self._error_message = error_message
        self._orientation = orientation
        self._color = color
        self._size = size
        self._radius = radius
        self._line_through = line_through
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._is_required = is_required
        self._theme_mode = theme
        self._theme = Checkbox._resolve_theme(theme)
        self._default_value = default_value or []

        self._checkboxes: List[Checkbox] = []

        self._setup_ui()
        self._apply_styles()

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    def _setup_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(8)

        # label
        self._label = QLabel(self._label_text)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._label, 0, Qt.AlignmentFlag.AlignLeft)

        # checkbox 容器
        self._wrapper = QWidget()
        if self._orientation == "horizontal":
            self._wrapper_layout = QHBoxLayout(self._wrapper)
        else:
            self._wrapper_layout = QVBoxLayout(self._wrapper)
        self._wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._wrapper_layout.setSpacing(8)
        self._root.addWidget(self._wrapper)

        # helper (desc / error)
        self._helper = QLabel("")
        self._helper.setWordWrap(True)
        self._helper.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._helper.hide()
        self._root.addWidget(self._helper)

    def _apply_styles(self):
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]

        # label
        label_color = dc[400] if is_dark else dc[500]
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        display = self._label_text + req_mark if self._label_text else ""
        self._label.setText(display)
        self._label.setStyleSheet(
            f"QLabel {{ color: {label_color}; font-family: {FONT_FAMILY}; "
            f"font-size: 14px; font-weight: 500; }}"
        )
        self._label.setVisible(bool(self._label_text))

        # helper
        if self._is_invalid and self._error_message:
            self._helper.setText(self._error_message)
            self._helper.setStyleSheet(
                f"QLabel {{ color: {HEROUI_COLORS['danger'][500]}; "
                f"font-family: {FONT_FAMILY}; font-size: 12px; }}"
            )
            self._helper.show()
        elif self._description:
            desc_color = dc[400] if is_dark else dc[500]
            self._helper.setText(self._description)
            self._helper.setStyleSheet(
                f"QLabel {{ color: {desc_color}; "
                f"font-family: {FONT_FAMILY}; font-size: 12px; }}"
            )
            self._helper.show()
        else:
            self._helper.hide()

    # ------------------------------------------------------------
    # 管理子 Checkbox
    # ------------------------------------------------------------
    def add_checkbox(self, checkbox: Checkbox):
        """添加一个已有 Checkbox（继承 group 的样式属性）"""
        # 统一样式
        checkbox.set_color(self._color)
        checkbox.set_size(self._size)
        if self._radius is not None:
            checkbox.set_radius(self._radius)
        checkbox.set_theme(self._theme)
        checkbox.set_line_through(self._line_through)
        if self._is_disabled:
            checkbox.set_is_disabled(True)
        if self._is_invalid:
            checkbox.set_is_invalid(True)

        # 默认值回填
        if checkbox.value() in self._default_value:
            checkbox.setChecked(True)

        checkbox.stateChanged.connect(self._emit_value)
        self._checkboxes.append(checkbox)
        self._wrapper_layout.addWidget(checkbox)

    def create_checkbox(self, text: str, value: Optional[str] = None) -> Checkbox:
        """便利方法：创建一个 Checkbox 并加入 group"""
        cb = Checkbox(
            text=text,
            value=value,
            color=self._color,
            size=self._size,
            theme=self._theme,
            line_through=self._line_through,
        )
        if self._radius is not None:
            cb.set_radius(self._radius)
        self.add_checkbox(cb)
        return cb

    def _emit_value(self, _state):
        vals = [cb.value() for cb in self._checkboxes if cb.isChecked()]
        self.value_changed.emit(vals)

    def value(self) -> List[str]:
        return [cb.value() for cb in self._checkboxes if cb.isChecked()]

    def set_value(self, values: List[str]):
        for cb in self._checkboxes:
            cb.setChecked(cb.value() in values)

    # ------------------------------------------------------------
    # 动态 API
    # ------------------------------------------------------------
    def _broadcast(self, fn):
        for cb in self._checkboxes:
            fn(cb)

    def set_color(self, color: str):
        self._color = color
        self._broadcast(lambda c: c.set_color(color))

    def set_size(self, size: str):
        self._size = size
        self._broadcast(lambda c: c.set_size(size))

    def set_radius(self, radius: Optional[str]):
        self._radius = radius
        self._broadcast(lambda c: c.set_radius(radius))

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = Checkbox._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._broadcast(lambda c: c.set_theme(theme))
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._broadcast(lambda c: c._apply_provider_theme(theme))
        self._apply_styles()

    def set_line_through(self, enabled: bool):
        self._line_through = enabled
        self._broadcast(lambda c: c.set_line_through(enabled))

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self._broadcast(lambda c: c.set_is_disabled(disabled))

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self._broadcast(lambda c: c.set_is_invalid(invalid))
        self._apply_styles()

    def set_is_required(self, required: bool):
        self._is_required = required
        self._apply_styles()

    def set_label(self, label: str):
        self._label_text = label
        self._apply_styles()

    def set_description(self, desc: str):
        self._description = desc
        self._apply_styles()

    def set_error_message(self, msg: str):
        self._error_message = msg
        self._apply_styles()

    def set_orientation(self, orientation: str):
        if orientation == self._orientation:
            return
        self._orientation = orientation
        # 重建布局
        old = self._wrapper_layout
        new_layout = QHBoxLayout() if orientation == "horizontal" else QVBoxLayout()
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(8)
        for cb in self._checkboxes:
            old.removeWidget(cb)
        # 删除旧 layout
        QWidget().setLayout(old)
        self._wrapper_layout = new_layout
        self._wrapper.setLayout(new_layout)
        for cb in self._checkboxes:
            new_layout.addWidget(cb)
