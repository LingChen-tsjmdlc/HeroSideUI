"""字色调参示例的预览区：把所有读字色配置的组件按固定主题摆出来。

build_theme_panel() 返回一个带窗口底色的面板；组件都显式传 theme，所以亮色和暗色面板
可以同时放在一页里，不受应用当前主题影响。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from hero_side_ui import (
    Alert,
    Autocomplete,
    Avatar,
    Badge,
    Body,
    Button,
    Calendar,
    Caption,
    Checkbox,
    Chip,
    DateInput,
    DatePicker,
    DateRangePicker,
    Input,
    InputOtp,
    Listbox,
    NumberInput,
    Pagination,
    Popover,
    Select,
    Slider,
    Subtitle,
    Switch,
    Table,
    Tabs,
    Textarea,
    TimeInput,
    Tooltip,
)
from hero_side_ui.themes.theme_values import get_background

BUTTON_VARIANTS = ("solid", "bordered", "flat", "light", "faded", "ghost")
CHIP_VARIANTS = ("solid", "bordered", "light", "flat", "faded", "shadow", "dot")
BADGE_VARIANTS = ("solid", "flat", "faded", "shadow")
ALERT_VARIANTS = ("solid", "bordered", "flat", "faded")
FIELD_VARIANTS = ("flat", "faded", "bordered", "underlined")
LIST_VARIANTS = ("solid", "shadow", "flat", "bordered", "faded", "light")
ITEMS = [{"key": "cat", "label": "Cat"}, {"key": "dog", "label": "Dog"}]


def _grid(widgets: list[QWidget], cols: int, gap: int = 10, stretch: bool = True) -> QWidget:
    """把控件按列数排成网格。

    Args:
        widgets: 要摆的控件。
        cols: 列数。
        gap: 间距。
        stretch: 列是否等分宽度。按钮、Chip 这类"宽度就是内容宽度"的控件要传 False：
            网格里列等宽拉伸且有两行以上时，它们会被分到 QSS 的最小宽度而不是自己需要的宽度，
            文字会被截掉。
    """
    box = QWidget()
    lay = QGridLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(gap)
    for i, w in enumerate(widgets):
        lay.addWidget(w, i // cols, i % cols, Qt.AlignmentFlag.AlignTop)
    if stretch:
        for c in range(cols):
            lay.setColumnStretch(c, 1)
    else:
        lay.setColumnStretch(cols, 1)
    return box


def _section(root: QVBoxLayout, title: str, hint: str, theme: str) -> None:
    root.addSpacing(8)
    root.addWidget(Subtitle(title, theme=theme))
    if hint:
        root.addWidget(Caption(hint, theme=theme))


def _tooltip_and_popover(theme: str, color: str, keep: list) -> list[QWidget]:
    """悬停 / 点击才出现的浮层：触发按钮放进预览，浮层对象交给 keep 持有。"""
    tip_btn = Button("悬停看 Tooltip", color=color, variant="flat", theme=theme)
    tip = Tooltip(content="Tooltip 提示文字", color=color, theme=theme)
    tip.attach(tip_btn)
    pop_btn = Button("点击看 Popover", color=color, variant="flat", theme=theme)
    pop = Popover(color=color, theme=theme)
    content = QWidget()
    QVBoxLayout(content).addWidget(Body("Popover 内容", theme=theme))
    pop.set_content(content)
    pop.attach(pop_btn)
    keep.extend([tip, pop])
    return [tip_btn, pop_btn]


def build_theme_panel(theme: str, color: str, field_variant: str, keep: list) -> QWidget:
    """构造一个主题下的完整预览面板。

    Args:
        theme: "light" 或 "dark"，面板里所有组件都固定用它。
        color: 语义色名。
        field_variant: 输入框家族使用的变体（flat / faded / bordered / underlined）。
        keep: 需要由调用方持有生命周期的浮层对象（Tooltip、Popover）会追加进来。
    """
    panel = QWidget()
    panel.setObjectName("fgPanel")
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    panel.setStyleSheet(f"#fgPanel {{ background: {get_background(theme)}; }}")
    root = QVBoxLayout(panel)
    root.setContentsMargins(16, 12, 16, 16)
    root.setSpacing(6)
    root.addWidget(Subtitle("亮色" if theme == "light" else "暗色", theme=theme))
    c, fv = color, field_variant

    _section(root, "按钮", "Button：文字、悬停、禁用、图标", theme)
    buttons = [Button(v, color=c, variant=v, theme=theme) for v in BUTTON_VARIANTS]
    buttons.append(Button("disabled", color=c, variant="flat", is_disabled=True, theme=theme))
    for v in ("flat", "solid", "bordered"):
        buttons.append(
            Button(icon="heroicons--check-solid", icon_only=True, color=c, variant=v, theme=theme)
        )
    root.addWidget(_grid(buttons, 3, stretch=False))

    _section(root, "Chip / Badge", "Chip 七个变体；Badge 四个变体", theme)
    chips = [Chip(v, color=c, variant=v, theme=theme) for v in CHIP_VARIANTS]
    chips.append(Chip("closable", color=c, variant="flat", is_closable=True, theme=theme))
    root.addWidget(_grid(chips, 4, stretch=False))
    badges = [
        Badge(Avatar(name="A", theme=theme), content="5", color=c, variant=v, theme=theme)
        for v in BADGE_VARIANTS
    ]
    root.addWidget(_grid(badges, 4, stretch=False))

    _section(root, "Alert", "标题 / 说明 / 图标；关闭按钮跟图标", theme)
    for v in ALERT_VARIANTS:
        root.addWidget(
            Alert(
                title=f"Alert · {v}",
                description="说明文字 description",
                color=c,
                variant=v,
                is_closable=True,
                theme=theme,
            )
        )

    _section(root, "输入框的四种变体", "正文 / 占位符 / 浮动标签 / 说明；最后一个是出错态", theme)
    fields = [
        Input(
            label=v, placeholder="占位符", description="说明文字", color=c, variant=v, theme=theme
        )
        for v in FIELD_VARIANTS
    ]
    fields.append(
        Input(
            label="invalid",
            value="abc",
            is_invalid=True,
            error_message="错误信息",
            color=c,
            variant=fv,
            theme=theme,
        )
    )
    root.addWidget(_grid(fields, 2))

    _section(root, f"输入框家族（变体 {fv}）", "其余输入类组件用上面选中的变体", theme)
    kw = {"color": c, "variant": fv, "theme": theme}
    family = [
        Textarea(label="Textarea", placeholder="多行输入", min_rows=2, **kw),
        NumberInput(label="NumberInput", value=3, **kw),
        Select(items=ITEMS, label="Select", placeholder="请选择", **kw),
        Autocomplete(items=ITEMS, label="Autocomplete", placeholder="搜索", **kw),
        DateInput(label="DateInput", **kw),
        TimeInput(label="TimeInput", **kw),
        DatePicker(label="DatePicker", **kw),
        DateRangePicker(label="DateRangePicker", **kw),
    ]
    root.addWidget(_grid(family, 2))
    root.addWidget(InputOtp(length=4, value="12", **kw))

    _section(
        root,
        "选中态（按 solid 读，选中的用 selected）",
        "Tabs、分页、复选框、开关、头像、滑块、日历",
        theme,
    )
    row = [
        Tabs(["A", "B", "C"], color=c, theme=theme),
        Pagination(total=5, initial_page=2, color=c, theme=theme),
        Checkbox("Checkbox", is_selected=True, color=c, theme=theme),
        Switch("Switch", is_selected=True, color=c, theme=theme),
        Avatar(name="AB", color=c, theme=theme),
        Slider(value=40, label="Slider", color=c, theme=theme),
    ]
    root.addWidget(_grid(row, 2))
    root.addWidget(Calendar(color=c, theme=theme))

    _section(root, "列表与表格的行", "只读标题；灰色（default）不读", theme)
    lists = []
    for v in LIST_VARIANTS:
        lb = Listbox(variant=v, color=c, selection_mode="single", selected_keys={"a"}, theme=theme)
        lb.add_item(f"{v} · 选中项", key="a")
        lb.add_item("普通项", key="b")
        lists.append(lb)
    root.addWidget(_grid(lists, 2))
    table = Table(selection_mode="single", color=c, theme=theme)
    table.set_columns([{"key": "name", "label": "NAME"}, {"key": "role", "label": "ROLE"}])
    table.set_rows(
        [
            {"key": "1", "name": "Tony Reichert", "role": "CEO"},
            {"key": "2", "name": "Zoey Lang", "role": "Tech Lead"},
        ]
    )
    table.set_selected_keys({"1"})
    root.addWidget(table)

    _section(root, "浮层", "悬停或点击后出现", theme)
    root.addWidget(_grid(_tooltip_and_popover(theme, c, keep), 2, stretch=False))
    root.addStretch()
    return panel


__all__ = ["FIELD_VARIANTS", "build_theme_panel"]
