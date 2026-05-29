"""Pagination 范围计算 — 移植自 use-pagination-base.ts。

输出 range 列表，元素是 int (页码) 或 PaginationItemType (PREV/NEXT/DOTS)。
"""

from typing import List, Union

from ._constants import PaginationItemType

PaginationItemValue = Union[int, PaginationItemType]


def _int_range(start: int, end: int) -> List[int]:
    """闭区间整数序列 [start, end]。end < start 时返回空列表。"""
    if end < start:
        return []
    return list(range(start, end + 1))


def compute_pagination_range(
    *,
    total: int,
    active_page: int,
    siblings: int = 1,
    boundaries: int = 1,
    show_controls: bool = False,
) -> List[PaginationItemValue]:
    """生成 pagination 显示项序列。

    严格对齐 use-pagination-base.ts 的 paginationRange 算法。
    """
    total = max(1, int(total))
    active_page = max(1, min(int(active_page), total))
    siblings = max(0, int(siblings))
    boundaries = max(0, int(boundaries))

    def _wrap(items: List[PaginationItemValue]) -> List[PaginationItemValue]:
        if show_controls:
            return [PaginationItemType.PREV, *items, PaginationItemType.NEXT]
        return items

    total_page_numbers = siblings * 2 + 3 + boundaries * 2

    # 全展开
    if total_page_numbers >= total:
        return _wrap(_int_range(1, total))

    left_sibling_index = max(active_page - siblings, boundaries)
    right_sibling_index = min(active_page + siblings, total - boundaries)

    should_show_left_dots = left_sibling_index > boundaries + 2
    should_show_right_dots = right_sibling_index < total - (boundaries + 1)

    # 仅右省略
    if not should_show_left_dots and should_show_right_dots:
        left_item_count = siblings * 2 + boundaries + 2
        return _wrap(
            [
                *_int_range(1, left_item_count),
                PaginationItemType.DOTS,
                *_int_range(total - (boundaries - 1), total),
            ]
        )

    # 仅左省略
    if should_show_left_dots and not should_show_right_dots:
        right_item_count = boundaries + 1 + 2 * siblings
        return _wrap(
            [
                *_int_range(1, boundaries),
                PaginationItemType.DOTS,
                *_int_range(total - right_item_count, total),
            ]
        )

    # 双省略
    return _wrap(
        [
            *_int_range(1, boundaries),
            PaginationItemType.DOTS,
            *_int_range(left_sibling_index, right_sibling_index),
            PaginationItemType.DOTS,
            *_int_range(total - boundaries + 1, total),
        ]
    )


__all__ = ["compute_pagination_range", "PaginationItemValue"]
