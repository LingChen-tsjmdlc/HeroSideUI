"""
SVG 图标渲染工具

提供统一的 SVG 加载、着色和渲染能力。支持两种方式:
  1. 内置图标名: load_svg_icon("heroicons--chevron-right-solid") — 从库自带的 resources/icons/ 加载
  2. 任意路径: load_svg_icon("/path/to/icon.svg") — 从用户指定的路径加载

颜色处理（color 参数）:
  - 传 QColor / "#RRGGBB" → 使用这个颜色
  - 传 None（或不传）→ 根据 ThemeProvider 当前主题自动选对比色：
      * 亮色模式 → 深色 icon（#18181b）
      * 暗色模式 → 浅色 icon（#fafafa）
  - 传 "original" → 保留 SVG 原始颜色（不做任何替换）

线宽处理（stroke_width 参数）:
  - None（默认）→ 保留 SVG 原始 stroke-width
  - 数值（如 2.0 / 2.5）→ 替换 SVG 中所有 stroke-width 属性,
    用于 outline 类 heroicons 调粗细（默认 1.5,常见加粗用 2.0/2.25/2.5）

用法:
    from hero_side_ui.utils import load_svg_icon

    # 方式1: 内置图标名（不含 .svg 后缀）
    pixmap = load_svg_icon("heroicons--chevron-right-solid", size=18, color=QColor("#a1a1aa"))

    # 方式2: 任意 SVG 文件路径
    pixmap = load_svg_icon("C:/my_project/icons/star.svg", size=24, color="#006FEE")

    # 方式3: 自动跟随主题（暗色显示浅色 icon，亮色显示深色 icon）
    pixmap = load_svg_icon("heroicons--eye-solid", size=24)

    # 方式4: 保留原始 SVG 颜色
    pixmap = load_svg_icon("my_colorful_logo.svg", size=24, color="original")

    # 方式5: 加粗 outline 图标的描边
    pixmap = load_svg_icon("heroicons--chevron-down", size=24, stroke_width=2.5)
"""

import re
from pathlib import Path
from typing import Optional, Union

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QPixmap, QColor, QPainter, QImage
from PySide6.QtSvg import QSvgRenderer

# 库内置图标目录（随包安装，位于 hero_side_ui/resources/icons/）
_BUILTIN_ICONS_DIR = (
    Path(__file__).resolve().parent.parent / "resources" / "icons"
)

# 主题感知的默认对比色
_DEFAULT_LIGHT_ICON = "#18181b"  # 亮色背景下用深色 icon（zinc-900）
_DEFAULT_DARK_ICON = "#fafafa"   # 暗色背景下用浅色 icon（zinc-50）

# 匹配 SVG 中的 stroke-width="..." 或 stroke-width='...' 属性
# (兼容数值带小数、带单位等情况;不匹配 CSS style 中的 stroke-width 因为
# heroicons 内置 SVG 用的都是 attribute 形式)
_STROKE_WIDTH_RE = re.compile(r'stroke-width\s*=\s*"[^"]*"|stroke-width\s*=\s*\'[^\']*\'')


def _resolve_theme_aware_color() -> str:
    """根据 ThemeProvider 当前主题返回合适的对比色

    - 暗色主题 → 浅色 icon
    - 亮色主题 → 深色 icon
    - ThemeProvider 未初始化或无 QApplication → fallback 到深色
    """
    try:
        # 延迟 import 避免循环依赖
        from ..core import ThemeProvider
        theme = ThemeProvider.instance().current_theme
        return _DEFAULT_DARK_ICON if theme == "dark" else _DEFAULT_LIGHT_ICON
    except Exception:
        return _DEFAULT_LIGHT_ICON


def load_svg_icon(
    name_or_path: str,
    size: int = 24,
    color=None,
    stroke_width: Optional[Union[int, float]] = None,
) -> QPixmap:
    """加载 SVG 图标并渲染为 QPixmap

    Args:
        name_or_path: 可以是:
            - 内置图标名（不含 .svg），如 "heroicons--chevron-right-solid"
            - SVG 文件的完整路径，如 "/path/to/icon.svg"
        size: 渲染尺寸（正方形，单位 px）
        color: 图标颜色。
            - None（默认）：根据 ThemeProvider 当前主题自动选对比色（暗色→浅，亮色→深）
            - QColor 对象或 HEX 字符串（如 "#006FEE"）：使用这个颜色
            - "original"：保留 SVG 原始颜色，不做替换
        stroke_width: 描边粗细。
            - None（默认）：保留 SVG 原始 stroke-width
            - 数值：替换所有 stroke-width="..." 属性,适合给 outline 类 heroicons
              加粗（默认 1.5,常用 2.0/2.25/2.5）

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

    # 着色策略
    if color is None:
        # None → 根据主题自动选对比色
        color_str = _resolve_theme_aware_color()
    elif isinstance(color, str) and color == "original":
        # "original" → 保留 SVG 原始颜色
        color_str = None
    elif isinstance(color, QColor):
        color_str = color.name()
    else:
        color_str = color

    if color_str is not None:
        svg_data = svg_data.replace("currentColor", color_str)

    # 描边粗细：用正则替换所有 stroke-width="..." 属性
    if stroke_width is not None:
        # 格式化:整数去小数点(2 而非 2.0),小数保留(2.5)
        sw = float(stroke_width)
        sw_str = str(int(sw)) if sw.is_integer() else str(sw)
        svg_data = _STROKE_WIDTH_RE.sub(f'stroke-width="{sw_str}"', svg_data)

    # 渲染
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    return QPixmap.fromImage(image)


def _resolve_svg_path(name_or_path: str):
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
