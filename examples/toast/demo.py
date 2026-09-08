"""Toast 组件示例 — severity / color × variant / radius / shadow
× 6 placements / 超时与进度 / loading / 自定义图标 / end_content
× 堆叠折叠 / 手动关闭；触发按钮样式跟随目标 toast
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer

from hero_side_ui import (
    Body,
    Button,
    add_toast,
    clear_toasts,
    close_toast,
    get_toast_provider,
)
from _base import DemoBase

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("flat", "bordered", "solid")
RADII = ("none", "sm", "md", "lg", "full")
SHADOWS = ("none", "sm", "md", "lg")
PLACEMENTS = (
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)
SEVERITIES = ("default", "primary", "secondary", "success", "warning", "danger")


class ToastDemo(DemoBase):
    component_name = "Toast"

    def build_content(self, layout, labels_bag: list):
        # host 固定为示例窗口，避免全局函数去猜当前活动窗口
        self._host = self

        # ============================================================
        # 1) 基础 + 内置 severity 图标（按钮 flat + 同色）
        # ============================================================
        self.add_section(
            layout,
            "基础（severity 决定内置图标，默认 flat / 6s 自动关闭）",
            [
                self._btn(f"severity {s}", lambda s=s: self._basic(s), color=s, variant="flat")
                for s in SEVERITIES
            ],
            labels_bag,
        )

        # ============================================================
        # 2) 6 colors × 3 variants（按钮逐个跟随行列的 variant / color）
        # ============================================================
        for v in VARIANTS:
            self.add_section_grid(
                layout,
                f"variant = {v}",
                [
                    self._btn(c, lambda c=c, v=v: self._styled(c, v), color=c, variant=v)
                    for c in COLORS
                ],
                labels_bag,
                cols=6,
            )

        # ============================================================
        # 3) radius / shadow / size
        # ============================================================
        self.add_section(
            layout,
            "5 radius",
            [
                self._btn(r, lambda r=r: self._styled("primary", "flat", radius=r), color="primary", variant="flat")
                for r in RADII
            ],
            labels_bag,
        )
        self.add_section(
            layout,
            "4 shadow",
            [
                self._btn(s, lambda s=s: self._styled("default", "flat", shadow=s), color="default", variant="flat")
                for s in SHADOWS
            ],
            labels_bag,
        )

        # ============================================================
        # 4) 6 placements（toast 为 solid primary，按钮跟随）
        # ============================================================
        self.add_section(
            layout,
            "6 placements（切方位后连点可看堆叠方向）",
            [
                self._btn(p, lambda p=p: self._placed(p), color="primary", variant="solid")
                for p in PLACEMENTS
            ],
            labels_bag,
        )

        # ============================================================
        # 5) 超时与进度条（按钮逐个跟随对应 toast 的配色）
        # ============================================================
        self.add_section(
            layout,
            "超时 / 进度（timeout=0 常驻，需手动关或拖拽）",
            [
                self._btn("2s + 进度条", lambda: add_toast(
                    title="即将关闭",
                    description="底部进度条走完即消失",
                    color="primary",
                    timeout=2000,
                    should_show_timeout_progress=True,
                    parent=self._host,
                ), color="primary", variant="flat"),
                self._btn("常驻 + 进度条", lambda: add_toast(
                    title="一直显示",
                    description="timeout=0 时不启动倒计时",
                    color="warning",
                    timeout=0,
                    parent=self._host,
                ), color="warning", variant="flat"),
                self._btn("长文本换行", lambda: add_toast(
                    title="这是一条比较长的标题会被单行省略号截断处理",
                    description="描述区会自动换行，卡片高度随内容增长，堆叠区会跟着重排。",
                    color="default",
                    timeout=8000,
                    parent=self._host,
                ), color="default", variant="flat"),
            ],
            labels_bag,
        )

        # ============================================================
        # 6) loading（promise 风格）
        # ============================================================
        self.add_section(
            layout,
            "loading（loading 期间不计时，结束后换成结果）",
            [self._btn("模拟异步 2s", self._async, color="primary", variant="bordered")],
            labels_bag,
        )

        # ============================================================
        # 7) 图标 / 关闭按钮 / end_content
        # ============================================================
        self.add_section(
            layout,
            "图标与附加内容",
            [
                self._btn("自定义图标", lambda: add_toast(
                    title="使用自定义图标",
                    icon="lucide--bell",
                    parent=self._host,
                ), color="default", variant="flat"),
                self._btn("隐藏图标", lambda: add_toast(
                    title="没有图标",
                    description="hide_icon=True",
                    hide_icon=True,
                    parent=self._host,
                ), color="default", variant="flat"),
                self._btn("隐藏关闭按钮", lambda: add_toast(
                    title="只能等超时",
                    description="hide_close_button=True",
                    hide_close_button=True,
                    color="danger",
                    timeout=3000,
                    parent=self._host,
                ), color="danger", variant="flat"),
                self._btn("end_content", self._with_action, color="default", variant="bordered"),
            ],
            labels_bag,
        )

        # ============================================================
        # 8) 堆叠折叠（一次 5 条，鼠标移入展开）
        # ============================================================
        self.add_section(
            layout,
            "堆叠（连点几次：新的在前，旧的被隐藏；鼠标移入展开全部并暂停倒计时）",
            [
                self._btn("弹一条", lambda: add_toast(
                    title=f"第 {self._seq()} 条",
                    description="鼠标移入展开，移开 120ms 后折叠",
                    color="success",
                    timeout=10000,
                    parent=self._host,
                ), color="success", variant="flat"),
                self._btn("一次 5 条", lambda: [self._stack_one(i) for i in range(5)],
                          color="primary", variant="flat"),
                self._btn("清空", lambda: clear_toasts(self._host),
                          color="danger", variant="bordered"),
            ],
            labels_bag,
        )
        self.add_full_width(
            layout,
            "提示",
            Body("拖拽卡片超过阈值可甩出关闭；关闭按钮常显，hover 有反馈。"),
            labels_bag,
        )

    # ============================================================
    # 内部工具
    # ============================================================
    def _btn(self, label: str, slot, *, color: str = "default", variant: str = "bordered") -> Button:
        b = Button(label, variant=variant, color=color, size="sm")
        # clicked 带 checked 参数，直接连会把 bool 塞进 slot 的首个位置参数
        b.clicked.connect(lambda *_: slot())
        return b

    def _seq(self) -> int:
        self._n = getattr(self, "_n", 0) + 1
        return self._n

    def _basic(self, severity: str):
        add_toast(
            title=f"{severity} 提示",
            description="这是一条轻提示",
            severity=severity,
            color=severity,
            parent=self._host,
        )

    def _styled(self, color: str, variant: str, **kw):
        add_toast(
            title=f"{color} / {variant}",
            description="样式全部由组件内部决定",
            color=color,
            variant=variant,
            parent=self._host,
            **kw,
        )

    def _placed(self, placement: str):
        get_toast_provider(self._host).set_placement(placement)
        add_toast(
            title=placement,
            description="切方位后新 toast 沿用同一 placement",
            placement=placement,
            color="primary",
            parent=self._host,
        )

    def _async(self):
        key = add_toast(
            title="正在上传…",
            is_loading=True,
            timeout=0,
            parent=self._host,
        )
        card = get_toast_provider(self._host).card(key)

        def _done():
            if card is None:
                return
            card.set_loading(False)
            card.set_color("success")
            card.set_title("上传完成")
            card.set_description("耗时 2s")

        QTimer.singleShot(2000, self, _done)

    def _with_action(self):
        undo = Button("撤销", size="sm", variant="flat", color="default")
        key = add_toast(
            title="已删除 1 个文件",
            description="10 秒内可撤销",
            end_content=undo,
            timeout=0,
            color="default",
            parent=self._host,
        )
        undo.clicked.connect(lambda: close_toast(key))

    def _stack_one(self, index: int):
        add_toast(
            title=f"堆叠 {index + 1}",
            description="超出配额的旧卡只是隐藏，鼠标移入展开",
            severity="primary",
            color="primary",
            timeout=12000,
            parent=self._host,
        )


if __name__ == "__main__":
    ToastDemo.run()
