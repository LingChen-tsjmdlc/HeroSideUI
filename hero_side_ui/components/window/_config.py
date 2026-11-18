"""Window 的配置层：自己的值、向父窗口继承、解析后的取值与对应 setter。"""

from __future__ import annotations

import math

from ...themes import VALID_WINDOW_RADII, VALID_WINDOW_SYSTEMS, WINDOW_RADII
from ._style import clamp_title_bar_height, default_title_bar_height, platform_system

_UNSET = object()
QWIDGETSIZE_MAX = 16777215


def check_radius(value):
    """圆角取值检查：None、"system"、"sm"/"md"/"lg"，或非负有限数字；bool 不算数字。"""
    if value is None or value in VALID_WINDOW_RADII:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(
            f"radius must be None, one of {VALID_WINDOW_RADII}, or a finite number >= 0, got {value!r}"
        )


def is_custom_radius(value) -> bool:
    """是否自绘圆角（beta）：档位名 sm/md/lg 或大于 0 的数字。None、0、"system" 都是系统模式。"""
    if value is None or value == "system":
        return False
    return value in WINDOW_RADII or value > 0


def radius_to_px(value) -> float:
    """圆角值换算成像素；None、0、"system" 对应 0（系统圆角由系统画，不在此处）。"""
    if value is None or value == "system":
        return 0.0
    return float(WINDOW_RADII.get(value, value) if isinstance(value, str) else value)


def check_choice(name: str, value, valid: tuple):
    """允许 None（表示继承）或合法取值，否则抛 ValueError。"""
    if value is not None and value not in valid:
        raise ValueError(f"{name} must be one of {valid} or None, got {value!r}")


def check_int(name: str, value, *, minimum: int = 1):
    """允许 None 或不小于 minimum 的数字；bool 不算数字。"""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) < minimum:
        raise ValueError(f"{name} must be a number >= {minimum} or None, got {value!r}")


def check_bool(name: str, value):
    """允许 None 或 bool。"""
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{name} must be bool or None, got {value!r}")


