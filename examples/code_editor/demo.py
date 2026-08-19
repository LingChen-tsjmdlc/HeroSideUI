"""CodeEditor 组件示例 —— 语法高亮 / 行号 / 智能缩进 / 值 API / 只读 / 行数上限 / 多语言 / 主题 / tab_width"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from hero_side_ui import (
    Button,
    Caption,
    Chip,
    CodeEditor,
    Input,
    Switch,
    Text,
    Title,
)
from _base import DemoBase


# ============================================================
# 示例代码
# ============================================================

PY_SAMPLE = '''def average(scores):
    """返回平均分，保留一位小数。"""
    total = sum(scores)
    return round(total / len(scores), 1)


# 试试：Tab / Shift+Tab 缩进、回车自动缩进、三引号跨行
class Report:
    version = 1

    def dump(self, items):
        lines = [f"- {n}: {average(v)}" for n, v in items.items()]
        return "\\n".join(lines)
'''

PY_INDENT = (
    "def greet(name):\n"
    "    # 回车会自动保持缩进；行尾冒号再进一级\n"
    "    if name:\n"
    "        return f\"hello {name}\"\n"
    "    return \"hello\"\n"
)

JSON_SAMPLE = (
    '{\n'
    '  "name": "HeroSideUI",\n'
    '  "version": "0.8.0",\n'
    '  "components": ["input", "table", "code_editor"],\n'
    '  "tags": {"language": "python", "gui": "pyside6"}\n'
    '}\n'
)

SQL_SAMPLE = (
    "SELECT id, name, age FROM users\n"
    "WHERE age > 18 AND status = 'active'\n"
    "ORDER BY name DESC\n"
    "LIMIT 20;\n"
)

JS_SAMPLE = (
    "const add = (a, b) => a + b;\n"
    "const nums = [1, 2, 3].map((x) => x * 2);\n"
    "console.log(`sum = ${add(nums[0], nums[1])}`);\n"
)

SHELL_SAMPLE = (
    "# 任意 pygments 支持的语言都能高亮\n"
    "uv run python examples/code_editor/demo.py\n"
    "git switch -c feat/new-component\n"
    "echo \"done\" && exit 0\n"
)


class CodeEditorDemo(DemoBase):
    component_name = "CodeEditor"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 基础（默认 Python：语法高亮 + 行号 + 智能缩进）
        # ============================================================
        layout.addWidget(Title("基础（Python 高亮 / 行号 / 智能缩进）", level=3))
        layout.addWidget(
            Caption("当前行由行号颜色标识；Tab 转 4 空格，回车保持缩进，冒号行自动进一级")
        )
        layout.addWidget(CodeEditor(PY_SAMPLE, min_lines=10))

        # ============================================================
        # 2) 智能缩进细节
        # ============================================================
        layout.addWidget(Title("智能缩进", level=3))
        layout.addWidget(
            Caption("回车继承当前行缩进；冒号结尾的行自动多缩进一级；Tab / Shift+Tab 对选中行整体增删缩进")
        )
        layout.addWidget(CodeEditor(PY_INDENT, min_lines=6))

        # ============================================================
        # 3) 值 API（与 Input / Textarea 同构）
        # ============================================================
        layout.addWidget(Title("值 API（value / set_value / text_changed）", level=3))
        layout.addWidget(
            Caption("构造传 value；value() 取全文；text_changed(str) 在每次变更时发出；下方输入框与编辑器双向联动")
        )
        api_ed = CodeEditor("x = 1\n", min_lines=5)

        api_row = QWidget()
        ar = QHBoxLayout(api_row)
        ar.setContentsMargins(0, 0, 0, 0)
        api_input = Input(placeholder="set_value(...) 写入编辑器", size="sm")
        get_btn = Button("value() → 打印", size="sm", variant="flat", color="primary")
        clear_btn = Button("clear()", size="sm", variant="flat")
        ar.addWidget(api_input, stretch=1)
        ar.addWidget(get_btn)
        ar.addWidget(clear_btn)

        api_out = Text("（编辑左侧/上方编辑器看联动）", size="sm")

        def _on_input_text(t: str) -> None:
            api_out.setText(f"字符数 {len(t)} · 行数 {t.count(chr(10)) + 1}")

        api_ed.text_changed.connect(_on_input_text)
        api_input.text_changed.connect(lambda t: api_ed.set_value(t + "\n"))
        get_btn.clicked.connect(
            lambda: api_out.setText(f"value() = {api_ed.value()[:40]!r}...")
            if len(api_ed.value()) > 40
            else api_out.setText(f"value() = {api_ed.value()!r}")
        )
        clear_btn.clicked.connect(api_ed.clear)

        layout.addWidget(api_ed)
        layout.addWidget(api_row)
        layout.addWidget(api_out)

        # ============================================================
        # 4) 只读
        # ============================================================
        layout.addWidget(Title("只读（set_read_only）", level=3))
        layout.addWidget(Caption("只读态可正常选择/复制/滚动，但不能编辑"))
        ro_row = QWidget()
        rr = QHBoxLayout(ro_row)
        rr.setContentsMargins(0, 0, 0, 0)
        ro_switch = Switch()
        ro_switch.setChecked(True)
        ro_state = Text("只读：开", size="sm")
        rr.addWidget(ro_switch)
        rr.addWidget(ro_state)
        rr.addStretch()
        ro_ed = CodeEditor(PY_INDENT, min_lines=5)
        ro_ed.set_read_only(True)

        def _toggle_ro(checked: bool) -> None:
            ro_ed.set_read_only(checked)
            ro_state.setText("只读：开" if checked else "只读：关")

        ro_switch.toggled.connect(_toggle_ro)
        layout.addWidget(ro_row)
        layout.addWidget(ro_ed)

        # ============================================================
        # 5) 行数上限
        # ============================================================
        layout.addWidget(Title("行数上限（max_lines）", level=3))
        layout.addWidget(Caption("默认 10000 行；超出上限的输入（含粘贴）自动截断尾行，max_lines_exceeded(int) 报告被截行数"))
        capped = CodeEditor("a\nb\nc\n", min_lines=4, max_lines=5)
        cap_chip = Chip("max_lines = 5", size="sm")
        cap_note = Text("（往里粘贴超过 5 行的内容试试）", size="sm")
        capped.max_lines_exceeded.connect(
            lambda n: cap_note.setText(f"超出上限，截断了 {n} 行")
        )
        cap_row = QWidget()
        cr = QHBoxLayout(cap_row)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.addWidget(cap_chip)
        cr.addWidget(cap_note)
        cr.addStretch()
        layout.addWidget(capped)
        layout.addWidget(cap_row)

        # ============================================================
        # 6) 外观参数（字号 / tab_width / min_lines）
        # ============================================================
        layout.addWidget(Title("外观参数", level=3))
        layout.addWidget(Caption("font_size 自定义字号；tab_width 控制 Tab 宽度（下例为 8）；min_lines 决定最小高度；行号栏随字号自动对齐"))
        layout.addWidget(CodeEditor(font_size=16, tab_width=8, min_lines=5,
                                    value="# tab_width=8：按一下 Tab 试试\nif ok:\n        pass\n"))

        # ============================================================
        # 7) 多语言（pygments 短名）
        # ============================================================
        layout.addWidget(Title("多语言高亮（pygments）", level=3))
        layout.addWidget(Caption("language 传 pygments 短名；识别失败自动降级纯文本编辑"))
        for lang, code, lines in (
            ("json", JSON_SAMPLE, 6),
            ("sql", SQL_SAMPLE, 4),
            ("javascript", JS_SAMPLE, 3),
            ("bash", SHELL_SAMPLE, 4),
        ):
            lang_row = QWidget()
            lr = QHBoxLayout(lang_row)
            lr.setContentsMargins(0, 0, 0, 0)
            lr.addWidget(Chip(f'language="{lang}"', size="sm"))
            lr.addStretch()
            layout.addWidget(lang_row)
            layout.addWidget(CodeEditor(code, language=lang, min_lines=lines))

        # ============================================================
        # 8) 运行时 API（set_language / set_font_size / insert_at_cursor）
        # ============================================================
        layout.addWidget(Title("运行时 API", level=3))
        layout.addWidget(Caption("set_language 切换高亮、set_font_size 调字号、insert_at_cursor 在光标处插入"))
        live = CodeEditor(JSON_SAMPLE, language="json", min_lines=6)
        live_row = QWidget()
        lr2 = QHBoxLayout(live_row)
        lr2.setContentsMargins(0, 0, 0, 0)
        lang_btns = [
            Button(t, size="sm", variant="flat", color=c)
            for t, c in (
                ("→ python", "primary"),
                ("→ sql", "secondary"),
                ("→ json", "success"),
            )
        ]
        font_sm = Button("字号 12", size="sm", variant="flat")
        font_lg = Button("字号 16", size="sm", variant="flat")
        ins_btn = Button('insert_at_cursor("# 光标处")', size="sm", variant="flat")
        lang_btns[0].clicked.connect(lambda: live.set_language("python"))
        lang_btns[1].clicked.connect(lambda: live.set_language("sql"))
        lang_btns[2].clicked.connect(lambda: live.set_language("json"))
        font_sm.clicked.connect(lambda: live.set_font_size(12))
        font_lg.clicked.connect(lambda: live.set_font_size(16))
        ins_btn.clicked.connect(lambda: live.insert_at_cursor("# 光标处"))
        for b in (*lang_btns, font_sm, font_lg, ins_btn):
            lr2.addWidget(b)
        lr2.addStretch()
        layout.addWidget(live)
        layout.addWidget(live_row)

        # ============================================================
        # 9) 主题（右上角 ThemeSwitcher 即时切换）
        # ============================================================
        layout.addWidget(Title("主题自适应", level=3))
        layout.addWidget(
            Caption("light / dark / auto：切换右上角 ThemeSwitcher，编辑区即时换配色，文本/光标/撤销栈保留")
        )
        layout.addWidget(CodeEditor(PY_SAMPLE, min_lines=6))


if __name__ == "__main__":
    CodeEditorDemo.run()
