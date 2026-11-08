"""TABLE_SIZES：wrapper 16、表头高 40、td padding 8/12、compact 4 等字段。"""

TABLE_SIZES = {
    "sm": {
        "wrapper_padding": 12,
        "wrapper_gap": 12,
        "header_height": 32,
        "header_gap": 3,
        "header_font_size": 11,
        "cell_padding_x": 10,
        "cell_padding_y": 6,
        "compact_padding_y": 3,
        "row_min_height": 36,
        "font_size": 13,
        "checkbox_col_width": 36,
        "sort_icon_size": 12,
        "cell_gap": 6,
    },
    "md": {
        "wrapper_padding": 16,
        "wrapper_gap": 16,
        "header_height": 40,
        "header_gap": 4,
        "header_font_size": 12,
        "cell_padding_x": 12,
        "cell_padding_y": 8,
        "compact_padding_y": 4,
        "row_min_height": 44,
        "font_size": 14,
        "checkbox_col_width": 40,
        "sort_icon_size": 14,
        "cell_gap": 8,
    },
    "lg": {
        "wrapper_padding": 20,
        "wrapper_gap": 18,
        "header_height": 48,
        "header_gap": 4,
        "header_font_size": 13,
        "cell_padding_x": 14,
        "cell_padding_y": 10,
        "compact_padding_y": 5,
        "row_min_height": 52,
        "font_size": 15,
        "checkbox_col_width": 44,
        "sort_icon_size": 16,
        "cell_gap": 10,
    },
}

TABLE_SIZES["small"] = TABLE_SIZES["sm"]
TABLE_SIZES["medium"] = TABLE_SIZES["md"]
TABLE_SIZES["large"] = TABLE_SIZES["lg"]

__all__ = ["TABLE_SIZES"]
