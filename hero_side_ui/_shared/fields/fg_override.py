"""输入框一族读取用户字色配置的小工具。

Input / Textarea / DateInput / InputOtp 各自有一份取色代码，它们都在原有取色结果上
调用这里，用户在 color_foreground 里写过的位置就覆盖，没写过的保持原样。
"""

from __future__ import annotations

from ...themes.theme_values import foreground_override

_SLOTS = ("text", "placeholder", "label", "label_resting", "description")


def input_fg_overrides(color: str, theme: str, variant: str, invalid: bool) -> dict:
    """取输入框五个位置的用户字色。

    Args:
        color: 语义色名。
        theme: "light" 或 "dark"。
        variant: flat / faded / bordered / underlined。
        invalid: 是否处于出错状态。

    Returns:
        {位置: 色值或 None}；None 表示用户没写，用组件原来的颜色。
    """
    states = ("invalid",) if invalid else ()
    return {
        slot: foreground_override(color, theme, variant, states=states, slot=slot)
        for slot in _SLOTS
    }


__all__ = ["input_fg_overrides"]
