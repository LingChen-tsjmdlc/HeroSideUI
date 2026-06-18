"""Table 排序状态机（mixin）。

对齐 HeroUI v2 sortDescriptor：点击可排序列头在三状态间循环切换：
    无排序 → ascending → descending → 无排序 → ...
仅维护状态并发出 sort_changed 信号，实际数据排序由使用者在槽函数里完成
（与 HeroUI 一致，排序受控，组件不擅自重排数据）。direction 为 None 表示无排序。

宿主必须提供：
    self._sort_column (Optional[str]), self._sort_direction (Optional["ascending"/"descending"]),
    self._headers (dict[key -> _TableColumnHeader]),
    self.sort_changed (Signal(object, object))
"""

from __future__ import annotations


class _SortingMixin:
    def _on_header_sort_clicked(self, key: str):
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
        for k, header in self._headers.items():
            active = k == self._sort_column and self._sort_direction is not None
            header.set_sort_state(
                active=active,
                descending=(self._sort_direction == "descending"),
            )

    def sort_descriptor(self) -> dict:
        return {"column": self._sort_column, "direction": self._sort_direction}

    def set_sort_descriptor(self, column, direction=None):
        if direction in ("ascending", "descending"):
            self._sort_column = column
            self._sort_direction = direction
        else:
            self._sort_column = None
            self._sort_direction = None
        self._sync_header_sort_state()
