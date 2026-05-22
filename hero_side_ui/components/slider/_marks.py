"""Slider marks 解析 + 数值文字格式化（纯函数）。

marks 三种输入格式：
    - dict: {"value": 50, "label": "1/2"}
    - tuple: (50, "1/2") 或 (50,)
    - number: 50 → label="50"
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple, Union

from ._geometry import clamp_value

NumPair = Tuple[float, float]
ValueT = Union[float, NumPair]
MarkT = Union[float, Tuple[float, str], dict]

__all__ = ["parse_marks", "format_value", "fmt_num"]


def parse_marks(
    marks: Sequence[MarkT],
    vmin: float,
    vmax: float,
) -> List[Tuple[float, str]]:
    """统一三种输入格式 → [(value, label), ...]，并 clamp 到 [vmin, vmax]。"""
    out: List[Tuple[float, str]] = []
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
    """按 step 决定小数位数：
    step >= 1 且 v 接近整数 → 整数显示；否则取 step 的小数位数。
    """
    if step >= 1 and abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    digits = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0
    return f"{v:.{digits}f}"


def format_value(
    value: ValueT,
    is_range: bool,
    step: float,
    formatter: Optional[Callable[[ValueT], str]] = None,
) -> str:
    """格式化顶部 value 文字：
    1) 优先使用用户自定义 formatter
    2) range 模式 "lo – hi"
    3) 否则按 step 精度的纯数字
    """
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
