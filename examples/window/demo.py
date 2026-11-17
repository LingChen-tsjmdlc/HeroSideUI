"""Window 组件示例 — 风格 / 圆角 / 标题栏高度 / 控制按钮 / 三个槽 / 子窗口 / 尺寸限制

示例窗口本身就是一个 Window，所以不继承 DemoBase（它是 QMainWindow）。
窗口顶部的左 / 中 / 右三个槽在下面的「三个槽」一节里动态替换。

触发按钮的 variant/color 按动作语义分层：
- 切换类（风格 / 圆角 / 高度）用 Tabs，选中态由 Tabs 自己表达
- 打开子窗口：继承 bordered default，特殊配置 bordered primary，模态 solid primary
- 限制类：设置 bordered warning（会隐藏最大化），清除 flat
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hero_side_ui import (
    Body,
    Button,
    Caption,
    HeroSideUIProvider,
    Subtitle,
    Switch,
    Tabs,
    ThemeSwitcher,
    Title,
    Window,
)

SYSTEMS = ("auto", "windows", "mac", "linux")
RADII = ("system", None)
# 标题栏高度档位：None 表示跟随风格的标准高度
HEIGHTS = (None, 24, 32, 40, 48, 64)
UNLIMITED = 16777215


class WindowDemo(Window):
    """Window 全功能示例：窗口自己就是被调节的对象。"""

    def __init__(self):
        super().__init__(width=1000, height=780, min_width=560, min_height=420)
        self.setWindowTitle("Window 示例")
        self._children: list[Window] = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        self._layout = QVBoxLayout(body)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(40, 24, 40, 30)
        scroll.setWidget(body)
        self.set_content(scroll)

        header = QHBoxLayout()
        header.addWidget(Title("Window 无边框窗口", level=1))
        header.addStretch()
        header.addWidget(ThemeSwitcher(size="md"))
        self._layout.addLayout(header)

        self._info = Body("")
        self._add("当前状态", self._info)
        self._add_choice("风格 system（auto 按当前操作系统解析）", SYSTEMS, 0, self._on_system)
        self._add_choice(
            "圆角 radius（系统模式：system = 系统圆角；None = 直角。自绘圆角见下方子窗口）",
            ("system", "None（直角）"),
            0,
            self._on_radius,
        )
        self._add_choice(
            "标题栏高度 title_bar_height（默认按风格取标准高度）",
            [("默认" if h is None else f"{h}px") for h in HEIGHTS],
            0,
            self._on_height,
        )
        self._build_controls()
        self._build_slots()
        self._build_children()
        self._build_limits()
        self._add(
            "说明",
            Body(
                "标题栏拖动、双击最大化、边缘缩放都由 Window 自己处理。"
                "Windows 上最大化按钮悬停会弹出 Snap Layouts；mac 风格的绿色按钮默认切换全屏，"
                "按住 Alt 点击才是最大化。"
            ),
        )
        self._layout.addStretch()

        self.system_changed.connect(lambda *_: self._refresh_info())
        self.maximized_changed.connect(lambda *_: self._refresh_info())
        self._refresh_info()

    # ============================================================
    # 版面小工具
    # ============================================================
    def _add(self, title: str, widget: QWidget):
        self._layout.addWidget(Subtitle(title))
        self._layout.addWidget(widget)

    def _add_row(self, title: str, widgets: list[QWidget]):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        for w in widgets:
            lay.addWidget(w)
        lay.addStretch()
        self._add(title, row)

    def _add_choice(self, title: str, labels, selected: int, slot):
        tabs = Tabs(list(labels), size="sm")
        tabs.set_selected(selected, animate=False)
        tabs.selection_changed.connect(lambda index, *_: slot(index))
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tabs)
        lay.addStretch()
        self._add(title, row)

    @staticmethod
    def _btn(label: str, slot, *, color: str = "default", variant: str = "flat") -> Button:
        b = Button(label, variant=variant, color=color, size="sm")
        b.clicked.connect(lambda *_: slot())
        return b

    # ============================================================
    # 各节
    # ============================================================
    def _build_controls(self):
        self._switches = {}
        specs = (
            ("最小化", "minimize"),
            ("最大化 / 缩放", "maximize"),
            ("关闭", "close"),
        )
        widgets = []
        for text, key in specs:
            sw = Switch(text, is_selected=True, size="sm")
            sw.selected_changed.connect(lambda on, k=key: self.set_controls(**{k: on}))
            self._switches[key] = sw
            widgets.append(sw)
        resizable = Switch("可缩放 resizable", is_selected=True, size="sm")
        resizable.selected_changed.connect(self.set_resizable)
        widgets.append(resizable)
        self._add_row("窗口控制按钮（关掉可缩放会同时隐藏最大化）", widgets)

    def _build_slots(self):
        self._add_row(
            "三个槽（windows / linux：左槽定宽，中右均分；mac：中槽定宽居中，左右均分）",
            [
                self._btn("左槽：自定义文字", self._slot_left),
                self._btn("左槽：保留标题 + 按钮", self._slot_left_keep_title, variant="bordered"),
                self._btn("中槽：按钮", self._slot_center),
                self._btn("右槽：按钮", self._slot_right),
                self._btn("恢复默认", self._slot_reset, color="danger"),
            ],
        )
        self._add("提示", Caption("槽里的旧控件会被窗口销毁；槽高度等于标题栏高度，控件垂直居中。"))

    def _build_children(self):
        self._add_row(
            "子窗口（风格 / 高度 / 按钮默认继承本窗口，圆角不继承；也可以各自独立）",
            [
                self._btn("继承本窗口", self._child_inherit, variant="bordered"),
                self._btn("隐藏最大化", self._child_no_max, variant="bordered"),
                self._btn("独立：mac 风格 + 48 高", self._child_mac, color="primary", variant="bordered"),
                self._btn("模态子窗口", self._child_modal, color="primary", variant="solid"),
            ],
        )
        self._add_row(
            "自绘圆角 beta（透明窗口 + 超椭圆；Windows 上自动启用 D3D11 避免缩放闪烁）",
            [
                self._btn("radius='sm'", lambda: self._child_beta("sm"), variant="bordered"),
                self._btn("radius='md'", lambda: self._child_beta("md"), variant="bordered"),
                self._btn("radius='lg'", lambda: self._child_beta("lg"), variant="bordered"),
                self._btn("radius=24", lambda: self._child_beta(24), variant="bordered"),
            ],
        )

    def _build_limits(self):
        self._add_row(
            "尺寸限制（设了最大尺寸，最大化会钳到最大值并居中；固定尺寸会隐藏最大化）",
            [
                self._btn("最小 560x420", self._limit_min, variant="bordered"),
                self._btn("最大 1200x800", self._limit_max, variant="bordered"),
                self._btn("固定 800x600", self._limit_fixed, color="warning", variant="bordered"),
                self._btn("清除限制", self._limit_clear),
            ],
        )

    # ============================================================
    # 回调：切换类
    # ============================================================
    def _on_system(self, index: int):
        self.set_system(SYSTEMS[index])
        self._refresh_info()

    def _on_radius(self, index: int):
        self.set_radius(RADII[index])
        self._refresh_info()

    def _on_height(self, index: int):
        self.set_title_bar_height(HEIGHTS[index])
        self._refresh_info()

    def _refresh_info(self):
        self._info.setText(
            f"resolved_system = {self.resolved_system()}    "
            f"radius = {self.radius()!r}    "
            f"title_bar_height = {self.resolved_title_bar_height()}px    "
            f"maximized = {self.isMaximized()}"
        )

    # ============================================================
    # 回调：槽
    # ============================================================
    def _slot_left(self):
        self.set_left(Body("自定义左槽"))

    def _slot_left_keep_title(self):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self.default_title_widget())
        lay.addWidget(Button("新建", size="sm", variant="light", color="primary"))
        self.set_left(row)

    def _slot_center(self):
        self.set_center(Button("中槽按钮", size="sm", variant="flat"))

    def _slot_right(self):
        self.set_right(Button("右槽按钮", size="sm", variant="flat", color="primary"))

    def _slot_reset(self):
        self.set_left(None)
        self.set_center(None)
        self.set_right(None)

    # ============================================================
    # 回调：子窗口
    # ============================================================
    def _open_child(self, title: str, note: str, *, modal: bool = False, **kw) -> Window:
        child = Window(parent=self, width=460, height=300, **kw)
        child.setWindowTitle(title)
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.addWidget(Subtitle(title))
        lay.addWidget(Body(note))
        lay.addStretch()
        child.set_content(box)
        if modal:
            # 模态要在显示之前设置，显示后再设不会生效
            child.setWindowModality(Qt.WindowModality.WindowModal)
        self._children.append(child)
        child.show()
        return child

    def _child_inherit(self):
        self._open_child("继承的子窗口", "没有传风格 / 标题栏高度 / 按钮：它们跟随主窗口，主窗口改了它也跟着变。圆角不继承。")

    def _child_no_max(self):
        self._open_child("隐藏最大化", "只覆盖 show_maximize，其余仍然继承主窗口。", show_maximize=False)

    def _child_mac(self):
        self._open_child(
            "独立的 mac 风格",
            "自己设了 system 与 title_bar_height，之后不再受主窗口这两项影响。",
            system="mac",
            title_bar_height=48,
        )

    def _child_beta(self, radius):
        self._open_child(
            f"自绘圆角 {radius!r}（beta）",
            "radius 传档位或数字就是自绘超椭圆圆角（透明窗口），全平台一致；构造时决定，不能改回系统圆角。",
            radius=radius,
        )

    def _child_modal(self):
        self._open_child("模态子窗口", "WindowModal：关闭前不能操作主窗口。", modal=True, show_minimize=False)

    # ============================================================
    # 回调：尺寸限制
    # ============================================================
    def _limit_min(self):
        self.setMinimumSize(560, 420)

    def _limit_max(self):
        self.setMaximumSize(1200, 800)

    def _limit_fixed(self):
        self.setFixedSize(800, 600)

    def _limit_clear(self):
        self.setMinimumSize(0, 0)
        self.setMaximumSize(UNLIMITED, UNLIMITED)

    # ============================================================
    # 启动器
    # ============================================================
    @classmethod
    def run(cls):
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        HeroSideUIProvider.setup(app, theme="light")
        win = cls()
        win.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    WindowDemo.run()
