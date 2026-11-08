"""DRAWER_SPEC（全局数值）与 DRAWER_SIZES（10 档主/副轴上限）；遮罩配色归 popover/_backdrop。"""

DRAWER_SPEC = {
    # ---- 内容区（modal: header/body px-6 py-4，body gap-3）----
    "padding": 24,
    "content_gap": 12,
    # ---- 关闭按钮（modal closeButton: absolute top-1 end-1 p-2 rounded-full）----
    "close_size": 32,
    "close_icon": 16,
    "close_offset": 4,
    # ---- 侧滑（use-drawer: enter 0.2s easeOut / exit 0.1s easeIn）----
    "duration_enter": 200,
    "duration_exit": 100,
    # 遮罩淡出时长（与 _Backdrop 的 duration_out 对齐），用于收尾隐藏 Drawer
    "duration_backdrop_out": 200,
}

DRAWER_SIZES = {
    "xs": {"max_w": 320, "max_h": 320},
    "sm": {"max_w": 384, "max_h": 384},
    "md": {"max_w": 448, "max_h": 448},
    "lg": {"max_w": 512, "max_h": 512},
    "xl": {"max_w": 576, "max_h": 576},
    "2xl": {"max_w": 672, "max_h": 672},
    "3xl": {"max_w": 768, "max_h": 768},
    "4xl": {"max_w": 896, "max_h": 896},
    "5xl": {"max_w": 1024, "max_h": 1024},
    "full": {"max_w": 0, "max_h": 0},
}

VALID_DRAWER_SIZES = (
    "xs",
    "sm",
    "md",
    "lg",
    "xl",
    "2xl",
    "3xl",
    "4xl",
    "5xl",
    "full",
)
VALID_DRAWER_RADII = ("none", "sm", "md", "lg")
VALID_DRAWER_PLACEMENTS = ("left", "right", "top", "bottom")
VALID_DRAWER_BACKDROPS = ("transparent", "opaque", "blur")

__all__ = [
    "DRAWER_SIZES",
    "DRAWER_SPEC",
    "VALID_DRAWER_BACKDROPS",
    "VALID_DRAWER_PLACEMENTS",
    "VALID_DRAWER_RADII",
    "VALID_DRAWER_SIZES",
]
