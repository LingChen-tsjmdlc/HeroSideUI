"""输入类组件共享的外框、清除按钮、标签几何与样式决策。

消费者：Input、DateInput（含 TimeInput）、Textarea。

InputLayoutMixin 与 InputStylingMixin 读取宿主的状态与子控件，
使用它们的组件必须在构造完成后提供对应属性；契约由
tests/shared/test_fields_contract.py 逐宿主校验。
"""

from .clear_button import ClearButton
from .layout_mixin import InputLayoutMixin
from .styling_mixin import InputStylingMixin
from .wrapper import InputWrapper

__all__ = ["ClearButton", "InputLayoutMixin", "InputStylingMixin", "InputWrapper"]
