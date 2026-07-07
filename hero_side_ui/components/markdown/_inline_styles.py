"""行内样式声明式配置：一份 dict → 编译成富文本 span/anchor 的样式模板。

对标 react-markdown 的 ``components``：用户构造 ``Markdown`` 时传一次 ``inline_styles``，
之后流式进来的任何文本都按此配置渲染。所有行内格式（strong/em/s/code/link）**只画样式、
不拆 widget**，故整段始终是单个富文本 ``Text``，连续框选、换行正常。

配置值一律用 HeroUI 语义 token（``primary`` / ``default-100``）或 HEX / rgba，由
``resolve_text_color`` 统一解析成 CSS 可用色串——不写死颜色、随主题解析。
"""

from __future__ import annotations

from typing import Dict

from ...core import resolve_text_color, resolve_text_weight
from ...themes import HEROUI_COLORS, MARKDOWN_INLINE_CODE

# 支持配置的行内节点类型
INLINE_STYLE_KEYS = ("strong", "em", "s", "code", "link")


def _css_weight(weight) -> str:
    """字重 token/int → Qt 富文本可用的 CSS font-weight 串（normal/bold/数值）。"""
    w = resolve_text_weight(weight)
    if w == 400:
        return "normal"
    if w == 700:
        return "bold"
    return str(w)


def _default_styles(theme: str) -> Dict[str, dict]:
    """内置默认样式（不传 inline_styles 时使用）。

    code 对齐 Chip(variant="flat", default)，link 对齐 Link(color="primary")。
    code 底色比正文明显并带边框，取自 MARKDOWN_INLINE_CODE 色阶 token。
    """
    default = HEROUI_COLORS["default"]
    spec = MARKDOWN_INLINE_CODE
    if theme == "dark":
        code_bg = default[spec["bg_shade_dark"]]
        code_fg = default[spec["fg_shade_dark"]]
        code_border = default[spec["border_shade_dark"]]
    else:
        code_bg = default[spec["bg_shade"]]
        code_fg = default[spec["fg_shade"]]
        code_border = default[spec["border_shade"]]
    return {
        "strong": {"weight": "bold"},
        "em": {"italic": True, "weight": "medium"},
        "s": {"strike": True},
        "code": {
            "bg": code_bg,
            "fg": code_fg,
            "border": code_border,
            "radius": spec["radius"],
        },
        "link": {"color": HEROUI_COLORS["primary"][500], "underline": "none"},
    }


def _css_color(value, theme: str) -> str:
    """token / HEX / rgba → CSS 颜色串（rgba(r,g,b,a)）。"""
    c = resolve_text_color(value, theme)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alphaF():.4f})"


class InlineStyleSheet:
    """把 inline_styles 配置编译成"给 inner 文本、吐 HTML 片段"的样式表。

    构造时把用户配置并入默认配置并解析成 CSS 串，渲染期只做字符串拼接。
    """

    def __init__(self, theme: str, user_styles: Dict[str, dict] | None = None):
        self._theme = theme
        merged = _default_styles(theme)
        if user_styles:
            for k, v in user_styles.items():
                if k in merged and isinstance(v, dict):
                    merged[k] = {**merged[k], **v}
                elif isinstance(v, dict):
                    merged[k] = v
        self._styles = merged

    # ---- 行内格式 ----
    def strong(self, inner: str) -> str:
        spec = self._styles.get("strong", {})
        css = []
        if spec.get("weight", "bold") != "normal":
            css.append("font-weight:bold")
        if "color" in spec:
            css.append(f"color:{_css_color(spec['color'], self._theme)}")
        return f'<span style="{"; ".join(css)};">{inner}</span>'

    def em(self, inner: str) -> str:
        spec = self._styles.get("em", {})
        css = ["font-style:italic"] if spec.get("italic", True) else []
        # VF 无原生 italic face，Qt 剪切合成伪斜体会让笔画偏细，故默认锁 medium
        # 字重补偿，使斜体视觉粗细≈正文 Regular。可经 inline_styles["em"]["weight"] 覆盖。
        css.append(f"font-weight:{_css_weight(spec.get('weight', 'medium'))}")
        if "color" in spec:
            css.append(f"color:{_css_color(spec['color'], self._theme)}")
        return f'<span style="{"; ".join(css)};">{inner}</span>'

    def s(self, inner: str) -> str:
        spec = self._styles.get("s", {})
        css = ["text-decoration:line-through"] if spec.get("strike", True) else []
        if "color" in spec:
            css.append(f"color:{_css_color(spec['color'], self._theme)}")
        return f'<span style="{"; ".join(css)};">{inner}</span>'

    def code(self, text: str) -> str:
        spec = self._styles.get("code", {})
        css = ["font-family:Consolas,'Courier New',monospace"]
        if "bg" in spec:
            css.append(f"background-color:{_css_color(spec['bg'], self._theme)}")
        if "fg" in spec:
            css.append(f"color:{_css_color(spec['fg'], self._theme)}")
        if "border" in spec:
            css.append(f"border:1px solid {_css_color(spec['border'], self._theme)}")
        radius = spec.get("radius", MARKDOWN_INLINE_CODE["radius"])
        css.append(f"border-radius:{radius}px")
        return f'<code style="{"; ".join(css)};">&nbsp;{text}&nbsp;</code>'

    def link(self, inner: str, href: str) -> str:
        spec = self._styles.get("link", {})
        color = spec.get("color", HEROUI_COLORS["primary"][500])
        css = [f"color:{_css_color(color, self._theme)}"]
        underline = spec.get("underline", "none")
        css.append(
            "text-decoration:underline"
            if underline == "always"
            else "text-decoration:none"
        )
        return f'<a href="{href}" style="{"; ".join(css)};">{inner}</a>'

    def wrap(self, inner: str, fmt) -> str:
        """把 strong/em/s 的组合格式解析成单个 span。

        用单 span 而非嵌套，避免内层 font-weight 覆盖外层：字重按优先级取——
        有 strong 取 bold；否则 em 取 medium 抵消 VF 合成斜体的视觉变细。

        fmt: 含 "strong"/"em"/"s" 的集合。
        """
        if not fmt or not inner:
            return inner
        strong_spec = self._styles.get("strong", {})
        em_spec = self._styles.get("em", {})
        s_spec = self._styles.get("s", {})
        css = []
        italic = "em" in fmt and em_spec.get("italic", True)
        if italic:
            css.append("font-style:italic")
        # 斜体靠几何切变合成会视觉削细，故带斜体时字重整体升一档补偿：
        # 纯斜体 regular→medium；粗+斜 bold→black，使视觉粗细≈对应正体。
        if "strong" in fmt and strong_spec.get("weight", "bold") != "normal":
            css.append(
                f"font-weight:{_css_weight('black')}" if italic else "font-weight:bold"
            )
        elif "em" in fmt:
            css.append(f"font-weight:{_css_weight(em_spec.get('weight', 'medium'))}")
        if "s" in fmt and s_spec.get("strike", True):
            css.append("text-decoration:line-through")
        # 颜色优先级 strong > em > s
        color = None
        if "s" in fmt and "color" in s_spec:
            color = s_spec["color"]
        if "em" in fmt and "color" in em_spec:
            color = em_spec["color"]
        if "strong" in fmt and "color" in strong_spec:
            color = strong_spec["color"]
        if color is not None:
            css.append(f"color:{_css_color(color, self._theme)}")
        if not css:
            return inner
        return f'<span style="{"; ".join(css)};">{inner}</span>'


__all__ = ["InlineStyleSheet", "INLINE_STYLE_KEYS"]
