"""
HeroUI v2 圆角系统 (Border Radius)

所有组件共享的圆角 token。
"full" 需要根据组件高度动态计算，不在这里定义。
"""

RADIUS = {
    "none": "0px",
    "sm": "4px",
    "md": "8px",
    "lg": "14px",
}

# 兼容长名称
RADIUS["small"] = RADIUS["sm"]
RADIUS["medium"] = RADIUS["md"]
RADIUS["large"] = RADIUS["lg"]
