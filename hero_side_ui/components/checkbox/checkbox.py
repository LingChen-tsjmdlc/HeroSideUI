"""Checkbox 组件：HeroUI v2 风格复选框，paintEvent 全自绘。

文件同时提供 CheckboxGroup（label/description/errorMessage、方向排布、
组级样式下发与 value 聚合）。
"""

from PySide6.QtCore import (
    Property,
    QByteArray,
    QEasingCurve,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QWidget,
)

from ...animation import CheckDrawAnimation, paint_animated_check, tween_property
from ...core import ThemeProvider
from ...themes import CHECKBOX_SIZES, HEROUI_COLORS, RADIUS

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
    """把 SVG 模板里的 currentColor 替换成实际颜色并构造渲染器。

    Args:
        svg_tpl: 含 currentColor 占位符的 SVG 文本。
        color: 要替换进去的 QColor。

    Returns:
        可直接 render 到 QPainter 的 QSvgRenderer。
    """
    data = svg_tpl.replace("currentColor", color.name())
    return QSvgRenderer(QByteArray(data.encode("utf-8")))


# ============================================================
# Checkbox
# ============================================================
class Checkbox(QCheckBox):
    """HeroUI 风格 Checkbox，继承 QCheckBox 保留原生信号。

    Args:
        text: label 文字。
        is_selected: 初始选中。
        color: 语义色，默认 primary。
        size: sm/md/lg。
        radius: 圆角；None 跟随 size。
        line_through: 选中时 label 加删除线。
        is_disabled: 禁用。
        is_invalid: 无效态（边框变红）。
        is_indeterminate: 未定态（minus 图标）。
        disable_animation: 关闭动画。
        theme: light/dark/auto。
        value: 在 CheckboxGroup 中的标识值。
    """

    def __init__(
        self,
        text: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        radius: str | None = None,
        line_through: bool = False,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_indeterminate: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        value: str | None = None,
        parent: QWidget | None = None,
    ):
        """创建复选框并接管外观自绘。

        Args:
            text: label 文字。
            is_selected: 初始选中。
            color: 语义色，默认 primary。
            size: sm / md / lg。
            radius: 圆角；None 跟随默认 md。
            line_through: 选中时 label 加删除线。
            is_disabled: 禁用。
            is_invalid: 无效态（边框变红）。
            is_indeterminate: 未定态（minus 图标）。
            disable_animation: 关闭全部补间动画。
            theme: light / dark / auto。
            value: 在 CheckboxGroup 中的标识值；None 时用 text。
            parent: Qt 父对象。

        Note:
            保留 QCheckBox 原生信号，stateChanged 驱动填充与对勾动画；
            样式用空 QSS 让 paintEvent 完全接管外观。
        """
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
        self._check_anim = CheckDrawAnimation(
            self,
            on_step=lambda _: self.update(),
            duration_in=500,
            delay_in=100,
        )
        self._hover = False

        # 初始状态
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setEnabled(not is_disabled)
        self._check_anim.set_immediate(is_selected and not is_indeterminate)
        if is_selected:
            self._fill_progress = 1.0
            if line_through:
                self._line_progress = 1.0

        # 动画
        self._fill_anim = None
        self._line_anim = None
        self._press_anim = None

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
        """Property getter：填充进度。

        Returns:
            0.0 未选中、1.0 完全选中。
        """
        return self._fill_progress

    def _set_fill(self, v: float):
        """Property setter：写入填充进度并重绘。

        Args:
            v: 新进度，由 tween 每帧调用。
        """
        self._fill_progress = v
        self.update()

    fill_progress = Property(float, _get_fill, _set_fill)

    def _get_line(self) -> float:
        """Property getter：删除线展开进度。

        Returns:
            0.0 无线、1.0 全长。
        """
        return self._line_progress

    def _set_line(self, v: float):
        """Property setter：写入删除线进度并重绘。

        Args:
            v: 新进度，由 tween 每帧调用。
        """
        self._line_progress = v
        self.update()

    line_progress = Property(float, _get_line, _set_line)

    def _get_press(self) -> float:
        """Property getter：按压缩放进度。

        Returns:
            0.0 原始尺寸、1.0 缩到 0.95。
        """
        return self._press_progress

    def _set_press(self, v: float):
        """Property setter：写入按压进度并重绘。

        Args:
            v: 新进度，由 tween 每帧调用。
        """
        self._press_progress = v
        self.update()

    press_progress = Property(float, _get_press, _set_press)

    def _get_check_draw(self) -> float:
        """Property getter：对勾描绘进度。

        Returns:
            动画对象当前的 progress。
        """
        return self._check_anim.progress

    def _set_check_draw(self, value: float):
        """Property setter：驱动对勾动画进度。

        Args:
            value: 新的进度值。
        """
        self._check_anim.progress = value

    check_draw = Property(float, _get_check_draw, _set_check_draw)

    # ============================================================
    # 状态变化 / 动画
    # ============================================================
    def _on_state_changed(self, state):
        """状态变化回调：同步填充、对勾与删除线三条动画。

        Args:
            state: Qt stateChanged 的整数状态（未直接使用，改用 isChecked）。

        Note:
            indeterminate 或禁用动画时，对勾走 set_immediate 直达终态。
        """
        checked = self.isChecked()
        tween_property(
            self,
            "_fill_anim",
            b"fill_progress",
            1.0 if checked else 0.0,
            duration=200,
            easing=QEasingCurve.Type.Linear,
            animated=not self._disable_animation,
        )
        if self._is_indeterminate or self._disable_animation:
            self._check_anim.set_immediate(checked and not self._is_indeterminate)
        else:
            self._check_anim.play(checked)
        tween_property(
            self,
            "_line_anim",
            b"line_progress",
            1.0 if checked and self._line_through else 0.0,
            duration=200,
            animated=not self._disable_animation,
        )

    # ============================================================
    # 按压缩放
    # ============================================================
    def mousePressEvent(self, event):
        """鼠标按下：启用且未禁用动画时播放缩放。

        Args:
            event: Qt 鼠标按下事件。
        """
        if self.isEnabled() and not self._disable_animation:
            tween_property(self, "_press_anim", b"press_progress", 1.0, duration=80)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：恢复按压缩放。

        Args:
            event: Qt 鼠标释放事件。
        """
        if self.isEnabled() and not self._disable_animation:
            tween_property(self, "_press_anim", b"press_progress", 0.0, duration=150)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """鼠标进入：置 hover 位并重绘。

        Args:
            event: Qt 进入事件。
        """
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：清 hover 位并重绘。

        Args:
            event: Qt 离开事件。
        """
        self._hover = False
        self.update()
        super().leaveEvent(event)

    # ============================================================
    # 几何计算 (基于 size)
    # ============================================================
    def _size_config(self) -> dict:
        """取当前尺寸档位的配置。

        Returns:
            CHECKBOX_SIZES 中的配置字典；非法档位回退 md。
        """
        return CHECKBOX_SIZES.get(self._size, CHECKBOX_SIZES["md"])

    def _refresh_geometry(self):
        """按字体与文本重算最小尺寸并通知布局。

        Note:
            外围留 2px padding 作为 HeroUI 的 p-2 tap 热区。
        """
        cfg = self._size_config()
        from ...core import make_text_qfont

        font = make_text_qfont(cfg["label_font_size"], "normal")
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
        """覆写 setText：文本变化后重算最小尺寸。

        Args:
            text: 新 label 文本。
        """
        super().setText(text)
        self._refresh_geometry()

    def sizeHint(self) -> QSize:
        """返回容纳 box + 间距 + 文本的推荐尺寸。

        Returns:
            宽度 = box + gap + 文字宽 + 4px padding，
            高度 = max(box, 文字行高) + 4px padding。
        """
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
        """按主题、语义色与状态解析全部绘制颜色。

        Returns:
            (border_color, fill_color, icon_color, label_color,
            hover_bg_color) 五元组；invalid 态边框与文字改 danger 色，
            default / warning 各有专门的填充与图标对比色。
        """
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
        """解析方框圆角像素值。

        Args:
            box_size: 方框边长。

        Returns:
            None 档默认 8px；full 为边长一半；none 为 0；
            sm/md/lg 分别 4/8/14，未知档回退 8。
        """
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
        """完整自绘：hover 底 → 边框 → 选中填充 → 图标 → 文字 → 删除线 → 蒙层。

        Args:
            event: Qt 绘制事件。

        Note:
            按压缩放围绕 box 中心做整体 scale；填充用 scale 0.5→1
            叠加 opacity 淡入；indeterminate 恒画满并改用 minus 图标；
            对勾描绘复用 animation/check_draw.paint_animated_check。
        """
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
        self.isChecked() or self._is_indeterminate
        p = 1.0 if (self._is_indeterminate and not self.isChecked()) else self._fill_progress
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
                # check: 手绘两段线，按 _check_draw 进度描出 —— 复用 animation/check_draw.paint_animated_check
                paint_animated_check(
                    painter,
                    (ic_x, ic_y, ic_w, ic_h),
                    icon_color,
                    progress=self._check_anim.progress,
                    opacity=opacity,
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
    # 动画 check 图标（手绘对勾）—— 已抽取到 animation/check_draw.paint_animated_check
    # 保留这一段标题占位，便于读者按"功能区"导航；具体绘制见 paintEvent 的调用。
    # ============================================================

    # ============================================================
    # 公共 API (运行时切换)
    # ============================================================
    def set_color(self, color: str):
        """切换语义色并重绘。

        Args:
            color: 语义色名。
        """
        self._color = color
        self.update()

    def set_size(self, size: str):
        """切换尺寸档位并重算几何。

        Args:
            size: sm / md / lg。
        """
        self._size = size
        self._refresh_geometry()
        self.update()

    def set_radius(self, radius: str | None):
        """切换圆角档位并重绘。

        Args:
            radius: 圆角档位；None 恢复默认。
        """
        self._radius = radius
        self.update()

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
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
        self.update()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_line_through(self, enabled: bool):
        """切换选中文字删除线（无动画直达目标态）。

        Args:
            enabled: True 且当前已选中时展开删除线。
        """
        self._line_through = enabled
        tween_property(
            self,
            "_line_anim",
            b"line_progress",
            1.0 if enabled and self.isChecked() else 0.0,
            duration=0,
        )

    def set_is_disabled(self, disabled: bool):
        """切换禁用态并同步 Qt 启用状态。

        Args:
            disabled: True 表示禁用。
        """
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_invalid(self, invalid: bool):
        """切换无效态（红边框与红文字）。

        Args:
            invalid: True 表示无效。
        """
        self._is_invalid = invalid
        self.update()

    def set_is_indeterminate(self, indeterminate: bool):
        """切换未定态（minus 图标、恒满填充）。

        Args:
            indeterminate: True 表示未定态。
        """
        self._is_indeterminate = indeterminate
        self._check_anim.set_immediate(self.isChecked() and not indeterminate)
        self.update()

    def set_disable_animation(self, disable: bool):
        """切换动画开关，并立即把状态对齐到终态。

        Args:
            disable: True 关闭动画；关闭时重置 on_state_changed 与按压进度。
        """
        self._disable_animation = disable
        if disable:
            self._on_state_changed(None)
            tween_property(self, "_press_anim", b"press_progress", 0.0, duration=0)

    def is_selected(self) -> bool:
        """别名：isChecked()。

        Returns:
            当前勾选状态。
        """
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        """别名：setChecked()。

        Args:
            selected: 目标勾选状态。
        """
        self.setChecked(selected)

    def value(self) -> str:
        """在 CheckboxGroup 中使用的值标识。

        Returns:
            构造时的 value；未指定时为 label 文本。
        """
        return self._value

    def set_value(self, value: str):
        """更新值标识。

        Args:
            value: 新的 value 字符串。
        """
        self._value = value
