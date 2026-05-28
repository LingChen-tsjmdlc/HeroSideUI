"""HeroSideUI Radio Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/radio.ts
组件来源: https://github.com/heroui-inc/heroui/tree/main/packages/components/radio

结构 (slots):
    Radio (继承 RadioBase → QAbstractButton)
        ├── wrapper  (外圈圆环，带边框)
        ├── control  (内圆点，选中时缩放+透明度过渡)
        └── labelWrapper
            ├── label        (children/text)
            └── description  (副文本)

特性对齐 HeroUI:
    - 6 种颜色 / 3 种尺寸 / hover bg / press scale / control 过渡 / disabled / invalid
    - 双 variant：default（圆点 radio）+ card（卡片选择器，对齐 v2 Custom Styles 示例）
"""

from typing import Optional

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget

from ...core import make_text_qfont
from ...themes import HEROUI_COLORS
from ._base import RadioBase, VALID_COLORS, VALID_SIZES, VALID_VARIANTS


class Radio(RadioBase):
    """HeroUI 风格的 Radio 组件

    单选 wrapper —— 配合 RadioGroup 使用时由 group 互斥；独立使用时
    setCheckable(True) 即可像普通按钮那样 toggle。

    variant:
        "default" — 经典圆点 radio（label 在右）
        "card"    — 卡片式选择器（label 在左，圆点在右，对齐 HeroUI v2 Custom Styles）
    """

    def __init__(
        self,
        text: str = "",
        value: Optional[str] = None,
        description: str = "",
        is_selected: bool = False,
        color: str = "primary",
        size: str = "md",
        variant: str = "default",
        is_disabled: bool = False,
        is_invalid: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            text=text,
            value=value,
            description=description,
            is_selected=is_selected,
            color=color,
            size=size,
            variant=variant,
            is_disabled=is_disabled,
            is_invalid=is_invalid,
            disable_animation=disable_animation,
            theme=theme,
            parent=parent,
        )

    # ============================================================
    # 字体
    # ============================================================
    def _label_font(self) -> QFont:
        cfg = self._size_config()
        return make_text_qfont(cfg["label_font_size"], "normal")

    def _desc_font(self) -> QFont:
        cfg = self._size_config()
        return make_text_qfont(cfg["desc_font_size"], "normal")

    # ============================================================
    # 几何
    # ============================================================
    def _refresh_geometry(self):
        self.setFont(self._label_font())
        super()._refresh_geometry()

    def sizeHint(self) -> QSize:
        if self._variant == "card":
            return self._card_size_hint()
        return self._default_size_hint()

    def _default_size_hint(self) -> QSize:
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

    def _card_size_hint(self) -> QSize:
        cfg = self._size_config()
        wrapper = cfg["wrapper"]
        pad = cfg["card_padding"]
        gap = cfg["card_gap"]
        max_w = cfg["card_max_width"]

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
        # 卡片宽 = padding + text + gap + wrapper + padding，但不超过 max_width
        natural_w = pad + text_w + gap + wrapper + pad
        total_w = min(natural_w, max_w)
        total_h = pad + max(text_h, wrapper) + pad
        return QSize(total_w, total_h)

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

    def _card_palette(self):
        """卡片变体专用：底色 / 边框 / hover 底色"""
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["primary"])

        # bg-content1 ≈ default-50（亮）/ default-900（暗）
        card_bg = QColor("#ffffff" if not is_dark else dc[900])
        # hover: bg-content2 ≈ default-100 / default-800
        card_bg_hover = QColor(dc[100] if not is_dark else dc[800])
        # 透明边框默认；选中时使用主色
        if self._color == "default":
            selected_border = QColor(dc[300] if is_dark else dc[500])
        else:
            selected_border = QColor(colors[500])
        if self._is_invalid:
            selected_border = QColor(HEROUI_COLORS["danger"][500])
        return card_bg, card_bg_hover, selected_border

    # ============================================================
    # paintEvent — 完整自绘
    # ============================================================
    def paintEvent(self, event):
        if self._variant == "card":
            self._paint_card()
        else:
            self._paint_default()

    # ----------------------------------------------------------------
    # 默认 variant
    # ----------------------------------------------------------------
    def _paint_default(self):
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

        rect = self.rect()
        pad_x = 4
        box_x = pad_x
        box_y = (rect.height() - wrapper_size) // 2
        cx = box_x + wrapper_size / 2.0
        cy = box_y + wrapper_size / 2.0

        # 按压缩放 (scale-95)
        press_scale = 1.0 - 0.05 * self._press_progress
        if press_scale < 1.0:
            painter.save()
            painter.translate(cx, cy)
            painter.scale(press_scale, press_scale)
            painter.translate(-cx, -cy)

        is_selected = self.isChecked()

        # hover 内底色（仅未选中时显示）
        if self._hover and not is_selected and not self._is_disabled:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(hover_bg)
            painter.drawEllipse(QRectF(box_x, box_y, wrapper_size, wrapper_size))
            painter.restore()

        # wrapper 边框（圆环），选中时颜色随 progress 渐变
        cp = self._control_progress
        if is_selected:
            r = self._lerp(border_color.red(), selected_border.red(), cp)
            g = self._lerp(border_color.green(), selected_border.green(), cp)
            b = self._lerp(border_color.blue(), selected_border.blue(), cp)
            ring = QColor(r, g, b)
        else:
            ring = border_color

        painter.save()
        painter.setPen(QPen(ring, bw))
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

        # 内圆点 control（scale 0 → 1 + opacity 0 → 1）
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

        # labelWrapper：label + description
        if self.text() or self._description:
            text_x = box_x + wrapper_size + gap
            label_fm = QFontMetrics(self._label_font())
            desc_fm = QFontMetrics(self._desc_font())
            label_h = label_fm.height() if self.text() else 0
            desc_h = desc_fm.height() if self._description else 0
            block_h = label_h + desc_h
            text_top = (rect.height() - block_h) // 2

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

        painter.end()

    # ----------------------------------------------------------------
    # card variant —— 对齐 HeroUI v2 Custom Styles 示例
    # 卡片底 + label 左侧（label 上、description 下）+ 圆点右侧；
    # 选中时边框变主色；hover 时切换底色。
    # ----------------------------------------------------------------
    def _paint_card(self):
        cfg = self._size_config()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        (
            ring_default,
            ring_selected,
            control_color,
            _,
            label_color,
            desc_color,
        ) = self._palette()
        card_bg, card_bg_hover, card_selected_border = self._card_palette()

        wrapper_size = cfg["wrapper"]
        control_size = cfg["control"]
        ring_bw = cfg["border_width"]
        card_bw = cfg["card_border_width"]
        radius = cfg["card_radius"]
        pad = cfg["card_padding"]

        rect = self.rect()
        cp = self._control_progress
        is_selected = self.isChecked()

        # 按压缩放
        press_scale = 1.0 - 0.03 * self._press_progress
        cx_total = rect.width() / 2.0
        cy_total = rect.height() / 2.0
        if press_scale < 1.0:
            painter.save()
            painter.translate(cx_total, cy_total)
            painter.scale(press_scale, press_scale)
            painter.translate(-cx_total, -cy_total)

        # ---- 1) 卡片底（圆角矩形 + 边框）----
        painter.save()
        if self._is_disabled:
            painter.setOpacity(0.5)
        bg = card_bg_hover if (self._hover and not self._is_disabled) else card_bg
        # 边框：未选中=透明（与 bg 同色避免突兀），选中=主色
        if is_selected:
            r = self._lerp(bg.red(), card_selected_border.red(), cp)
            g = self._lerp(bg.green(), card_selected_border.green(), cp)
            b = self._lerp(bg.blue(), card_selected_border.blue(), cp)
            border = QColor(r, g, b)
        else:
            border = bg
        painter.setBrush(bg)
        painter.setPen(QPen(border, card_bw))
        half = card_bw / 2.0
        painter.drawRoundedRect(
            QRectF(
                half,
                half,
                rect.width() - card_bw,
                rect.height() - card_bw,
            ),
            radius,
            radius,
        )
        painter.restore()

        # ---- 2) 圆点 wrapper —— 卡片右侧垂直居中 ----
        box_x = rect.width() - pad - wrapper_size
        box_y = (rect.height() - wrapper_size) // 2
        cx = box_x + wrapper_size / 2.0
        cy = box_y + wrapper_size / 2.0

        painter.save()
        if self._is_disabled:
            painter.setOpacity(0.5)
        # 圆环
        if is_selected:
            r = self._lerp(ring_default.red(), ring_selected.red(), cp)
            g = self._lerp(ring_default.green(), ring_selected.green(), cp)
            b = self._lerp(ring_default.blue(), ring_selected.blue(), cp)
            ring = QColor(r, g, b)
        else:
            ring = ring_default
        painter.setPen(QPen(ring, ring_bw))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rh = ring_bw / 2.0
        painter.drawEllipse(
            QRectF(
                box_x + rh,
                box_y + rh,
                wrapper_size - ring_bw,
                wrapper_size - ring_bw,
            )
        )
        # 内圆点
        if cp > 0.001:
            painter.save()
            painter.setOpacity(cp * (0.5 if self._is_disabled else 1.0))
            painter.translate(cx, cy)
            painter.scale(cp, cp)
            painter.translate(-cx, -cy)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(control_color)
            r2 = control_size / 2.0
            painter.drawEllipse(QRectF(cx - r2, cy - r2, control_size, control_size))
            painter.restore()
        painter.restore()

        # ---- 3) label / description —— 卡片左侧 ----
        if self.text() or self._description:
            text_x = pad
            text_right = box_x - pad  # 右边界（不挤到圆点）
            label_fm = QFontMetrics(self._label_font())
            desc_fm = QFontMetrics(self._desc_font())
            label_h = label_fm.height() if self.text() else 0
            desc_h = desc_fm.height() if self._description else 0
            block_h = label_h + desc_h
            text_top = (rect.height() - block_h) // 2

            painter.save()
            if self._is_disabled:
                painter.setOpacity(0.5)

            if self.text():
                painter.setPen(QPen(label_color))
                painter.setFont(self._label_font())
                painter.drawText(
                    QRectF(text_x, text_top, max(0, text_right - text_x), label_h),
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
                        max(0, text_right - text_x),
                        desc_h,
                    ),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    self._description,
                )
            painter.restore()

        if press_scale < 1.0:
            painter.restore()

        painter.end()

    # ============================================================
    # 工具
    # ============================================================
    @staticmethod
    def _lerp(a: int, b: int, t: float) -> int:
        return max(0, min(255, int(round(a + (b - a) * t))))


__all__ = ["Radio", "RadioBase", "VALID_COLORS", "VALID_SIZES", "VALID_VARIANTS"]
