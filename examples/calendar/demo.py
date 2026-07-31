"""Calendar / RangeCalendar 组件演示。

分节顺序对齐官方 HeroUI Calendar 文档：
  Usage / Disabled / Read Only / Controlled / Min Date / Max Date /
  Unavailable Dates / Controlled Focused Value / Invalid Date /
  With Month And Year Picker / Custom First Day Of Week /
  Visible Months / Page Behavior / Range Calendar。
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from examples._base import DemoBase
from hero_side_ui import Body, Button, Calendar, RadioGroup, RangeCalendar
from hero_side_ui.components.calendar._date import CalendarDate


def _fmt(d: CalendarDate) -> str:
    return f"{d.year}-{d.month:02d}-{d.day:02d}"


class CalendarDemo(DemoBase):
    component_name = "Calendar"

    def _row(self, *widgets):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)
        for w in widgets:
            h.addWidget(w)
        h.addStretch()
        return row

    def build_content(self, layout: QVBoxLayout, _labels):
        today = CalendarDate.today()

        # ---------- Usage ----------
        layout.addWidget(self._section_title("Usage 基础用法"))
        layout.addWidget(self._row(Calendar(value=today)))

        # ---------- Color（HeroSideUI 扩展，官方无此分节）----------
        layout.addWidget(self._section_title("Color 颜色（HeroSideUI 扩展）"))
        color_row = QWidget()
        cr = QHBoxLayout(color_row)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.setSpacing(16)
        for c in ("foreground", "primary", "secondary", "success", "warning", "danger"):
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(6)
            bl.addWidget(Body(c))
            bl.addWidget(Calendar(value=today, color=c))
            cr.addWidget(box)
        cr.addStretch()
        layout.addWidget(color_row)

        # ---------- Disabled ----------
        layout.addWidget(self._section_title("Disabled 禁用"))
        layout.addWidget(self._row(Calendar(value=today, is_disabled=True)))

        # ---------- Read Only ----------
        layout.addWidget(self._section_title("Read Only 只读"))
        layout.addWidget(self._row(Calendar(value=today.with_fields(day=1),
                                            is_readonly=True)))

        # ---------- Controlled ----------
        layout.addWidget(self._section_title("Controlled 受控（change 信号回显）"))
        cal = Calendar(value=today)
        echo = Body(f"Selected date: {_fmt(today)}")
        cal.change.connect(lambda d: echo.setText(
            f"Selected date: {_fmt(d)}" if d else "Selected date: —"))
        layout.addWidget(self._row(cal, echo))

        # ---------- Min Date Value ----------
        layout.addWidget(self._section_title("Min Date Value 最小可选日期（今天起）"))
        layout.addWidget(self._row(Calendar(value=today, min_value=today)))

        # ---------- Max Date Value ----------
        layout.addWidget(self._section_title("Max Date Value 最大可选日期（今天止）"))
        layout.addWidget(self._row(Calendar(value=today, max_value=today)))

        # ---------- Unavailable Dates ----------
        layout.addWidget(self._section_title("Unavailable Dates 不可用日期（周末删除线）"))
        layout.addWidget(self._row(Calendar(
            value=today, is_date_unavailable=lambda d: d.weekday in (1, 7))))

        # ---------- Controlled Focused Value ----------
        layout.addWidget(self._section_title("Controlled Focused Value 受控焦点"))
        fcal = Calendar(value=today)
        finfo = Body(f"Focused: {_fmt(today)}")
        fcal.focus_change.connect(lambda d: finfo.setText(f"Focused: {_fmt(d)}"))
        layout.addWidget(self._row(fcal, finfo))

        # ---------- Invalid Date ----------
        layout.addWidget(self._section_title(
            "Invalid Date 无效日期（选到休息日才报错）"))
        inv_cal = Calendar(value=today)

        def _check_invalid(d):
            # 周末（周日=1 / 周六=7）视为无效，显示红框 + 提示
            if d and d.weekday in (1, 7):
                inv_cal.set_invalid(True, "不可选择休息日，我们休息日不上班。")
            else:
                inv_cal.set_invalid(False)

        inv_cal.change.connect(_check_invalid)
        _check_invalid(today)  # 初始按当前值判定
        layout.addWidget(self._row(inv_cal))

        # ---------- With Month And Year Picker ----------
        layout.addWidget(self._section_title("With Month And Year Picker 月/年选择器"))
        layout.addWidget(self._row(
            Calendar(show_month_and_year_pickers=True, value=today),
            Calendar(show_month_and_year_pickers=True,
                     is_header_default_expanded=True, value=today)))

        # ---------- Custom First Day Of Week ----------
        layout.addWidget(self._section_title("Custom First Day Of Week 自定义周起点"))
        layout.addWidget(self._row(
            Calendar(value=today, first_day_of_week="mon"),
            Calendar(value=today, first_day_of_week="sat")))

        # ---------- Visible Months ----------
        layout.addWidget(self._section_title("Visible Months 多月并排"))
        layout.addWidget(self._row(Calendar(value=today, visible_months=2)))
        layout.addWidget(self._row(Calendar(value=today, visible_months=3)))

        # ---------- Page Behavior ----------
        layout.addWidget(self._section_title(
            "Page Behavior 翻页行为（single=每次翻 1 月）"))
        layout.addWidget(self._row(
            Calendar(value=today, visible_months=2, page_behavior="single")))

        # ---------- Presets（top_content + bottom_content 自定义）----------
        layout.addWidget(self._section_title(
            "Presets 预设（top_content 快捷按钮 + bottom_content 精度选择）"))

        # top_content: 快捷预设按钮（平分日历宽度，标签精简以适配 256px）
        top_bar = QWidget()
        tb = QHBoxLayout(top_bar)
        tb.setContentsMargins(10, 8, 10, 4)
        tb.setSpacing(6)
        btn_today = Button("今天", variant="bordered", color="default", size="sm",
                           full_width=True)
        btn_week = Button("下周", variant="bordered", color="default", size="sm",
                          full_width=True)
        btn_month = Button("下月", variant="bordered", color="default", size="sm",
                           full_width=True)
        tb.addWidget(btn_today, 1)
        tb.addWidget(btn_week, 1)
        tb.addWidget(btn_month, 1)

        # bottom_content: 精度选择（横向单选，选项数适配日历宽度）
        bottom_bar = RadioGroup(orientation="horizontal", size="sm",
                                default_value="exact_dates")
        for label, val in (("精确", "exact_dates"), ("±1天", "1_day"),
                           ("±3天", "3_days"), ("±7天", "7_days")):
            bottom_bar.create_radio(label, val)

        presets_cal = Calendar(value=today, top_content=top_bar,
                               bottom_content=bottom_bar)
        btn_today.clicked.connect(lambda: presets_cal.set_value(today))
        btn_week.clicked.connect(lambda: presets_cal.set_value(today.add(days=7)))
        btn_month.clicked.connect(
            lambda: presets_cal.set_value(today.add(months=1).first_of_month()))
        layout.addWidget(self._row(presets_cal))

        # ---------- Range Calendar ----------
        layout.addWidget(self._section_title("Range Calendar 范围日历（两次点击选起止）"))
        rc = RangeCalendar(value=(today.with_fields(day=8), today.with_fields(day=20)))
        rng_echo = Body("")

        def _on_range(v):
            if v:
                rng_echo.setText(f"{_fmt(v[0])} ~ {_fmt(v[1])}")

        rc.change.connect(_on_range)
        if rc.value():
            rng_echo.setText(f"{_fmt(rc.value()[0])} ~ {_fmt(rc.value()[1])}")
        layout.addWidget(self._row(rc, rng_echo))
        layout.addWidget(self._row(RangeCalendar(color="success", visible_months=2)))


if __name__ == "__main__":
    CalendarDemo.run()
