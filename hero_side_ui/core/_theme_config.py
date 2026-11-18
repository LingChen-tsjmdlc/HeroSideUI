"""setup() 新增主题参数的校验与应用。

先校验、后生效：任何一项不合法，整体抛一个 ValueError，一次列出所有问题。
"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

from ..themes import theme_values
from ..themes.colors import HEROUI_COLORS
from ..themes.shadow import SHADOW_TIERS, Layer
from ._foreground_config import (
    check_color_foreground,
    check_foreground_hints,
)
from ._foreground_config import contrast as _contrast
from ._foreground_config import is_hex as _is_hex
from ._foreground_config import luminance as _lum

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_SURFACE_KEYS = ("background", "foreground", "content_background", "popup_background")
_FONT_EXT = (".ttf", ".otf", ".ttc")
_FONT_PX_RANGE = (8, 28)


def _is_mapping(v) -> bool:
    return isinstance(v, dict)


# ---------------------------------------------------------------- 各参数


def _check_colors(value, errors: list, warns: list) -> dict:
    """校验色板，返回 {色名: {档位: hex}}。"""
    out: dict = {}
    if not _is_mapping(value):
        errors.append("colors：必须是 {色名: 10 阶色值} 字典")
        return out
    for name, ramp in value.items():
        if name not in theme_values.COLOR_NAMES:
            errors.append(
                f"colors：未知色名 {name!r}，只能是 {', '.join(theme_values.COLOR_NAMES)}"
            )
            continue
        if _is_mapping(ramp):
            if sorted(ramp) != sorted(theme_values.COLOR_STEPS):
                errors.append(f"colors[{name!r}]：字典键必须是 50, 100 … 900 共 10 个")
                continue
            vals = [ramp[k] for k in theme_values.COLOR_STEPS]
        elif isinstance(ramp, (list, tuple)):
            if len(ramp) != 10:
                errors.append(f"colors[{name!r}]：必须写满 10 阶，当前 {len(ramp)} 个")
                continue
            vals = list(ramp)
        else:
            errors.append(f"colors[{name!r}]：必须是 10 个色值的列表或字典")
            continue
        bad = [v for v in vals if not _is_hex(v)]
        if bad:
            errors.append(f"colors[{name!r}]：色值必须是 #RRGGBB，非法：{bad}")
            continue
        lums = [_lum(v) for v in vals]
        if any(lums[i] < lums[i + 1] for i in range(9)):
            warns.append(f"colors[{name!r}]：色阶应从浅到深排列，否则暗色下镜像取色会反相")
        out[name] = dict(zip(theme_values.COLOR_STEPS, vals, strict=True))
    return out


def _check_side_pair(label: str, value, errors: list) -> dict | None:
    """校验 {"light": hex, "dark": hex}。"""
    if not _is_mapping(value) or sorted(value) != ["dark", "light"]:
        errors.append(
            f"{label}：必须同时写 light 与 dark，如 {{'light': '#RRGGBB', 'dark': '#RRGGBB'}}"
        )
        return None
    if not (_is_hex(value["light"]) and _is_hex(value["dark"])):
        errors.append(f"{label}：色值必须是 #RRGGBB")
        return None
    return {"light": value["light"], "dark": value["dark"]}


def _check_radius(value, errors: list) -> dict | None:
    """校验圆角 sm/md/lg。"""
    if not _is_mapping(value) or sorted(value) != ["lg", "md", "sm"]:
        errors.append("radius：必须同时写 sm、md、lg 三个，如 {'sm': 4, 'md': 8, 'lg': 14}")
        return None
    vals = {k: value[k] for k in ("sm", "md", "lg")}
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in vals.values()):
        errors.append("radius：值必须是非负整数 px")
        return None
    if not vals["sm"] <= vals["md"] <= vals["lg"]:
        errors.append(f"radius：要求 sm <= md <= lg，当前 {vals}")
        return None
    return vals


def _check_font_size(value, errors: list) -> dict | None:
    """校验五档字号。"""
    if not _is_mapping(value) or sorted(value) != sorted(theme_values.FONT_TIERS):
        errors.append("font_size：必须同时写 xs、sm、md、lg、xl 五档")
        return None
    lo, hi = _FONT_PX_RANGE
    vals = {k: value[k] for k in theme_values.FONT_TIERS}
    if not all(
        isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi for v in vals.values()
    ):
        errors.append(f"font_size：值必须是 {lo}~{hi} 的整数 px")
        return None
    seq = [vals[k] for k in theme_values.FONT_TIERS]
    if any(seq[i] > seq[i + 1] for i in range(4)):
        errors.append(f"font_size：要求 xs <= sm <= md <= lg <= xl，当前 {vals}")
        return None
    return vals


def _check_layer(label: str, raw, errors: list) -> Layer | None:
    """校验单层阴影。"""
    if not _is_mapping(raw):
        errors.append(f"{label}：每层必须是字典")
        return None
    extra = set(raw) - {"y", "blur", "color", "opacity", "inset"}
    miss = {"y", "blur", "color", "opacity"} - set(raw)
    if extra or miss:
        errors.append(f"{label}：缺少 {sorted(miss)} 或含未知键 {sorted(extra)}")
        return None
    y, blur, op = raw["y"], raw["blur"], raw["opacity"]
    ok = isinstance(y, (int, float)) and isinstance(blur, (int, float)) and blur >= 0
    ok = ok and isinstance(op, (int, float)) and 0 <= op <= 1 and _is_hex(raw["color"])
    if not ok:
        errors.append(f"{label}：y/blur 须为数字且 blur>=0，opacity 须在 0~1，color 须为 #RRGGBB")
        return None
    return Layer(float(y), float(blur), raw["color"], float(op), bool(raw.get("inset", False)))


def _check_shadow(value, errors: list) -> dict | None:
    """校验阴影：亮暗各 sm/md/lg，每档 1~4 层。"""
    if not _is_mapping(value) or sorted(value) != ["dark", "light"]:
        errors.append("shadow：必须同时写 light 与 dark")
        return None
    out: dict = {}
    for side in ("light", "dark"):
        tiers = value[side]
        if not _is_mapping(tiers) or sorted(tiers) != sorted(SHADOW_TIERS):
            errors.append(f"shadow[{side!r}]：必须同时写 sm、md、lg 三档")
            continue
        out[side] = {}
        for tier in SHADOW_TIERS:
            layers = tiers[tier]
            label = f"shadow[{side!r}][{tier!r}]"
            if not isinstance(layers, (list, tuple)) or not 1 <= len(layers) <= 4:
                errors.append(f"{label}：必须是 1~4 层的列表")
                continue
            parsed = [_check_layer(f"{label}[{i}]", raw, errors) for i, raw in enumerate(layers)]
            if all(parsed):
                out[side][tier] = tuple(parsed)
    if len(out) == 2 and all(len(out[s]) == 3 for s in out):
        return out
    return None


def _resolve_font(label: str, value, errors: list, builtin_loader=None) -> str | None:
    """字体名或字体文件路径 → 已注册的 family 名。"""
    from PySide6.QtGui import QFontDatabase

    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}：必须是非空字符串（字体名或字体文件路径）")
        return None
    s = value.strip()
    if builtin_loader:
        builtin_loader()
    if s.lower().endswith(_FONT_EXT) or os.sep in s or "/" in s:
        path = Path(s)
        if not path.is_file():
            errors.append(f"{label}：字体文件不存在：{s}")
            return None
        fid = QFontDatabase.addApplicationFont(str(path))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if not fams:
            errors.append(f"{label}：字体文件注册失败：{s}")
            return None
        return fams[0]
    if s in QFontDatabase.families():
        return s
    errors.append(f"{label}：找不到字体 {s!r}（未安装；若是文件请写完整路径）")
    return None


# ---------------------------------------------------------------- 总入口


def validate(
    *,
    colors=None,
    color_foreground=None,
    radius=None,
    background=None,
    foreground=None,
    content_background=None,
    popup_background=None,
    shadow=None,
    font_family=None,
    mono_family=None,
    font_size=None,
    font_base_size=None,
) -> dict:
    """校验全部新参数并产出可应用的配置。

    Args:
        colors: 色板，{色名: 10 阶}。
        color_foreground: 实色上的字色。
        radius: 三档圆角。
        background: 窗口底色 {light, dark}。
        foreground: 默认文字色。
        content_background: 内容面底色。
        popup_background: 弹出层底色。
        shadow: 阴影，亮暗各三档多层。
        font_family: 正文字体名或路径。
        mono_family: 代码字体名或路径。
        font_size: 五档字号。
        font_base_size: font_size["md"] 的简写。

    Returns:
        只含用户写了的项的配置字典；另含 "warnings" 列表与 "font_family" 解析结果。

    Raises:
        ValueError: 任一项不合法，信息里列出全部问题。
    """
    errors: list = []
    warns: list = []
    cfg: dict = {}

    if colors is not None:
        cfg["colors"] = _check_colors(colors, errors, warns)
    if color_foreground is not None:
        cfg["color_foreground"] = check_color_foreground(color_foreground, errors)
    if radius is not None:
        r = _check_radius(radius, errors)
        if r:
            cfg["radius"] = r

    surfaces: dict = {}
    given = (background, foreground, content_background, popup_background)
    for key, val in zip(_SURFACE_KEYS, given, strict=True):
        if val is not None:
            pair = _check_side_pair(key, val, errors)
            if pair:
                surfaces[key] = pair
    if surfaces:
        cfg["surfaces"] = surfaces

    # 改了色阶的色，必须同时写字色
    changed = set(cfg.get("colors", {}))
    missing = sorted(changed - set(cfg.get("color_foreground", {})))
    for name in missing:
        errors.append(f"colors：{name} 的色阶已改，请同时在 color_foreground 里写 {name!r} 的字色")

    if font_size is not None and font_base_size is not None:
        base = font_size.get("md") if _is_mapping(font_size) else None
        if base != font_base_size:
            errors.append(
                f"font_base_size={font_base_size} 与 font_size['md']={base} 不一致，只写一个即可"
            )
    if font_size is None and font_base_size is not None:
        merged = dict(theme_values.DEFAULT_FONT_SIZE)
        merged["md"] = font_base_size
        font_size = merged
    if font_size is not None:
        fs = _check_font_size(font_size, errors)
        if fs:
            cfg["font_size"] = fs
    if shadow is not None:
        sh = _check_shadow(shadow, errors)
        if sh:
            cfg["shadow"] = sh

    if font_family is not None:
        from .font_provider import FontProvider

        fam = _resolve_font(
            "font_family", font_family, errors, lambda: FontProvider.instance().ensure_loaded()
        )
        if fam:
            cfg["font_family"] = fam
    if mono_family is not None:
        from .._shared.code.font import mono_family as _builtin_mono

        fam = _resolve_font("mono_family", mono_family, errors, lambda: _builtin_mono())
        if fam:
            cfg["mono_family"] = fam

    if not errors:
        _check_order_and_contrast(cfg, warns)
    if errors:
        raise ValueError("HeroSideUIProvider.setup() 参数不合法：\n  - " + "\n  - ".join(errors))
    cfg["warnings"] = warns
    return cfg


def _check_order_and_contrast(cfg: dict, warns: list) -> None:
    """窗口底 ≤ 内容面 ≤ 弹出层的明度顺序；字色对比度提示。"""
    merged = {k: dict(v) for k, v in theme_values.DEFAULT_SURFACES.items()}
    merged.update(cfg.get("surfaces", {}))
    for side in ("light", "dark"):
        a, b, c = (
            merged[k][side] for k in ("background", "content_background", "popup_background")
        )
        if not _lum(a) <= _lum(b) <= _lum(c):
            warns.append(f"{side} 主题：窗口底、内容面、弹出层应一层比一层不暗，否则层次会倒挂")

    ramps = {n: dict(HEROUI_COLORS[n]) for n in theme_values.COLOR_NAMES}
    ramps.update(cfg.get("colors", {}))
    fg = {n: dict(v) for n, v in theme_values.DEFAULT_COLOR_FOREGROUND.items()}
    fg.update(cfg.get("color_foreground", {}))
    for name in set(cfg.get("colors", {})) | set(cfg.get("color_foreground", {})):
        for side in ("light", "dark"):
            # 只检查用户改动过的：色阶与字色都等于默认值时跳过
            if not isinstance(fg[name][side], str):
                continue  # 对象写法由 check_foreground_hints 检查
            same_ramp = ramps[name] == theme_values.DEFAULT_COLORS[name]
            if same_ramp and fg[name][side] == theme_values.DEFAULT_COLOR_FOREGROUND[name][side]:
                continue
            step = 700 if (name == "default" and side == "dark") else 500
            ratio = _contrast(fg[name][side], ramps[name][step])
            if ratio < 4.5:
                warns.append(
                    f"color_foreground[{name!r}] 的 {side} 字色与底色对比度仅 {ratio:.2f}:1（建议 ≥ 4.5）"
                )
    check_foreground_hints(cfg.get("color_foreground", {}), cfg, warns)


def apply(cfg: dict) -> None:
    """还原全部主题取值后应用配置，并输出校验警告。

    Args:
        cfg: validate 的返回值。
    """
    had_read = theme_values.was_read()
    touched = any(
        k in cfg
        for k in (
            "colors",
            "color_foreground",
            "radius",
            "surfaces",
            "font_size",
            "shadow",
            "mono_family",
        )
    )
    if touched and had_read:
        warnings.warn(
            "HeroSideUIProvider.setup() 在组件创建之后才应用主题参数：已创建的组件不会刷新，请在创建组件之前调用 setup。",
            stacklevel=4,
        )
    for text in cfg.get("warnings", []):
        warnings.warn(text, stacklevel=4)
    theme_values.reset()
    theme_values.apply(cfg)
    theme_values.clear_read_flag()
    from . import shadow_paint

    shadow_paint.clear_cache()


__all__ = ["apply", "validate"]
