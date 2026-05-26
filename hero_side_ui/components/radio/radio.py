"""
HeroSideUI Radio Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/radio.ts
组件来源: https://github.com/heroui-inc/heroui/tree/main/packages/components/radio

结构 (slots):
    Radio (继承 QAbstractButton)
        ├── wrapper  (外圈圆环，带边框)
        ├── control  (内圆点，选中时缩放+透明度过渡)
        └── labelWrapper
            ├── label        (children/text)
            └── description  (副文本)

特性对齐 HeroUI:
    - 6 种颜色 (default / primary / secondary / success / warning / danger)
    - 3 种尺寸 (sm / md / lg)
    - hover 时 wrapper 加 default-100 底色 (group-data-[hover-unselected])
    - 按压缩放 (scale-95)
    - 内圆点 scale 0 → 1 + opacity 0 → 1 过渡
    - isDisabled / isInvalid / disableAnimation
    - 主题: light / dark / auto
"""

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QAbstractButton, QSizePolicy, QWidget

from ...core import ThemeProvider, make_text_qfont
from ...themes import HEROUI_COLORS, RADIO_SIZES

VALID_COLORS = tuple(HEROUI_COLORS.keys())
VALID_SIZES = ("sm", "md", "lg")


class Radio(QAbstractButton):
    """HeroUI 风格的 Radio 组件

    单选 wrapper —— 配合 RadioGroup 使用时由 group 互斥；独立使用时
    setCheckable(True) 即可像普通按钮那样 toggle。
    """

    selected = Signal(str)

    def __init__(
        self,
        text: str = "",
        value: Optional[str] = None,
        description: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        is_disabled: bool = False,
        is_invalid: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}, got {color!r}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}, got {size!r}")

        self._color = color
        self._size = size
        self._description = description
        self._is_disabled = is_disabled
        self._is_invalid = is_invalid
        self._disable_animation = disable_animation
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._value = value if value is not None else text

        # 动画驱动值
        self._control_progress = 0.0  # 0 = hidden, 1 = full
        self._press_progress = 0.0  # 0 = 1.0, 1 = 0.95
        self._hover = False

        self.setText(text)
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setEnabled(not is_disabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        if is_selected and not disable_animation:
            self._control_progress = 1.0

        # 动画
        self._control_anim = QPropertyAnimation(self, b"control_progress")
        self._control_anim.setDuration(180)
        self._control_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._press_anim = QPropertyAnimation(self, b"press_progress")
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)
        self._refresh_geometry()

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Qt 属性（驱动动画）
    # ============================================================
    def _get_control(self) -> float:
        return self._control_progress

    def _set_control(self, v: float):
        self._control_progress = v
        self.update()

    control_progress = Property(float, _get_control, _set_control)

    def _get_press(self) -> float:
        return self._press_progress

    def _set_press(self, v: float):
        self._press_progress = v
        self.update()

    press_progress = Property(float, _get_press, _set_press)

    # ============================================================
    # 状态变化
    # ============================================================
    def _on_toggled(self, checked: bool):
        if self._disable_animation:
            self._control_progress = 1.0 if checked else 0.0
            self.update()
        else:
            self._control_anim.stop()
            self._control_anim.setStartValue(self._control_progress)
            self._control_anim.setEndValue(1.0 if checked else 0.0)
            self._control_anim.start()
        if checked:
            self.selected.emit(self._value)

    # ============================================================
    # 鼠标 / 焦点事件
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

    # 关键：QAbstractButton 默认点击会 toggle，但 radio 语义是
    # "已选中时再次点击不取消"。RadioGroup 模式下点击其它 radio 才会
    # 把当前 radio 置回未选中。这里复制 HeroUI 行为：单体使用时仍允许
    # 反向 toggle（无 group 时无人帮忙取消，反而方便测试/独立用）；
    # group 模式由 RadioGroup 在 add_radio 时改写为"已选中再点忽略"。
    def nextCheckState(self):
        # 由 RadioGroup 注入 hook 控制是否允许反向取消
        guard = getattr(self, "_toggle_guard", None)
        if callable(guard) and guard(self):
            # 守卫返回 True = 拦截：不切状态
            return
        super().nextCheckState()

    # ============================================================
    # 几何
    # ============================================================
    def _size_config(self) -> dict:
        return RADIO_SIZES.get(self._size, RADIO_SIZES["md"])

    def _label_font(self) -> QFont:
        cfg = self._size_config()
        return make_text_qfont(cfg["label_font_size"], "normal")

    def _desc_font(self) -> QFont:
        cfg = self._size_config()
        return make_text_qfont(cfg["desc_font_size"], "normal")

    def _refresh_geometry(self):
        self.setFont(self._label_font())
        self.updateGeometry()
        self.update()

    def setText(self, text: str):  # type: ignore[override]
        super().setText(text)
        self._refresh_geometry()

    def sizeHint(self) -> QSize:
        cfg = self._size_config()
        wrapper = cfg["wrapper"]
        gap = cfg["gap"]

        label_w = label_h = desc_w = desc_h = 0
        if self.text():
            fm = QFontMetrics(self._label_font())
            label_w = fm.horizontalAdvance(self.text())
            label_h = fm.height()
        if self._description:
            fm = QFontMetrics(self._desc_font())
            desc_w = fm.horizontalAdvance(self._description)
            desc_h = fm.height()

        text_w = max(label_w, desc_w)
        text_h = label_h + desc_h
        total_w = wrapper + (gap if text_w > 0 else 0) + text_w
        total_h = max(wrapper, text_h)
        # HeroUI: p-2 -m-2 = 4px 视觉点击热区
        pad = 4
        return QSize(total_w + pad * 2, total_h + pad * 2)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ============================================================
    # 色彩决策
    # ============================================================
    def _palette(self):
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])

        # 默认 wrapper 边框 = default-300（亮）/ default-400（暗）
        border = QColor(dc[400] if is_dark else dc[300])
        # 选中 wrapper 边框 = 主色（default 用 default-500）
        if self._color == "default":
            selected_border = QColor(dc[300] if is_dark else dc[500])
            control = QColor(dc[300] if is_dark else dc[500])
        else:
            selected_border = QColor(colors[500])
            control = QColor(colors[500])

        # invalid 强制 danger
        if self._is_invalid:
            border = QColor(HEROUI_COLORS["danger"][500])
            selected_border = QColor(HEROUI_COLORS["danger"][500])
            control = QColor(HEROUI_COLORS["danger"][500])

        # hover 底色（wrapper 内部 bg-default-100）
        hover_bg = QColor(dc[700] if is_dark else dc[100])

        # label / description
        label_color = QColor("#ecedee" if is_dark else "#11181c")
        desc_color = QColor(dc[400] if is_dark else dc[400])

        if self._is_invalid:
            label_color = QColor(HEROUI_COLORS["danger"][500])
            desc_color = QColor(HEROUI_COLORS["danger"][300])

        return border, selected_border, control, hover_bg, label_color, desc_color

    # ============================================================
    # paintEvent — 完整自绘
    # ============================================================
    def paintEvent(self, event):
        cfg = self._size_config()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        (
            border_color,
            selected_border,
            control_color,
            hover_bg,
            label_color,
            desc_color,
        ) = self._palette()

        wrapper_size = cfg["wrapper"]
        control_size = cfg["control"]
        bw = cfg["border_width"]
        gap = cfg["gap"]

        # 计算 wrapper 与文字布局
        rect = self.rect()
        pad_x = 4
        # wrapper 整体垂直居中
        box_x = pad_x
        box_y = (rect.height() - wrapper_size) // 2
        cx = box_x + wrapper_size / 2.0
        cy = box_y + wrapper_size / 2.0

        # ---- 按压缩放 (scale-95) ----
        press_scale = 1.0 - 0.05 * self._press_progress
        if press_scale < 1.0:
            painter.save()
            painter.translate(cx, cy)
            painter.scale(press_scale, press_scale)
            painter.translate(-cx, -cy)

        is_selected = self.isChecked()

        # ---- 1) hover 内底色（仅未选中时显示）----
        if self._hover and not is_selected and not self._is_disabled:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hover_bg)
            painter.drawEllipse(QRectF(box_x, box_y, wrapper_size, wrapper_size))
            painter.restore()

        # ---- 2) wrapper 边框（圆环）----
        # 选中时边框颜色随 control_progress 从 default → 主色 渐变更稳
        cp = self._control_progress
        if is_selected:
            r = self._lerp(border_color.red(), selected_border.red(), cp)
            g = self._lerp(border_color.green(), selected_border.green(), cp)
            b = self._lerp(border_color.blue(), selected_border.blue(), cp)
            ring = QColor(r, g, b)
        else:
            ring = border_color

        painter.save()
        pen = QPen(ring, bw)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        half = bw / 2.0
        painter.drawEllipse(
            QRectF(
                box_x + half,
                box_y + half,
                wrapper_size - bw,
                wrapper_size - bw,
            )
        )
        painter.restore()

        # ---- 3) 内圆点 control（scale 0 → 1 + opacity 0 → 1）----
        if cp > 0.001:
            painter.save()
            painter.setOpacity(cp)
            painter.translate(cx, cy)
            painter.scale(cp, cp)
            painter.translate(-cx, -cy)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(control_color)
            r2 = control_size / 2.0
            painter.drawEllipse(QRectF(cx - r2, cy - r2, control_size, control_size))
            painter.restore()

        if press_scale < 1.0:
            painter.restore()

        # ---- 4) labelWrapper：label + description ----
        if self.text() or self._description:
            text_x = box_x + wrapper_size + gap
            label_fm = QFontMetrics(self._label_font())
            desc_fm = QFontMetrics(self._desc_font())
            label_h = label_fm.height() if self.text() else 0
            desc_h = desc_fm.height() if self._description else 0
            block_h = label_h + desc_h
            text_top = (rect.height() - block_h) // 2

            # disabled 整体半透明
            painter.save()
            if self._is_disabled:
                painter.setOpacity(0.5)

            if self.text():
                painter.setPen(QPen(label_color))
                painter.setFont(self._label_font())
                painter.drawText(
                    QRectF(text_x, text_top, rect.width() - text_x - pad_x, label_h),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    self.text(),
                )

            if self._description:
                painter.setPen(QPen(desc_color))
                painter.setFont(self._desc_font())
                painter.drawText(
                    QRectF(
                        text_x,
                        text_top + label_h,
                        rect.width() - text_x - pad_x,
                        desc_h,
                    ),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    self._description,
                )
            painter.restore()

        # ---- 5) disabled 蒙层（wrapper 也半透明）----
        if self._is_disabled:
            # 上面文字已带 0.5；wrapper / control 在 paint 时未单独处理，
            # 通过 setEnabled(False) 失去交互；视觉上给整体一个 0.6 蒙层
            painter.save()
            painter.setOpacity(0.4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(127, 127, 127, 0))  # 占位
            painter.restore()

        painter.end()

    # ============================================================
    # 工具
    # ============================================================
    @staticmethod
    def _lerp(a: int, b: int, t: float) -> int:
        return max(0, min(255, int(round(a + (b - a) * t))))

    # ============================================================
    # 公共 API（运行时切换）
    # ============================================================
    def set_color(self, color: str):
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        self._color = color
        self.update()

    def set_size(self, size: str):
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        self._size = size
        self._refresh_geometry()

    def set_description(self, description: str):
        self._description = description
        self._refresh_geometry()

    def description(self) -> str:
        return self._description

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        self.setEnabled(not disabled)
        self.update()

    def set_is_invalid(self, invalid: bool):
        self._is_invalid = invalid
        self.update()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = disable

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

    def is_selected(self) -> bool:
        return self.isChecked()

    def set_is_selected(self, selected: bool):
        self.setChecked(selected)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str):
        self._value = value
