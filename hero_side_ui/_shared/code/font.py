"""等宽字体加载：默认内置 Maple Mono，独立于 FontProvider；无 QGuiApplication
时返回 monospace 兜底。同时提供 family 名与构造好的 QFont。
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "fonts"
_DEFAULT_MONO_FILE = "MapleMono-NF-CN-Medium.ttf"

_FALLBACK_MONO_CSS = "Consolas, 'Courier New', monospace"
_FALLBACK_MONO_FAMILY = "Consolas"

# 路径 → 已注册 family 名（避免重复 addApplicationFont）
_LOADED: dict[str, str] = {}


def _load_font_family(path: Path) -> str | None:
    """注册 ttf 并返回主 family 名。

    Args:
        path: 字体文件路径。

    Returns:
        已注册的 family 名；无 QGuiApplication、文件不存在、
        注册失败或无可用 family 时返回 None。

    Note:
        结果按路径缓存进 _LOADED，避免重复 addApplicationFont。
    """
    if QGuiApplication.instance() is None:
        return None
    key = os.fspath(path)
    if key in _LOADED:
        return _LOADED[key]
    if not path.is_file():
        return None
    font_id = QFontDatabase.addApplicationFont(key)
    if font_id < 0:
        return None
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        return None
    _LOADED[key] = families[0]
    return families[0]


def mono_family(font_path: str | None = None) -> str:
    """返回代码区等宽字体的主 family 名。

    Args:
        font_path: 自定义字体路径；None 用内置 Maple Mono。

    Returns:
        已加载字体的 family 名；加载失败回退 Consolas。
    """
    path = Path(font_path) if font_path else _FONTS_DIR / _DEFAULT_MONO_FILE
    return _load_font_family(path) or _FALLBACK_MONO_FAMILY


def mono_qfont(size_px: int, font_path: str | None = None) -> QFont:
    """构造代码区 QFont。

    Args:
        size_px: 字号，单位像素。
        font_path: 自定义字体路径；None 用内置 Maple Mono。

    Returns:
        固定间距、Monospace style hint 的 QFont。

    Note:
        显式锁 Normal 字重，防止字体族里挑到偏细变体。
    """
    font = QFont(mono_family(font_path))
    font.setPixelSize(size_px)
    font.setWeight(QFont.Weight.Normal)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    return font


__all__ = ["mono_family", "mono_qfont"]
