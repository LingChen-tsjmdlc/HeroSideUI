"""
Table 进阶综合示例 — 完整复刻 HeroUI v2 文档页 "real-world data table"。

对应 React 源码（@heroui/react Table 完整示例）逐项还原：
  - 8 列：ID / NAME / AGE / ROLE / TEAM / EMAIL / STATUS / ACTIONS
    （sortable: id/name/age/role/status；team/email/actions 不可排序）
  - 初始可见列：name / role / status / actions（其余靠 Columns 下拉切换）
  - 顶部工具栏（outside）：搜索框 + Status 多选筛选 + Columns 列显隐
    + Add New + "Total N users" + Rows per page
  - 底部（outside）：选中计数（含 "All items selected"）+ Pagination + Prev/Next
  - 多选 + 全选、可排序列（age 默认 ascending）、sticky 表头 + max-height 滚动
  - 自定义 cell：头像+姓名+邮箱(User)、角色+团队、状态 Chip、操作 ⋮ 菜单(Dropdown)
"""

import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Qt

from hero_side_ui import (
    HeroSideUIProvider, ThemeSwitcher, Title,
    Table, Chip, Button, Input, Select, SelectItem, Pagination,
    Popover, Listbox, Text,
)


# ============================================================
# 数据（对齐 React 示例的 columns / statusOptions / users）
# ============================================================
COLUMNS = [
    {"key": "id", "label": "ID", "sortable": True},
    {"key": "name", "label": "NAME", "sortable": True},
    {"key": "age", "label": "AGE", "sortable": True},
    {"key": "role", "label": "ROLE", "sortable": True},
    {"key": "team", "label": "TEAM"},
    {"key": "email", "label": "EMAIL"},
    {"key": "status", "label": "STATUS", "sortable": True},
    {"key": "actions", "label": "ACTIONS", "align": "center"},
]
ALL_COLUMN_KEYS = [c["key"] for c in COLUMNS]
INITIAL_VISIBLE_COLUMNS = ["name", "role", "status", "actions"]

STATUS_OPTIONS = [("active", "Active"), ("paused", "Paused"), ("vacation", "Vacation")]
STATUS_COLOR = {"active": "success", "paused": "danger", "vacation": "warning"}

# (id, name, role, team, status, age)
_RAW = [
    (1, "Tony Reichert", "CEO", "Management", "active", 29),
    (2, "Zoey Lang", "Tech Lead", "Development", "paused", 25),
    (3, "Jane Fisher", "Sr. Dev", "Development", "active", 22),
    (4, "William Howard", "C.M.", "Marketing", "vacation", 28),
    (5, "Kristen Copper", "S. Manager", "Sales", "active", 24),
    (6, "Brian Kim", "P. Manager", "Management", "active", 29),
    (7, "Michael Hunt", "Designer", "Design", "paused", 27),
    (8, "Samantha Brooks", "HR Manager", "HR", "active", 31),
    (9, "Frank Harrison", "F. Manager", "Finance", "vacation", 33),
    (10, "Emma Adams", "Ops Manager", "Operations", "active", 35),
    (11, "Brandon Stevens", "Jr. Dev", "Development", "active", 22),
    (12, "Megan Richards", "P. Manager", "Product", "paused", 28),
    (13, "Oliver Scott", "S. Manager", "Security", "active", 37),
    (14, "Grace Allen", "M. Specialist", "Marketing", "active", 30),
    (15, "Noah Carter", "IT Specialist", "I. Technology", "paused", 31),
    (16, "Ava Perez", "Manager", "Sales", "active", 29),
    (17, "Liam Johnson", "Data Analyst", "Analysis", "active", 28),
    (18, "Sophia Taylor", "QA Analyst", "Testing", "active", 27),
    (19, "Lucas Harris", "Administrator", "Information Technology", "paused", 32),
    (20, "Mia Robinson", "Coordinator", "Operations", "active", 26),
]
USERS = [
    {
        "key": str(uid),
        "id": uid,
        "name": name,
        "role": role,
        "team": team,
        "status": status,
        "age": age,
        "email": f"{name.split()[0].lower()}.{name.split()[-1].lower()}@example.com",
    }
    for (uid, name, role, team, status, age) in _RAW
]

