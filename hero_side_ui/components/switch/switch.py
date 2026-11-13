"""Switch 组件：HeroUI v2 风格胶囊开关，paintEvent 全自绘。"""

from __future__ import annotations

from PySide6.QtCore import (
    QByteArray,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QWidget

from ...animation.tween import tween_value
from ...core import FontProvider, ThemeProvider
from ...themes import HEROUI_COLORS, SWITCH_SIZES


def _render_svg(svg_str: str, color: QColor | None = None) -> QSvgRenderer:
    """把 currentColor 占位符替换为指定色后生成 QSvgRenderer。

    Args:
        svg_str: 含 currentColor 占位符的 SVG 源文本。
        color: 替换色；为 None 时保留占位符不替换。

    Returns:
        由替换后文本构造的 QSvgRenderer。
    """
    data = svg_str
    if color is not None:
        data = data.replace("currentColor", color.name())
    return QSvgRenderer(QByteArray(data.encode("utf-8")))


class Switch(QAbstractButton):
    """HeroUI 风格 Switch，继承 QAbstractButton（checkable）保留原生信号。"""

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
        start_content: str | None = None,
        end_content: str | None = None,
        thumb_icon: str | None = None,
        parent: QWidget | None = None,
    ):
        """按外观与状态配置创建胶囊开关。

        Args:
            text: label 文字，位于 wrapper 右侧。
            is_selected: 初始选中状态。
            color: 语义色，默认 primary。
            size: 尺寸档位 sm/md/lg。
            is_disabled: 是否禁用。
            is_read_only: 是否只读，可视不切换。
            disable_animation: 是否关闭过渡动画。
            theme: 主题模式 auto/light/dark。
            start_content: 开时显现的 SVG。
            end_content: 关时显现的 SVG。
            thumb_icon: 随 thumb 移动的 SVG。
            parent: 父级 QWidget。

        Note:
            auto 主题会向 ThemeProvider 注册；color 与 size 直接赋值，未做非法值校验。
        """
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
        FontProvider.instance().register(self)

    # ============================================================
    # 尺寸 / 字体
    # ============================================================
    def _cfg(self) -> dict:
        """返回当前尺寸档位的配置字典。"""
        return SWITCH_SIZES.get(self._size, SWITCH_SIZES["md"])

    def _apply_font(self):
        """全局字体变化后重设字体并通知布局。"""
        self._refresh_font()
        self.updateGeometry()
        self.update()

    def _refresh_font(self):
        """按尺寸档位重设 label 字体。"""
        cfg = self._cfg()
        from ...core import make_text_qfont

        self.setFont(make_text_qfont(cfg["label_font_size"], "normal"))

    def setText(self, text: str):
        """设置 label 文字并刷新字体与几何尺寸。

        Args:
            text: label 文字。
        """
        super().setText(text)
        self._refresh_font()
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        """返回含 label 文字宽度的推荐尺寸。"""
        cfg = self._cfg()
        w = cfg["wrapper_w"]
        h = cfg["wrapper_h"]
        if self.text():
            fm = QFontMetrics(self.font())
            w += cfg["label_gap"] + fm.horizontalAdvance(self.text())
            h = max(h, fm.height())
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        """返回与 sizeHint 相同的最小推荐尺寸。"""
        return self.sizeHint()

    # ============================================================
    # 色彩
    # ============================================================
    def _unchecked_bg(self) -> QColor:
        """返回未选中状态的 wrapper 背景色。"""
        dc = HEROUI_COLORS["default"]
        if self._theme == "dark":
            # HeroUI 暗色 default-100 ≈ #27272a*0.5 的层级;用 200 也偏灰
            return QColor(dc[700])
        return QColor(dc[200])

    def _checked_bg(self) -> QColor:
        """返回选中状态的 wrapper 背景色。"""
        if self._color == "default":
            dc = HEROUI_COLORS["default"]
            return QColor(dc[300] if self._theme == "dark" else dc[500])
        return QColor(HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])[500])

    def _thumb_bg(self) -> QColor:
        """返回 thumb 的背景色，固定为白色。"""
        return QColor("#ffffff")

    def _thumb_icon_color(self) -> QColor:
        """返回 thumbIcon 的默认颜色，固定为黑色。"""
        return QColor("#000000")

    def _content_color(self, on_checked: bool) -> QColor:
        """取 startContent/endContent 颜色：start 用前景对比色，end 用 default-600。"""
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
        """返回 wrapper 外 label 的文字色。"""
        return QColor("#ecedee" if self._theme == "dark" else "#11181c")

    # ============================================================
    # 状态切换 → 动画
    # ============================================================
    def _on_toggled(self, checked: bool):
        """响应选中态变化，发射语义信号并启动 thumb 与背景过渡。

        Args:
            checked: 新的选中状态。
        """
        self.selected_changed.emit(checked)
        self._target_bg = self._checked_bg() if checked else self._unchecked_bg()
        tween_value(
            self,
            "_thumb_anim_runner",
            self._thumb_t,
            1.0 if checked else 0.0,
            self._on_thumb_step,
            duration=250,
            animated=not self._disable_animation,
        )
        tween_value(
            self,
            "_bg_anim_runner",
            QColor(self._bg_color),
            QColor(self._target_bg),
            self._on_bg_step,
            duration=250,
            animated=not self._disable_animation,
        )

    def _on_thumb_step(self, v):
        """接收 thumb 动画帧并触发重绘。

        Args:
            v: 当前动画值。
        """
        self._thumb_t = float(v)
        self.update()

    def _on_bg_step(self, v):
        """接收背景色动画帧并触发重绘。

        Args:
            v: 当前动画颜色值。
        """
        self._bg_color = QColor(v)
        self.update()

    def _on_press_step(self, v):
        """接收按压动画帧并触发重绘。

        Args:
            v: 当前动画值。
        """
        self._press_t = float(v)
        self.update()

    def _animate_press_to(self, target: float):
        """把按压进度过渡到目标值。

        Args:
            target: 目标按压进度，0 为静态宽、1 为按压宽。
        """
        tween_value(
            self,
            "_press_anim_runner",
            self._press_t,
            target,
            self._on_press_step,
            duration=100,
            animated=not self._disable_animation,
        )

    # ============================================================
    # 事件
    # ============================================================
    def mousePressEvent(self, event):
        """处理按下事件，只读或禁用时吞掉事件不切换。

        Args:
            event: Qt 鼠标事件。
        """
        if self._is_read_only or not self.isEnabled():
            # read-only: 吃掉事件,不切换
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._animate_press_to(1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """处理释放事件，复位按压态并收敛按压动画。

        Args:
            event: Qt 鼠标事件。
        """
        self._pressed = False
        self._animate_press_to(0.0)
        if self._is_read_only or not self.isEnabled():
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """处理按键事件，只读时忽略输入。

        Args:
            event: Qt 按键事件。
        """
        if self._is_read_only:
            event.ignore()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event):
        """进入组件时置悬停态并触发重绘。

        Args:
            event: Qt 进入事件。
        """
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """离开组件时清悬停态并收敛按压动画。

        Args:
            event: Qt 离开事件。
        """
        self._hover = False
        if self._pressed:
            self._pressed = False
            self._animate_press_to(0.0)
        super().leaveEvent(event)

    # ============================================================
    # paintEvent
    # ============================================================
    def paintEvent(self, event):
        """全自绘 wrapper、thumb、内容与 label。

        Args:
            event: Qt 绘制事件，本实现不读取。
        """
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
        self.isChecked()
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
        painter.drawRoundedRect(QRectF(thumb_x, thumb_y + 1, thumb_w, thumb_h), thumb_r, thumb_r)
        painter.setBrush(self._thumb_bg())
        painter.drawRoundedRect(QRectF(thumb_x, thumb_y, thumb_w, thumb_h), thumb_r, thumb_r)
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
            QFontMetrics(self.font())
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
        """返回当前选中状态，等价于 isChecked。"""
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        """设置选中状态。

        Args:
            selected: 目标选中状态。
        """
        self.setChecked(selected)

    def set_color(self, color: str):
        """设置语义色并过渡 wrapper 背景。

        Args:
            color: 目标语义色。

        Note:
            与当前色相同则直接返回；color 未做非法值校验。
        """
        if color == self._color:
            return
        self._color = color
        self._target_bg = self._checked_bg() if self.isChecked() else self._unchecked_bg()
        tween_value(
            self,
            "_bg_anim_runner",
            QColor(self._bg_color),
            QColor(self._target_bg),
            self._on_bg_step,
            duration=200,
            animated=not self._disable_animation,
        )
        self.update()

    def set_size(self, size: str):
        """设置尺寸档位并刷新字体与几何尺寸。

        Args:
            size: 目标尺寸档位。

        Note:
            与当前档位相同则直接返回；size 未做非法值校验。
        """
        if size == self._size:
            return
        self._size = size
        self._refresh_font()
        self.updateGeometry()
        self.update()

    def set_is_disabled(self, disabled: bool):
        """设置禁用状态并同步 Qt 启用状态。

        Args:
            disabled: 是否禁用。
        """
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_read_only(self, read_only: bool):
        """设置只读状态，只读时可视但不切换。

        Args:
            read_only: 是否只读。
        """
        self._is_read_only = read_only
        self.update()

    def set_disable_animation(self, disable: bool):
        """设置是否关闭过渡动画。

        Args:
            disable: 是否关闭动画。

        Note:
            关闭时用 duration=0 把 thumb、背景与按压进度立即收敛到当前状态。
        """
        self._disable_animation = disable
        if disable:
            tween_value(
                self,
                "_thumb_anim_runner",
                self._thumb_t,
                1.0 if self.isChecked() else 0.0,
                self._on_thumb_step,
                duration=0,
            )
            target = self._checked_bg() if self.isChecked() else self._unchecked_bg()
            tween_value(
                self,
                "_bg_anim_runner",
                QColor(self._bg_color),
                QColor(target),
                self._on_bg_step,
                duration=0,
            )
            self._animate_press_to(0.0)

    def set_start_content(self, svg: str | None):
        """设置开时显现的 SVG 内容。

        Args:
            svg: SVG 源文本，None 表示不显示。
        """
        self._start_content = svg
        self.update()

    def set_end_content(self, svg: str | None):
        """设置关时显现的 SVG 内容。

        Args:
            svg: SVG 源文本，None 表示不显示。
        """
        self._end_content = svg
        self.update()

    def set_thumb_icon(self, svg: str | None):
        """设置随 thumb 移动的 SVG 图标。

        Args:
            svg: SVG 源文本，None 表示不显示。
        """
        self._thumb_icon = svg
        self.update()

    def set_theme(self, theme: str):
        """设置主题模式并立即刷新背景色。

        Args:
            theme: 主题名或 auto。

        Note:
            auto 会向 ThemeProvider 注册，从 auto 切到固定主题时注销；背景色直接刷新不做动画。
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
        # 立即更新当前 bg 色(不动画)
        self._target_bg = self._checked_bg() if self.isChecked() else self._unchecked_bg()
        self._bg_color = QColor(self._target_bg)
        self.update()

    def _apply_provider_theme(self, theme: str):
        """响应 ThemeProvider 广播并刷新背景色。"""
        self._theme = theme
        self._target_bg = self._checked_bg() if self.isChecked() else self._unchecked_bg()
        self._bg_color = QColor(self._target_bg)
        self.update()

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
