"""Local icon resources and names. No Provider, network policy or Qt startup."""

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from os import PathLike
from pathlib import Path
from typing import TypeAlias
from xml.sax.saxutils import quoteattr

from pyside_iconify import IconData, IconNotFoundError, add_icon, get_icon_data

IconSource: TypeAlias = str | PathLike[str] | IconData
_PREFIX = "herosideui:"
_STROKE_WIDTH = re.compile(r"stroke-width\s*=\s*([\"'])(.*?)\1")


@lru_cache(maxsize=1)
def _builtin_index() -> dict[str, str]:
    """构建内置 SVG 图标名到文件名的索引（缓存一次）。"""
    directory = files("hero_side_ui").joinpath("resources", "icons")
    return {
        resource.name[:-4]: resource.name
        for resource in directory.iterdir()
        if resource.name.endswith(".svg")
    }


def builtin_icon_names() -> tuple[str, ...]:
    """返回全部内置图标的 legacy 名称，不下载数据。"""
    return tuple(sorted(_builtin_index()))


@lru_cache(maxsize=1)
def _aliases() -> dict[str, str]:
    """构建 legacy 名及其带前缀别名到 legacy 名的映射（缓存一次）。"""
    aliases = {}
    for legacy in _builtin_index():
        aliases[legacy] = legacy
        aliases[_PREFIX + legacy.replace("--", "-")] = legacy
        if "--" in legacy:
            aliases[legacy.replace("--", ":", 1)] = legacy
    return aliases


def _svg_data(source: str) -> IconData:
    """把 SVG 文本解析为 IconData，保留视图尺寸与根节点呈现属性。"""
    root = ET.fromstring(source)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("icon source must be an SVG document")
    if root.get("viewBox"):
        left, top, width, height = map(float, re.split(r"[\s,]+", root.attrib["viewBox"].strip()))
    else:
        left = top = 0.0
        width = float(root.get("width", "24").removesuffix("px"))
        height = float(root.get("height", "24").removesuffix("px"))
    match = re.search(
        r"<(?:[\w.-]+:)?svg\b(?P<attrs>[^>]*)>(?P<body>.*)</(?:[\w.-]+:)?svg\s*>",
        source,
        re.S,
    )
    if match is None:
        raise ValueError("icon source must contain an SVG body")
    body = match.group("body")
    attributes = {
        key: value
        for key, value in root.attrib.items()
        if key not in {"viewBox", "width", "height"} and "}" not in key
    }
    if attributes:
        props = " ".join(key + "=" + quoteattr(value) for key, value in attributes.items())
        body = f"<g {props}>{body}</g>"
    # Preserve prefixed attributes used by external SVGs, e.g. xlink:href.
    namespaces = re.findall(r"\bxmlns:([\w-]+)\s*=\s*([\"'])(.*?)\2", match.group("attrs"))
    if namespaces:
        props = " ".join(f"xmlns:{prefix}={quoteattr(uri)}" for prefix, _, uri in namespaces)
        body = f"<g {props}>{body}</g>"
    return IconData(body=body, width=width, height=height, left=left, top=top)


@lru_cache(maxsize=128)
def _builtin_data(legacy: str) -> IconData:
    """按 legacy 名读取并解析内置 SVG 图标（带缓存）。"""
    resource = files("hero_side_ui").joinpath("resources", "icons", _builtin_index()[legacy])
    return _svg_data(resource.read_text(encoding="utf-8"))


@lru_cache(maxsize=128)
def _file_data(path: str, modified_ns: int, byte_count: int) -> IconData:
    """按路径读取并解析外部 SVG 文件，缓存键含修改时间与字节数。"""
    return _svg_data(Path(path).read_text(encoding="utf-8"))


def ensure_local_icon(name: str, data: IconData) -> None:
    """幂等登记图标数据，共享缓存被逐出后仍可重新注册。"""
    try:
        if get_icon_data(name) == data:
            return
    except IconNotFoundError:
        pass
    add_icon(name, data, replace=True)


def resolve_icon(source: IconSource, *, stroke_width: float | None = None) -> str:
    """解析内置名/路径/IconData；其余 Iconify 名透传。从不联网。"""
    name = None
    if isinstance(source, IconData):
        data = source
    elif isinstance(source, (str, PathLike)):
        value = str(source)
        legacy = _aliases().get(value)
        if legacy is not None:
            data = _builtin_data(legacy)
            name = _PREFIX + legacy.replace("--", "-")
        elif (
            isinstance(source, PathLike)
            or value.lower().endswith(".svg")
            or "/" in value
            or "\\" in value
        ):
            path = Path(value).resolve()
            stat = path.stat()
            data = _file_data(str(path), stat.st_mtime_ns, stat.st_size)
        elif value.startswith(_PREFIX + "svg-"):
            # Already-resolved local variants remain valid public resource names.
            data = get_icon_data(value)
            name = value
        elif value.startswith(_PREFIX) or ":" not in value:
            raise IconNotFoundError(f"unknown bundled icon: {value}")
        elif stroke_width is None:
            return value
        else:
            data = get_icon_data(value)
    else:
        raise TypeError("icon must be a name, SVG path or IconData")
    if stroke_width is not None:
        width = float(stroke_width)
        if not math.isfinite(width) or width < 0:
            raise ValueError("stroke_width must be a finite nonnegative number")
        body = _STROKE_WIDTH.sub(lambda m: f"stroke-width={m[1]}{width:g}{m[1]}", data.body)
        data = replace(data, body=body)
        name = None
    if name is None:
        name = _PREFIX + "svg-" + sha256(repr(data).encode("utf-8")).hexdigest()[:24]
    ensure_local_icon(name, data)
    return name
