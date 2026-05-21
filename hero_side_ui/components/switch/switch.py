"""
HeroSideUI Switch (Toggle) Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/toggle.ts

结构:
    Switch (继承 QAbstractButton, checkable)
        ├── wrapper (胶囊: bg-default-200 / 选中时 bg-<color>)
        │     ├── startContent (开时显现, opacity 0→1 + scale 0.5→1)
        │     ├── endContent   (关时显现, opacity 1→0 + translate-x 0→12px)
        │     └── thumb (白底胶囊，从左滑到右；按压时加宽变椭圆)
        │           └── thumbIcon (可选，随 thumb 移动)
        └── label (wrapper 右侧，ms-2 = 8px)

特性对齐 HeroUI:
    - 6 种颜色 (default / primary / secondary / success / warning / danger)
    - 3 种尺寸 (sm / md / lg)
    - isSelected / isDisabled / isReadOnly
    - startContent / endContent / thumbIcon (SVG string)
    - disableAnimation
    - 主题: light / dark / auto
    - 按压时 thumb 加宽 (scale 拉长);
    - 选中时 thumb 右移 selected_shift,按压且选中时右移 pressed_shift;
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    Qt,
    Signal,
    QByteArray,
    QRectF,
    QSize,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QFontMetrics,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QWidget

from ...themes import HEROUI_COLORS, SWITCH_SIZES
from ...core import ThemeProvider
from ...animation.tween import tween_value, stop_tween


def _render_svg(svg_str: str, color: Optional[QColor] = None) -> QSvgRenderer:
    """把 currentColor 占位符替换为指定色后生成 QSvgRenderer"""
    data = svg_str
    if color is not None:
        data = data.replace("currentColor", color.name())
    return QSvgRenderer(QByteArray(data.encode("utf-8")))


class Switch(QAbstractButton):
    """HeroUI 风格的 Switch (Toggle) 组件

    继承 QAbstractButton 并设 checkable=True,保留原生 toggled / clicked / isChecked。
    外观完全自绘(忽略系统风格)。

    参数:
        text: label 文字(可为空,放在 wrapper 右侧)
        is_selected: 初始选中状态(映射到 checked)
        color: default / primary / secondary / success / warning / danger
        size: sm / md / lg
        is_disabled: 禁用(opacity 0.5 + 不可交互)
        is_read_only: 只读(可视但点击不切换)
        disable_animation: 关闭所有过渡动画
        theme: auto / light / dark
        start_content: SVG 字符串(开时显现,位于 wrapper 左内侧)
        end_content: SVG 字符串(关时显现,位于 wrapper 右内侧)
        thumb_icon: SVG 字符串(随 thumb 一起移动)
    """

    # selected_changed 发射 True/False,语义对齐 HeroUI (onValueChange)
    selected_changed = Signal(bool)

    def __init__(
        self,
        text: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        is_disabled: bool = False,
        is_read_only: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        start_content: Optional[str] = None,
        end_content: Optional[str] = None,
        thumb_icon: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._color = color
        self._size = size
        self._is_disabled = is_disabled
        self._is_read_only = is_read_only
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._start_content = start_content
        self._end_content = end_content
        self._thumb_icon = thumb_icon

        # 运行时状态
        self._hover = False
        self._pressed = False

        # 动画驱动值
        self._thumb_t = 1.0 if is_selected else 0.0  # 0 = 关,1 = 开
        self._press_t = 0.0  # 按压拉伸进度: 0 = 静态宽, 1 = 按压宽
        self._bg_color = self._unchecked_bg()
        self._target_bg = self._checked_bg() if is_selected else self._unchecked_bg()

        # 动画 runners (tween_value 会挂到这些 attr 上)
        self._thumb_anim_runner = None
        self._bg_anim_runner = None
        self._press_anim_runner = None

        # QAbstractButton 配置
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setText(text)  # 保留原生 text 属性以兼容 QAbstractButton API
        self.setEnabled(not is_disabled)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 让自绘接管
        self.setStyleSheet("Switch { background: transparent; border: none; }")

        # toggled 驱动动画与语义信号
        self.toggled.connect(self._on_toggled)

        self._refresh_font()
        self.updateGeometry()

        # auto 模式:注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 尺寸 / 字体
    # ============================================================
    def _cfg(self) -> dict:
        return SWITCH_SIZES.get(self._size, SWITCH_SIZES["md"])

    def _refresh_font(self):
        cfg = self._cfg()
        from ...core import make_text_qfont

        self.setFont(make_text_qfont(cfg["label_font_size"], "normal"))

    def setText(self, text: str):
        super().setText(text)
        self._refresh_font()
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        cfg = self._cfg()
        w = cfg["wrapper_w"]
        h = cfg["wrapper_h"]
        if self.text():
            fm = QFontMetrics(self.font())
            w += cfg["label_gap"] + fm.horizontalAdvance(self.text())
            h = max(h, fm.height())
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ============================================================
    # 色彩
    # ============================================================
    def _unchecked_bg(self) -> QColor:
        """未选中时的 wrapper 背景(bg-default-200),暗色下用 default-200 更深版本"""
        dc = HEROUI_COLORS["default"]
        if self._theme == "dark":
            # HeroUI 暗色 default-100 ≈ #27272a*0.5 的层级;用 200 也偏灰
            return QColor(dc[700])
        return QColor(dc[200])

    def _checked_bg(self) -> QColor:
        """选中时 wrapper 背景 = 所选 color 的 500 级"""
        if self._color == "default":
            dc = HEROUI_COLORS["default"]
            return QColor(dc[300] if self._theme == "dark" else dc[500])
        return QColor(HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])[500])

    def _thumb_bg(self) -> QColor:
        """thumb 始终是白色"""
        return QColor("#ffffff")

    def _thumb_icon_color(self) -> QColor:
        """thumbIcon 默认黑色(对齐 HeroUI text-black)"""
        return QColor("#000000")

    def _content_color(self, on_checked: bool) -> QColor:
        """startContent (on_checked=True) / endContent (on_checked=False) 的颜色

        startContent 位于 wrapper 内左侧,选中时可见,使用 text-current → 前景对比色:
          - warning 前景偏黑, 其他色前景白
        endContent 位于 wrapper 内右侧,未选中可见,使用 text-default-600
        """
        if on_checked:
            if self._color == "default":
                dc = HEROUI_COLORS["default"]
                return QColor(dc[900] if self._theme == "dark" else "#ffffff")
            if self._color == "warning":
                return QColor("#000000")
            return QColor("#ffffff")
        # endContent: text-default-600
        dc = HEROUI_COLORS["default"]
        return QColor(dc[400] if self._theme == "dark" else dc[600])

    def _label_color(self) -> QColor:
        """wrapper 外 label 文字色 (text-foreground)"""
        return QColor("#ecedee" if self._theme == "dark" else "#11181c")

    # ============================================================
    # 状态切换 → 动画
    # ============================================================
    def _on_toggled(self, checked: bool):
        # 发射语义信号
        self.selected_changed.emit(checked)

        # 目标 bg 色
        self._target_bg = self._checked_bg() if checked else self._unchecked_bg()

        if self._disable_animation:
            stop_tween(self, "_thumb_anim_runner")
            stop_tween(self, "_bg_anim_runner")
            self._thumb_t = 1.0 if checked else 0.0
            self._bg_color = QColor(self._target_bg)
            self.update()
            return

        # thumb 位移动画
        tween_value(
            self,
            "_thumb_anim_runner",
            self._thumb_t,
            1.0 if checked else 0.0,
            self._on_thumb_step,
            duration=250,
        )

        # bg 颜色过渡
        tween_value(
            self,
            "_bg_anim_runner",
            QColor(self._bg_color),
            QColor(self._target_bg),
            self._on_bg_step,
            duration=250,
        )

    def _on_thumb_step(self, v):
        self._thumb_t = float(v)
        self.update()

    def _on_bg_step(self, v):
        self._bg_color = QColor(v)
        self.update()

    def _on_press_step(self, v):
        self._press_t = float(v)
        self.update()

    def _animate_press_to(self, target: float):
        """平滑过渡 thumb 的按压拉伸量 (0 ↔ 1),100ms。"""
        if self._disable_animation:
            stop_tween(self, "_press_anim_runner")
            self._press_t = target
            self.update()
            return
        tween_value(
            self,
            "_press_anim_runner",
            self._press_t,
            target,
            self._on_press_step,
            duration=100,
        )

    # ============================================================
    # 事件
    # ============================================================
    def mousePressEvent(self, event):
        if self._is_read_only or not self.isEnabled():
            # read-only: 吃掉事件,不切换
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._animate_press_to(1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._animate_press_to(0.0)
        if self._is_read_only or not self.isEnabled():
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self._is_read_only:
            event.ignore()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        if self._pressed:
            self._pressed = False
            self._animate_press_to(0.0)
        super().leaveEvent(event)

    # ============================================================
    # paintEvent
    # ============================================================
    def paintEvent(self, event):
        cfg = self._cfg()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        wrap_w = cfg["wrapper_w"]
        wrap_h = cfg["wrapper_h"]
        radius = wrap_h / 2.0  # 胶囊

        # 整个组件垂直居中 wrapper
        wrap_x = 0.0
        wrap_y = (self.height() - wrap_h) / 2.0

        # ---- 禁用蒙层:通过 opacity 实现(disabled opacity ≈ 0.5) ----
        if self._is_disabled:
            painter.setOpacity(0.5)

        # ---- 1) wrapper 背景 ----
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(QRectF(wrap_x, wrap_y, wrap_w, wrap_h), radius, radius)
        painter.restore()

        # ---- 2) startContent / endContent (wrapper 内) ----
        # 尺寸约定:图标正方形,边长 = icon_font_size (参考 heroui text-tiny/small/medium)
        icon_size = float(cfg["icon_font_size"])
        content_pad = cfg["content_pad"]
        content_y = wrap_y + (wrap_h - icon_size) / 2.0

        # startContent: 随 _thumb_t 从 0 → 1 显现 (opacity 0→1, scale 0.5→1)
        if self._start_content and self._thumb_t > 0.001:
            painter.save()
            t = self._thumb_t
            painter.setOpacity(painter.opacity() * t)
            cx = wrap_x + content_pad + icon_size / 2.0
            cy = content_y + icon_size / 2.0
            s = 0.5 + 0.5 * t
            painter.translate(cx, cy)
            painter.scale(s, s)
            painter.translate(-cx, -cy)
            svg = _render_svg(self._start_content, self._content_color(on_checked=True))
            svg.render(
                painter,
                QRectF(wrap_x + content_pad, content_y, icon_size, icon_size),
            )
            painter.restore()

        # endContent: 随 _thumb_t 从 1 → 0 消失 (opacity 1→0, translate-x 0→12px)
        if self._end_content and self._thumb_t < 0.999:
            painter.save()
            t = self._thumb_t
            painter.setOpacity(painter.opacity() * (1.0 - t))
            tx = 12.0 * t  # HeroUI: translate-x-3 = 12px
            end_x = wrap_x + wrap_w - content_pad - icon_size
            painter.translate(tx, 0)
            svg = _render_svg(self._end_content, self._content_color(on_checked=False))
            svg.render(
                painter,
                QRectF(end_x, content_y, icon_size, icon_size),
            )
            painter.restore()

        # ---- 3) thumb ----
        thumb_base = cfg["thumb"]
        thumb_pressed_w = cfg["thumb_pressed"]
        # 按压拉伸用 _press_t 插值 (0 → 1),100ms 过渡,视觉不突兀
        # 禁用态/只读态:强制 _press_t=0 (不拉伸)
        effective_press = self._press_t
        if self._disable_animation or not self.isEnabled() or self._is_read_only:
            effective_press = 0.0
        thumb_w = thumb_base + (thumb_pressed_w - thumb_base) * effective_press
        thumb_h = thumb_base  # 高度始终 = thumb_base (→ 按压时变椭圆)

        # 位置: 未选中时 thumb 靠左(pad 后紧贴);选中时向右移 selected_shift
        # 按压且选中时位移收敛到 pressed_shift (更靠左一点,让拉长不超出右边界)
        checked = self.isChecked()
        selected_shift = cfg["selected_shift"]
        pressed_shift = cfg["pressed_shift"]
        # 选中时的位移:在 selected_shift 和 pressed_shift 之间按 effective_press 插值
        shift_end = selected_shift + (pressed_shift - selected_shift) * effective_press
        # _thumb_t 0→1 线性插值位移
        thumb_x = wrap_x + cfg["pad"] + shift_end * self._thumb_t

        # 如果按压但不 selected,thumb 仍在左但宽度变大;不位移
        # (HeroUI: group-data-[pressed=true]:w-5 等)
        thumb_y = wrap_y + (wrap_h - thumb_h) / 2.0
        thumb_r = thumb_h / 2.0

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._thumb_bg())
        # 轻微阴影:在 thumb 下画一层半透明黑色椭圆偏移
        shadow = QColor(0, 0, 0, 35)
        painter.setBrush(shadow)
        painter.drawRoundedRect(
            QRectF(thumb_x, thumb_y + 1, thumb_w, thumb_h), thumb_r, thumb_r
        )
        painter.setBrush(self._thumb_bg())
        painter.drawRoundedRect(
            QRectF(thumb_x, thumb_y, thumb_w, thumb_h), thumb_r, thumb_r
        )
        painter.restore()

        # thumbIcon: 居中于 thumb
        if self._thumb_icon:
            painter.save()
            ic_size = thumb_h * 0.6
            ic_x = thumb_x + (thumb_w - ic_size) / 2.0
            ic_y = thumb_y + (thumb_h - ic_size) / 2.0
            svg = _render_svg(self._thumb_icon, self._thumb_icon_color())
            svg.render(painter, QRectF(ic_x, ic_y, ic_size, ic_size))
            painter.restore()

        # ---- 4) label ----
        text = self.text()
        if text:
            painter.save()
            painter.setOpacity(1.0 if not self._is_disabled else 0.5)
            painter.setPen(self._label_color())
            painter.setFont(self.font())
            fm = QFontMetrics(self.font())
            text_x = wrap_x + wrap_w + cfg["label_gap"]
            text_w = self.width() - text_x
            painter.drawText(
                QRectF(text_x, 0, text_w, self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                text,
            )
            painter.restore()

        painter.end()

    # ============================================================
    # 公共 API (运行时)
    # ============================================================
    def is_selected(self) -> bool:
        """别名:isChecked"""
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        self.setChecked(selected)

    def set_color(self, color: str):
        if color == self._color:
            return
        self._color = color
        # 重新计算目标 bg(如果当前选中要立即变色)
        self._target_bg = (
            self._checked_bg() if self.isChecked() else self._unchecked_bg()
        )
        if self._disable_animation:
            self._bg_color = QColor(self._target_bg)
        else:
            tween_value(
                self,
                "_bg_anim_runner",
                QColor(self._bg_color),
                QColor(self._target_bg),
                self._on_bg_step,
                duration=200,
            )
        self.update()

    def set_size(self, size: str):
        if size == self._size:
            return
        self._size = size
        self._refresh_font()
        self.updateGeometry()
        self.update()

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_read_only(self, read_only: bool):
        self._is_read_only = read_only
        self.update()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable

    def set_start_content(self, svg: Optional[str]):
        self._start_content = svg
        self.update()

    def set_end_content(self, svg: Optional[str]):
        self._end_content = svg
        self.update()

    def set_thumb_icon(self, svg: Optional[str]):
        self._thumb_icon = svg
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
        # 立即更新当前 bg 色(不动画)
        self._target_bg = (
            self._checked_bg() if self.isChecked() else self._unchecked_bg()
        )
        self._bg_color = QColor(self._target_bg)
        self.update()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用:只在 auto 模式下调用"""
        self._theme = theme
        self._target_bg = (
            self._checked_bg() if self.isChecked() else self._unchecked_bg()
        )
        self._bg_color = QColor(self._target_bg)
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme
