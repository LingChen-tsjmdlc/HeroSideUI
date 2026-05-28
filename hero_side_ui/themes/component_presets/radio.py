"""Radio 组件尺寸配置。

对齐 HeroUI v2 的 radio 规范:
    sm: wrapper 16x16 + control 6x6  + label text-small  + description text-tiny
    md: wrapper 20x20 + control 8x8  + label text-medium + description text-small  (默认)
    lg: wrapper 24x24 + control 10x10 + label text-large  + description text-medium

card 变体新增:
    card_padding / card_radius / card_max_width / card_gap (label↔wrapper 间距)
"""

RADIO_SIZES = {
    "sm": {
        "wrapper": 16,  # 外圈直径
        "control": 6,  # 内圆点直径
        "label_font_size": 13,  # text-small
        "desc_font_size": 11,  # text-tiny
        "gap": 4,  # ms-1 = 4px
        "border_width": 2,
        # card 变体
        "card_padding": 12,
        "card_radius": 10,
        "card_max_width": 260,
        "card_gap": 12,
        "card_border_width": 2,
    },
    "md": {
        "wrapper": 20,
        "control": 8,
        "label_font_size": 14,
        "desc_font_size": 13,
        "gap": 8,  # ms-2 = 8px
        "border_width": 2,
        "card_padding": 16,
        "card_radius": 12,
        "card_max_width": 300,
        "card_gap": 16,
        "card_border_width": 2,
    },
    "lg": {
        "wrapper": 24,
        "control": 10,
        "label_font_size": 16,
        "desc_font_size": 14,
        "gap": 8,
        "border_width": 2,
        "card_padding": 18,
        "card_radius": 14,
        "card_max_width": 340,
        "card_gap": 18,
        "card_border_width": 2,
    },
}

RADIO_SIZES["small"] = RADIO_SIZES["sm"]
RADIO_SIZES["medium"] = RADIO_SIZES["md"]
RADIO_SIZES["large"] = RADIO_SIZES["lg"]

__all__ = ["RADIO_SIZES"]
