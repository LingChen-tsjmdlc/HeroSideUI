"""_EndContentWidget — Autocomplete Input 右侧的 clear / arrow 复合槽（私有）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ..._shared.selection import SelectorButton as _SelectorButton
from ..button import Button


# ============================================================
# endContentWrapper: [clear] + [selector]，对齐 HeroUI endContentWrapper slot
# ============================================================
class _EndContentWidget(QWidget):
    def __init__(self, parent=None):
        """构建 clear + selector 双按钮槽位。

        Args:
            parent: Qt 父对象。

        Note:
            左 margin 8px 让 clear 与输入文本保持间距（历史反馈：缺左边距
            时 clear 像被裁进文本区）；两个按钮用 HeroSideUI 自己的 Button
            / SelectorButton，着色与 hover 全部内置自管理。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._h = QHBoxLayout(self)
        # 左边 margin 8px:让 clear 按钮与 input 文本之间有清晰间距,不"贴脸"
        # (用户反馈:之前 clear 看起来像被裁进文本区,实际是缺左 margin)。
        # 右 0、上下 0:popover 触发钮与 input 右内边对齐。
        self._h.setContentsMargins(8, 0, 0, 0)
        # clear 与 selector 之间 4px:两个按钮视觉上独立,而不是粘在一起。
        self._h.setSpacing(4)
        self._h.setAlignment(Qt.AlignVCenter)

        # clear 按钮:用 HeroSideUI 自己的 Button 组件(铁律 3「高层意图 API」)。
        # variant=light(无底,hover 才出淡灰) + radius=full(圆形点击区) +
        # icon_only + size=sm。icon 颜色 / hover bg / ripple 全部 Button 内部
        # 自管理 —— autocomplete 不需要手算 icon_color。
        # setFixedSize 在外部 _refresh_end_btn_sizes 中强制覆盖 Button 自己
        # icon_only 时算的 fixed size,让按钮严丝合缝嵌进 input row 高度。
        self.clear_btn = Button(
            variant="light",
            color="default",
            size="sm",
            radius="full",
            icon_only=True,
        )
        self.clear_btn.setFocusPolicy(Qt.NoFocus)
        self.clear_btn.hide()
        self._h.addWidget(self.clear_btn, 0, Qt.AlignVCenter)

        self.selector_btn = _SelectorButton(self)
        self._h.addWidget(self.selector_btn, 0, Qt.AlignVCenter)
