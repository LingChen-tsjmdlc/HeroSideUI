"""HeroUI 风格 Spinner（loading 旋转指示器）。

6 种 variant，对齐 HeroUI v2 官网：

    default   两条圆弧（一条 ease 旋、一条 linear 旋虚线）
    simple    经典 Tailwind loader（圆环 + 1/4 实心扇形整体旋转）
    gradient  圆环跑渐变（透明 → 主色）
    spinner   12 根时钟刻度，逐根淡入淡出（iOS UIActivityIndicator）
    wave      3 个圆点上下波动
    dots      3 个圆点间歇闪烁

公开 API::

    Spinner(variant="default", color="primary", size="md", label="",
            label_color="foreground", theme="auto")
"""

from .spinner import Spinner

__all__ = ["Spinner"]
