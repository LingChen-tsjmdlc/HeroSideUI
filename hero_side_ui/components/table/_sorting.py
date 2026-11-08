"""Table 排序 mixin：三状态循环，仅发 sort_changed 信号（受控排序）。"""

from __future__ import annotations


class _SortingMixin:
    """表格排序状态 mixin，维护三状态循环并发出受控排序信号。"""

    def _on_header_sort_clicked(self, key: str):
        """按三状态循环切换排序列与方向并发出信号。

        Args:
            key: 被点击的列 key。

        Note:
            同一列依次为升序、降序、无排序；新列首次进入升序，本 mixin 只发信号不自行排序。
        """
        if self._sort_column != key:
            # 切到新列：从无排序进入 ascending
            self._sort_column = key
            self._sort_direction = "ascending"
        elif self._sort_direction == "ascending":
            self._sort_direction = "descending"
        elif self._sort_direction == "descending":
            # 第三次点击：回到无排序
            self._sort_column = None
            self._sort_direction = None
        else:
            self._sort_direction = "ascending"
        self._sync_header_sort_state()
        self.sort_changed.emit(self._sort_column, self._sort_direction)

    def _sync_header_sort_state(self):
        """把当前排序状态同步到各列头。"""
        for k, header in self._headers.items():
            active = k == self._sort_column and self._sort_direction is not None
            header.set_sort_state(
                active=active,
                descending=(self._sort_direction == "descending"),
            )

    def sort_descriptor(self) -> dict:
        """返回当前排序列与方向的描述字典。"""
        return {"column": self._sort_column, "direction": self._sort_direction}

    def set_sort_descriptor(self, column, direction=None):
        """设置排序列与方向并同步表头状态。

        Args:
            column: 排序列 key。
            direction: 排序方向，非 ascending/descending 时清空排序。

        Note:
            direction 取其他值时把排序列与方向一并置空，未做报错。
        """
        if direction in ("ascending", "descending"):
            self._sort_column = column
            self._sort_direction = direction
        else:
            self._sort_column = None
            self._sort_direction = None
        self._sync_header_sort_state()
