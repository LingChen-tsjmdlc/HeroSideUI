"""字色调参示例：可视化编辑 color_foreground，亮色 / 暗色并排实时预览。

用法：
1. 左边是预览区，把所有读字色配置的组件同时按亮色、暗色摆出来。
2. 右边先选“目标”（颜色 / 变体 / 状态 / 位置），再给亮色、暗色各配一个颜色。
   点“选色”会打开调色板窗口；也可以直接在输入框里写 #RRGGBB。
3. 配置不合法会立刻提示（英文 / 中文）；对比度不足、没有任何组件读取会给警告。
4. “复制代码”得到可直接放进 HeroSideUIProvider.setup(color_foreground=...) 的写法。

注意：字色配置只在组件创建时读取，所以每次修改都会重建预览。
"""

from __future__ import annotations

import os
import pprint
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from palette_window import PaletteWindow
from preview import FIELD_VARIANTS, build_theme_panel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hero_side_ui import (
    Accordion,
    AccordionItem,
    Alert,
    Body,
    Button,
    Caption,
    CodeBlock,
    HeroSideUIProvider,
    Input,
    Select,
    Subtitle,
    Tabs,
    ThemeSwitcher,
    Title,
    add_toast,
)
from hero_side_ui.core import _theme_config
from hero_side_ui.core._foreground_config import (
    _backgrounds,
    collect_foreground_issues,
    format_contrast_report,
    hint_messages,
    unread_message,
)
from hero_side_ui.themes import HEROUI_COLORS, theme_values
from hero_side_ui.utils import clear_layout, safe_delete

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("solid", "bordered", "flat", "light", "faded", "ghost", "shadow", "dot", "underlined")
STATES = ("hover", "focus", "selected", "invalid", "disabled")
SLOTS = ("text", "icon", "title", "description", "label", "label_resting", "placeholder")
NONE = "_none"

# 魔杖里常见的“亮黄在浅底上看不清”的修正示例：(颜色, 主题, 变体, 状态, 位置, 色值)
EXAMPLE = (
    ("warning", "light", "solid", None, None, "#11181C"),
    ("warning", "light", "flat", None, None, "#5B3A00"),
    ("warning", "light", "flat", "hover", None, "#4A2F00"),
    ("warning", "light", "light", None, None, "#5B3A00"),
    ("warning", "light", "bordered", None, None, "#5B3A00"),
    ("warning", "light", "faded", None, None, "#5B3A00"),
    ("warning", "light", "underlined", None, "placeholder", "#7A5C00"),
    ("warning", "light", "underlined", None, "label", "#5B3A00"),
    ("warning", "dark", None, None, None, "#FFE08A"),
    # 暗色整体用浅黄字，但实色底（solid / shadow / ghost 悬停）上要用深色字，否则看不清
    ("warning", "dark", "solid", None, None, "#11181C"),
    ("warning", "dark", "shadow", None, None, "#11181C"),
    ("warning", "dark", "ghost", "hover", None, "#11181C"),
)

AFFECTED = """【读新写法】
Button：文字、悬停、禁用、图标
Chip、Badge：文字、关闭按钮
Alert：标题、说明、图标、关闭按钮
Toast：标题、说明、图标、关闭按钮、进度条；success 色实心样式改为读配置
Input、NumberInput、Select、Autocomplete：正文、占位符、标签、说明
Textarea、DateInput、TimeInput、DatePicker、DateRangePicker：同上
InputOtp：已填字符、空段、说明
Listbox、Dropdown 的行：标题（灰色不读）
Table：选中行的字（按 flat 的选中态，灰色不读）
【选中态传 selected】
Calendar 选中日、Pagination 选中页、Tabs 选中项、Checkbox 的勾、Switch 的图标
【走 solid 的老入口】
Avatar、Popover、Tooltip、Slider
【核心】
themes/theme_values.py、themes/foreground_spec.py、core/_foreground_config.py、
core/_theme_config.py、core/state_palette.py、_shared/fields/fg_override.py"""


def _first(value):
    """Select 的选择信号可能是单个 key 或 key 集合，统一取出一个。"""
    if isinstance(value, (set, frozenset, list, tuple)):
        return next(iter(value), None)
    return value


def _items(names, none_label=None):
    items = [{"key": n, "label": n} for n in names]
    if none_label:
        items.insert(0, {"key": NONE, "label": none_label})
    return items


