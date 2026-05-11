"""
颜色相关工具函数
"""

from PySide6.QtGui import QColor


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """将 HEX 颜色转为 rgba() 格式

    Args:
        hex_color: HEX 颜色值，如 "#006FEE"
        alpha: 透明度 0.0 ~ 1.0

    Returns:
        rgba() 格式字符串，如 "rgba(0, 111, 238, 0.5)"
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def aligned_color_pair(start: QColor, end: QColor) -> tuple[QColor, QColor]:
    """让 alpha=0 的一端继承另一端的 RGB，避免颜色 lerp 经过黑色。

    问题:
        ``QColor(0, 0, 0, 0)`` 的 RGB 是 (0, 0, 0)。对它和实色做线性插值时，
        前半段 alpha 上升的同时 RGB 也从 (0, 0, 0) 拉向目标色 → 出现"半透明
        深灰"瞬态（用户能明显感知为 hover 时一瞬间颜色很重 / leave 后还残留
        灰底）。

    解法:
        把透明端的 RGB 改写成另一端的 RGB（仅保留 alpha=0），让 lerp 全程
        沿同一色相变化，只有透明度起伏。

    用法::

        from hero_side_ui.utils import aligned_color_pair
        from hero_side_ui.animation import tween_value

        start, end = aligned_color_pair(self._cur_bg, target_bg)
        tween_value(self, "_bg_anim_runner", start, end, self._on_bg_step,
                    duration=150)

    适用任何 hover/checked/active 态在 ``transparent ↔ 实色`` 间的过渡动画
    （Listbox / Menu / Select / Autocomplete 等）。
    """
    if start.alpha() == 0 and end.alpha() != 0:
        s = QColor(end)
        s.setAlpha(0)
        return s, QColor(end)
    if end.alpha() == 0 and start.alpha() != 0:
        e = QColor(start)
        e.setAlpha(0)
        return QColor(start), e
    return QColor(start), QColor(end)
