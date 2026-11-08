"""Kbd 按键 token 映射：区分 backspace/delete；fn/alt 走平台路由。"""

import sys

# ============================================================
# Label / Glyph (跨平台一致)
# ============================================================

# KbdKey → 可读名称（QToolTip / abbr title 用）
KBD_KEYS_LABEL_MAP = {
    "command": "Command",
    "shift": "Shift",
    "ctrl": "Control",
    "option": "Option",
    "enter": "Enter",
    "backspace": "Backspace",
    "delete": "Delete",
    "escape": "Escape",
    "tab": "Tab",
    "capslock": "Caps Lock",
    "up": "Up",
    "right": "Right",
    "down": "Down",
    "left": "Left",
    "pageup": "Page Up",
    "pagedown": "Page Down",
    "home": "Home",
    "end": "End",
    "help": "Help",
    "space": "Space",
    "fn": "Fn",
    "win": "Win",
    "alt": "Alt",
}

# KbdKey → 字符 fallback（与 HeroUI 一致；当且仅当 SVG 缺失时回退到此）
KBD_KEYS_GLYPH_MAP = {
    "command": "\u2318",  # ⌘
    "shift": "\u21e7",  # ⇧
    "ctrl": "\u2303",  # ⌃
    "option": "\u2325",  # ⌥
    "enter": "\u21b5",  # ↵
    "backspace": "\u232b",  # ⌫
    "delete": "Del",  # Forward Delete 无统一字形，用文字
    "escape": "\u238b",  # ⎋
    "tab": "\u21e5",  # ⇥
    "capslock": "\u21ea",  # ⇪
    "up": "\u2191",  # ↑
    "right": "\u2192",  # →
    "down": "\u2193",  # ↓
    "left": "\u2190",  # ←
    "pageup": "\u21de",  # ⇞
    "pagedown": "\u21df",  # ⇟
    "home": "\u2196",  # ↖
    "end": "\u2198",  # ↘
    "help": "?",
    "space": "\u2423",  # ␣
    "fn": "Fn",
    "win": "\u2318",  # HeroUI 共用 ⌘ 字形
    "alt": "\u2325",  # HeroUI 共用 ⌥ 字形
}

# ============================================================
# Icon 路由
# ============================================================

# 跨平台共用 icon —— 绝大部分键不区分平台
_COMMON_ICON_MAP = {
    "command": "carbon--mac-command",
    "shift": "carbon--mac-shift",
    "ctrl": "qlementine-icons--key-ctrl",
    "option": "carbon--mac-option",
    "enter": "boxicons--enter",
    "backspace": "material-symbols--backspace-outline",
    "delete": "material-symbols--delete-outline",
    "escape": "bi--escape",
    "tab": "octicon--tab-24",
    "capslock": "bi--capslock",
    "up": "teenyicons--up-solid",
    "right": "teenyicons--right-solid",
    "down": "teenyicons--down-solid",
    "left": "teenyicons--left-solid",
    "pageup": "iconoir--page-up",
    "pagedown": "iconoir--page-down",
    "home": "mdi--arrow-top-left",
    "end": "mdi--arrow-bottom-right",
    "help": "material-symbols--help-outline",
    "space": "tabler--space",
    "win": "mingcute--windows-line",
}

# 平台敏感 icon —— mac / win 不同呈现
_PLATFORM_ICON_MAP = {
    "fn": {
        "mac": "ion--globe-outline",  # mac 新键盘 fn = 地球仪
        "win": "tabler--function",  # win 走 Fn 字样图标
        "linux": "tabler--function",
    },
    "alt": {
        "mac": "carbon--mac-option",  # mac 上 alt = option ⌥
        "win": "tabler--alt",  # win 走 Alt 字样图标
        "linux": "tabler--alt",
    },
}


def _detect_platform() -> str:
    """根据 sys.platform 推断当前平台 token。

    Returns:
        str: "mac" / "win" / "linux"。
    """
    p = sys.platform
    if p == "darwin":
        return "mac"
    if p.startswith("win"):
        return "win"
    return "linux"


def resolve_icon(key: str, platform: str = "auto") -> str | None:
    """根据 key + platform 取实际 icon name；找不到返回 None。

    Args:
        key: KbdKey 名称（如 "command" / "enter"）。
        platform: "auto" / "mac" / "win" / "linux"，auto 时按当前系统推断。

    Returns:
        str | None: 实际 SVG icon 名；无对应图标返回 None。
    """
    if platform == "auto":
        platform = _detect_platform()
    if platform not in ("mac", "win", "linux"):
        platform = _detect_platform()
    if key in _PLATFORM_ICON_MAP:
        return _PLATFORM_ICON_MAP[key].get(platform) or _PLATFORM_ICON_MAP[key]["mac"]
    return _COMMON_ICON_MAP.get(key)


# 全部合法 KbdKey（顺序 = LABEL_MAP 顺序，便于遍历演示）
KBD_KEY_NAMES = tuple(KBD_KEYS_LABEL_MAP.keys())

# 合法 platform token
VALID_PLATFORMS = ("auto", "mac", "win", "linux")

__all__ = [
    "KBD_KEYS_GLYPH_MAP",
    "KBD_KEYS_LABEL_MAP",
    "KBD_KEY_NAMES",
    "VALID_PLATFORMS",
    "resolve_icon",
]
