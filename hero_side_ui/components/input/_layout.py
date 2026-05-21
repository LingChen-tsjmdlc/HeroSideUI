"""Input 组件的几何/layout/label-位置 mixin（私有）。

负责：
- label_placement 切换时的 layout 重排
- inside-label 的浮起动画几何同步
- underline bar 的位置同步
- resize 事件下的重排
"""

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import QSizePolicy

from ...core import make_text_qfont
from ...themes import HEROUI_COLORS, INPUT_SIZES


class _InputLayoutMixin:
    """Input 的 layout / 几何 mixin。"""

    # ------------------------------------------------------------
    # label 位置切换
    # ------------------------------------------------------------
    def _relayout_for_label_placement(self):
        """根据 label_placement 切换 inside / outside / outside-top / outside-left 的 label 显隐

        - inside: 浮动 label（_inside_label），浮起终点在 inputWrapper 内顶部
        - outside: 浮动 label（_inside_label），浮起终点在 inputWrapper 上方外部（飞出 wrapper）
        - outside-top: 静态 label（_outside_label），始终固定在 inputWrapper 上方
        - outside-left: 静态 label（_outside_left_label），固定在 inputWrapper 左侧
        """
        has_label = self._has_label()

        # 默认全部隐藏
        self._outside_label.setVisible(False)
        self._outside_left_label.setVisible(False)
        self._inside_label.setVisible(False)

        # outside-left 使用横向行布局，其他使用竖向
        self._outside_left_row.setContentsMargins(0, 0, 0, 0)

        if self._label_placement == "outside-top" and has_label:
            # 静态 label 在上方
            self._outside_label.setVisible(True)
        elif self._label_placement == "outside-left" and has_label:
            self._outside_left_label.setVisible(True)
        elif self._label_placement in ("inside", "outside") and has_label:
            # inside 与 outside 都用浮动 label 动画，差别只在浮起终点
            self._inside_label.setVisible(True)

    def _reposition_inside_label(self):
        """手动摆放浮动 label 的位置（根据当前动画 progress）

        用于 inside 和 outside 两种 placement。
        """
        if not self._has_label() or self._label_placement not in ("inside", "outside"):
            return

        progress = self._label_anim._progress
        self._apply_label_progress(progress)

    def _apply_label_progress(self, progress: float):
        """根据 progress 插值 label 的 geometry / fontSize / color

        label 的 parent 是 Input 根控件，坐标需基于 Input 根容器。
        resting: label 位于 inputWrapper 垂直中心（模拟 placeholder 位置）
        floated:
            - inside:  label 飞到 inputWrapper 内部左上角
            - outside: label 飞出 inputWrapper 到达 Input 根顶部（在 wrapper 上方外部）
        """
        size_config = INPUT_SIZES.get(self._size, INPUT_SIZES["md"])

        f_rest = size_config["label_font_size"]
        f_float = size_config["label_float_font_size"]
        font_size = f_rest + (f_float - f_rest) * progress

        # 字体应用：走 Text/FontProvider 同源，保证全局换字体时跟随。
        # 按 progress 阔作中间跳阶 weight：<=0.5 normal，>0.5 medium。
        weight = "medium" if progress > 0.5 else "normal"
        font = make_text_qfont(int(round(font_size)), weight)
        self._inside_label.setFont(font)
        self._inside_label.adjustSize()

        # ---- 定位 ----
        # wrapper 在 Input 根坐标系中的位置
        # （wrapper 的 parent 可能是 outside_left_row，不一定是 self，所以需要 mapTo）
        from PySide6.QtCore import QPoint

        wrapper_pos_in_self = self._wrapper.mapTo(self, QPoint(0, 0))
        wrapper_x = wrapper_pos_in_self.x()
        wrapper_y = wrapper_pos_in_self.y()
        wrapper_w = self._wrapper.width()
        wrapper_h = self._wrapper.height()

        # wrapper 内部 padding（用于决定 label 在 wrapper 内部的对齐基点）
        pad_x = size_config["padding_x"]
        if self._variant == "underlined":
            pad_x = 4

        label_h = self._inside_label.height()

        # resting: label 在 wrapper 垂直中心、水平贴 wrapper 左 padding（像 placeholder 位置）
        x_rest = wrapper_x + pad_x
        y_rest = wrapper_y + (wrapper_h - label_h) // 2

        # floated 终点
        if self._label_placement == "outside":
            # outside: label 飞出 wrapper 到上方外部（Input 根坐标系下 y < wrapper_y）
            # 终点 y = 0（Input 根顶部），x = 0（贴左）
            x_float = 0
            # 让 label 底端稍微贴近 wrapper 顶（留 2px 间隙）
            y_float = max(0, wrapper_y - label_h - 2)
        else:
            # inside: label 浮到 wrapper 内部左上角（跟 line_edit 左对齐，距 wrapper 顶有呼吸间隙）
            # label_float_x/y 是相对 wrapper 内部 padding 起点的偏移
            x_float = wrapper_x + pad_x + size_config.get("label_float_x", 0)
            y_float = wrapper_y + size_config.get("label_float_y", 6)

        x = int(x_rest + (x_float - x_rest) * progress)
        y = int(y_rest + (y_float - y_rest) * progress)

        self._inside_label.move(x, y)
        self._inside_label.raise_()

        # 颜色插值
        c1 = self._label_color_resting
        c2 = self._label_color_floated
        r = int(c1.red() + (c2.red() - c1.red()) * progress)
        g = int(c1.green() + (c2.green() - c1.green()) * progress)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * progress)

        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        self._inside_label.setTextFormat(Qt.TextFormat.RichText)
        self._inside_label.setText(
            f"<span style='color:rgb({r},{g},{b});'>{self._label_text}</span>{req_mark}"
        )
        self._inside_label.adjustSize()

    def _on_label_progress(self, progress: float):
        """LabelFloatAnimation 的回调"""
        self._apply_label_progress(progress)

    # ------------------------------------------------------------
    # underline 摆放
    # ------------------------------------------------------------
    def _reposition_underline(self):
        if self._variant != "underlined":
            return
        w = self._wrapper.width()
        h = self._wrapper.height()
        self._underline.setGeometry(0, h - 2, w, 2)
        self._underline.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_underline()
        self._reposition_inside_label()

    def showEvent(self, event):
        super().showEvent(event)
        # 首次显示后再摆放一次，因为构造期 geometry 尚未生效
        self._reposition_inside_label()
        self._reposition_underline()
