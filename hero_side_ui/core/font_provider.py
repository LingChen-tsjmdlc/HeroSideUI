"""FontProvider 全局字体管理器；设计见 docs/font_provider.md。

只走 setStyleName 选 VF 原生 6 档；int weight 按区间兜底；幽灵 family
过滤；ensure_loaded 幂等（app 缺失不标 loaded）。
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication

from ..themes.font import DEFAULT_FONT_FAMILY
from ._registry import WidgetRegistry

# ============================================================
# 常量: 字体文件夹，字体文件名，字体 family 名
# ============================================================

_FONTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"
_VF_FONT_FILE = "SourceHanSansCN-VF.ttf"
_VF_FAMILY_NAME = "Source Han Sans CN VF"

# VF 6 档物理 instance：styleName -> Qt weight
_NATIVE_INSTANCES: dict[str, int] = {
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

_FALLBACK_FAMILY_CSS = DEFAULT_FONT_FAMILY


def _is_ghost_family(name: str, base: str) -> bool:
    """判断是否为 VF 命名实例派生出的幽灵 family 名。"""
    # VF 加载会暴露 "<base> ExtraLight" 这类 fvar named-instance family，跳过。
    return bool(name) and name != base and name.startswith(base + " ")


class FontProvider(QObject):
    """全局字体管理器（单例）。"""

    family_changed = Signal(str)
    base_size_changed = Signal(int)

    _instance: FontProvider | None = None

    def __init__(self) -> None:
        """初始化字体状态、默认 family 与组件弱引用集合。"""
        super().__init__()
        self._loaded: bool = False
        self._builtin_ok: bool = False
        self._font_id: int = -1
        self._family: str = _VF_FAMILY_NAME
        self._base_size_px: int = 16
        self._widgets = WidgetRegistry("FontProvider")

    # ------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------

    @classmethod
    def instance(cls) -> FontProvider:
        """获取全局单例并确保字体已加载。"""
        if cls._instance is None:
            cls._instance = FontProvider()
        cls._instance.ensure_loaded()
        return cls._instance

    # ------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------

    @property
    def family(self) -> str:
        """当前全局字体 family。"""
        return self._family

    @property
    def builtin_loaded(self) -> bool:
        """内置 VF 字体是否加载成功。"""
        return self._builtin_ok

    @property
    def base_size_px(self) -> int:
        """全局基准字号（px）。"""
        return self._base_size_px

    @property
    def native_instances(self) -> dict[str, int]:
        """VF 原生字重档位映射的副本。"""
        return dict(_NATIVE_INSTANCES)

    # ------------------------------------------------------------
    # 加载 VF
    # ------------------------------------------------------------

    def ensure_loaded(self) -> bool:
        """加载内置 VF 字体并选定主 family，返回是否加载成功。

        Returns:
            内置 VF 字体是否可用。

        Note:
            无 QGuiApplication 时直接返回且不标记加载完成，待应用就绪后重试。
        """
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
        main_fam: str | None = None
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
        """返回带系统字体栈回退的 CSS font-family 串。"""
        if not self._builtin_ok and self._family == _FALLBACK_FAMILY_CSS:
            return _FALLBACK_FAMILY_CSS
        return f'"{self._family}", {_FALLBACK_FAMILY_CSS}'

    def set_family(self, family: str) -> None:
        """设置全局字体 family 并广播变更，空串回落到默认值。"""
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

    def style_for_weight(self, weight: int) -> str | None:
        """把字重映射到 VF 原生 styleName，非 VF 时返回 None。

        Args:
            weight: 目标字重，内部先夹紧到 1~1000。

        Returns:
            对应的原生 styleName；非内置 VF 字体时返回 None。

        Note:
            非 VF 时返回 None 以提示调用方跳过 setStyleName。
        """
        # 非 VF / VF 加载失败时返回 None，调用方就别走 setStyleName 了。
        if not self._builtin_ok or self._family != _VF_FAMILY_NAME:
            return None
        w = max(1, min(1000, int(weight)))
        for upper, style, _ in _WEIGHT_BUCKETS:
            if w <= upper:
                return style
        return _WEIGHT_BUCKETS[-1][1]

    def resolve_qfont_weight(self, weight: int) -> int:
        """把字重解析为实际渲染的 Qt weight。

        Args:
            weight: 目标字重，非 VF 时仅夹紧到 1~1000 后透传。

        Returns:
            实际用于 QFont 的 Qt weight 值。
        """
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
        """设置全局基准字号并广播变更。"""
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
        """注册需要跟随字体变更刷新的组件。

        Args:
            widget: 需提供 _apply_font() 或 set_font_family() 方法的组件。

        Note:
            两者皆无时会抛 TypeError，避免无法刷新的组件被登记。
            _apply_font() 负责按当前 family 与基准字号重算自身字体，
            字体影响尺寸时同时刷新几何。
        """
        if not (hasattr(widget, "_apply_font") or hasattr(widget, "set_font_family")):
            raise TypeError(
                f"Widget {widget!r} has neither _apply_font() nor set_font_family(); "
                "cannot register to FontProvider."
            )
        self._widgets.add(widget)

    def unregister(self, widget) -> None:
        """注销已注册的组件。"""
        self._widgets.discard(widget)

    def is_registered(self, widget) -> bool:
        """判断组件是否已注册。"""
        return widget in self._widgets

    @property
    def registered_count(self) -> int:
        """当前已注册组件数量。"""
        return len(self._widgets)

    def _broadcast_font_changed(self) -> None:
        """向所有已注册组件广播字体变更。"""
        self._widgets.broadcast(self._push_font_to_widget)

    def _push_font_to_widget(self, widget) -> None:
        """通知单个组件刷新字体。"""
        if hasattr(widget, "_apply_font"):
            widget._apply_font()
        else:
            widget.set_font_family(self._family)

    # ------------------------------------------------------------
    # 测试用
    # ------------------------------------------------------------

    @classmethod
    def _reset_for_test(cls) -> None:
        """移除已加载字体并复位单例，仅供测试。"""
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
        """返回当前字体加载状态的诊断文本。"""
        lines: list[str] = []
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
    size_px: int | None = None,
    weight: int = int(QFont.Weight.Normal),
    style_name: bool = True,
) -> QFont:
    """生成 QFont；VF 下 setStyleName 精确选档。

    Args:
        size_px: 像素字号。
        weight: 字重。
        style_name: False 不锁 styleName，供富文本 <b>/<i> 自由切档。

    Returns:
        构造好的 QFont。
    """
    provider = FontProvider.instance()
    f = QFont(provider.family)
    f.setPixelSize(size_px if size_px is not None else provider.base_size_px)

    # 关闭 hinting：Windows 默认 full hinting 会把横向 stem 吸附到整像素网格，
    # 在正文小字号下横笔画被加权显粗、竖/斜笔画不受影响（视觉粗细不匀）。
    # 改走几何轮廓 + 抗锯齿，横竖粗细一致。
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

    rendered_weight = provider.resolve_qfont_weight(weight)
    f.setWeight(QFont.Weight(rendered_weight))

    if style_name:
        style = provider.style_for_weight(weight)
        if style:
            f.setStyleName(style)
    return f


__all__ = ["FontProvider", "make_qfont"]
