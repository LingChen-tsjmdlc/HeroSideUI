"""组件总览示例：把全部组件放进同一页，检查默认尺寸下大小是否协调。

每一行都是"同类放一起、默认 md 尺寸"，看高度、字号、圆角、间距有没有不齐的地方。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _base import DemoBase
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import (
    Accordion,
    AccordionItem,
    Alert,
    Autocomplete,
    Avatar,
    AvatarGroup,
    Badge,
    Body,
    BreadcrumbItem,
    Breadcrumbs,
    Button,
    Calendar,
    Caption,
    Card,
    Checkbox,
    CheckboxGroup,
    Chip,
    CodeBlock,
    CodeEditor,
    DateInput,
    DatePicker,
    DateRangePicker,
    Divider,
    Drawer,
    Dropdown,
    Icon,
    Image,
    Input,
    InputOtp,
    Kbd,
    Link,
    Listbox,
    Markdown,
    NumberInput,
    Pagination,
    Popover,
    Progress,
    Radio,
    RadioGroup,
    ScrollShadow,
    Select,
    Skeleton,
    Slider,
    Spacer,
    Spinner,
    Subtitle,
    Switch,
    Table,
    Tabs,
    Textarea,
    TimeInput,
    Title,
    Tooltip,
    add_toast,
)

ITEMS = [
    {"key": "cat", "label": "Cat"},
    {"key": "dog", "label": "Dog"},
    {"key": "fox", "label": "Fox"},
]
COLUMNS = [
    {"key": "name", "label": "NAME"},
    {"key": "role", "label": "ROLE"},
    {"key": "status", "label": "STATUS"},
]
ROWS = [
    {"key": "1", "name": "Tony Reichert", "role": "CEO", "status": "Active"},
    {"key": "2", "name": "Zoey Lang", "role": "Tech Lead", "status": "Paused"},
    {"key": "3", "name": "Jane Fisher", "role": "Developer", "status": "Active"},
]
MD = "## Markdown\n正文 **加粗** 与 `行内代码`。\n\n- 列表一\n- 列表二\n\n> 引用块"


def _row(*widgets, spacing: int = 12, top: bool = False) -> QWidget:
    """横向一行：控件按顺序摆放，默认垂直居中，尾部留弹性空白。"""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    align = Qt.AlignmentFlag.AlignTop if top else Qt.AlignmentFlag.AlignVCenter
    for x in widgets:
        lay.addWidget(x, 0, align)
    lay.addStretch()
    return w


def _placeholder_pixmap() -> QPixmap:
    pm = QPixmap(240, 160)
    pm.fill(QColor("#6366f1"))
    return pm


class OverviewDemo(DemoBase):
    component_name = "组件总览"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        self._keep: list = []  # 持有浮层对象，防止被回收
        self._section(layout, "文字 / 链接 / 标记", self._text_row())
        self._section(layout, "按钮四档（sm 24 / md 32 / lg 40 / xl 48）", self._buttons_row())
        self._section(layout, "按钮和输入类同排（默认 md）", self._inputs_with_button())
        self._section(layout, "输入类（全部默认 md）", self._inputs_grid())
        self._section(layout, "选择与开关", self._choices_row())
        self._section(layout, "滑块 / 进度 / 加载 / 验证码", self._feedback_row())
        self._section(layout, "提示与浮层触发", self._overlay_row())
        self._section(layout, "导航", self._navigation())
        self._section(layout, "卡片 / 表格 / 日历", self._data_row())
        self._section(layout, "代码与富文本", self._code_row())

    def _section(self, layout: QVBoxLayout, title: str, widget: QWidget):
        layout.addSpacing(10)
        layout.addWidget(Subtitle(title))
        layout.addWidget(Divider())
        layout.addWidget(widget)

    # ------------------------------------------------------------
    def _text_row(self) -> QWidget:
        crumbs = Breadcrumbs(
            items=[
                BreadcrumbItem("Home", key="home"),
                BreadcrumbItem("Music", key="music"),
                BreadcrumbItem("Artist", key="artist"),
            ]
        )
        avatars = AvatarGroup([Avatar(name=n) for n in "ABCDEF"], max=4)
        badge = Badge(Avatar(name="JW", color="primary"), content="5", color="danger")
        outer = QWidget()
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(
            _row(
                Title("Title", level=3),
                Subtitle("Subtitle"),
                Body("Body 正文"),
                Caption("Caption 说明"),
            )
        )
        lay.addWidget(
            _row(
                crumbs, Link("Link 链接", href="https://example.com"), Kbd(keys="command"), Kbd("K")
            )
        )
        lay.addWidget(
            _row(
                Chip("默认"),
                Chip("primary", color="primary", variant="flat"),
                Chip("closable", color="success", is_closable=True),
                avatars,
                badge,
                Icon("heroicons--check-solid", size="md"),
                Avatar(name="MD"),
                Spacer(x=2),
                Caption("Spacer"),
            )
        )
        return outer

    def _buttons_row(self) -> QWidget:
        outer = QWidget()
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        for variant in ("solid", "bordered", "flat", "faded", "light", "ghost"):
            lay.addWidget(
                _row(
                    *[
                        Button(f"{s} {variant}", size=s, variant=variant)
                        for s in ("sm", "md", "lg", "xl")
                    ]
                )
            )
        lay.addWidget(
            _row(
                *[
                    Button(icon="heroicons--check-solid", icon_only=True, size=s, variant="flat")
                    for s in ("sm", "md", "lg", "xl")
                ],
                *[Button(f"full {s}", size=s, radius="full") for s in ("sm", "md", "lg", "xl")],
            )
        )
        return outer

    def _inputs_with_button(self) -> QWidget:
        sel = Select(items=ITEMS, label="用量与生成归属项目")
        sel.setFixedWidth(280)
        inp = Input(label="名称")
        inp.setFixedWidth(220)
        return _row(
            sel,
            Button("刷新项目", color="default", variant="flat"),
            inp,
            Button("提交", color="primary"),
            Button("取消", variant="bordered"),
            Switch("启用", is_selected=True),
        )

    def _inputs_grid(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)
        cells = [
            Input(label="Input", placeholder="输入"),
            NumberInput(label="NumberInput", value=3),
            Select(items=ITEMS, label="Select"),
            Autocomplete(items=ITEMS, label="Autocomplete"),
            DateInput(label="DateInput"),
            TimeInput(label="TimeInput"),
            DatePicker(label="DatePicker"),
            DateRangePicker(label="DateRangePicker"),
        ]
        for i, c in enumerate(cells):
            c.setMinimumWidth(240)
            g.addWidget(c, i // 4, i % 4)
        ta = Textarea(label="Textarea", placeholder="多行输入")
        g.addWidget(ta, 2, 0, 1, 2)
        for size_i, size in enumerate(("sm", "md", "lg")):
            g.addWidget(Input(label=f"Input {size}", size=size), 3, size_i)
        return w

    def _choices_row(self) -> QWidget:
        cg = CheckboxGroup(label="Checkbox", orientation="vertical")
        for t, k in (("北京", "bj"), ("上海", "sh"), ("深圳", "sz")):
            cg.create_checkbox(t, k)
        rg = RadioGroup(label="Radio", orientation="vertical")
        for t in ("A", "B", "C"):
            rg.create_radio(t, value=t)
        return _row(
            Checkbox("单个 Checkbox", is_selected=True),
            Checkbox("sm", size="sm"),
            Checkbox("lg", size="lg"),
            Radio("Radio", value="r", is_selected=True),
            Switch("Switch", is_selected=True),
            Switch("sm", size="sm"),
            Switch("lg", size="lg"),
            cg,
            rg,
            top=True,
        )

    def _feedback_row(self) -> QWidget:
        s = Slider(value=40, label="Slider")
        s.setFixedWidth(220)
        p = Progress(value=60, label="Progress", show_value_label=True)
        p.setFixedWidth(220)
        otp = InputOtp(length=4)
        return _row(s, p, Spinner(label="Loading"), Spinner(variant="gradient"), otp)

    def _overlay_row(self) -> QWidget:
        b_tip = Button("Tooltip", variant="flat")
        tip = Tooltip(content="这是提示", placement="top")
        tip.attach(b_tip)
        self._keep.append(tip)

        b_pop = Button("Popover", variant="flat")
        pop = Popover(placement="bottom")
        c = QWidget()
        QVBoxLayout(c).addWidget(Body("Popover 内容"))
        pop.set_content(c)
        pop.attach(b_pop)
        self._keep.append(pop)

        dd = Dropdown(trigger=Button("Dropdown", variant="flat"), items=ITEMS)
        self._keep.append(dd)

        drawer = Drawer(parent=self)
        db = QWidget()
        QVBoxLayout(db).addWidget(Body("Drawer 内容"))
        drawer.set_content(db)
        b_drawer = Button("Drawer", variant="flat")
        b_drawer.clicked.connect(lambda *_: drawer.open())
        self._keep.append(drawer)

        b_toast = Button("Toast", variant="flat", color="primary")
        b_toast.clicked.connect(
            lambda *_: add_toast(title="标题", description="描述", color="primary")
        )

        alert = Alert(
            title="Alert 标题", description="Alert 描述文字", color="primary", is_closable=True
        )
        alert.setMinimumWidth(420)
        outer = QWidget()
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_row(b_tip, b_pop, dd, b_drawer, b_toast))
        lay.addWidget(_row(alert, Skeleton(child=Body("Skeleton 内容"))))
        return outer

    def _navigation(self) -> QWidget:
        tabs = Tabs(["Photos", "Music", "Videos"], variant="solid")
        tabs_u = Tabs(["Photos", "Music", "Videos"], variant="underlined")
        pg = Pagination(total=10, initial_page=3)
        lb = Listbox(selection_mode="single")
        lb.add_item("New file", key="new", description="Create a new file", shortcut="Ctrl+N")
        lb.add_item("Copy link", key="copy", description="Copy to clipboard")
        lb.setFixedWidth(280)
        acc = Accordion()
        for t in ("Anchor", "Credit"):
            acc.add_item(AccordionItem(t, content_text="手风琴内容文字"))
        acc.setFixedWidth(300)
        outer = QWidget()
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(_row(tabs, tabs_u, pg))
        lay.addWidget(_row(lb, acc, top=True))
        return outer

    def _data_row(self) -> QWidget:
        card = Card()
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.addWidget(Subtitle("Card 标题"))
        il.addWidget(Body("Card 内容文字，用来对照字号。"))
        il.addWidget(_row(Button("确定"), Button("取消", variant="light")))
        card.setLayout(QVBoxLayout())
        card.layout().addWidget(inner)
        card.setFixedWidth(280)

        table = Table(selection_mode="single", color="primary")
        table.set_columns(COLUMNS)
        table.set_rows(ROWS)
        table.setMinimumWidth(420)

        cal = Calendar()
        img = Image(src=_placeholder_pixmap(), width=200, height=130)
        return _row(card, table, cal, img, top=True)

    def _code_row(self) -> QWidget:
        cb = CodeBlock("def hello():\n    print('hi')\n", language="python", filename="a.py")
        cb.setMinimumWidth(360)
        ce = CodeEditor("x = 1\nprint(x)\n", min_lines=4)
        ce.setMinimumWidth(360)
        md = Markdown(MD)
        md.setMinimumWidth(300)
        ss = ScrollShadow()
        ss.add_widget(Body("ScrollShadow：" + "很长的文字，" * 40))
        ss.setFixedSize(260, 120)
        return _row(cb, ce, md, ss, top=True)


if __name__ == "__main__":
    OverviewDemo.run()