class ForegroundDemo(QMainWindow):
    """字色调参示例主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("字色调参示例")
        self.resize(1700, 980)
        # 规则：(颜色, 主题, 变体, 状态, 位置) -> #RRGGBB；变体 / 状态 / 位置为 None 表示这一层不写
        self._rules: dict[tuple, str] = {}
        self._color = "warning"
        self._variant: str | None = "flat"
        self._state: str | None = None
        self._slot: str | None = None
        self._mode = 0
        self._keep: list = []
        self._side_widgets: dict[str, tuple[QPushButton, Input]] = {}
        self._palette_side = "light"
        self._palette = PaletteWindow(self)
        self._palette.color_picked.connect(self._on_palette_color)

        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(60)
        self._rebuild_timer.timeout.connect(self._rebuild_preview)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._preview_row = QHBoxLayout()
        self._preview_row.setContentsMargins(0, 0, 0, 0)
        self._preview_row.setSpacing(0)
        holder = QWidget()
        holder.setLayout(self._preview_row)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(holder)
        self._preview_scroll = scroll
        lay.addWidget(scroll, 1)
        lay.addWidget(self._build_panel(), 0)
        self.setCentralWidget(central)

        self._load_example()

    # ------------------------------------------------------------ 右侧面板
    def _build_panel(self) -> QWidget:
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(18, 14, 18, 18)
        root.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(Title("字色调参", level=3))
        head.addStretch()
        head.addWidget(ThemeSwitcher(size="md"))
        root.addLayout(head)
        root.addWidget(Caption("先选目标，再给亮色 / 暗色各配一个颜色；左边实时看效果。"))

        root.addWidget(Subtitle("1. 选目标"))
        grid = QHBoxLayout()
        left, right = QVBoxLayout(), QVBoxLayout()
        self._color_sel = self._select("颜色", _items(COLORS), self._color, self._on_color)
        self._variant_sel = self._select(
            "变体", _items(VARIANTS, "（主题层 default）"), self._variant, self._on_variant
        )
        self._state_sel = self._select(
            "状态", _items(STATES, "（普通）"), self._state, self._on_state
        )
        self._slot_sel = self._select(
            "位置", _items(SLOTS, "default（兜底）"), self._slot, self._on_slot
        )
        left.addWidget(self._color_sel)
        left.addWidget(self._state_sel)
        right.addWidget(self._variant_sel)
        right.addWidget(self._slot_sel)
        grid.addLayout(left)
        grid.addLayout(right)
        root.addLayout(grid)
        self._path_label = Body("")
        root.addWidget(self._path_label)

        root.addWidget(Subtitle("2. 配颜色"))
        for side, title in (("light", "亮色"), ("dark", "暗色")):
            root.addLayout(self._side_row(side, title))

        actions = QHBoxLayout()
        for text, slot, kw in (
            ("载入示例", self._load_example, {"color": "primary", "variant": "flat"}),
            ("清空", self._clear_all, {"color": "danger", "variant": "light"}),
            ("复制代码", self._copy_code, {"variant": "bordered"}),
        ):
            b = Button(text, size="md", **kw)
            b.clicked.connect(lambda *_, f=slot: f())
            actions.addWidget(b)
        actions.addStretch()
        root.addLayout(actions)

        root.addWidget(Subtitle("3. 提示"))
        self._msg_box = QVBoxLayout()
        self._msg_box.setSpacing(6)
        root.addLayout(self._msg_box)

        root.addWidget(Subtitle("4. 当前配置"))
        self._code_box = QVBoxLayout()
        root.addLayout(self._code_box)

        root.addWidget(Subtitle("5. 预览设置"))
        mode = Tabs(["并排", "仅亮色", "仅暗色"], size="md")
        mode.selection_changed.connect(lambda i, *_: self._on_mode(i))
        root.addWidget(mode, 0, Qt.AlignmentFlag.AlignLeft)
        toast_row = QHBoxLayout()
        toast_row.addWidget(Caption("弹出 Toast："))
        for v in ("flat", "solid", "bordered"):
            b = Button(v, size="md", variant="flat")
            b.clicked.connect(lambda *_, v=v: self._toast(v))
            toast_row.addWidget(b)
        toast_row.addStretch()
        root.addLayout(toast_row)

        acc = Accordion()
        acc.add_item(AccordionItem("受影响的组件清单", content_text=AFFECTED))
        root.addWidget(acc)
        root.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setFixedWidth(470)
        scroll.setWidget(body)
        return scroll

    def _select(self, label, items, current, slot) -> Select:
        sel = Select(
            items=items,
            label=label,
            default_selected_keys=[current if current else NONE],
            size="sm",
        )
        sel.setFixedWidth(210)
        sel.selection_changed.connect(lambda v: slot(_first(v)))
        return sel

    def _side_row(self, side: str, title: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = Body(title)
        label.setFixedWidth(40)
        swatch = QPushButton()
        swatch.setFixedSize(36, 36)
        swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        swatch.clicked.connect(lambda *_: self._open_palette(side))
        hex_in = Input(placeholder="#RRGGBB", label_placement="outside", size="sm")
        hex_in.setFixedWidth(120)
        hex_in.returned.connect(lambda s=side: self._on_hex(s))
        pick = Button("选色", size="md", variant="bordered", color="primary")
        pick.clicked.connect(lambda *_: self._open_palette(side))
        clear = Button("清除", size="md", variant="light", color="danger")
        clear.clicked.connect(lambda *_: self._clear_value(side))
        for w in (label, swatch, hex_in, pick, clear):
            row.addWidget(w)
        row.addStretch()
        self._side_widgets[side] = (swatch, hex_in)
        return row

    # ------------------------------------------------------------ 目标切换
    def _on_color(self, key):
        self._color = key
        self._after_target_change(rebuild=True)

    def _on_variant(self, key):
        self._variant = None if key in (None, NONE) else key
        self._after_target_change(rebuild=True)

    def _on_state(self, key):
        self._state = None if key in (None, NONE) else key
        self._after_target_change()

    def _on_slot(self, key):
        self._slot = None if key in (None, NONE) else key
        self._after_target_change()

    def _on_mode(self, index: int):
        self._mode = index
        self._schedule_rebuild()

    def _after_target_change(self, rebuild: bool = False):
        self._refresh_target_ui()
        if rebuild:
            self._schedule_rebuild()
        if self._palette.isVisible():
            self._push_palette_target()

    # ------------------------------------------------------------ 规则读写
    def _key(self, side: str) -> tuple:
        return (self._color, side, self._variant, self._state, self._slot)

    def _path_text(self) -> str:
        parts = [self._variant or "（主题层）", self._state, self._slot or "default"]
        return ".".join(p for p in parts if p)

    def _set_value(self, side: str, value: str):
        new = dict(self._rules)
        new[self._key(side)] = value.upper()
        self._commit(new)

    def _clear_value(self, side: str):
        new = dict(self._rules)
        if new.pop(self._key(side), None) is not None:
            self._commit(new)

    def _clear_all(self):
        self._commit({})

    def _load_example(self):
        rules = {(c, s, v, st, sl): hx for c, s, v, st, sl, hx in EXAMPLE}
        self._color, self._variant, self._state, self._slot = "warning", "flat", None, None
        for sel, key in (
            (self._color_sel, "warning"),
            (self._variant_sel, "flat"),
            (self._state_sel, NONE),
            (self._slot_sel, NONE),
        ):
            sel.set_selected_keys([key])
        self._commit(rules)

    def _on_hex(self, side: str):
        text = self._side_widgets[side][1].text().strip()
        text = text if text.startswith("#") else "#" + text
        if len(text) == 7:
            self._set_value(side, text)
        else:
            self._show_messages(f"{text!r} is not #RRGGBB / 不是 #RRGGBB", [], [], [])

    def _on_palette_color(self, value: str):
        self._set_value(self._palette_side, value)

    # ------------------------------------------------------------ 应用配置
    def _build_config(self, rules: dict) -> dict:
        """把规则表拼成嵌套的 color_foreground 写法；某一侧没有规则就沿用默认字色。"""
        cfg: dict = {}
        for color in {k[0] for k in rules}:
            sides = {}
            for side in ("light", "dark"):
                node: dict = {}
                for (c, s, v, st, sl), hx in rules.items():
                    if c != color or s != side:
                        continue
                    target = node
                    if v:
                        target = target.setdefault(v, {})
                    if st:
                        target = target.setdefault(st, {})
                    target[sl or "default"] = hx
                sides[side] = node or theme_values.DEFAULT_COLOR_FOREGROUND[color][side]
            cfg[color] = sides
        return cfg

    def _commit(self, rules: dict) -> bool:
        """校验并应用；不合法就保持原状并提示。"""
        cfg = self._build_config(rules)
        try:
            out = _theme_config.validate(color_foreground=cfg) if cfg else _theme_config.validate()
        except ValueError as e:
            self._show_messages(str(e), [], [], [])
            return False
        theme_values.reset()
        theme_values.apply(out)
        theme_values.clear_read_flag()
        self._rules = rules
        self._cfg = cfg
        issues, unread = collect_foreground_issues(out.get("color_foreground", {}), out)
        hinted = set(hint_messages(issues, unread))
        other = [w for w in out["warnings"] if w not in hinted]
        self._show_messages("", issues, unread, other)
        self._refresh_code()
        self._refresh_target_ui()
        self._schedule_rebuild()
        return True

    # ------------------------------------------------------------ 界面刷新
    def _refresh_target_ui(self):
        self._path_label.setText(f"当前目标：{self._color} · {self._path_text()}")
        for side, (swatch, hex_in) in self._side_widgets.items():
            value = self._rules.get(self._key(side))
            hex_in.set_text(value or "")
            bg = value or "transparent"
            swatch.setStyleSheet(
                f"QPushButton {{ background: {bg}; border: 1px solid rgba(128,128,128,0.6);"
                f" border-radius: 8px; }} QPushButton:hover {{ border: 2px solid #006FEE; }}"
            )
            swatch.setToolTip(value or "还没写，点击选色")

    def _show_messages(self, error: str, issues: list, unread: list, other: list):
        """显示提示。

        对比度过低：标题"有 X 处配色对比度过低"，描述"当前亮/暗色模式下，XX 颜色 XX 变体
        XX 位置对比度是 XX，推荐 XX 对比度"，多条用分号连起来；英文放在下面一行。
        """
        clear_layout(self._msg_box)
        if error:
            self._msg_box.addWidget(
                Alert(title="这份配置有错，没有生效", description=error, color="danger")
            )
            return
        if not (issues or unread or other):
            self._msg_box.addWidget(Caption("没有提示：配置合法，对比度都够。"))
            return
        if issues:
            tz, te, dz, de = format_contrast_report(issues)
            self._msg_box.addWidget(Alert(title=tz, description=dz, color="warning"))
            self._msg_box.addWidget(Caption(f"{te}: {de}", word_wrap=True))
        if unread:
            self._msg_box.addWidget(
                Alert(
                    title=f"有 {len(unread)} 处配置不会生效",
                    description="这些项目前没有任何组件会读，写了也不会有变化。",
                    color="default",
                )
            )
            for entry in unread:
                zh, _, en = unread_message(entry).partition("\n")
                self._msg_box.addWidget(Body(zh))
                self._msg_box.addWidget(Caption(en, word_wrap=True))
        for text in other:
            self._msg_box.addWidget(Body(text))

    def _code_text(self) -> str:
        cfg = getattr(self, "_cfg", {})
        if not cfg:
            return "# 还没有规则"
        return "color_foreground=" + pprint.pformat(cfg, width=70, sort_dicts=False)

    def _refresh_code(self):
        clear_layout(self._code_box)
        self._code_box.addWidget(CodeBlock(self._code_text(), language="python"))

    def _copy_code(self):
        QApplication.clipboard().setText(self._code_text())

    # ------------------------------------------------------------ 调色板
    def _refs(self, side: str) -> list[tuple[str, str]]:
        """当前目标在这一侧的参考底色，用来算对比度。"""
        ramps = {n: dict(HEROUI_COLORS[n]) for n in COLORS}
        parent = theme_values.get_background(side, mark=False)
        variants = (self._variant,) if self._variant else ("solid", "flat", "bordered")
        out: list[tuple[str, str]] = []
        for v in variants:
            for who, bg in _backgrounds(
                v, self._state, self._slot, self._color, side, ramps, parent
            ):
                out.append((f"{v} · {who}", bg))
        return out

    def _push_palette_target(self):
        side = self._palette_side
        text = f"{self._color} · {'亮色' if side == 'light' else '暗色'} · {self._path_text()}"
        self._palette.set_target(text, self._rules.get(self._key(side)), self._refs(side))

    def _open_palette(self, side: str):
        self._palette_side = side
        self._push_palette_target()
        self._palette.show()
        self._palette.raise_()
        self._palette.activateWindow()

    # ------------------------------------------------------------ 预览
    def _schedule_rebuild(self):
        self._rebuild_timer.start()

    def _field_variant(self) -> str:
        return self._variant if self._variant in FIELD_VARIANTS else "flat"

    def _rebuild_preview(self):
        self.setUpdatesEnabled(False)
        try:
            clear_layout(self._preview_row)
            for obj in self._keep:
                safe_delete(obj)
            self._keep.clear()
            themes = (("light", "dark"), ("light",), ("dark",))[self._mode]
            for th in themes:
                self._preview_row.addWidget(
                    build_theme_panel(th, self._color, self._field_variant(), self._keep), 1
                )
        finally:
            self.setUpdatesEnabled(True)

    def _toast(self, variant: str):
        add_toast(
            title="Toast 标题",
            description="标题、说明、图标、关闭按钮、进度条的颜色",
            color=self._color,
            variant=variant,
            timeout=4000,
            should_show_timeout_progress=True,
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    HeroSideUIProvider.setup(app, theme="light")
    win = ForegroundDemo()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
