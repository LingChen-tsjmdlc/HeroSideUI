"""等宽字体加载：默认内置 Maple Mono NF CN，支持用户传自定义字体路径。

CodeBlock 代码区需要等宽字体保证对齐。这里独立于 FontProvider（它只管正文 VF），
按需把 ttf 注册进 QFontDatabase 并缓存 family 名。无 QGuiApplication 时不加载
（返回 monospace 兜底栈），避免 import 期 access violation。

关键：Qt 富文本 <pre> 的 CSS font-family 常不生效，真正让字体落地要靠 QFont +
widget.setFont()。故这里同时提供 family 名与构造好的 QFont。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "fonts"
_DEFAULT_MONO_FILE = "MapleMono-NF-CN-Medium.ttf"

_FALLBACK_MONO_CSS = "Consolas, 'Courier New', monospace"
_FALLBACK_MONO_FAMILY = "Consolas"

# 路径 → 已注册 family 名（避免重复 addApplicationFont）
_LOADED: Dict[str, str] = {}


def _load_font_family(path: Path) -> Optional[str]:
    """注册 ttf 并返回主 family 名；失败或无 app 返回 None。"""
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


def mono_family(font_path: Optional[str] = None) -> str:
    """返回代码区等宽字体的主 family 名（加载失败回退 Consolas）。"""
    path = Path(font_path) if font_path else _FONTS_DIR / _DEFAULT_MONO_FILE
    return _load_font_family(path) or _FALLBACK_MONO_FAMILY


def mono_qfont(size_px: int, font_path: Optional[str] = None) -> QFont:
    """构造代码区用的 QFont（真正让等宽字体落地的入口）。

    显式锁 Normal 字重：不设的话 QFont 在有多个 weight 变体的 family 上可能
    挑到偏细的一档，表现为"字体太细"。
    """
    font = QFont(mono_family(font_path))
    font.setPixelSize(size_px)
    font.setWeight(QFont.Weight.Normal)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    return font


__all__ = ["mono_family", "mono_qfont"]
