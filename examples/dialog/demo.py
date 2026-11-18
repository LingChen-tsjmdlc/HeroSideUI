"""Dialog 组件示例 — 一行调用 / 图标 / 结果码与结果数据 / 九宫格位置 / 遮罩 / 模态与置顶 / 自动高度 / 按钮

触发按钮的 variant/color 按动作语义分层：
- 一行调用：alert / confirm 用 bordered default，危险确认 bordered danger，自定义结果码 bordered primary
- 图标：按图标语义色映射（info/question primary，success，warning，danger）
- 位置、遮罩、对齐：flat default（只是切换观察效果），影响更大的用 bordered / solid 递进
- 模态：application 这类影响面大的用 bordered warning
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _base import DemoBase
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from hero_side_ui import Body, Button, Caption, Dialog, Input, Window

PLACEMENTS = (
    "top-left",
    "top",
    "top-right",
    "left",
    "center",
    "right",
    "bottom-left",
    "bottom",
    "bottom-right",
)
ICONS = (
    ("info", "primary"),
    ("success", "success"),
    ("warning", "warning"),
    ("danger", "danger"),
    ("question", "primary"),
)
LONG_TEXT = "这是一段很长的文案，用来观察对话框高度随内容自动撑开，超出上限后正文区内部滚动。" * 18
SYSTEMS = ("auto", "windows", "mac", "linux")
SKIP = -1  # 自己定义的结果码


class DialogDemo(DemoBase):
    component_name = "Dialog"

    def build_content(self, layout, labels_bag: list):
        self._status = Body("结果：（点下面的按钮，关闭后这里显示结果码 / 数据）")
        self.add_full_width(layout, "结果", self._status, labels_bag)
        self._build_quick(layout, labels_bag)
        self._build_icons(layout, labels_bag)
        self._build_position(layout, labels_bag)
        self._build_behavior(layout, labels_bag)
        self._build_layout(layout, labels_bag)
        self.add_full_width(
            layout,
            "提示",
            Caption(
                "标题栏的关闭按钮、Esc、close() 都等于取消（结果码 0）；"
                "点被挡住的主窗口会闪烁对话框并响提示音，是系统自带的行为。"
            ),
            labels_bag,
        )

    # ============================================================
    # 各节
    # ============================================================
    def _build_quick(self, layout, labels_bag):
        self.add_section(
            layout,
            "一行调用 alert / confirm / choose（choose 的按钮可以带自定义结果码）",
            [
                self._btn("alert", self._alert, variant="bordered"),
                self._btn("confirm", self._confirm, variant="bordered"),
                self._btn("confirm 危险", self._confirm_danger, color="danger", variant="bordered"),
                self._btn("choose 跳过 = -1", self._choose, color="primary", variant="bordered"),
            ],
            labels_bag,
        )
        self.add_section(
            layout,
            "结果数据（输入框的内容在关闭那一刻由 provider 取出）",
            [self._btn("重命名", self._rename, color="primary", variant="solid")],
            labels_bag,
        )

    def _build_icons(self, layout, labels_bag):
        buttons = [
            self._btn(name, lambda n=name: self._icon(n), color=color, variant="bordered")
            for name, color in ICONS
        ]
        buttons.append(self._btn("无图标", lambda: self._icon(None), variant="flat"))
        title = "5 种图标（颜色跟随图标，也可用 color 单独指定）"
        self.add_section(layout, title, buttons, labels_bag)

    def _build_position(self, layout, labels_bag):
        self.add_section_grid(
            layout,
            "九宫格位置 placement（相对本窗口，默认 center）",
            [self._btn(p, lambda p=p: self._place(p), variant="flat") for p in PLACEMENTS],
            labels_bag,
            cols=3,
        )
        self.add_section(
            layout,
            "对父窗口的遮罩 backdrop",
            [
                self._btn("none", lambda: self._backdrop("none"), variant="flat"),
                self._btn("dim 压暗", lambda: self._backdrop("dim"), variant="bordered"),
                self._btn(
                    "blur 模糊", lambda: self._backdrop("blur"), color="primary", variant="solid"
                ),
            ],
            labels_bag,
        )

    def _build_behavior(self, layout, labels_bag):
        self.add_section(
            layout,
            "模态 modality 与置顶 stay_on_top（先点“打开无关窗口”：window 只挡本窗口，"
            "application 连它一起挡，none 谁都不挡）",
            [
                self._btn("打开无关窗口", self._open_other, color="primary", variant="bordered"),
                self._btn(
                    "window（默认）", lambda: self._modal("window", "system"), variant="flat"
                ),
                self._btn("none 不挡父窗口", lambda: self._modal("none", "system"), variant="flat"),
                self._btn(
                    "application 挡整个程序",
                    lambda: self._modal("application", "system"),
                    color="warning",
                    variant="bordered",
                ),
                self._btn(
                    "只压在父窗口上", lambda: self._modal("window", "parent"), variant="bordered"
                ),
            ],
            labels_bag,
        )
        self.add_section(
            layout,
            "Esc 与 Enter（默认 Esc 不关闭；Enter 触发第一个 reject 角色的按钮）",
            [
                self._btn("Esc 不可关闭（默认）", lambda: self._esc(False), variant="flat"),
                self._btn("Esc 可关闭", lambda: self._esc(True), variant="bordered"),
            ],
            labels_bag,
        )

    def _build_layout(self, layout, labels_bag):
        self.add_section(
            layout,
            "高度：默认自动；传数字固定；超出上限（屏幕可用高度 80%）正文内部滚动",
            [
                self._btn("自动 · 短", lambda: self._height("短文案。", None), variant="flat"),
                self._btn(
                    "自动 · 长", lambda: self._height(LONG_TEXT[:160], None), variant="bordered"
                ),
                self._btn(
                    "自动 · 超长",
                    lambda: self._height(LONG_TEXT, None),
                    color="primary",
                    variant="bordered",
                ),
                self._btn(
                    "固定 360", lambda: self._height("固定高度 360。", 360), variant="bordered"
                ),
            ],
            labels_bag,
        )
        buttons = [
            self._btn(a, lambda a=a: self._footer(align=a), variant="flat")
            for a in ("start", "center", "end", "stretch")
        ]
        for order in ("ok_first", "cancel_first"):
            buttons.append(
                self._btn(order, lambda o=order: self._footer(order=o), variant="bordered")
            )
        self.add_section(
            layout,
            "按钮对齐 footer_align 与顺序 button_order（默认取消在前、确定在后）",
            buttons,
            labels_bag,
        )
        systems = [self._btn(s, lambda s=s: self._system(s), variant="bordered") for s in SYSTEMS]
        self.add_section(
            layout,
            "窗口风格 system（对话框继承 Window：标题栏与按钮样式随风格变，mac 的红黄绿在左）",
            systems,
            labels_bag,
        )

    # ============================================================
    # 版面小工具
    # ============================================================
    @staticmethod
    def _btn(label: str, slot, *, color: str = "default", variant: str = "flat") -> Button:
        b = Button(label, variant=variant, color=color, size="sm")
        b.clicked.connect(lambda *_: slot())
        return b

    def _report(self, text: str):
        self._status.setText(f"结果：{text}")

    def _run(self, dlg: Dialog):
        """阻塞打开，关闭后汇报结果码与数据。"""
        code = dlg.exec()
        self._report(f"结果码 = {code}，结果数据 = {dlg.result_data()!r}")
        dlg.deleteLater()

    def _make(self, **kw) -> Dialog:
        kw.setdefault("title", "Dialog 示例")
        kw.setdefault("message", "这是一段对话框正文。")
        dlg = Dialog(parent=self, **kw)
        dlg.set_footer([("取消", "reject"), ("确定", "accept")])
        return dlg

    # ============================================================
    # 回调
    # ============================================================
    def _alert(self):
        Dialog.alert(self, "保存成功", "项目已保存到本地。", icon="success")
        self._report("alert 已关闭")

    def _confirm(self):
        ok = Dialog.confirm(self, "退出", "还有未保存的修改，仍要退出吗？")
        self._report(f"confirm 返回 {ok}")

    def _confirm_danger(self):
        ok = Dialog.confirm(
            self,
            "删除文件",
            "删除后无法恢复，确定继续吗？",
            heading="此操作不可撤销",
            icon="warning",
            color="danger",
            ok_text="删除",
        )
        self._report(f"confirm 返回 {ok}")

    def _choose(self):
        code = Dialog.choose(
            self,
            "导入",
            "发现同名文件，怎么处理？",
            [("跳过", SKIP), ("取消", "reject"), ("覆盖", "accept")],
            heading="目标目录已存在",
            icon="question",
        )
        names = {SKIP: "跳过", 0: "取消 / 关闭", 1: "覆盖"}
        self._report(f"choose 返回 {code}（{names.get(code, '?')}）")

    def _icon(self, icon):
        heading = "图标" if icon else "无图标"
        self._run(self._make(icon=icon, heading=heading, message=f"icon = {icon!r}"))

    def _rename(self):
        edit = Input(placeholder="新名称")
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(Body("请输入新的文件名："))
        lay.addWidget(edit)
        dlg = self._make(title="重命名", icon=None)
        dlg.set_body(box)
        dlg.set_result_data_provider(lambda: edit.text())
        self._run(dlg)

    def _place(self, placement: str):
        self._run(self._make(placement=placement, message=f"placement = {placement!r}"))

    def _backdrop(self, kind: str):
        self._run(self._make(backdrop=kind, message=f"backdrop = {kind!r}"))

    def _open_other(self):
        """打开一个与对话框无父子关系的独立窗口，用来观察 application 模态的范围。"""
        other = Window(width=360, height=200, parent=None)
        other.setWindowTitle("无关窗口")
        other.set_content(Body("我和对话框没有父子关系。\napplication 模态会把我也挡住。"))
        other.move(self.x() + self.width() + 20, self.y() + 60)
        other.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        other.show()
        self._other = other

    def _modal(self, modality: str, stay: str):
        text = f"modality = {modality!r}，stay_on_top = {stay!r}"
        dlg = self._make(modality=modality, stay_on_top=stay, message=text)
        if modality == "none":
            dlg.open()  # 不挡父窗口时用非阻塞打开，主窗口仍可操作
            dlg.finished.connect(lambda c: (self._report(f"结果码 = {c}"), dlg.deleteLater()))
        else:
            self._run(dlg)

    def _height(self, text: str, height):
        self._run(self._make(message=text, height=height, title=f"height = {height!r}"))

    def _footer(self, align: str = "end", order: str = "auto"):
        text = f"align = {align!r}，order = {order!r}"
        self._run(self._make(footer_align=align, button_order=order, message=text))

    def _system(self, system: str):
        text = f"system = {system!r}"
        self._run(self._make(system=system, title=f"{system} 风格", message=text))

    def _esc(self, enabled: bool):
        text = f"dismiss_on_escape = {enabled}，试试按 Esc。"
        self._run(self._make(dismiss_on_escape=enabled, message=text))


if __name__ == "__main__":
    DialogDemo.run()
