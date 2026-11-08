"""HeroUI 圆角 token：none/sm/md/lg；full 需按高度动态算不在此定义。"""

RADIUS = {
    "none": "0px",
    "sm": "4px",
    "md": "8px",
    "lg": "14px",
}

# 兼容长名称
RADIUS["no"] = RADIUS["none"]
RADIUS["small"] = RADIUS["sm"]
RADIUS["medium"] = RADIUS["md"]
RADIUS["large"] = RADIUS["lg"]
