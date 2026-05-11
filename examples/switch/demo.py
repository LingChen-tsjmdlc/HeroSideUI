"""
Switch 组件示例 — 6 种颜色 × 3 尺寸 × 状态 × 图标变体
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout

from hero_side_ui import Switch
from _base import DemoBase


# 常用 SVG 资源 (直接内联,避免外部文件依赖)
_SUN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="currentColor" d="M12 17q-2.075 0-3.537-1.463T7 12q0-2.075 1.463-3.537T12 7q2.075 0 3.538 1.463T17 12q0 2.075-1.463 3.538T12 17ZM2 13q-.425 0-.712-.288T1 12q0-.425.288-.712T2 11h2q.425 0 .713.288T5 12q0 .425-.287.712T4 13H2Zm18 0q-.425 0-.712-.288T19 12q0-.425.288-.712T20 11h2q.425 0 .713.288T23 12q0 .425-.287.712T22 13h-2ZM12 5q-.425 0-.712-.288T11 4V2q0-.425.288-.712T12 1q.425 0 .713.288T13 2v2q0 .425-.287.712T12 5Zm0 18q-.425 0-.712-.288T11 22v-2q0-.425.288-.712T12 19q.425 0 .713.288T13 20v2q0 .425-.287.713T12 23ZM5.65 7.05L4.575 6q-.3-.275-.288-.7t.288-.725q.3-.3.725-.3t.7.3L7.05 5.65q.275.3.275.7t-.275.7q-.275.3-.687.288T5.65 7.05Zm12.725 12.725L17.3 18.7q-.275-.3-.275-.712t.275-.688q.275-.3.688-.287t.712.287L19.775 18.3q.3.275.288.7t-.288.725q-.3.3-.725.3t-.7-.3ZM17.3 7.05q-.3-.275-.288-.687t.288-.713L18.3 4.575q.275-.3.7-.288t.725.288q.3.3.3.725t-.3.7L18.7 7.05q-.3.275-.7.275t-.7-.275ZM4.575 19.425q-.3-.3-.3-.725t.3-.7L5.65 16.95q.3-.275.712-.275t.688.275q.3.275.288.688t-.288.712L6 19.425q-.275.3-.7.288t-.725-.288Z"/>'
    '</svg>'
)

_MOON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="currentColor" d="M12 21q-3.75 0-6.375-2.625T3 12q0-3.75 2.625-6.375T12 3q.35 0 .688.025t.662.075q-1.025.725-1.638 1.888T11.1 7.5q0 2.25 1.575 3.825T16.5 12.9q1.375 0 2.525-.613T20.9 10.65q.05.325.075.662T21 12q0 3.75-2.625 6.375T12 21Z"/>'
    '</svg>'
)

_CHECK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="none" stroke="currentColor" stroke-linecap="round" '
    'stroke-linejoin="round" stroke-width="3" d="M4.5 12.75l6 6 9-13.5"/>'
    '</svg>'
)

_X_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="none" stroke="currentColor" stroke-linecap="round" '
    'stroke-linejoin="round" stroke-width="3" d="M6 6l12 12M18 6L6 18"/>'
    '</svg>'
)


class SwitchDemo(DemoBase):
    component_name = "Switch"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # 默认
        self.add_section(layout, "默认(primary,md,未选中 / 已选中)", [
            Switch(),
            Switch(is_selected=True),
        ], labels_bag, spacing=20)

        # 6 种颜色(默认选中)
        self.add_section(layout, "6 种颜色(默认选中)", [
            Switch(is_selected=True, color=c)
            for c in ["default", "primary", "secondary", "success", "warning", "danger"]
        ], labels_bag, spacing=16)

        # 3 种尺寸
        self.add_section(layout, "3 种尺寸(sm / md / lg,均选中)", [
            Switch(is_selected=True, size=s)
            for s in ["sm", "md", "lg"]
        ], labels_bag, spacing=20)

        # 带 label
        self.add_section(layout, "带文字标签", [
            Switch("Auto sync", is_selected=True, color="success"),
            Switch("Notifications", color="primary"),
            Switch("Remember me", is_selected=True, color="secondary"),
        ], labels_bag, spacing=20)

        # 状态
        self.add_section(layout, "状态:disabled / readOnly", [
            Switch("Disabled off", is_disabled=True),
            Switch("Disabled on", is_selected=True, is_disabled=True, color="primary"),
            Switch("Read-only off", is_read_only=True),
            Switch("Read-only on", is_selected=True, is_read_only=True, color="success"),
        ], labels_bag, spacing=20)

        # start/end content
        self.add_section(layout, "startContent / endContent(开关图标出现在两端)", [
            Switch(
                is_selected=True, color="success", size="lg",
                start_content=_SUN_SVG, end_content=_MOON_SVG,
            ),
            Switch(
                color="warning", size="lg",
                start_content=_CHECK_SVG, end_content=_X_SVG,
            ),
            Switch(
                "日间 / 夜间模式",
                is_selected=True, color="primary", size="md",
                start_content=_SUN_SVG, end_content=_MOON_SVG,
            ),
        ], labels_bag, spacing=20)

        # thumbIcon
        self.add_section(layout, "thumbIcon(图标跟随 thumb 移动)", [
            Switch(is_selected=True, color="primary", size="lg", thumb_icon=_CHECK_SVG),
            Switch(color="danger", size="lg", thumb_icon=_X_SVG),
            Switch(is_selected=True, color="secondary", size="md", thumb_icon=_SUN_SVG),
        ], labels_bag, spacing=20)


if __name__ == "__main__":
    SwitchDemo.run()
