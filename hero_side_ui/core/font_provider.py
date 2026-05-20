"""全局字体管理器 (FontProvider)。完整设计与 API 见 ``docs/font_provider.md``。

关键约束（容易踩的坑）：
- 只走 ``setStyleName(<原生 instance>)`` 选 VF 档；不做 wght 轴插值（思源 VF 上插值不分明）。
- 任意 int weight 按 ``_WEIGHT_BUCKETS`` 区间兜底到 6 档之一；非 VF / 第三方 family 时返 None。
- VF 加载会暴露形如 ``Source Han Sans CN VF Light`` 的幽灵 family，靠 ``_is_ghost_family`` 过滤。
- 模块 import 期没有 QGuiApplication 就 ``addApplicationFont`` 会 access violation；
  ``ensure_loaded`` 必须每次 ``instance()`` 都跑（幂等），首次 app 缺失时 _不_ 标 _loaded=True_。
"""

from __future__ import annotations

import os
import warnings
import weakref
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

# ============================================================
# 常量: 字体文件夹，字体文件名，字体 family 名
# ============================================================

_FONTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
_VF_FONT_FILE = "SourceHanSansCN-VF.ttf"
_VF_FAMILY_NAME = "Source Han Sans CN VF"

# VF 6 档物理 instance：styleName -> Qt weight
_NATIVE_INSTANCES: Dict[str, int] = {
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "Bold": 700,
    "Heavy": 900,
}

# 任意 weight 兜底到 6 档：(上界, styleName, rendered_weight)
_WEIGHT_BUCKETS = (
    (250, "ExtraLight", 200),
    (350, "Light", 300),
    (450, "Regular", 400),
    (600, "Medium", 500),
    (800, "Bold", 700),
    (1000, "Heavy", 900),
)

_FALLBACK_FAMILY_CSS = (
    '"Inter", "SF Pro Display", -apple-system, '
    '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
)


def _is_ghost_family(name: str, base: str) -> bool:
    # VF 加载会暴露 "<base> ExtraLight" 这类 fvar named-instance family，跳过。
    return bool(name) and name != base and name.startswith(base + " ")


