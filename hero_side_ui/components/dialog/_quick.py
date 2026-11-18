"""Dialog.alert / confirm / choose 的共用实现：搭一个预设对话框、阻塞运行、销毁。"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ...themes import DIALOG_SPEC
from ...utils import safe_delete
from ._footer import ACCEPTED


def run_quick(
    cls,
    parent: QWidget | None,
    *,
    title: str,
    message: str,
    heading: str | None,
    icon,
    color: str | None,
    buttons: list,
    enter_accepts: bool,
    options: dict,
) -> int:
    """搭一个对话框，阻塞到关闭后返回结果码并销毁它。

    Args:
        cls: Dialog 类（避免本模块反向导入）。
        parent: 父窗口；None 时相对屏幕。
        title: 标题栏文字。
        message: 正文。
        heading: 小标题。
        icon: 图标，写法同 Dialog。
        color: 图标与主按钮语义色；None 跟随图标。
        buttons: 按钮规格，写法同 Dialog.set_footer。
        enter_accepts: True 时 Enter 触发第一个按钮（只有"确定"的提示框用）。
        options: 其余转给 Dialog 构造的参数。
    """
    dlg = cls(
        title=title,
        heading=heading,
        message=message,
        icon=icon,
        color=color,
        parent=parent,
        **options,
    )
    dlg.set_footer(buttons)
    if enter_accepts and dlg.buttons():
        dlg.set_default_button(dlg.buttons()[0])
    try:
        return dlg.exec()
    finally:
        safe_delete(dlg)


class _QuickMixin:
    """Dialog.alert / confirm / choose：用同一套参数搭出的预设对话框。"""

    @classmethod
    def alert(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        *,
        heading: str | None = None,
        icon: str | QWidget | None = "info",
        color: str | None = None,
        ok_text: str = "确定",
        width: int = DIALOG_SPEC["default_width"],
        placement: str = "center",
        backdrop: str = "none",
        stay_on_top: str = "system",
        theme: str = "auto",
    ) -> None:
        """只有"确定"的提示，阻塞到关闭。

        Args:
            parent: 父窗口；None 时相对屏幕。
            title: 标题栏文字。
            message: 正文。
            heading: 小标题。
            icon: 图标，写法同构造参数。
            color: 图标与按钮的语义色；None 跟随图标。
            ok_text: 按钮文字。
            width: 固定宽度。
            placement: 九宫格位置。
            backdrop: none / dim / blur。
            stay_on_top: none / parent / system。
            theme: auto / light / dark。
        """
        run_quick(
            cls,
            parent,
            title=title,
            message=message,
            heading=heading,
            icon=icon,
            color=color,
            buttons=[(ok_text, "accept")],
            enter_accepts=True,
            options={
                "width": width,
                "placement": placement,
                "backdrop": backdrop,
                "stay_on_top": stay_on_top,
                "theme": theme,
            },
        )

    @classmethod
    def confirm(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        *,
        heading: str | None = None,
        icon: str | QWidget | None = "question",
        color: str | None = None,
        ok_text: str = "确定",
        cancel_text: str = "取消",
        width: int = DIALOG_SPEC["default_width"],
        placement: str = "center",
        backdrop: str = "none",
        stay_on_top: str = "system",
        theme: str = "auto",
    ) -> bool:
        """确认 / 取消，阻塞到关闭。

        Args:
            parent: 父窗口；None 时相对屏幕。
            title: 标题栏文字。
            message: 正文。
            heading: 小标题。
            icon: 图标，写法同构造参数。
            color: 图标与确认按钮的语义色，删除类操作传 danger；None 跟随图标。
            ok_text: 确认按钮文字。
            cancel_text: 取消按钮文字。
            width: 固定宽度。
            placement: 九宫格位置。
            backdrop: none / dim / blur。
            stay_on_top: none / parent / system。
            theme: auto / light / dark。

        Returns:
            点了确认为 True；点取消、关闭窗口、Esc 都是 False。
        """
        code = run_quick(
            cls,
            parent,
            title=title,
            message=message,
            heading=heading,
            icon=icon,
            color=color,
            buttons=[(cancel_text, "reject"), (ok_text, "accept")],
            enter_accepts=False,
            options={
                "width": width,
                "placement": placement,
                "backdrop": backdrop,
                "stay_on_top": stay_on_top,
                "theme": theme,
            },
        )
        return code == ACCEPTED

    @classmethod
    def choose(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        buttons: list,
        *,
        heading: str | None = None,
        icon: str | QWidget | None = "info",
        color: str | None = None,
        width: int = DIALOG_SPEC["default_width"],
        placement: str = "center",
        backdrop: str = "none",
        stay_on_top: str = "system",
        theme: str = "auto",
    ) -> int:
        """自定义按钮的一行调用，阻塞到关闭。

        Args:
            parent: 父窗口；None 时相对屏幕。
            title: 标题栏文字。
            message: 正文。
            buttons: 按钮规格，写法同 set_footer。
            heading: 小标题。
            icon: 图标，写法同构造参数。
            color: 图标与主按钮的语义色；None 跟随图标。
            width: 固定宽度。
            placement: 九宫格位置。
            backdrop: none / dim / blur。
            stay_on_top: none / parent / system。
            theme: auto / light / dark。

        Returns:
            被点按钮的结果码；关闭窗口、Esc 返回 0。
        """
        return run_quick(
            cls,
            parent,
            title=title,
            message=message,
            heading=heading,
            icon=icon,
            color=color,
            buttons=buttons,
            enter_accepts=False,
            options={
                "width": width,
                "placement": placement,
                "backdrop": backdrop,
                "stay_on_top": stay_on_top,
                "theme": theme,
            },
        )


__all__ = ["_QuickMixin", "run_quick"]
