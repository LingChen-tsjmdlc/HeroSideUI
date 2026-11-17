"""WINDOW_SPEC 窗口数值规格与合法取值（桌面端专属组件，HeroUI 无对应项）。"""

VALID_WINDOW_SYSTEMS = ("auto", "windows", "mac", "linux")
VALID_WINDOW_RADII = ("system", "sm", "md", "lg")

# 自绘圆角（beta）的档位像素；也可以直接传数字。固定值，不取主题 RADIUS（窗口圆角与组件圆角是两回事）
WINDOW_RADII = {"sm": 6, "md": 10, "lg": 14}

# 各风格的标准标题栏高度
WINDOW_TITLE_BAR_HEIGHTS = {"windows": 32, "mac": 28, "linux": 40}

WINDOW_SPEC = {
    # ---- 圆角 ----
    # 超椭圆（苹果的连续圆角）平滑度 0~1：0 是普通圆角，0.6 是 iOS 观感；越大弧线越长越柔和
    "corner_smoothing": 0.6,
    # ---- 标题栏高度下限 ----
    "min_title_bar_height": 20,
    # ---- 窗口尺寸 ----
    "default_width": 800,
    "default_height": 600,
    # 最小尺寸固定下限（再小基本没法用）
    "min_width_floor": 280,
    "min_height_floor": 160,
    # 最小尺寸保底 = 控制按钮组宽度 + 80 / 标题栏高度 + 40
    "min_width_extra": 80,
    "min_height_extra": 40,
    # ---- 缩放热区 ----
    "resize_edge": 6,
    # ---- 槽 ----
    "slot_padding": 12,
    "slot_gap": 8,
    "title_icon_size": 16,
    "title_icon_gap": 8,
    # ---- windows 控制按钮 ----
    "windows_button_width": 46,
    "windows_icon_size": 16,
    "windows_close_hover": "#e81123",
    "windows_close_press": "#f1707a",
    # ---- linux (GNOME) 控制按钮 ----
    "linux_button_gap": 6,
    "linux_side_padding": 8,
    "linux_diameter_inset": 16,
    "linux_min_diameter": 16,
    "linux_icon_ratio": 0.6,
    "linux_min_icon": 12,
    # ---- mac 红黄绿 ----
    "mac_base_height": 28,
    "mac_base_diameter": 16,
    "mac_gap": 8,
    "mac_side_padding": 12,
    "mac_icon_ratio": 0.8,
    "mac_min_icon": 9,
    "mac_symbol_opacity": 0.6,
    "mac_close": "#ff5f57",
    "mac_minimize": "#febc2e",
    "mac_maximize": "#28c840",
    "mac_inactive_light": "#cdcdcd",
    "mac_inactive_dark": "#5a5a5a",
}

__all__ = [
    "VALID_WINDOW_RADII",
    "VALID_WINDOW_SYSTEMS",
    "WINDOW_RADII",
    "WINDOW_SPEC",
    "WINDOW_TITLE_BAR_HEIGHTS",
]
