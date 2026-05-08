"""Accordion 组件尺寸配置。"""

ACCORDION_SIZES = {
    "sm": {
        "trigger_padding_y": 6,
        "content_padding_y": 0,
        "title_font_size": "14px",
        "subtitle_font_size": "12px",
        "content_font_size": "13px",
        "indicator_size": 16,
    },
    "md": {
        "trigger_padding_y": 8,
        "content_padding_y": 2,
        "title_font_size": "16px",
        "subtitle_font_size": "13px",
        "content_font_size": "14px",
        "indicator_size": 18,
    },
    "lg": {
        "trigger_padding_y": 12,
        "content_padding_y": 4,
        "title_font_size": "18px",
        "subtitle_font_size": "14px",
        "content_font_size": "16px",
        "indicator_size": 20,
    },
}

__all__ = ["ACCORDION_SIZES"]
