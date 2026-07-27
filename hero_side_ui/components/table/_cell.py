"""Table 单元格（自绘）。

对齐 HeroUI v2 table.ts 的 ``td`` slot：每个单元格自己绘制 ``before`` 行条背景
（选中 / hover / 斑马纹），并根据"首列/尾列 + 首行/中行/尾行 + 是否多选"拼接圆角，
还原 HeroUI 的 ``rounded-s-lg`` / ``rounded-ss-lg`` 等角拼接逻辑。

单元格内容是真正的子 widget（Text 或用户自定义 QWidget），放在 cell 内部 layout 中，
绘制在 before 背景之上。行状态由父 Table 通过 ``set_row_state`` 推入，状态变化时
cell 平滑过渡 before 背景色。
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ...animation.tween import tween_value
from ...utils import safe_delete
from ...utils.color_utils import aligned_color_pair
from ..text import Text
from . import _palette as pal
from ._constants import VALID_ALIGNS

_TRANSPARENT = QColor(0, 0, 0, 0)
_HOVER_ANIM_MS = 150

_ALIGN_FLAGS = {
    "start": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    "center": Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
    "end": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
}


def _corner_radii(
    *,
    is_multi: bool,
    is_first_row: bool,
    is_last_row: bool,
    is_first_col: bool,
    is_last_col: bool,
    r: int,
) -> Tuple[int, int, int, int]:
    """计算 before 行条四角圆角 (tl, tr, br, bl)，对齐 table.ts。

    - 单选 / 无选择：每行独立药丸 —— 首列左两角圆、尾列右两角圆（first:before:rounded-s-lg）。
    - 多选 / hover：整块连续 —— 仅表格首行上两角圆、尾行下两角圆，中间行全直角
      （isMultiSelectable：group-data-[first]/last/middle）。这样连续选中区是一整块，
      不会每行都鼓起圆角形成起伏边缘。
    """
    tl = tr = br = bl = 0
    if not is_multi:
        if is_first_col:
            tl = bl = r
        if is_last_col:
            tr = br = r
        return (tl, tr, br, bl)

    # 多选：圆角只出现在整张表的四个外角
    if is_first_row:
        if is_first_col:
            tl = r
        if is_last_col:
            tr = r
    if is_last_row:
        if is_first_col:
            bl = r
        if is_last_col:
            br = r
    return (tl, tr, br, bl)


def _rounded_path(rect: QRectF, tl: int, tr: int, br: int, bl: int) -> QPainterPath:
    """构造四角独立圆角的矩形路径。"""
    path = QPainterPath()
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    path.moveTo(x + tl, y)
    path.lineTo(x + w - tr, y)
    if tr:
        path.quadTo(x + w, y, x + w, y + tr)
    path.lineTo(x + w, y + h - br)
    if br:
        path.quadTo(x + w, y + h, x + w - br, y + h)
    path.lineTo(x + bl, y + h)
    if bl:
        path.quadTo(x, y + h, x, y + h - bl)
    path.lineTo(x, y + tl)
    if tl:
        path.quadTo(x, y, x + tl, y)
    path.closeSubpath()
    return path


class _TableCell(QWidget):
    """表格数据单元格。内容 widget + 自绘 before 行条背景。"""

    def __init__(self, content=None, *, align: str = "start", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 竖直 Preferred（非 Fixed）：让本格被 QGridLayout 拉伸填满整行高度。
        # 否则纯文本格停在 sizeHint 高度居中，而含按钮的格更高撑高整行，
        # 各格的 before 行条只画自身 rect → 选中条左右高度不齐。
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        if align not in VALID_ALIGNS:
            align = "start"
        self._align = align

        # 样式状态（由 Table.apply_style 注入）
        self._color = "default"
        self._size = "md"
        self._theme = "light"
        self._radius = "lg"
        self._is_striped = False
        self._is_compact = False
        self._is_multi = False
        self._disable_animation = False

        # 行状态（由 Table.set_row_state 推入）
        self._row_hover = False
        self._row_selected = False
        self._row_odd = False
        self._row_disabled = False
        self._is_first_row = False
        self._is_last_row = False
        self._is_first_col = False
        self._is_last_col = False

        # 当前过渡中的 before 背景色
        self._cur_before = QColor(_TRANSPARENT)

        # 行交互回调（由 Table 注入）：上报 hover / click 给所属行
        self._row_key: Optional[str] = None
        self._hover_report = None  # callable(row_key, entered: bool)
        self._click_report = None  # callable(row_key)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(_ALIGN_FLAGS[self._align])

        self._content: Optional[QWidget] = None
        self.set_content(content)

    # ------------------------------------------------------------
    # 内容
    # ------------------------------------------------------------
    def set_content(self, content):
        """设置单元格内容；str → 包 Text，QWidget → 直接放，None → 空。"""
        if self._content is not None:
            self._layout.removeWidget(self._content)
            safe_delete(self._content)
            self._content = None
        if content is None:
            return
        if isinstance(content, QWidget):
            self._content = content
        else:
            self._content = Text(str(content), theme="auto")
        self._content.setParent(self)
        self._layout.addWidget(self._content)
        self._refresh_content_style()

    def update_content(self, content):
        """行复用专用：尽量原地更新内容，避免销毁重建子 widget。

        - 当前是 Text 且新内容是纯文本 → 只 set_text（最省，不动 widget 树）。
        - 其余情况（QWidget 内容、类型不匹配）→ 回退到 set_content 重建。
        复用能显著降低翻页 / 滚动时的重建开销。
        """
        if (
            isinstance(self._content, Text)
            and not isinstance(content, QWidget)
        ):
            self._content.setText(str(content) if content is not None else "")
            self._refresh_content_style()
            return
        self.set_content(content)

    def content(self) -> Optional[QWidget]:
        return self._content

    # ------------------------------------------------------------
    # 行交互绑定
    # ------------------------------------------------------------
    def bind_row(self, row_key: str, hover_report, click_report):
        """绑定所属行 key 与上报回调。"""
        self._row_key = row_key
        self._hover_report = hover_report
        self._click_report = click_report
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def rebind_row(self, row_key: str):
        """行复用专用：只换 row_key，保留已绑定的回调，不重设属性。"""
        self._row_key = row_key

    def enterEvent(self, e):
        if self._hover_report and self._row_key is not None:
            self._hover_report(self._row_key, True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._hover_report and self._row_key is not None:
            self._hover_report(self._row_key, False)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if (
            self._click_report
            and self._row_key is not None
            and e.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(e.pos())
        ):
            self._click_report(self._row_key)
        super().mouseReleaseEvent(e)

    # ------------------------------------------------------------
    # 样式注入（Table → cell）
    # ------------------------------------------------------------
    def apply_style(
        self,
        *,
        color: str,
        size: str,
        theme: str,
        radius: str,
        is_striped: bool,
        is_compact: bool,
        is_multi: bool,
        align: str,
        disable_animation: bool,
    ):
        # 幂等守卫：样式维度全未变时跳过整段重设——虚拟滚动每帧每格都调本方法，
        # 但滚动只换内容不换样式（内容走 update_content、行状态走 set_row_state，
        # 均独立于此）。跳过可省下 margins/sizeHint/height/字体/颜色的高频重算。
        sig = (color, size, theme, radius, is_striped, is_compact,
               is_multi, align, disable_animation)
        if sig == getattr(self, "_style_sig", None):
            return
        self._style_sig = sig

        self._color = color
        self._size = size
        self._theme = theme
        self._radius = radius
        self._is_striped = is_striped
        self._is_compact = is_compact
        self._is_multi = is_multi
        self._disable_animation = disable_animation
        if align in VALID_ALIGNS:
            self._align = align
            self._layout.setAlignment(_ALIGN_FLAGS[self._align])

        from ...themes import TABLE_SIZES

        cfg = TABLE_SIZES.get(size, TABLE_SIZES["md"])
        py = cfg["compact_padding_y"] if is_compact else cfg["cell_padding_y"]
        px = cfg["cell_padding_x"]
        self._layout.setContentsMargins(px, py, px, py)
        # 行高由内容撑开：最小高度取 (token 行高) 与 (内容 sizeHint + 上下 padding) 的较大者，
        # 不再钉死 token 值，否则头像/多行文字等高内容会被截断。
        content_h = 0
        if self._content is not None:
            content_h = self._content.sizeHint().height() + 2 * py
        floor_h = 0 if is_compact else cfg["row_min_height"]
        self.setMinimumHeight(max(floor_h, content_h))
        self._refresh_content_style()
        self._refresh_before(animated=False)

    def set_position(
        self, *, is_first_row: bool, is_last_row: bool, is_first_col: bool, is_last_col: bool
    ):
        self._is_first_row = is_first_row
        self._is_last_row = is_last_row
        self._is_first_col = is_first_col
        self._is_last_col = is_last_col
        self.update()

    def set_row_state(
        self, *, hover: bool, selected: bool, odd: bool, disabled: bool, animated: bool = True
    ):
        bg_changed = (
            hover != self._row_hover
            or selected != self._row_selected
            or odd != self._row_odd
            or disabled != self._row_disabled
        )
        # 字色只受 selected / disabled 影响（hover 不改字色）；仅这两者变化时才重算，
        # 避免单纯 hover 触发整行字体/颜色重建 → 大表掉帧。
        text_changed = (
            selected != self._row_selected or disabled != self._row_disabled
        )
        self._row_hover = hover
        self._row_selected = selected
        self._row_odd = odd
        self._row_disabled = disabled
        if bg_changed:
            self._refresh_before(animated=animated and not self._disable_animation)
        if text_changed:
            self._refresh_text_color()

    # ------------------------------------------------------------
    # 内容样式（字体 / 字色）
    # ------------------------------------------------------------
    def _refresh_content_style(self):
        """完整刷新内容字体 + 字色（仅 apply_style 调，含字号重建）。"""
        if not isinstance(self._content, Text):
            return
        from ...themes import TABLE_SIZES

        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        self._content.set_size(cfg["font_size"])
        self._refresh_text_color()

    def _refresh_text_color(self):
        """只刷字色（hover/选中切换走这里，不重建字体）。"""
        if not isinstance(self._content, Text):
            return
        # 选中行字色走 color variant；禁用行灰一档；否则默认前景色
        if self._row_disabled:
            c = pal.cell_text_disabled(self._theme)
        elif self._row_selected:
            c = pal.selected_text(self._color, self._theme)
        else:
            c = pal.cell_text(self._theme)
        self._content.set_color(c.name())

    # ------------------------------------------------------------
    # before 行条背景
    # ------------------------------------------------------------
    def _target_before(self) -> QColor:
        """当前应显示的 before 背景色（优先级：选中 > 斑马奇行 > hover）。"""
        if self._row_disabled:
            # disabled 行仍显示斑马纹底，但不响应 hover/selected
            if self._is_striped and self._row_odd:
                return pal.striped_before_bg(self._theme)
            return QColor(_TRANSPARENT)
        if self._row_selected:
            return pal.selected_before_bg(self._color, self._theme)
        if self._is_striped and self._row_odd:
            return pal.striped_before_bg(self._theme)
        if self._row_hover:
            return pal.hover_before_bg(self._theme)
        return QColor(_TRANSPARENT)

    def _refresh_before(self, *, animated: bool):
        target = self._target_before()
        if not animated:
            self._cur_before = target
            self.update()
            return
        start, end = aligned_color_pair(self._cur_before, target)
        tween_value(
            self,
            "_before_anim_runner",
            start,
            end,
            self._on_before_step,
            duration=_HOVER_ANIM_MS,
        )

    def _on_before_step(self, c):
        self._cur_before = QColor(c)
        self.update()

    # ------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------
    def paintEvent(self, e):
        if self._cur_before.alpha() <= 0:
            return
        cfg_r = pal.resolve_radius_px(self._radius, self.height())
        tl, tr, br, bl = _corner_radii(
            is_multi=self._is_multi,
            is_first_row=self._is_first_row,
            is_last_row=self._is_last_row,
            is_first_col=self._is_first_col,
            is_last_col=self._is_last_col,
            r=cfg_r,
        )
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        path = _rounded_path(rect, tl, tr, br, bl)
        p.fillPath(path, self._cur_before)


__all__ = ["_TableCell"]
