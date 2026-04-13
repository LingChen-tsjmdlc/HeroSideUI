"""
颜色相关工具函数
"""


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """将 HEX 颜色转为 rgba() 格式

    Args:
        hex_color: HEX 颜色值，如 "#006FEE"
        alpha: 透明度 0.0 ~ 1.0

    Returns:
        rgba() 格式字符串，如 "rgba(0, 111, 238, 0.5)"
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
