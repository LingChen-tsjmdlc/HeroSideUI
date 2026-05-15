"""_EndContentWidget — Autocomplete Input 右侧的 clear / arrow 复合槽（私有）。"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ..button import Button

from ._selector_button import _SelectorButton




# ============================================================
# Clear 按钮：data-visible 行为
# ============================================================
# 历史:这里曾经有 _ClearButton 手写 QPushButton —— 因为 16/14 px 的 x-mark icon
# 在 Fusion QPushButton 默认 setIcon 路径下会被裁掉左侧。
# 后来用户做了 16-design 的 heroicons--x-mark-16-solid(viewBox 16,path 在 4-12
# 范围内,有充足 padding),配合 HeroSideUI 自己的 Button 组件就完全够用了 ——
# 直接在 _EndContentWidget 里实例化 Button 即可,不需要再有 _ClearButton 类。
# Button 的 icon 着色、hover bg、ripple 都是组件内置能力(铁律 3「高层意图 API」)。


# ============================================================
# endContentWrapper: [clear] + [selector]，对齐 HeroUI endContentWrapper slot
# ============================================================
class _EndContentWidget(QWidget):
    def __init__(self, parent=None):
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
