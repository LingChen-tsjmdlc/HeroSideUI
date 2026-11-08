"""Pagination 颜色与几何解析：variant/color/radius 复合规则 → QColor/px。"""

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS, RADIUS

# ============================================================
# default 语义 token: dark 模式色阶反转
# HeroUI v2 dark 主题下 default-N 是反向映射:
#   50↔900, 100↔800, 200↔700, 300↔600, 400↔500
# 例 light default-100=#f4f4f5  ↔  dark default-100=#27272a (=palette[800])
# ============================================================

_DARK_MIRROR = {
    50: 900,
    100: 800,
    200: 700,
    300: 600,
    400: 500,
    500: 400,
    600: 300,
    700: 200,
    800: 100,
    900: 50,
}


def _default_token(n: int, theme: str) -> str:
    """按主题取 default-N: light 直接取,dark 用对称镜像。"""
    palette = HEROUI_COLORS["default"]
    if theme == "light":
        return palette[n]
    return palette[_DARK_MIRROR.get(n, n)]


# ============================================================
# Cursor 颜色（cursor 永远是 solid 风格 = bg-{color} text-{color}-foreground）
# ============================================================


def resolve_cursor_fill(color: str, theme: str) -> QColor:
    """取 cursor 填充色：default 取反差中灰，其余色取 colors[500]。"""
    if color == "default":
        return QColor(_default_token(300, theme))
    return QColor(HEROUI_COLORS[color][500])


def resolve_cursor_text(color: str, theme: str) -> QColor:
    """cursor 上文字色 = text-{color}-foreground。"""
    if color == "default":
        # text-default-foreground: light=黑, dark=白
        return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
    if color == "warning":
        # warning 反差为黑色
        return QColor("#000000")
    return QColor("#FFFFFF")


# ============================================================
# Item 颜色（item 由 variant 决定底色 / 边框 / 文字色）
# ============================================================


def resolve_item_text(theme: str) -> QColor:
    """普通 item 文字色 = text-default-foreground。"""
    return QColor("#000000") if theme == "light" else QColor("#FFFFFF")


def resolve_item_disabled_text(theme: str) -> QColor:
    """禁用 item 文字色 = text-default-300。"""
    return QColor(_default_token(300, theme))


def resolve_item_bg(
    variant: str, theme: str, *, hover: bool, pressed: bool, active: bool
) -> QColor | None:
    """取 item 底色（透明返回 None），flat/bordered/light/faded 各态对齐 HeroUI。

    Args:
        variant: flat/bordered/light/faded。
        theme: light/dark。
        hover: 悬停态。
        pressed: 按压态。
        active: 选中项由 cursor 接管，自身透明。
    """
    if active:
        return None

    if variant in ("flat", "faded"):
        if pressed:
            return QColor(_default_token(300, theme))
        if hover:
            return QColor(_default_token(200, theme))
        return QColor(_default_token(100, theme))

    if variant == "bordered":
        if pressed:
            return QColor(_default_token(200, theme))
        if hover:
            return QColor(_default_token(100, theme))
        return None  # 透明

    if variant == "light":
        if pressed:
            return QColor(_default_token(200, theme))
        if hover:
            return QColor(_default_token(100, theme))
        return None  # 透明

    return None


def resolve_item_border(variant: str, theme: str) -> QColor | None:
    """item 边框色（None=无边框）。bordered/faded 用 border-default 色。

    border-default: light=default-300, dark=反转 default-200/300 (=palette[700])
    """
    if variant in ("bordered", "faded"):
        return QColor(_default_token(200, theme))
    return None


# ============================================================
# Radius 解析
# ============================================================


def resolve_radius_px(radius: str, height: int) -> int:
    """rounded token 转像素：none 0 / sm 8 / md 12 / lg 14 / full 为半高。"""
    if radius == "none":
        return 0
    if radius == "full":
        return max(int(height) // 2, 4)
    # themes/radius.py 的 token 形如 "8px",剥掉单位后转 int
    raw = RADIUS.get(radius, RADIUS["md"])
    return int(float(str(raw).rstrip("px")))


def resolve_compact_corners(
    is_compact: bool,
    is_first: bool,
    is_last: bool,
    radius_px: int,
) -> tuple[int, int, int, int]:
    """isCompact 模式下,中间 item 无圆角,首/尾仅外侧两角圆角。

    返回 (tl, tr, br, bl) 四角圆角值。
    """
    if not is_compact:
        return (radius_px, radius_px, radius_px, radius_px)
    if is_first and is_last:
        return (radius_px, radius_px, radius_px, radius_px)
    if is_first:
        # 仅左侧两角
        return (radius_px, 0, 0, radius_px)
    if is_last:
        # 仅右侧两角
        return (0, radius_px, radius_px, 0)
    return (0, 0, 0, 0)


__all__ = [
    "resolve_compact_corners",
    "resolve_cursor_fill",
    "resolve_cursor_text",
    "resolve_item_bg",
    "resolve_item_border",
    "resolve_item_disabled_text",
    "resolve_item_text",
    "resolve_radius_px",
]
