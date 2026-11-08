"""INPUT_OTP_SIZES：段 32/40/48，字号 14/14/16，wrapper gap 4。"""

INPUT_OTP_SIZES = {
    "sm": {"segment": 32, "font": 14, "gap": 4, "padding_y": 8},
    "md": {"segment": 40, "font": 14, "gap": 4, "padding_y": 8},
    "lg": {"segment": 48, "font": 16, "gap": 4, "padding_y": 8},
}

# 兼容长名称
INPUT_OTP_SIZES["small"] = INPUT_OTP_SIZES["sm"]
INPUT_OTP_SIZES["medium"] = INPUT_OTP_SIZES["md"]
INPUT_OTP_SIZES["large"] = INPUT_OTP_SIZES["lg"]

VALID_INPUT_OTP_SIZES = ("sm", "md", "lg")
VALID_INPUT_OTP_VARIANTS = ("flat", "bordered", "faded", "underlined")
VALID_INPUT_OTP_RADII = ("none", "sm", "md", "lg", "full")
VALID_INPUT_OTP_TEXT_ALIGNS = ("left", "center", "right")

# 官方默认 radius=md；caret 闪烁周期（官方 appearance-in 1s infinite）
INPUT_OTP_CARET_PERIOD_MS = 1000

__all__ = [
    "INPUT_OTP_CARET_PERIOD_MS",
    "INPUT_OTP_SIZES",
    "VALID_INPUT_OTP_RADII",
    "VALID_INPUT_OTP_SIZES",
    "VALID_INPUT_OTP_TEXT_ALIGNS",
    "VALID_INPUT_OTP_VARIANTS",
]
