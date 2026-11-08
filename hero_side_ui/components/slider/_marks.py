"""marks 解析（dict/tuple/number 三格式）与 value 文字格式化（纯函数）。"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from ._geometry import clamp_value

NumPair = tuple[float, float]
ValueT = float | NumPair
MarkT = float | tuple[float, str] | dict

__all__ = ["fmt_num", "format_value", "parse_marks"]


def parse_marks(
    marks: Sequence[MarkT],
    vmin: float,
    vmax: float,
) -> list[tuple[float, str]]:
    """统一三种输入格式 → [(value, label), ...]，并 clamp 到 [vmin, vmax]。"""
    out: list[tuple[float, str]] = []
    for m in marks:
        if isinstance(m, dict):
            v = float(m.get("value", 0))
            lbl = str(m.get("label", ""))
        elif isinstance(m, tuple):
            v = float(m[0])
            lbl = str(m[1]) if len(m) > 1 else ""
        else:
            v = float(m)
            lbl = str(m)
        v = clamp_value(v, vmin, vmax)
        out.append((v, lbl))
    return out


def fmt_num(v: float, step: float) -> str:
    """按 step 决定数值的小数位数并格式化。

    Note:
        step >= 1 且 v 接近整数时按整数显示；否则取 step 的小数位数。
    """
    if step >= 1 and abs(v - round(v)) < 1e-9:
        return str(round(v))
    digits = max(0, -math.floor(math.log10(step))) if step < 1 else 0
    return f"{v:.{digits}f}"


def format_value(
    value: ValueT,
    is_range: bool,
    step: float,
    formatter: Callable[[ValueT], str] | None = None,
) -> str:
    """格式化顶部 value：自定义 formatter 优先，range 拼 "lo – hi"，否则按 step 精度。"""
    if formatter is not None:
        try:
            return str(formatter(value))
        except Exception:
            # 用户 formatter 异常时降级到默认格式（不让文字消失）
            pass
    if is_range:
        lo, hi = value  # type: ignore[misc]
        return f"{fmt_num(lo, step)} – {fmt_num(hi, step)}"
    return fmt_num(value, step)  # type: ignore[arg-type]
