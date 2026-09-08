"""Toast 组件主题预设。

对齐 HeroUI v2 toast.ts：默认 flat / radius md / shadow sm / 宽 356px，
6 个 placement，堆叠折叠时每层露出 8px。

字段说明:
    TOAST_SPEC       - 布局与动效的全局数值（px / ms）
    TOAST_SHADOWS    - 4 档阴影，走多层半透明圆角矩形自绘（与 Popover 同思路）
"""

TOAST_SPEC = {
    # ---- 尺寸 ----
    "width": 356,          # HeroUI: sm:w-[356px]
    "min_width": 220,
    "margin": 16,          # 卡片距宿主窗口边缘
    "content_gap": 16,     # HeroUI: content gap-x-4
    "close_offset": 8,     # HeroUI: -right-2 -top-2
    # ---- 卡片内部（HeroUI toast.ts 无 size 属性，取其 md 档值）----
    "icon": 24,            # 内置图标边长
    "title_size": "sm",
    "desc_size": "sm",
    "padding_x": 12,
    "padding_y": 12,
    "close": 24,           # 关闭按钮边长
    "close_icon": 14,
    # ---- 堆叠 ----
    "stack_gap": 4,        # 展开态相邻卡片间距（HeroUI 每卡 mb-1，liftHeight 起始值）
    "collapsed_step": 8,   # 折叠态每层露出的高度
    "collapsed_width_step": 8,   # 折叠态每层左右内缩总量
    "max_visible_toasts": 3,
    # ---- 时间 ----
    "timeout": 6000,
    "tick_interval": 50,   # 倒计时/进度条刷新间隔
    "duration_enter": 300,
    "duration_exit": 300,
    "duration_move": 300,
    "enter_offset": 50,    # HeroUI: INITIAL_POSITION
    # ---- 交互 ----
    "swipe_threshold_x": 100,    # HeroUI: SWIPE_THRESHOLD_X
    "swipe_threshold_y": 20,     # HeroUI: SWIPE_THRESHOLD_Y
    "progress_alpha": 0.2,       # HeroUI: progressIndicator opacity-20
    "collapse_delay": 120,       # 鼠标离开后延迟折叠，避免卡片间移动闪烁
}

TOAST_SHADOWS = {
    "none": {"layers": 0, "blur": 0, "offset_y": 0, "alpha": 0},
    "sm": {"layers": 2, "blur": 4, "offset_y": 1, "alpha": 12},
    "md": {"layers": 3, "blur": 8, "offset_y": 2, "alpha": 16},
    "lg": {"layers": 4, "blur": 16, "offset_y": 4, "alpha": 20},
}

VALID_TOAST_PLACEMENTS = (
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)
VALID_TOAST_VARIANTS = ("flat", "solid", "bordered")
VALID_TOAST_COLORS = (
    "default",
    "foreground",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
VALID_TOAST_RADII = ("none", "sm", "md", "lg", "full")
VALID_TOAST_SHADOWS = ("none", "sm", "md", "lg")
VALID_TOAST_SEVERITIES = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)

# severity → 内置图标名（HeroUI toast.tsx iconMap）
TOAST_SEVERITY_ICONS = {
    "default": "heroicons--information-circle-solid",
    "primary": "heroicons--information-circle-solid",
    "secondary": "heroicons--information-circle-solid",
    "success": "heroicons--check-solid",
    "warning": "heroicons--exclamation-triangle-solid",
    "danger": "heroicons--x-circle-solid",
}

__all__ = [
    "TOAST_SPEC",
    "TOAST_SHADOWS",
    "VALID_TOAST_PLACEMENTS",
    "VALID_TOAST_VARIANTS",
    "VALID_TOAST_COLORS",
    "VALID_TOAST_RADII",
    "VALID_TOAST_SHADOWS",
    "VALID_TOAST_SEVERITIES",
    "TOAST_SEVERITY_ICONS",
]
