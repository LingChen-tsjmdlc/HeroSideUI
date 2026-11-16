"""输入类组件的宽度约定：建议宽度只当 sizeHint，不当最小宽度。

官方 HeroUI 的输入框没有任何像素宽度，宽度全由外层容器给。Qt 里控件没人撑会缩成一条线，
所以补一个"建议宽度"：它只影响 sizeHint（没人管时有多宽），用户 setFixedWidth /
setMinimumWidth / setMaximumWidth 一律直接生效，组件不拦截、不抬高。
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLayout, QWidget


class SuggestedWidthMixin:
    """给输入类组件提供"建议宽度"，须排在 QWidget 之前。"""

    _suggested_width = 0

    def set_suggested_width(self, w: int) -> None:
        """设置没人管它时的宽度。

        Args:
            w: 建议宽度（像素）；0 表示完全跟内容走。
        """
        w = max(0, int(w))
        if w != self._suggested_width:
            self._suggested_width = w
            self.updateGeometry()

    def suggested_width(self) -> int:
        """返回当前建议宽度（像素）。"""
        return self._suggested_width

    def sizeHint(self) -> QSize:
        """内容宽度与建议宽度取较大者。"""
        hint = super().sizeHint()
        return QSize(max(hint.width(), self._suggested_width), hint.height())


def release_width_floor(wrapper: QWidget) -> None:
    """解除外框的宽度下限，让用户设的窄宽度也能被遵守。

    Args:
        wrapper: 输入框的外框控件。

    Note:
        外框自己的 layout（左右 padding + 图标 + 文字）有最小尺寸，用户把整体设窄时，
        外框若强守这个下限，右半边会超出视口被裁；必须用 QWidget.setMinimumWidth
        （不走可能被子类重写的同名方法）并把内部 layout 切到 SetNoConstraint。
    """
    QWidget.setMinimumWidth(wrapper, 0)
    layout = wrapper.layout()
    if layout is not None:
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
