"""Input 几何/label 位置 mixin：placement 切换重排、浮动动画几何同步。"""

import shiboken6
from PySide6.QtCore import QPoint, Qt

from ...core import make_text_qfont
from ...themes import HEROUI_COLORS, INPUT_SIZES


class _InputLayoutMixin:
    """Input 的 layout / 几何 mixin。"""

    def _size_config(self) -> dict:
        """取当前尺寸档 token 表。

        Returns:
            INPUT_SIZES 中的配置字典；复用方可覆盖为自己的尺寸表。
        """
        return INPUT_SIZES.get(self._size, INPUT_SIZES["md"])

    # ------------------------------------------------------------
    # label 位置切换
    # ------------------------------------------------------------
    def _relayout_for_label_placement(self):
        """按 label_placement 重排四种布局的 label 显隐与位置。

        Note:
            outside-top 用上方静态 label；outside-left 用左侧静态 label；
            inside 与 outside 共用浮动 label，差别只在浮起终点。
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
        """按当前动画 progress 手动摆放浮动 label 的位置。

        Note:
            用于 inside 和 outside 两种 placement；无 label 或
            其它 placement 时直接返回。
        """
        if not self._has_label() or self._label_placement not in ("inside", "outside"):
            return

        progress = self._label_anim._progress
        self._apply_label_progress(progress)

    def _apply_label_progress(self, progress: float):
        """按进度插值 label 的 geometry / 字号 / 颜色。

        Args:
            progress: 0 为 resting（wrapper 中线），1 为 floated（浮起终点）。

        Note:
            进程退出 / 组件销毁时动画可能还剩一帧，底层 C++ 对象已析构，
            用 shiboken6.isValid 守卫掉这一帧；
            wrapper 的 parent 可能是 outside_left_row，故需 mapTo 换算。
            字重按 progress 跳阶：>0.5 medium，否则 normal。
        """
        # 进程退出 / 组件销毁时动画可能还剩一帧未跑完，此时底层 C++ 对象已析构，
        # 再访问 self._wrapper 会抛 RuntimeError。守卫掉这一帧。
        if not shiboken6.isValid(self) or not shiboken6.isValid(self._wrapper):
            return

        size_config = self._size_config()

        f_rest = size_config["label_font_size"]
        f_float = size_config["label_float_font_size"]
        font_size = f_rest + (f_float - f_rest) * progress

        # 字体应用：走 Text/FontProvider 同源，保证全局换字体时跟随。
        # 按 progress 阔作中间跳阶 weight：<=0.5 normal，>0.5 medium。
        weight = "medium" if progress > 0.5 else "normal"
        font = make_text_qfont(round(font_size), weight)
        self._inside_label.setFont(font)
        self._inside_label.adjustSize()

        # ---- 定位 ----
        # wrapper 在 Input 根坐标系中的位置
        # （wrapper 的 parent 可能是 outside_left_row，不一定是 self，所以需要 mapTo）
        wrapper_pos_in_self = self._wrapper.mapTo(self, QPoint(0, 0))
        wrapper_x = wrapper_pos_in_self.x()
        wrapper_y = wrapper_pos_in_self.y()
        self._wrapper.width()
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
        """LabelFloatAnimation 的进度回调。

        Args:
            progress: 当前动画进度 0.0 ~ 1.0。
        """
        self._apply_label_progress(progress)

    # ------------------------------------------------------------
    # underline 摆放
    # ------------------------------------------------------------
    def _reposition_underline(self):
        """把 underlined 变体的彩色展开线贴到 wrapper 底部并置顶。"""
        if self._variant != "underlined":
            return
        w = self._wrapper.width()
        h = self._wrapper.height()
        self._underline.setGeometry(0, h - 2, w, 2)
        self._underline.raise_()

    def resizeEvent(self, event):
        """尺寸变化后重摆 underline 与浮动 label。

        Args:
            event: Qt 尺寸变化事件。
        """
        super().resizeEvent(event)
        self._reposition_underline()
        self._reposition_inside_label()

    def showEvent(self, event):
        """首次显示后再摆一次，因为构造期 geometry 尚未生效。

        Args:
            event: Qt 显示事件。
        """
        super().showEvent(event)
        # 首次显示后再摆放一次，因为构造期 geometry 尚未生效
        self._reposition_inside_label()
        self._reposition_underline()
