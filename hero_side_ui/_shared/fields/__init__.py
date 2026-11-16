"""输入类组件共享的外框、清除按钮、标签几何与样式决策。

消费者：Input、DateInput（含 TimeInput）、Textarea。
SuggestedWidthMixin 提供"建议宽度"（只当 sizeHint，用户设宽直接生效）。

InputLayoutMixin 与 InputStylingMixin 读取宿主的状态与子控件，
使用它们的组件必须在构造完成后提供对应属性；契约由
tests/shared/test_fields_contract.py 逐宿主校验。
"""

from .clear_button import ClearButton
from .layout_mixin import InputLayoutMixin
from .styling_mixin import InputStylingMixin, fill_slot
from .width_mixin import SuggestedWidthMixin, release_width_floor
from .wrapper import InputWrapper

__all__ = [
    "ClearButton",
    "InputLayoutMixin",
    "InputStylingMixin",
    "InputWrapper",
    "SuggestedWidthMixin",
    "fill_slot",
    "release_width_floor",
]
