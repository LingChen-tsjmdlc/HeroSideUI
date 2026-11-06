"""保留 Spinner 的循环驱动名称与导入入口。"""

from .loop import LoopDriver


class PhaseDriver(LoopDriver):
    """使用公共循环契约的 Spinner 进度驱动。"""


__all__ = ["PhaseDriver"]