class _ConfigMixin:
    """标题栏相关配置：每个窗口一份，没设的向最近的 Window 祖先继承。

    宿主类需提供 _own / _user_max / _apply_all() / _child_windows() / parentWidget()。
    """

    # ---- 继承 ----
    def _parent_window(self) -> _ConfigMixin | None:
        """向上找最近的 Window 祖先。"""
        w = self.parentWidget()
        while w is not None:
            if isinstance(w, _ConfigMixin):
                return w
            w = w.parentWidget()
        return None

    def _inherited(self, name: str):
        """自己没设就向上取父窗口生效的值；一路都没有返回 None。"""
        own = self._own[name]
        if own is not None:
            return own
        parent = self._parent_window()
        return parent._inherited(name) if parent is not None else None

    def _set_own(self, name: str, value):
        """记录自己的值并把变化推给自己与所有子窗口。"""
        self._own[name] = value
        self._config_changed()

    def _config_changed(self):
        """自己和所有子窗口重新解析配置并刷新。"""
        self._apply_all()
        for child in self._child_windows():
            child._apply_all()

    def _flag(self, name: str) -> bool:
        v = self._inherited(name)
        return True if v is None else bool(v)

    def _is_fixed_size(self) -> bool:
        """是否固定尺寸：宽高的最小值都不小于最大值（setFixedSize 的效果）。"""
        mx, my = self._user_max
        return (
            mx < QWIDGETSIZE_MAX
            and my < QWIDGETSIZE_MAX
            and self._user_min[0] >= mx
            and self._user_min[1] >= my
        )

    def _can_maximize(self) -> bool:
        """最大化是否可用：按钮开启、可缩放、且不是固定尺寸。

        Note:
            设了最大尺寸不会禁用最大化：点击时按屏幕工作区与最大尺寸算目标，见 _maximize_target。
        """
        return self._flag("show_maximize") and self._flag("resizable") and not self._is_fixed_size()

    def _visible_buttons(self) -> dict[str, bool]:
        """三个控制按钮最终是否可见。"""
        return {
            "minimize": self._flag("show_minimize"),
            "maximize": self._can_maximize(),
            "close": self._flag("show_close"),
        }

    # ---- system ----
    def set_system(self, system: str | None):
        """切换风格。

        Args:
            system: auto / windows / mac / linux；None 恢复继承。

        Raises:
            ValueError: 取值非法。
        """
        check_choice("system", system, VALID_WINDOW_SYSTEMS)
        self._set_own("system", system)

    def system(self) -> str | None:
        """自己设的风格，可能是 None（继承）。"""
        return self._own["system"]

    def resolved_system(self) -> str:
        """继承与 auto 都解析完后的实际风格：windows / mac / linux。"""
        v = self._inherited("system") or "auto"
        return platform_system() if v == "auto" else v

    # ---- radius ----
    def set_radius(self, radius: str | float | None):
        """切换圆角。同一模式内可随意切，跨模式不行（模式在构造时定）。

        Args:
            radius: "system" 系统圆角；None / 0 直角；"sm" / "md" / "lg" 或正数 = 自绘圆角（beta）。

        Raises:
            ValueError: 取值非法，或试图在系统模式与自绘模式之间切换。
        """
        check_radius(radius)
        if is_custom_radius(radius) and not self._beta:
            raise ValueError(
                "radius: 系统模式的窗口不能改成自绘圆角，请在构造时传 radius='md' 或数字"
            )
        if radius == "system" and self._beta:
            raise ValueError("radius: 自绘圆角模式的窗口不能改回 'system'，请在构造时决定")
        self._radius = radius
        self._apply_all()

    def radius(self) -> str | float | None:
        """当前设置的圆角值（原样返回，不继承父窗口）。"""
        return self._radius

    # ---- title_bar_height ----
    def set_title_bar_height(self, height: int | None):
        """设置标题栏高度。

        Args:
            height: px，最小 20；None 恢复继承。

        Raises:
            ValueError: 不是正数。
        """
        check_int("title_bar_height", height)
        self._set_own("title_bar_height", None if height is None else int(height))

    def title_bar_height(self) -> int | None:
        """自己设的标题栏高度，可能是 None（继承）。"""
        return self._own["title_bar_height"]

    def resolved_title_bar_height(self) -> int:
        """继承后的标题栏高度；都没设时按风格取标准值。"""
        v = self._inherited("title_bar_height")
        if v is None:
            return default_title_bar_height(self.resolved_system())
        return clamp_title_bar_height(v)

    # ---- controls / resizable ----
    def set_controls(self, *, minimize=_UNSET, maximize=_UNSET, close=_UNSET):
        """设置三个控制按钮的显隐，没传的保持不变。

        Args:
            minimize: 最小化按钮；None 恢复继承。
            maximize: 最大化 / 还原按钮（mac 为缩放按钮）；None 恢复继承。
            close: 关闭按钮；None 恢复继承。

        Raises:
            ValueError: 传了 bool 与 None 之外的值。
        """
        updates = {"show_minimize": minimize, "show_maximize": maximize, "show_close": close}
        updates = {k: v for k, v in updates.items() if v is not _UNSET}
        for k, v in updates.items():
            check_bool(k, v)
        if updates:
            self._own.update(updates)
            self._config_changed()

    def resolved_controls(self) -> tuple[bool, bool, bool]:
        """继承后的 (最小化, 最大化, 关闭) 开关，不含"可缩放 / 最大尺寸"的影响。"""
        return (
            self._flag("show_minimize"),
            self._flag("show_maximize"),
            self._flag("show_close"),
        )

    def set_resizable(self, resizable: bool | None):
        """设置能否缩放；False 时同时隐藏最大化。

        Args:
            resizable: None 恢复继承。
        """
        check_bool("resizable", resizable)
        self._set_own("resizable", resizable)

    def resizable(self) -> bool | None:
        """自己设的可缩放开关，可能是 None（继承）。"""
        return self._own["resizable"]

    def resolved_resizable(self) -> bool:
        """继承后的可缩放开关。"""
        return self._flag("resizable")


__all__ = [
    "QWIDGETSIZE_MAX",
    "_UNSET",
    "_ConfigMixin",
    "check_bool",
    "check_choice",
    "check_int",
    "check_radius",
    "is_custom_radius",
    "radius_to_px",
]