class FontProvider(QObject):
    """全局字体管理器（单例）。"""

    family_changed = Signal(str)
    base_size_changed = Signal(int)

    _instance: Optional["FontProvider"] = None

    def __init__(self) -> None:
        super().__init__()
        self._loaded: bool = False
        self._builtin_ok: bool = False
        self._font_id: int = -1
        self._family: str = _VF_FAMILY_NAME
        self._base_size_px: int = 16
        self._widgets: "weakref.WeakSet" = weakref.WeakSet()

    # ------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------

    @classmethod
    def instance(cls) -> "FontProvider":
        if cls._instance is None:
            cls._instance = FontProvider()
        cls._instance.ensure_loaded()
        return cls._instance

    # ------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------

    @property
    def family(self) -> str:
        return self._family

    @property
    def builtin_loaded(self) -> bool:
        return self._builtin_ok

    @property
    def base_size_px(self) -> int:
        return self._base_size_px

    @property
    def native_instances(self) -> Dict[str, int]:
        return dict(_NATIVE_INSTANCES)

    # ------------------------------------------------------------
    # 加载 VF
    # ------------------------------------------------------------

    def ensure_loaded(self) -> bool:
        # 幂等；没 QGuiApplication 时直接返回，不能标 _loaded（要等 app 起来再试）。
        if self._loaded:
            return self._builtin_ok

        if QGuiApplication.instance() is None:
            self._family = _FALLBACK_FAMILY_CSS
            return False

        self._loaded = True

        vf_path = _FONTS_DIR / _VF_FONT_FILE
        if not vf_path.is_file():
            warnings.warn(
                f"[HeroSideUI] FontProvider: VF font not found at {vf_path}; "
                "fallback to Inter/system stack.",
                stacklevel=2,
            )
            self._family = _FALLBACK_FAMILY_CSS
            return False

        font_id = QFontDatabase.addApplicationFont(os.fspath(vf_path))
        if font_id < 0:
            warnings.warn(
                f"[HeroSideUI] FontProvider: Qt rejected {_VF_FONT_FILE}; "
                "fallback to Inter/system stack.",
                stacklevel=2,
            )
            self._family = _FALLBACK_FAMILY_CSS
            return False

        self._font_id = font_id
        families = QFontDatabase.applicationFontFamilies(font_id)

        # 选主 family：精确匹配 _VF_FAMILY_NAME；否则取第一个非幽灵 ASCII family
        main_fam: Optional[str] = None
        for fam in families:
            if fam == _VF_FAMILY_NAME:
                main_fam = fam
                break
        if main_fam is None:
            for fam in families:
                if fam.isascii() and not _is_ghost_family(fam, _VF_FAMILY_NAME):
                    main_fam = fam
                    break
        if main_fam is None and families:
            main_fam = families[0]

        if main_fam is None:
            self._family = _FALLBACK_FAMILY_CSS
            return False

        self._family = main_fam
        self._builtin_ok = True
        return True

    # ------------------------------------------------------------
    # family / 字体栈
    # ------------------------------------------------------------

    def font_family_css(self) -> str:
        if not self._builtin_ok and self._family == _FALLBACK_FAMILY_CSS:
            return _FALLBACK_FAMILY_CSS
        return f'"{self._family}", {_FALLBACK_FAMILY_CSS}'

    def set_family(self, family: str) -> None:
        new_family = (family or "").strip()
        if not new_family:
            new_family = _VF_FAMILY_NAME if self._builtin_ok else _FALLBACK_FAMILY_CSS
        if new_family == self._family:
            return
        self._family = new_family
        self._broadcast_font_changed()
        self.family_changed.emit(new_family)

    # ------------------------------------------------------------
    # 字重解析
    # ------------------------------------------------------------

    def style_for_weight(self, weight: int) -> Optional[str]:
        # 非 VF / VF 加载失败时返回 None，调用方就别走 setStyleName 了。
        if not self._builtin_ok or self._family != _VF_FAMILY_NAME:
            return None
        w = max(1, min(1000, int(weight)))
        for upper, style, _ in _WEIGHT_BUCKETS:
            if w <= upper:
                return style
        return _WEIGHT_BUCKETS[-1][1]

    def resolve_qfont_weight(self, weight: int) -> int:
        # 非 VF 时透传 clamp，仅做语义提示。
        if not self._builtin_ok or self._family != _VF_FAMILY_NAME:
            return max(1, min(1000, int(weight)))
        w = max(1, min(1000, int(weight)))
        for upper, _, rendered in _WEIGHT_BUCKETS:
            if w <= upper:
                return rendered
        return _WEIGHT_BUCKETS[-1][2]

    # ------------------------------------------------------------
    # 基准字号
    # ------------------------------------------------------------

    def set_base_size_px(self, px: int) -> None:
        new_px = max(1, int(px))
        if new_px == self._base_size_px:
            return
        self._base_size_px = new_px
        self._broadcast_font_changed()
        self.base_size_changed.emit(new_px)

    # ------------------------------------------------------------
    # 组件注册
    # ------------------------------------------------------------

    def register(self, widget) -> None:
        if not (hasattr(widget, "_apply_font") or hasattr(widget, "set_font_family")):
            raise TypeError(
                f"Widget {widget!r} has neither _apply_font() nor set_font_family(); "
                "cannot register to FontProvider."
            )
        self._widgets.add(widget)

    def unregister(self, widget) -> None:
        self._widgets.discard(widget)

    def is_registered(self, widget) -> bool:
        return widget in self._widgets

    @property
    def registered_count(self) -> int:
        return len(self._widgets)

    def _broadcast_font_changed(self) -> None:
        for w in list(self._widgets):
            try:
                if hasattr(w, "_apply_font"):
                    w._apply_font()
                else:
                    w.set_font_family(self._family)
            except Exception:
                pass

    # ------------------------------------------------------------
    # 测试用
    # ------------------------------------------------------------

    @classmethod
    def _reset_for_test(cls) -> None:
        if cls._instance is not None:
            if cls._instance._font_id >= 0:
                try:
                    QFontDatabase.removeApplicationFont(cls._instance._font_id)
                except Exception:
                    pass
            cls._instance._widgets.clear()
            cls._instance.deleteLater()
        cls._instance = None

    # ------------------------------------------------------------
    # 诊断
    # ------------------------------------------------------------

    def dump_diagnostics(self) -> str:
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("[FontProvider] Diagnostics")
        lines.append("=" * 60)
        lines.append(f"builtin_loaded     = {self._builtin_ok}")
        lines.append(f"main family        = {self._family!r}")
        lines.append(f"base_size_px       = {self._base_size_px}")
        lines.append(f"font_id            = {self._font_id}")
        lines.append(f"native instances   = {_NATIVE_INSTANCES}")
        if QGuiApplication.instance() is not None and self._font_id >= 0:
            fams = QFontDatabase.applicationFontFamilies(self._font_id)
            lines.append(f"  fid={self._font_id} -> families={fams}")
            if self._family and not self._family.startswith('"'):
                styles = QFontDatabase.styles(self._family)
                lines.append(f"  {self._family!r} -> styles={styles}")
        else:
            lines.append("  (QGuiApplication not yet created, skip queries)")
        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# QFont 工厂
# ============================================================


def make_qfont(
    *,
    size_px: Optional[int] = None,
    weight: int = int(QFont.Weight.Normal),
) -> QFont:
    """生成 QFont；VF 模式下走 setStyleName 精确选档，setWeight 仅语义提示。"""
    provider = FontProvider.instance()
    f = QFont(provider.family)
    f.setPixelSize(size_px if size_px is not None else provider.base_size_px)

    rendered_weight = provider.resolve_qfont_weight(weight)
    f.setWeight(QFont.Weight(rendered_weight))

    style = provider.style_for_weight(weight)
    if style:
        f.setStyleName(style)
    return f


__all__ = ["FontProvider", "make_qfont"]
