"""Input 组件的样式计算与应用 mixin（私有）。

把 _apply_styles 及其辅助颜色解析方法（约 500 行）从主组件文件抽出，
让 input.py 专注于 API + 编排，本文件专注于"如何根据 variant/color/size/theme/state
推导出每个子部件的 QSS / 字色 / 边框"。
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QLabel, QSizePolicy

from ...themes import FONT_FAMILY, HEROUI_COLORS, INPUT_SIZES, RADIUS
from ...utils import hex_to_rgba, load_svg_icon


class _InputStylingMixin:
    """Input 的样式 mixin（参见模块 docstring）。"""

    # ============================================================
    # 样式应用
    # ============================================================
    def _apply_styles(self):
        """计算并应用全部样式"""
        is_dark = self._theme == "dark"
        size_config = INPUT_SIZES.get(self._size, INPUT_SIZES["md"])
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 根控件 ----
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 禁用整体半透明
        if self._is_disabled:
            self.setGraphicsEffect(None)  # 清除
            self.setStyleSheet("QWidget#heroInput { color: palette(disabled); }")
        else:
            self.setStyleSheet("")

        # ---- inputWrapper 高度 ----
        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()
        height = size_config["inside_height"] if is_inside else size_config["height"]
        self._wrapper.setFixedHeight(height)

        # ---- 最小宽度 ----
        min_w = size_config.get("min_width", 260)
        self.setMinimumWidth(min_w)
        self._wrapper.setMinimumWidth(min_w)

        # ---- Input 根容器: outside 模式下给顶部预留空间作为浮出 label 的落脚处 ----
        if is_outside_float:
            top_reserve = size_config["label_float_font_size"] + 6
            self._root.setContentsMargins(0, top_reserve, 0, 0)
        else:
            self._root.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper padding ----
        pad_x = size_config["padding_x"]
        pad_y = size_config["padding_y"] if not is_inside else size_config["inside_padding_y"]
        if self._radius == "full":
            pad_x += 4
        # underlined 特殊 padding
        if self._variant == "underlined":
            self._wrapper.layout().setContentsMargins(4, 0, 4, 0)
        else:
            self._wrapper.layout().setContentsMargins(pad_x, pad_y, pad_x, pad_y)

        # ---- innerWrapper: inside 模式下给输入文字上方留出浮起 label 的空间 ----
        # 这样输入的文字会被挤到下半部分，与浮起的 label 有视觉呼吸感
        # outside 模式下 label 浮到 wrapper 外部，不占 wrapper 内部空间，无需预留
        if is_inside:
            top_space = size_config["inside_input_top_space"]
            self._inner_layout.setContentsMargins(0, top_space, 0, 0)
            # ★ start/end content 图标与 clear button 也一起下移，与输入文字水平对齐
            # 否则它们会居中于整个高高度 wrapper，相对输入文字显得偏上
            self._start_slot_layout.setContentsMargins(0, top_space, 0, 0)
            self._end_slot_layout.setContentsMargins(0, top_space, 0, 0)
            # clear 按钮没有自己的 layout，用 contentsMargins 直接设
            self._clear_btn.setContentsMargins(0, top_space, 0, 0)
        else:
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._start_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._end_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._clear_btn.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper 背景/边框/圆角 (手绘 + 150ms 过渡) ----
        bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color = \
            self._resolve_wrapper_colors(is_dark, colors, dc)

        # 根据当前 hover/focus 状态选色
        if self._is_focused:
            cur_bg = bg_focus
            cur_border = border_focus
        elif self._is_hover:
            cur_bg = bg_hover
            cur_border = border_hover
        else:
            cur_bg = bg
            cur_border = border_color

        # 圆角解析
        radius_px_str = self._resolve_radius(size_config)
        # 从字符串 "8px" 解析成 int
        try:
            radius_px = int(radius_px_str.replace("px", ""))
        except Exception:
            radius_px = 8

        bw = size_config["border_width"]

        # 首次应用（构造期）不要用动画，避免从全透明淡入
        animate = getattr(self, "_styles_applied_once", False)

        if self._variant == "underlined":
            # underlined: 透明背景 + 底部 2px 分割线
            base_line_color = dc[700] if is_dark else dc[200]
            hover_line_color = dc[600] if is_dark else dc[300]
            cur_bottom = hover_line_color if self._is_hover else base_line_color

            self._wrapper.set_static(border_width=0, radius_px=0, show_bottom_line=True)
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(self._qcolor(cur_bottom), animate=animate)

            # 聚焦色的下划线由 UnderlineBar 覆盖绘制
            self._underline.set_color(QColor(main_color))
            self._underline.show()

        elif self._variant == "flat":
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        elif self._variant == "faded":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        elif self._variant == "bordered":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            # bordered 背景透明
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        else:
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        # 标记首次应用已完成，后续切换都走动画
        self._styles_applied_once = True

        # ---- line_edit 样式 ----
        fg_color, placeholder_color = self._resolve_input_text_color(is_dark, colors, dc)
        self.line_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {fg_color};
                font-family: {FONT_FAMILY};
                font-size: {size_config['input_font_size']}px;
                selection-background-color: {colors[200]};
                padding: 0;
            }}
            """
        )
        # 占位符颜色 + 保持 Base 透明（防止 Fusion 覆盖画白色背景）
        pal = self.line_edit.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_color))
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.line_edit.setPalette(pal)

        # ---- 禁用态 ----
        if self._is_disabled:
            self.line_edit.setEnabled(False)
            self._wrapper.setEnabled(False)
            op = QGraphicsOpacityEffect(self)
            op.setOpacity(0.5)
            self.setGraphicsEffect(op)
        else:
            self.line_edit.setEnabled(True)
            self._wrapper.setEnabled(True)
            self.setGraphicsEffect(None)

        # ---- Label 配色 ----
        self._label_color_resting = QColor(
            self._resolve_label_resting_color(is_dark, colors, dc)
        )
        self._label_color_floated = QColor(
            self._resolve_label_floated_color(is_dark, colors, dc)
        )

        # ---- outside label ----
        outside_label_font = size_config["outside_label_font_size"]
        outside_qss = (
            f"QLabel {{ color: {self._label_color_floated.name()}; "
            f"font-family: {FONT_FAMILY}; font-size: {outside_label_font}px; "
            f"font-weight: 500; }}"
        )
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"

        display_label = self._label_text + req_mark if self._label_text else ""
        self._outside_label.setText(display_label)
        self._outside_label.setStyleSheet(outside_qss)
        self._outside_left_label.setText(display_label)
        self._outside_left_label.setStyleSheet(outside_qss)

        # ---- 内部 label 字号 ----
        self._inside_label.setStyleSheet(
            f"QLabel {{ background: transparent; font-family: {FONT_FAMILY}; }}"
        )

        # ---- start/end icon ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- clear button icon ----
        if self._is_clearable:
            ic_size = size_config["clear_icon_size"]
            ic_color = QColor(dc[400] if is_dark else dc[500])
            pix = load_svg_icon(
                "heroicons--x-circle-solid", size=ic_size, color=ic_color
            )
            self._clear_btn.setIcon(pix)
            self._clear_btn.setIconSize(QSize(ic_size, ic_size))
            self._clear_btn.setFixedSize(ic_size + 4, ic_size + 4)
            self._clear_btn.setVisible(True)  # 仅控制 opacity，不 hide widget
        else:
            self._clear_btn.hide()

        # ---- helper ----
        helper_font = size_config["helper_font_size"]
        if self._is_invalid and self._error_message:
            self._helper_label.setText(self._error_message)
            self._helper_label.setStyleSheet(
                f"QLabel {{ color: {HEROUI_COLORS['danger'][500]}; "
                f"font-family: {FONT_FAMILY}; font-size: {helper_font}px; }}"
            )
            self._helper_label.show()
        elif self._description:
            self._helper_label.setText(self._description)
            desc_color = dc[400] if is_dark else dc[500]
            self._helper_label.setStyleSheet(
                f"QLabel {{ color: {desc_color}; "
                f"font-family: {FONT_FAMILY}; font-size: {helper_font}px; }}"
            )
            self._helper_label.show()
        else:
            self._helper_label.hide()

        # ---- 重新摆放 label 位置 ----
        self._relayout_for_label_placement()
        self._reposition_inside_label()
        self._reposition_underline()

    # ------------------------------------------------------------
    # 颜色决策
    # ------------------------------------------------------------
    def _flat_bg_colors(self, is_dark: bool, colors: dict, dc: dict):
        """抽离 flat 变体的三态底色，供 faded(底色) / bordered(默认边框) 复用。

        ★ HeroSideUI 规则：
        - 亮色主题 hover/focus: 朝"压暗"方向走（色阶数字变大，颜色变深）
          resting {color}-100 → hover {color}-200 → focus {color}-200
          default: resting default-100 → hover default-200 → focus default-200
        - 暗色主题 hover/focus: 朝"提亮"方向走（透明度增加，看起来更亮）
          resting rgba({color}, 0.15) → hover rgba({color}, 0.25) → focus rgba({color}, 0.25)
          default: resting default-800 → hover default-700 → focus default-700

        返回 (bg, bg_hover, bg_focus)。
        """
        is_default = self._color == "default"
        if is_default:
            if is_dark:
                # 暗色 default: 提亮（800 → 700）
                bg = dc[800]
                bg_hover = dc[700]
                bg_focus = dc[700]
            else:
                # 亮色 default: 压暗（100 → 200）
                bg = dc[100]
                bg_hover = dc[200]
                bg_focus = dc[200]
        else:
            if is_dark:
                # 暗色有色: 提亮（透明度增加）
                bg = hex_to_rgba(colors[500], 0.15)
                bg_hover = hex_to_rgba(colors[500], 0.25)
                bg_focus = hex_to_rgba(colors[500], 0.25)
            else:
                # 亮色有色: 压暗（100 → 200）
                bg = colors[100]
                bg_hover = colors[200]
                bg_focus = colors[200]
        return bg, bg_hover, bg_focus

    def _resolve_wrapper_colors(self, is_dark: bool, colors: dict, dc: dict):
        """返回 (bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color)

        HeroSideUI 自定义规则（对 HeroUI 的偏离）:
        - flat: 同 HeroUI —— 浅彩/浅灰底，hover/focus 略变化。无边框。
        - faded: **底色使用 flat 的底色**（不再是固定灰 default-100）；
                 边框行为保留 —— 默认灰，hover/focus 变主色（default 时变 default-400）
        - bordered: **默认边框 = flat 的底色**（浅彩或浅灰），透明背景；
                    hover 边框变 {color}-400（暗色 -600），
                    focus 边框变 {color}-500（暗色保持 -500）。default 时 hover→500 focus→900/50。
        - underlined: 透明底 + 底部 2px 线（hover 变浅灰），focus 时底部 after 彩条展开。
        """
        is_default = self._color == "default"
        # 主色: 用于 focus 边框 / underlined after / label
        main_color = colors[500] if not is_default else (dc[50] if is_dark else dc[900])

        if self._variant == "flat":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        elif self._variant == "faded":
            # ★ 偏离 HeroUI: 底色使用 flat 的底色（而不是固定灰 default-100）
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            # ★ 默认边框: 比底色"深一档"，仍在同色色板范围内，使边框能隐约看出
            #   亮色: 底 {color}-100 → 边 {color}-200 (或 default-200)
            #   暗色: 底是半透明主色 → 边用色板里更可见的一档 ({color}-700 / default-700)
            if is_default:
                default_border = dc[700] if is_dark else dc[200]
            else:
                # 有色情况：取同色系比底色深一档
                default_border = colors[700] if is_dark else colors[200]
            # hover / focus 过渡
            default_border_hover = dc[500] if is_dark else dc[400]
            border = default_border
            border_color = default_border
            if is_default:
                border_hover = default_border_hover
                border_focus = default_border_hover
            else:
                border_hover = colors[500]
                border_focus = colors[500]

        elif self._variant == "bordered":
            # ★ 偏离 HeroUI: 默认边框 = flat 的底色；
            #   边框的归宿就是 500 主色，hover/focus 都会变主色
            #   亮色: hover {color}-400 (比 500 亮一档) → focus {color}-500
            #   暗色: hover {color}-600 (比 500 深一档) → focus {color}-500
            flat_bg, _, _ = self._flat_bg_colors(is_dark, colors, dc)
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = flat_bg           # 默认: flat 底色
            border_color = flat_bg
            if is_default:
                # default 色: hover default-400, focus default-500
                border_hover = dc[400]
                border_focus = dc[500]
            else:
                if is_dark:
                    border_hover = colors[600]
                    border_focus = colors[500]
                else:
                    border_hover = colors[400]
                    border_focus = colors[500]

        else:  # underlined
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        # isInvalid 覆盖
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            main_color = d[500]
            if self._variant == "flat":
                bg = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
                bg_hover = hex_to_rgba(d[500], 0.25) if is_dark else d[100]
                bg_focus = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
            elif self._variant == "bordered":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]
            elif self._variant == "faded":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]

        return bg, border, border_color, bg_hover, bg_focus, border_hover, border_focus, main_color

    def _resolve_input_text_color(self, is_dark: bool, colors: dict, dc: dict):
        """返回 (fg_color, placeholder_color)"""
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return (
                d[400] if is_dark else d[500],
                d[400] if is_dark else d[500],
            )

        # flat 有色变体：文字跟随主色（HeroUI: text-{color}-600 / dark:text-{color}）
        if self._variant == "flat" and self._color != "default":
            if self._color in ("success", "warning"):
                fg = colors[500] if is_dark else colors[600]
                ph = colors[500] if is_dark else colors[600]
            elif self._color == "danger":
                fg = colors[500] if is_dark else colors[500]
                ph = colors[500] if is_dark else colors[500]
            else:  # primary / secondary
                fg = colors[400] if is_dark else colors[500]
                ph = colors[400] if is_dark else colors[500]
            return fg, ph

        # 默认
        fg = dc[100] if is_dark else dc[900]
        ph = dc[400] if is_dark else dc[500]
        return fg, ph

    def _resolve_label_resting_color(self, is_dark: bool, colors: dict, dc: dict) -> str:
        """未浮动时 label 颜色 — HeroUI 默认 text-foreground-500"""
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        return dc[400] if is_dark else dc[500]

    def _resolve_label_floated_color(self, is_dark: bool, colors: dict, dc: dict) -> str:
        """浮动后（聚焦/有值）label 颜色"""
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        # 有色变体: label 跟主色
        if self._color != "default":
            if self._variant == "flat" and self._color in ("success", "warning"):
                return colors[500] if is_dark else colors[600]
            return colors[500] if not is_dark else colors[400]
        # default: 聚焦时变深
        return dc[100] if is_dark else dc[900]

    # ------------------------------------------------------------
    # 圆角
    # ------------------------------------------------------------
    def _resolve_radius(self, size_config: dict) -> str:
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            h = size_config["height"]
            return f"{h // 2}px"
        return RADIUS.get(radius_key, RADIUS["md"])

    # ------------------------------------------------------------
    # start / end content (图标 or 自定义 widget)
    # ------------------------------------------------------------
    def _render_adornment_icons(self, is_dark, colors, dc, size_config):
        """渲染 start_content / end_content 到对应槽位。

        content 规则：
            - None：隐藏槽位
            - str：当作图标名/SVG 路径，渲染为图标。如果同时有 on_*_click，则包成可点击按钮
            - QWidget：直接放入槽位（当作用户自定义组件，比如 Button）
        """
        self._fill_slot(
            slot=self._start_slot,
            slot_layout=self._start_slot_layout,
            content=self._start_content,
            on_click=self._on_start_click,
            icon_size=size_config["start_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )
        self._fill_slot(
            slot=self._end_slot,
            slot_layout=self._end_slot_layout,
            content=self._end_content,
            on_click=self._on_end_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )

    def _fill_slot(self, slot, slot_layout, content, on_click, icon_size, is_dark, dc):
        """把 content 填充到 slot 容器中。"""
        # 先清空槽位里"我们自己创建的"widget（不删除用户外部 widget，只 takeAt）
        while slot_layout.count():
            item = slot_layout.takeAt(0)
            w = item.widget()
            if w is None:
                continue
            # 如果是我们内部创建的图标 label / 按钮，安全删除
            if w.property("_hs_internal") is True:
                w.deleteLater()
            else:
                # 用户 widget，只从布局里移除，reparent 到 None
                w.setParent(None)

        if content is None:
            slot.hide()
            return

        # content 是 QWidget（用户塞进来的自定义组件）
        if isinstance(content, QWidget):
            slot_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignVCenter)
            # setParent(None) / reparent 后 widget 默认 hidden，必须显式 show
            # 否则用户传进来的 QWidget 根本不会显示（这是 QWidget 的默认行为，
            # 调用方无感知）
            content.show()
            slot.show()
            return

        # content 是字符串：图标名 / SVG 路径
        icon_color = QColor(dc[400] if is_dark else dc[500])
        pix = load_svg_icon(str(content), size=icon_size, color=icon_color)

        if on_click is not None:
            # 包成可点击按钮
            btn = QPushButton()
            btn.setProperty("_hs_internal", True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(pix)
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setFixedSize(icon_size + 4, icon_size + 4)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; padding: 0; }"
            )
            btn.clicked.connect(on_click)
            slot_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            # 静态图标
            lbl = QLabel()
            lbl.setProperty("_hs_internal", True)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl.setFixedSize(icon_size, icon_size)
            lbl.setPixmap(pix)
            slot_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        slot.show()