_AVATAR_COLORS = ["#7828c8", "#006FEE", "#17c964", "#f5a524", "#f31260", "#7e7e8a"]


def _capitalize(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else ""


# ============================================================
# 自定义 cell 渲染
# ============================================================
def _avatar(name: str, index: int) -> QLabel:
    """圆形首字母头像（离线替代 pravatar URL）。"""
    initials = "".join(p[0] for p in name.split()[:2]).upper()
    dot = QLabel(initials)
    color = _AVATAR_COLORS[index % len(_AVATAR_COLORS)]
    dot.setFixedSize(34, 34)
    dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
    dot.setStyleSheet(
        f"background:{color}; color:white; border-radius:17px;"
        f"font-size:12px; font-weight:600;"
    )
    return dot


def _user_cell(user: dict) -> QWidget:
    """对应 React 的 <User>：头像 + 姓名 + 邮箱描述。"""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(10)
    h.addWidget(_avatar(user["name"], user["id"] - 1))
    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(0)
    col.addWidget(Text(user["name"], weight="medium"))
    col.addWidget(Text(user["email"], size="sm", color="default-400"))
    h.addLayout(col)
    h.addStretch()
    return w


def _role_cell(user: dict) -> QWidget:
    """对应 React role 列：角色 + 团队（次级灰字）。"""
    w = QWidget()
    col = QVBoxLayout(w)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(0)
    col.addWidget(Text(_capitalize(user["role"]), weight="medium"))
    col.addWidget(Text(_capitalize(user["team"]), size="sm", color="default-400"))
    return w


# ============================================================
# 主窗口
# ============================================================
class TableAdvancedDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table — 综合数据表示例")
        self.resize(1100, 780)

        # 受控状态（对齐 React useState）
        self._filter_text = ""
        self._status_filter: set[str] = set()          # 空集 = all（不筛选）
        self._visible_cols: set[str] = set(INITIAL_VISIBLE_COLUMNS)
        self._rows_per_page = 5
        self._page = 1
        self._sort_col = "age"                          # 默认 age ascending
        self._sort_dir = "ascending"

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 20, 32, 24)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = Title("Table — 综合示例", level=1)
        title.set_color("#006FEE")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(ThemeSwitcher(size="md"))
        root.addLayout(header)

        # 表格本体：多选 + sticky 表头 + max-height 滚动 + 内容外置
        self._table = Table(
            color="primary",
            selection_mode="multiple",
            is_header_sticky=True,
            max_height=382,
            top_content_placement="outside",
            bottom_content_placement="outside",
            empty_content="No users found",
        )
        self._table.set_render_cell(self._render_cell)
        self._table.selection_changed.connect(lambda *_: self._refresh_bottom())
        self._table.sort_changed.connect(self._on_sort)
        # 初始排序描述符（让表头排序箭头与状态同步）
        self._table.set_sort_descriptor(self._sort_col, self._sort_dir)

        self._table.set_top_content(self._build_top())
        self._table.set_bottom_content(self._build_bottom())
        root.addWidget(self._table)
        root.addStretch()

        self.setCentralWidget(central)
        self._reload()

    # ------------------------------------------------------------
    # 列 / cell 渲染
    # ------------------------------------------------------------
    def _visible_columns(self) -> list:
        """按 visibleColumns 过滤列，保持 COLUMNS 原顺序。"""
        return [c for c in COLUMNS if c["key"] in self._visible_cols]

    def _render_cell(self, row_key, col_key, value):
        user = next((u for u in USERS if u["key"] == row_key), None)
        if user is None:
            return value
        if col_key == "name":
            return _user_cell(user)
        if col_key == "role":
            return _role_cell(user)
        if col_key == "status":
            return Chip(_capitalize(value), color=STATUS_COLOR.get(value, "default"),
                        variant="flat", size="sm")
        if col_key == "actions":
            return self._actions_cell(row_key)
        # id / age / team / email 直接显示
        return str(value)

    def _actions_cell(self, row_key: str) -> QWidget:
        """对应 React 的 Dropdown：⋮ 按钮 → View / Edit / Delete 菜单。

        Popover + Listbox 是重控件，每次翻页全部重建会卡顿，故懒建：
        首次点击 ⋮ 才创建菜单并缓存在按钮上。
        """
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = Button("", variant="light", size="sm", color="default", icon_only=True,
                     icon="heroicons--ellipsis-horizontal")
        btn.clicked.connect(lambda *_a, b=btn, rk=row_key: self._open_actions_menu(b, rk))
        h.addWidget(btn)
        return w

    def _open_actions_menu(self, btn, row_key: str):
        menu = getattr(btn, "_row_menu", None)
        if menu is None:
            menu = Popover(placement="bottom-end")
            lb = Listbox()
            lb.add_item("View", key="view")
            lb.add_item("Edit", key="edit")
            lb.add_item("Delete", key="delete")
            lb.action.connect(lambda k, rk=row_key: (print(f"{k} -> row {rk}"), menu.close()))
            menu.set_content(lb)
            menu.attach(btn, event="manual")
            btn._row_menu = menu
        menu.open(near=btn)

    # ------------------------------------------------------------
    # 顶部工具栏（topContent）
    # ------------------------------------------------------------
    def _build_top(self) -> QWidget:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # 第一行：搜索 + Status + Columns + Add New
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        search = Input(placeholder="Search by name...", is_clearable=True, size="sm")
        search.text_changed.connect(self._on_search)
        search.cleared.connect(lambda: self._on_search(""))
        row1.addWidget(search, 1)  # 搜索框占据弹性空间
        row1.addStretch()

        # Status 多选筛选（disallowEmptySelection 语义：空集视为 all）
        status_sel = Select(
            [SelectItem(label, key=uid) for uid, label in STATUS_OPTIONS],
            selection_mode="multiple", placeholder="Status", size="sm",
        )
        status_sel.selection_changed.connect(self._on_status_filter)
        row1.addWidget(status_sel)

        # Columns 列显隐（初始仅 name/role/status/actions）
        cols_sel = Select(
            [SelectItem(_capitalize(c["label"]), key=c["key"]) for c in COLUMNS],
            selection_mode="multiple", placeholder="Columns", size="sm",
            selected_keys=set(INITIAL_VISIBLE_COLUMNS),
        )
        cols_sel.selection_changed.connect(self._on_cols_change)
        row1.addWidget(cols_sel)

        add_btn = Button("Add New", color="primary", size="sm")
        row1.addWidget(add_btn)
        v.addLayout(row1)

        # 第二行：Total N users + Rows per page
        row2 = QHBoxLayout()
        self._count_label = Text(f"Total {len(USERS)} users", size="sm", color="default-400")
        row2.addWidget(self._count_label)
        row2.addStretch()
        row2.addWidget(Text("Rows per page:", size="sm", color="default-400"))
        rpp = Select(
            [SelectItem(n, key=n) for n in ("5", "10", "15")],
            selection_mode="single", size="sm", selected_keys={"5"},
        )
        rpp.selection_changed.connect(self._on_rpp_change)
        row2.addWidget(rpp)
        v.addLayout(row2)
        return wrap

    # ------------------------------------------------------------
    # 底部（bottomContent）：选中计数 + Pagination + Prev/Next
    # ------------------------------------------------------------
    def _build_bottom(self) -> QWidget:
        wrap = QWidget()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(8)

        self._sel_label = Text("0 of 0 selected", size="sm", color="default-400")
        self._sel_label.setMinimumWidth(180)
        h.addWidget(self._sel_label)
        h.addStretch()

        self._pager = Pagination(total=1, initial_page=1, color="primary",
                                 is_compact=True, show_controls=True)
        self._pager.page_changed.connect(self._on_page)
        h.addWidget(self._pager)
        h.addStretch()

        right = QWidget()
        rh = QHBoxLayout(right)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(8)
        rh.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._prev_btn = Button("Previous", variant="flat", size="sm", color="default")
        self._next_btn = Button("Next", variant="flat", size="sm", color="default")
        self._prev_btn.clicked.connect(self._on_prev)
        self._next_btn.clicked.connect(self._on_next)
        rh.addWidget(self._prev_btn)
        rh.addWidget(self._next_btn)
        right.setMinimumWidth(180)
        h.addWidget(right)
        return wrap

    # ------------------------------------------------------------
    # 数据流（filter → sort → paginate）
    # ------------------------------------------------------------
    def _filtered(self) -> list:
        rows = list(USERS)
        if self._filter_text:
            t = self._filter_text.lower()
            rows = [u for u in rows if t in u["name"].lower()]
        # status 空集 = all（对齐 React：statusFilter==="all" 或全选时不过滤）
        if self._status_filter and len(self._status_filter) != len(STATUS_OPTIONS):
            rows = [u for u in rows if u["status"] in self._status_filter]
        return rows

    def _sorted(self, rows: list) -> list:
        if not self._sort_col or self._sort_dir is None:
            return rows
        key = self._sort_col
        if key in ("id", "age"):
            keyfn = lambda u: u.get(key, 0)
        elif key in ("name", "role", "status", "team", "email"):
            keyfn = lambda u: str(u.get(key, "")).lower()
        else:
            return rows
        return sorted(rows, key=keyfn, reverse=(self._sort_dir == "descending"))

    def _reload(self):
        rows = self._sorted(self._filtered())
        total_pages = max(1, (len(rows) + self._rows_per_page - 1) // self._rows_per_page)
        if self._page > total_pages:
            self._page = total_pages
        start = (self._page - 1) * self._rows_per_page
        page_rows = rows[start:start + self._rows_per_page]

        self._table.set_columns(self._visible_columns())
        self._table.set_rows(page_rows)
        self._pager.set_total(total_pages)
        self._pager.set_page(self._page)
        self._count_label.setText(f"Total {len(self._filtered())} users")
        self._prev_btn.setEnabled(total_pages > 1)
        self._next_btn.setEnabled(total_pages > 1)
        self._refresh_bottom()

    def _refresh_bottom(self):
        sel = len(self._table.selected_keys())
        total = len(self._filtered())
        if sel and sel == total:
            self._sel_label.setText("All items selected")
        else:
            self._sel_label.setText(f"{sel} of {total} selected")

    # ------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------
    def _on_search(self, text):
        self._filter_text = text or ""
        self._page = 1
        self._reload()

    def _on_status_filter(self, keys):
        self._status_filter = set(keys) if keys else set()
        self._page = 1
        self._reload()

    def _on_cols_change(self, keys):
        ks = set(keys) if keys else set()
        if not ks:
            return  # disallowEmptySelection：至少保留一列
        self._visible_cols = ks
        self._reload()

    def _on_rpp_change(self, key):
        # single Select 的 selection_changed 发 Optional[str]
        val = next(iter(key)) if isinstance(key, (set, list, tuple)) and key else key
        try:
            self._rows_per_page = int(val)
        except (TypeError, ValueError):
            return
        self._page = 1
        self._reload()

    def _on_page(self, page):
        self._page = page
        self._reload()

    def _on_prev(self):
        if self._page > 1:
            self._page -= 1
            self._reload()

    def _on_next(self):
        rows = self._filtered()
        total_pages = max(1, (len(rows) + self._rows_per_page - 1) // self._rows_per_page)
        if self._page < total_pages:
            self._page += 1
            self._reload()

    def _on_sort(self, col, direction):
        self._sort_col = col
        self._sort_dir = direction
        self._reload()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    HeroSideUIProvider.setup(app, theme="light")
    win = TableAdvancedDemo()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
