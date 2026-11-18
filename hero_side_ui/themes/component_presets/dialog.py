"""DIALOG_SPEC 对话框数值规格与合法取值（桌面端专属组件，HeroUI 无对应项）。"""

DIALOG_SPEC = {
    # ---- 尺寸 ----
    "default_width": 420,
    # 自动高度的上限 = 屏幕可用高度 x 该比例（未传 max_height 时）
    "max_height_ratio": 0.8,
    # ---- 内容区边距 ----
    "padding_x": 24,
    "padding_top": 20,
    "padding_bottom": 16,
    # ---- 图标与文案 ----
    "icon_size": 32,
    "icon_gap": 16,
    "text_gap": 6,
    # 小标题的文字不透明度（次要色）
    "heading_opacity": 0.6,
    # success 图标：圆内对勾占圆直径的比例
    "success_check_ratio": 0.6,
    # ---- 按钮区 ----
    "footer_gap": 8,
    "footer_padding_top": 4,
    "footer_padding_bottom": 20,
}

# 预设图标：名称 -> (内置图标名, 默认语义色)。success 的图标外面再画一个圆底
DIALOG_ICONS = {
    "info": ("heroicons--information-circle-solid", "primary"),
    "success": ("heroicons--check-solid", "success"),
    "warning": ("heroicons--exclamation-triangle-solid", "warning"),
    "danger": ("heroicons--x-circle-solid", "danger"),
    "question": ("material-symbols--help-outline", "primary"),
}

VALID_DIALOG_ICONS = tuple(DIALOG_ICONS)
VALID_DIALOG_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VALID_DIALOG_PLACEMENTS = (
    "top-left",
    "top",
    "top-right",
    "left",
    "center",
    "right",
    "bottom-left",
    "bottom",
    "bottom-right",
)
VALID_DIALOG_MODALITIES = ("window", "application", "none")
VALID_DIALOG_BACKDROPS = ("none", "dim", "blur")
# 对话框 backdrop 取值到共享遮罩 Backdrop 的 kind
DIALOG_BACKDROP_KINDS = {"dim": "opaque", "blur": "blur"}
VALID_DIALOG_STAY_ON_TOP = ("none", "parent", "system")
VALID_DIALOG_FOOTER_ALIGNS = ("start", "center", "end", "stretch")
VALID_DIALOG_BUTTON_ORDERS = ("auto", "ok_first", "cancel_first")

__all__ = [
    "DIALOG_BACKDROP_KINDS",
    "DIALOG_ICONS",
    "DIALOG_SPEC",
    "VALID_DIALOG_BACKDROPS",
    "VALID_DIALOG_BUTTON_ORDERS",
    "VALID_DIALOG_COLORS",
    "VALID_DIALOG_FOOTER_ALIGNS",
    "VALID_DIALOG_ICONS",
    "VALID_DIALOG_MODALITIES",
    "VALID_DIALOG_PLACEMENTS",
    "VALID_DIALOG_STAY_ON_TOP",
]
