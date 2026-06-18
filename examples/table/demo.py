"""
Table 组件示例 — 静态/动态表 × 6 colors × 单选/多选 × 斑马纹 × 紧凑 × 排序 × 自定义 cell
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt

from hero_side_ui import (
    Table,
    Chip,
    Button,
    Input,
    Pagination,
    Title,
    Caption,
)
from _base import DemoBase


COLUMNS = [
    {"key": "name", "label": "NAME"},
    {"key": "role", "label": "ROLE"},
    {"key": "status", "label": "STATUS"},
]

ROWS = [
    {"key": "1", "name": "Tony Reichert", "role": "CEO", "status": "Active"},
    {"key": "2", "name": "Zoey Lang", "role": "Tech Lead", "status": "Paused"},
    {"key": "3", "name": "Jane Fisher", "role": "Sr. Developer", "status": "Active"},
    {"key": "4", "name": "William Howard", "role": "Community Mgr", "status": "Vacation"},
]


def _basic_table(**kwargs) -> Table:
    t = Table(**kwargs)
    t.set_columns(COLUMNS)
    t.set_rows(ROWS)
    return t


class TableDemo(DemoBase):
    component_name = "Table"

    def build_content(self, layout: QVBoxLayout, labels_bag: list):
        # ============================================================
        # 1) 基础静态表
        # ============================================================
        layout.addWidget(Title("基础", level=3))
        layout.addWidget(_basic_table())

        # ============================================================
        # 2) 单选 / 多选
        # ============================================================
        layout.addWidget(Title("单选 (single)", level=3))
        t_single = _basic_table(color="primary", selection_mode="single")
        t_single.set_selected_keys({"2"})
        layout.addWidget(t_single)

        layout.addWidget(Title("多选 (multiple) + 全选 checkbox", level=3))
        t_multi = _basic_table(color="secondary", selection_mode="multiple")
        t_multi.set_selected_keys({"1", "3"})
        layout.addWidget(t_multi)

        # ============================================================
        # 3) 六种语义色（多选选中态展示行条配色）
        # ============================================================
        layout.addWidget(Title("六种语义色（选中行条）", level=3))
        for color in ("default", "primary", "secondary", "success", "warning", "danger"):
            row = QHBoxLayout()
            cap = Caption(color)
            cap.setFixedWidth(90)
            row.addWidget(cap)
            t = _basic_table(color=color, selection_mode="multiple")
            t.set_selected_keys({"1", "2"})
            row.addWidget(t)
            holder = QWidget()
            holder.setLayout(row)
            layout.addWidget(holder)

        # ============================================================
        # 4) 斑马纹 / 紧凑 / 隐藏表头
        # ============================================================
        layout.addWidget(Title("斑马纹 (isStriped)", level=3))
        layout.addWidget(_basic_table(is_striped=True, selection_mode="single"))

        layout.addWidget(Title("紧凑 (isCompact)", level=3))
        layout.addWidget(_basic_table(is_compact=True))

        layout.addWidget(Title("隐藏表头 (hideHeader)", level=3))
        layout.addWidget(_basic_table(hide_header=True))

        # ============================================================
        # 5) 圆角 / 阴影
        # ============================================================
        layout.addWidget(Title("圆角 radius (none / sm / md / lg / full)", level=3))
        for r in ("none", "sm", "md", "lg", "full"):
            row = QHBoxLayout()
            cap = Caption(r)
            cap.setFixedWidth(90)
            row.addWidget(cap)
            row.addWidget(_basic_table(radius=r, selection_mode="single"))
            holder = QWidget()
            holder.setLayout(row)
            layout.addWidget(holder)

        layout.addWidget(Title("阴影 shadow (none / sm / md / lg)", level=3))
        for s in ("none", "sm", "md", "lg"):
            row = QHBoxLayout()
            cap = Caption(s)
            cap.setFixedWidth(90)
            row.addWidget(cap)
            row.addWidget(_basic_table(shadow=s))
            holder = QWidget()
            holder.setLayout(row)
            layout.addWidget(holder)

        # ============================================================
        # 6) 可排序列
        # ============================================================
        layout.addWidget(Title("可排序列 (allowsSorting)", level=3))
        t_sort = Table(color="primary")
        sortable_cols = [
            {"key": "name", "label": "NAME", "allows_sorting": True},
            {"key": "role", "label": "ROLE", "allows_sorting": True},
            {"key": "status", "label": "STATUS"},
        ]
        t_sort.set_columns(sortable_cols)
        t_sort.set_rows(ROWS)

        def _on_sort(col, direction):
            if direction is None:
                # 无排序：恢复原始顺序
                t_sort.set_rows(ROWS)
                return
            reverse = direction == "descending"
            ordered = sorted(ROWS, key=lambda r: r.get(col, ""), reverse=reverse)
            t_sort.set_rows(ordered)

        t_sort.sort_changed.connect(_on_sort)
        layout.addWidget(t_sort)

        # ============================================================
        # 7) 自定义单元格（Chip 状态 + 操作按钮）
        # ============================================================
        layout.addWidget(Title("自定义单元格 (render_cell)", level=3))
        custom_cols = [
            {"key": "name", "label": "NAME"},
            {"key": "role", "label": "ROLE"},
            {"key": "status", "label": "STATUS", "align": "center"},
            {"key": "actions", "label": "ACTIONS", "align": "center"},
        ]
        status_color = {"Active": "success", "Paused": "danger", "Vacation": "warning"}

        def render_cell(row_key, col_key, value):
            if col_key == "status":
                return Chip(
                    str(value),
                    color=status_color.get(value, "default"),
                    variant="flat",
                    size="sm",
                )
            if col_key == "actions":
                holder = QWidget()
                h = QHBoxLayout(holder)
                h.setContentsMargins(0, 0, 0, 0)
                h.setSpacing(4)
                h.addWidget(Button("Edit", variant="light", size="sm", color="primary"))
                h.addWidget(Button("Delete", variant="light", size="sm", color="danger"))
                return holder
            return value

        t_custom = Table(color="primary", selection_mode="multiple")
        t_custom.set_columns(custom_cols)
        t_custom.set_render_cell(render_cell)
        t_custom.set_rows(ROWS)
        layout.addWidget(t_custom)

        # ============================================================
        # 8) 禁用行 + 必选 + 去外壳
        # ============================================================
        layout.addWidget(Title("禁用行 (disabledKeys)", level=3))
        t_disabled = _basic_table(selection_mode="multiple", color="success")
        t_disabled.set_disabled_keys({"2", "4"})
        layout.addWidget(t_disabled)

        layout.addWidget(Title("禁止空选 (disallowEmptySelection)", level=3))
        t_must = _basic_table(
            selection_mode="single", color="secondary",
            disallow_empty_selection=True,
        )
        t_must.set_selected_keys({"1"})
        layout.addWidget(t_must)

        layout.addWidget(Title("去外壳 (removeWrapper)", level=3))
        t_bare = _basic_table(selection_mode="single", remove_wrapper=True)
        layout.addWidget(t_bare)

        # ============================================================
        # 9) 顶部内容（搜索框） + 底部内容（分页）
        # ============================================================
        layout.addWidget(Title("顶部 + 底部内容 (topContent / bottomContent + Pagination)", level=3))
        many_rows = [
            {"key": str(i), "name": f"User {i}", "role": f"Role {i}",
             "status": ("Active", "Paused", "Vacation")[i % 3]}
            for i in range(1, 21)
        ]
        page_size = 5
        t_page = Table(color="primary", selection_mode="multiple")
        t_page.set_columns(COLUMNS)

        search = Input(placeholder="Search by name...", is_clearable=True, size="sm")
        search.setMaximumWidth(280)
        t_page.set_top_content(search)

        pager = Pagination(total=(len(many_rows) + page_size - 1) // page_size,
                           initial_page=1, color="primary", show_controls=True)
        t_page.set_bottom_content(pager)

        def _load_page(page):
            start = (page - 1) * page_size
            t_page.set_rows(many_rows[start:start + page_size])

        pager.page_changed.connect(_load_page)
        _load_page(1)
        layout.addWidget(t_page)

        # ============================================================
        # 10) 空状态 + 三档尺寸
        # ============================================================
        layout.addWidget(Title("尺寸 size (sm / md / lg)", level=3))
        for s in ("sm", "md", "lg"):
            row = QHBoxLayout()
            cap = Caption(s)
            cap.setFixedWidth(90)
            row.addWidget(cap)
            row.addWidget(_basic_table(size=s, selection_mode="single"))
            holder = QWidget()
            holder.setLayout(row)
            layout.addWidget(holder)

        layout.addWidget(Title("空状态 (emptyContent)", level=3))
        t_empty = Table(empty_content="No rows to display.")
        t_empty.set_columns(COLUMNS)
        layout.addWidget(t_empty)


if __name__ == "__main__":
    TableDemo.run()
