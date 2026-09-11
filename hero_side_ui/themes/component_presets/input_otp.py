"""InputOtp 组件尺寸配置。

对照 HeroUI inputOtp.ts 的 size / compound variants：
- segment（段）：sm w-8 h-8(32) / md w-10 h-10(40) / lg w-12 h-12(48)
- 字号：sm/md text-small(14) / lg text-medium(16)
- segmentWrapper：gap-x-1(4) py-2(8)
- helper：text-tiny(12)，mt-0.5(2)
"""

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
    "INPUT_OTP_SIZES",
    "VALID_INPUT_OTP_SIZES",
    "VALID_INPUT_OTP_VARIANTS",
    "VALID_INPUT_OTP_RADII",
    "VALID_INPUT_OTP_TEXT_ALIGNS",
    "INPUT_OTP_CARET_PERIOD_MS",
]
