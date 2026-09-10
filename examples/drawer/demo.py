"""Drawer 组件示例 — placement / size / radius / backdrop / 关闭行为

demo 触发按钮的 variant/color 按动作语义分层（避免全部同一种 outlined 看着没层次）：
- 4 placement：左/右 bordered default（标准"贴边"按钮），上/下 flat default（补充）
- 10 size：xs/sm flat（小），md bordered default（中），lg/xl bordered primary（中等突出），
  2xl/3xl/4xl solid primary（大），5xl/full solid danger（特殊）
- 4 radius：none flat，sm bordered default，md bordered primary，lg solid primary
- 3 backdrop：transparent flat（不可见），opaque bordered default，blur solid primary（最重）
- 数字 size：240 flat，360 bordered default，520 bordered primary，720 solid primary
- 关闭行为：点遮罩/Esc 关不掉 bordered warning（警示），其余 flat

抽屉内容直接摆组件（Subtitle/Body/Input/按钮），不再包 Card —— 面板本身就是表面。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QHBoxLayout, QWidget

from hero_side_ui import (
    Body,
    Button,
    Drawer,
    Input,
    Subtitle,
)
from _base import DemoBase

SIZES = ("xs", "sm", "md", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "full")
NUMERIC_SIZES = (240, 360, 520, 720)
RADII = ("none", "sm", "md", "lg")
PLACEMENTS = ("left", "right", "top", "bottom")
BACKDROPS = ("transparent", "opaque", "blur")

# size 字符串档位 → 触发器视觉（按"尺寸越大越突出"递进）
_SIZE_BTN = {
    "xs": ("default", "flat"),
    "sm": ("default", "flat"),
    "md": ("default", "bordered"),
    "lg": ("primary", "bordered"),
    "xl": ("primary", "bordered"),
    "2xl": ("primary", "solid"),
    "3xl": ("primary", "solid"),
    "4xl": ("primary", "solid"),
    "5xl": ("danger", "solid"),
    "full": ("danger", "solid"),
}
_RADIUS_BTN = {
    "none": ("default", "flat"),
    "sm": ("default", "bordered"),
    "md": ("primary", "bordered"),
    "lg": ("primary", "solid"),
}
_BACKDROP_BTN = {
    "transparent": ("default", "flat"),
    "opaque": ("default", "bordered"),
    "blur": ("primary", "solid"),
}
_NUM_BTN = [
    (240, "default", "flat"),
    (360, "default", "bordered"),
    (520, "primary", "bordered"),
    (720, "primary", "solid"),
]


class DrawerDemo(DemoBase):
    component_name = "Drawer"

    def build_content(self, layout, labels_bag: list):
        self._drawer = Drawer(
            parent=self,
            on_open_change=self._on_open_change,
            on_close=self._on_close,
        )
        self._fill_content(self._drawer)

        self._status = Body("状态：关闭（on_open_change / on_close 会更新这行）")
        self.add_full_width(layout, "回调", self._status, labels_bag)

        self.add_section(
            layout,
            "4 placement（左/右 = bordered 标准贴边，上/下 = flat 弱化）",
            [
                self._btn(p, lambda p=p: self._open_with(placement=p),
                          color="default", variant="bordered")
                if p in ("left", "right") else
                self._btn(p, lambda p=p: self._open_with(placement=p),
                          color="default", variant="flat")
                for p in PLACEMENTS
            ],
            labels_bag,
        )

        self.add_section_grid(
            layout,
            "10 size（视觉权重按尺寸递增：flat→bordered→solid）",
            [self._btn(s, lambda s=s: self._open_with(size=s),
                       color=_SIZE_BTN[s][0], variant=_SIZE_BTN[s][1]) for s in SIZES],
            labels_bag,
            cols=5,
        )

        self.add_section(
            layout,
            "4 radius（圆角越强按钮越重）",
            [self._btn(r, lambda r=r: self._open_with(radius=r),
                       color=_RADIUS_BTN[r][0], variant=_RADIUS_BTN[r][1]) for r in RADII],
            labels_bag,
        )

        self.add_section(
            layout,
            "3 backdrop（transparent = flat 不可见，opaque = bordered，blur = solid）",
            [self._btn(b, lambda b=b: self._open_with(backdrop=b),
                       color=_BACKDROP_BTN[b][0], variant=_BACKDROP_BTN[b][1]) for b in BACKDROPS],
            labels_bag,
        )

        self.add_section(
            layout,
            "数字 size（px，作用在滑出轴上）",
            [self._btn(f"{n}px", lambda n=n: self._open_with(size=n),
                       color=c, variant=v) for n, c, v in _NUM_BTN],
            labels_bag,
        )

        self.add_section(
            layout,
            "关闭行为",
            [
                self._btn("点遮罩关不掉", self._open_locked,
                          color="warning", variant="bordered"),
                self._btn("Esc 关不掉", self._open_no_esc,
                          color="warning", variant="bordered"),
                self._btn("隐藏关闭按钮", self._open_no_close, variant="flat"),
                self._btn("自定义关闭按钮", self._open_custom_close,
                          color="danger", variant="flat"),
                self._btn("禁用动画", self._open_no_animation, variant="flat"),
            ],
            labels_bag,
        )

        self.add_full_width(
            layout,
            "说明",
            Body("内容区就是一个普通 QWidget：drawer.content_widget() 拿到后随便塞；"
                 "内容超出面板时把 ScrollShadow 作为 content 传进去即可滚动。"),
            labels_bag,
        )

    # ============================================================
    # 内部工具
    # ============================================================
    def _btn(self, label: str, slot, *, color: str = "default", variant: str = "flat") -> Button:
        b = Button(label, variant=variant, color=color, size="sm")
        b.clicked.connect(lambda *_: slot())
        return b

    def _fill_content(self, drawer: Drawer):
        """主抽屉内容 —— 面板本身就是表面，组件直接摆，不再包 Card。"""
        drawer.add_widget(Subtitle("通知设置"))
        drawer.add_widget(
            Body("内容区可以直接 add_widget 任意组件，也可以 set_content 整体替换。")
        )
        drawer.add_widget(Input(placeholder="随便输入点什么"))
        row = QWidget(drawer.content_widget())
        btns = QHBoxLayout(row)
        btns.setContentsMargins(0, 0, 0, 0)
        confirm = Button("确认", size="sm", color="primary")
        confirm.clicked.connect(lambda *_: drawer.close_drawer())
        cancel = Button("取消", size="sm", variant="flat", color="default")
        btns.addWidget(confirm)
        btns.addWidget(cancel)
        btns.addStretch()
        drawer.add_widget(row)

    def _open_with(
        self,
        placement: str = None,
        size=None,
        radius: str = None,
        backdrop: str = None,
    ):
        if placement:
            self._drawer.set_placement(placement)
        if size is not None:
            self._drawer.set_size(size)
        if radius:
            self._drawer.set_radius(radius)
        if backdrop:
            self._drawer.set_backdrop(backdrop)
        self._drawer.open_drawer()

    def _special(self, key: str, **kw) -> Drawer:
        """按 key 缓存一个特殊配置的抽屉，避免连点不停新建。"""
        cache = getattr(self, "_specials", None)
        if cache is None:
            cache = self._specials = {}
        d = cache.get(key)
        if d is None:
            kw.setdefault("parent", self)
            d = Drawer(**kw)
            self._fill_content(d)
            cache[key] = d
        return d

    def _open_locked(self):
        self._special("locked", is_dismissable=False).open_drawer()

    def _open_no_esc(self):
        self._special("no_esc", is_keyboard_dismiss_disabled=True).open_drawer()

    def _open_no_close(self):
        self._special("no_close", hide_close_button=True).open_drawer()

    def _open_custom_close(self):
        d = self._special("custom_close")
        if getattr(d, "_custom_close", None) is None:
            custom = Button("关闭", size="sm", variant="flat", color="danger")
            d.set_close_button(custom)
            custom.clicked.connect(lambda *_: d.close_drawer())
            d._custom_close = custom
        d.open_drawer()

    def _open_no_animation(self):
        self._special("no_anim", disable_animation=True).open_drawer()

    def _on_open_change(self, opened: bool):
        self._status.setText(f"on_open_change: {opened}")

    def _on_close(self):
        self._status.setText("on_close：抽屉已关闭")


if __name__ == "__main__":
    DrawerDemo.run()
