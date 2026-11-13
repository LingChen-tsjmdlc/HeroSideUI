"""输入类组件的样式决策与应用 mixin。"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ...themes import HEROUI_COLORS, RADIUS
from ...utils import hex_to_rgba, load_svg_icon


class InputStylingMixin:
    """输入类组件的样式 mixin，依赖宿主提供的状态与子控件见包说明。"""

    # ============================================================
    # 样式应用
    # ============================================================
    def _apply_styles(self):
        """计算并应用全部样式：外框、line_edit、label、图标、clear、helper。

        Note:
            用户显式接管过宽度时释放 wrapper 的 min_width 并把内部 layout
            设为 SetNoConstraint，避免 wrapper 真实宽度超出 Input 视口被裁；
            必须用 QWidget.setMinimumWidth 而非 self.setMinimumWidth，
            后者被重写为标记 _user_width_locked 会污染守卫位。
            首次应用不走颜色补间，避免从全透明淡入。
        """
        is_dark = self._theme == "dark"
        size_config = self._size_config()
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 根控件 ----
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 禁用整体半透明
        if self._is_disabled:
            self.setGraphicsEffect(None)  # 清除
            self.setStyleSheet(f"QWidget#{self.objectName()} {{ color: palette(disabled); }}")
        else:
            self.setStyleSheet("")

        # ---- inputWrapper 高度 ----
        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()
        height = size_config["inside_height"] if is_inside else size_config["height"]
        self._wrapper.setFixedHeight(height)

        # ---- 最小宽度 ----
        # 用户调过 setFixedWidth/setMinimumWidth/setMaximumWidth/set_width
        # 即视为显式接管，避免 size_config 里的 240/260/300 反复抬高
        # minimumWidth、把 setFixedWidth(80) 这类硬约束涨破。
        # ★ 注意必须用 QWidget.setMinimumWidth，不能走 self.setMinimumWidth——
        #   后者被我们重写为"标记 _user_width_locked=True"，组件内部调用一次
        #   就会把守卫位污染掉，导致以后真的接管失效。
        from PySide6.QtWidgets import QWidget

        if not getattr(self, "_user_width_locked", False):
            min_w = size_config.get("min_width", 260)
            QWidget.setMinimumWidth(self, min_w)
            QWidget.setMinimumWidth(self._wrapper, min_w)
        else:
            # 用户接管宽度（如 setFixedWidth(80)）：必须把 wrapper 的 min_width
            # 也释放为 0，并把 wrapper 内部 layout 的 SizeConstraint 设为
            # SetMinAndMaxSize 之外的宽松值——否则 _wrapper 自己 layout 的
            # minimumSize（左右 padding 12+12 + spacing + 子控件最小宽 ≈ 100+）
            # 会让 wrapper 强守那个最小宽度，wrapper 真实宽度 > Input.width()=80，
            # wrapper 右半边超出 Input 视口被父容器 clip，于是只看到左圆右直。
            QWidget.setMinimumWidth(self._wrapper, 0)
            wrap_layout = self._wrapper.layout()
            if wrap_layout is not None:
                wrap_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

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
        (
            bg,
            _border,
            border_color,
            bg_hover,
            bg_focus,
            border_hover,
            border_focus,
            main_color,
        ) = self._resolve_wrapper_colors(is_dark, colors, dc)

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
        # 选区调色板走 core.selection_palette——与 Text 组件同源。
        # 规则：
        #   - bordered/underlined（无底色）：走 adapt，让选区色相跟 colors[500]
        #     走（彩色出 pastel 同色相，default 出浅灰，与边框/下划线同源）。
        #   - flat/faded（有底色）：一律走默认半透明 primary 蓝。
        #     彩色 variant 靠 hue 差从同色相浅底跳出来；default 也走蓝（flat 浅灰底/
        #     faded 近白底，叠浅灰 adapt 会和底色混淆，蓝色刚好跳出来）。
        from ...core import selection_palette

        theme_str = "dark" if is_dark else "light"
        if self._variant in ("bordered", "underlined"):
            sel_bg, sel_fg = selection_palette(
                theme_str,
                selection_adapts_color=True,
                text_color=QColor(colors[500]),
            )
        else:
            sel_bg, sel_fg = selection_palette(theme_str)
        sel_bg_css = (
            f"rgba({sel_bg.red()}, {sel_bg.green()}, {sel_bg.blue()}, {sel_bg.alphaF():.4f})"
        )
        sel_fg_css = sel_fg.name()
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {fg_color};
                font-size: {size_config["input_font_size"]}px;
                selection-background-color: {sel_bg_css};
                selection-color: {sel_fg_css};
                padding: 0;
            }}
            """)
        # 字体走 Text 同源：font-family 不再在 QSS 写，避免二元源。
        from ...core import make_text_qfont

        self.line_edit.setFont(make_text_qfont(size_config["input_font_size"], "normal"))
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
        self._label_color_resting = QColor(self._resolve_label_resting_color(is_dark, colors, dc))
        self._label_color_floated = QColor(self._resolve_label_floated_color(is_dark, colors, dc))

        # ---- outside label ----
        outside_label_font = size_config["outside_label_font_size"]
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"

        display_label = self._label_text + req_mark if self._label_text else ""
        for lbl in (self._outside_label, self._outside_left_label):
            lbl.setText(display_label)
            lbl.set_size(outside_label_font)
            lbl.set_color(self._label_color_floated.name())

        # ---- 内部 label 字号 ----
        # 颜色由 _layout._apply_label_progress() 插值后以 RichText <span> 写入；
        # 这里只需保证字体/字号不被 Text 默认覆写即可。
        self._inside_label.set_size(size_config["label_font_size"])

        # ---- start/end icon ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- clear button icon ----
        if self._is_clearable:
            ic_size = size_config["clear_icon_size"]
            ic_color = QColor(dc[400] if is_dark else dc[500])
            pix = load_svg_icon("heroicons--x-circle-solid", size=ic_size, color=ic_color)
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
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(HEROUI_COLORS["danger"][500])
            self._helper_label.show()
        elif self._description:
            self._helper_label.setText(self._description)
            desc_color = dc[400] if is_dark else dc[500]
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(desc_color)
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
        """取 flat 三态底色，供 faded / bordered 复用。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            (bg, bg_hover, bg_focus)；亮色 hover 压暗一档，
            暗色 hover 提亮（透明度 0.15→0.25）。
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
        """取全套外框颜色八元组。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            (bg, border, border_color, bg_hover, bg_focus,
            border_hover, border_focus, main_color)。

        Note:
            isInvalid 时主色与边框被 danger 覆盖；
            faded / bordered 的底色策略有意偏离 HeroUI 原生。
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
            border = flat_bg  # 默认: flat 底色
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
            elif self._variant == "bordered" or self._variant == "faded":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]

        return (
            bg,
            border,
            border_color,
            bg_hover,
            bg_focus,
            border_hover,
            border_focus,
            main_color,
        )

    def _resolve_input_text_color(self, is_dark: bool, colors: dict, dc: dict):
        """返回输入文字色与占位符色。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            (fg_color, placeholder_color)；invalid 态走 danger 色，
            有色变体文字跟主色，default 走中性黑/白。
        """
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return (
                d[400] if is_dark else d[500],
                d[400] if is_dark else d[500],
            )

        # 文字色跟随 color 主色（不区分 variant）：
        # - flat/faded 有底色：文字跟主色，与浅彩底同色相
        # - bordered/underlined 无底色：文字也跟主色，与彩色边框/下划线/选区同源
        # 仅 default 走默认黑/白（中性灰语义，没有"主色"概念）
        if self._color != "default":
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
        """未浮动时 label 颜色 —— HeroUI 默认 text-foreground-500。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典（本方法未使用）。
            dc: default 色阶字典。

        Returns:
            十六进制色串；invalid 态为 danger-500。
        """
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        return dc[400] if is_dark else dc[500]

    def _resolve_label_floated_color(self, is_dark: bool, colors: dict, dc: dict) -> str:
        """浮动后（聚焦 / 有值）label 颜色。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            十六进制色串；有色变体跟主色，default 聚焦时变深。
        """
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
        """解析外框圆角值。

        Args:
            size_config: 尺寸 token（default_radius / height / inside_height）。

        Returns:
            full 按实际生效的 wrapper 高度折算；其余取全局 RADIUS token。
        """
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            # 按实际生效的 wrapper 高度算半径（inside label 模式下高度更大）
            is_inside = self._label_placement == "inside" and self._has_label()
            h = size_config["inside_height"] if is_inside else size_config["height"]
            return f"{h // 2}px"
        return RADIUS.get(radius_key, RADIUS["md"])

    # ------------------------------------------------------------
    # start / end content (图标 or 自定义 widget)
    # ------------------------------------------------------------
    def _render_adornment_icons(self, is_dark, colors, dc, size_config):
        """渲染 start / end_content 到槽位。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。
            size_config: 尺寸 token（start/end_icon_size）。

        Note:
            content 规则：None 隐藏；str 图标名（带 on_click 时包按钮）；
            QWidget 直接放入。
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
        """把 content 填充到 slot 容器中。

        Args:
            slot: 槽位 QWidget。
            slot_layout: 槽位内部 layout。
            content: None / 图标名字符串 / 用户 QWidget。
            on_click: 图标点击回调；None 时渲染静态图标。
            icon_size: 图标边长（像素）。
            is_dark: 是否深色主题。
            dc: default 色阶字典。

        Note:
            用户 QWidget 已在槽位时跳过 teardown+rebuild，避免 FocusOut
            触发重排时 reparent 正在接收鼠标事件的按钮导致释放事件丢失；
            内部创建的 widget 带 _hs_internal 标记可安全 deleteLater。
        """
        # 用户传入的 QWidget 已经在槽位里时跳过 teardown+rebuild，
        # 避免 FocusOut 触发 _apply_styles → _fill_slot 时 reparent
        # 正在接收鼠标事件的 Button，导致 mouseReleaseEvent 丢失。
        if (
            isinstance(content, QWidget)
            and slot_layout.count() == 1
            and slot_layout.itemAt(0).widget() is content
        ):
            slot.show()
            return

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
                # 用户 widget，只从布局里移除，reparent 到 None。
                # 先 hide 再 setParent(None)，避免 detach 瞬间变顶层窗口闪原生 frame。
                w.hide()
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
            btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
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
