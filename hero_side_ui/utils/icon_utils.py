"""
SVG 图标渲染工具

提供统一的 SVG 加载、着色和渲染能力。支持两种方式:
  1. 内置图标名: load_svg_icon("heroicons--chevron-right-solid") — 从库自带的 resources/icons/ 加载
  2. 任意路径: load_svg_icon("/path/to/icon.svg") — 从用户指定的路径加载

用法:
    from hero_side_ui.utils import load_svg_icon

    # 方式1: 内置图标名（不含 .svg 后缀）
    pixmap = load_svg_icon("heroicons--chevron-right-solid", size=18, color=QColor("#a1a1aa"))

    # 方式2: 任意 SVG 文件路径
    pixmap = load_svg_icon("C:/my_project/icons/star.svg", size=24, color="#006FEE")
"""

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPixmap, QColor, QPainter, QImage
from PySide6.QtSvg import QSvgRenderer

# 库内置图标目录
_BUILTIN_ICONS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
)


def load_svg_icon(
    name_or_path: str,
    size: int = 24,
    color: QColor | str | None = None,
) -> QPixmap:
    """加载 SVG 图标并渲染为 QPixmap

    Args:
        name_or_path: 可以是:
            - 内置图标名（不含 .svg），如 "heroicons--chevron-right-solid"
            - SVG 文件的完整路径，如 "/path/to/icon.svg"
        size: 渲染尺寸（正方形，单位 px）
        color: 图标颜色。None 则使用 SVG 原始颜色。
               支持 QColor 对象或 HEX 字符串如 "#006FEE"

    Returns:
        渲染好的 QPixmap。路径不存在时返回空的透明 pixmap。
    """
    # 解析路径: 先看是不是完整路径，不是就当内置图标名
    svg_path = _resolve_svg_path(name_or_path)

    if svg_path is None or not svg_path.exists():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        return pixmap

    svg_data = svg_path.read_text(encoding="utf-8")

    # 着色: 替换 SVG 中的 currentColor
    if color is not None:
        if isinstance(color, QColor):
            color_str = color.name()
        else:
            color_str = color
        svg_data = svg_data.replace("currentColor", color_str)

    # 渲染
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    return QPixmap.fromImage(image)


def _resolve_svg_path(name_or_path: str) -> Path | None:
    """解析 SVG 路径

    - 如果是完整路径（含 / 或 \\ 或 .svg 后缀）→ 直接用
    - 否则当作内置图标名 → 从 resources/icons/ 查找
    """
    p = Path(name_or_path)

    # 完整路径: 含目录分隔符或 .svg 后缀
    if p.suffix == ".svg" or "/" in name_or_path or "\\" in name_or_path:
        return p

    # 内置图标名
    builtin = _BUILTIN_ICONS_DIR / f"{name_or_path}.svg"
    if builtin.exists():
        return builtin

    return None
