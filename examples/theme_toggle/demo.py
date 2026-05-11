"""
ThemeProvider 示例 — 一键切换全局亮暗色

演示：
- ThemeProvider.toggle() 一键切换所有 auto 组件
- theme="auto" 组件跟随全局切换
- theme="dark" 硬锁组件不受影响
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PySide6.QtCore import Qt

from hero_side_ui import (
    ThemeProvider, Button, Input, Card, CardHeader, CardBody,
    Checkbox, Progress, Divider, Tabs, ThemeSwitcher, Title,
)


class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ThemeProvider 示例 — 一键切换亮暗色")
        self.setMinimumSize(600, 500)

        provider = ThemeProvider.instance()

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # --- 标题栏 ---
        header = QHBoxLayout()
        title = Title("ThemeProvider 示例", level=1)
        header.addWidget(title)

        # 状态标签
        self._status = QLabel(f"当前模式: {provider.mode} → {provider.current_theme}")
        header.addStretch()
        header.addWidget(self._status)
        root.addLayout(header)

        # --- 切换按钮 ---
        toggle_row = QHBoxLayout()

        # 主角：ThemeSwitcher 组件 — 一键切换的核心
        # 它内部已经会调 ThemeProvider.toggle()，背景由 ThemeProvider 自动同步，无需额外回调
        switcher = ThemeSwitcher(size="md")
        toggle_row.addWidget(switcher)

        # 也可以用普通 Button 显式调用 set_mode
        btn_light = Button("强制亮色", color="default", variant="bordered")
        btn_light.clicked.connect(lambda: self._set_mode("light"))
        toggle_row.addWidget(btn_light)

        btn_dark = Button("强制暗色", color="default", variant="bordered")
        btn_dark.clicked.connect(lambda: self._set_mode("dark"))
        toggle_row.addWidget(btn_dark)

        btn_auto = Button("跟随系统 (Auto)", color="secondary", variant="flat")
        btn_auto.clicked.connect(lambda: self._set_mode("auto"))
        toggle_row.addWidget(btn_auto)

        toggle_row.addStretch()
        root.addLayout(toggle_row)

        root.addWidget(Divider())

        # --- 组件展示区 (theme="auto"，跟随切换) ---
        root.addWidget(QLabel("以下组件 theme=\"auto\"，跟随全局切换："))

        row1 = QHBoxLayout()
        row1.addWidget(Button("Primary Solid", color="primary"))
        row1.addWidget(Button("Success Flat", color="success", variant="flat"))
        row1.addWidget(Button("Danger Bordered", color="danger", variant="bordered"))
        row1.addWidget(Button("Warning Ghost", color="warning", variant="ghost"))
        row1.addStretch()
        root.addLayout(row1)

        root.addWidget(Input(label="邮箱", placeholder="请输入邮箱", color="primary"))
        root.addWidget(Progress(value=65, label="下载进度", color="success", show_value_label=True))

        cb_row = QHBoxLayout()
        cb_row.addWidget(Checkbox("React", is_selected=True, color="primary"))
        cb_row.addWidget(Checkbox("Vue", color="secondary"))
        cb_row.addWidget(Checkbox("Angular", color="success"))
        cb_row.addStretch()
        root.addLayout(cb_row)

        root.addWidget(Tabs(items=["标签一", "标签二", "标签三"], color="primary"))

        root.addWidget(Divider())

        # --- 硬锁组件 (不受影响) ---
        root.addWidget(QLabel("以下组件 theme=\"dark\" 硬锁，不跟随切换："))
        fixed_row = QHBoxLayout()
        fixed_row.addWidget(Button("固定暗色", color="primary", theme="dark"))
        fixed_row.addWidget(Button("固定暗色 Flat", color="secondary", variant="flat", theme="dark"))
        fixed_row.addStretch()
        root.addLayout(fixed_row)

        root.addStretch()

        # 监听主题变化更新状态标签
        provider.theme_changed.connect(self._update_status)

        # 注：窗口背景 / 文字色由 ThemeProvider 自动同步 QApplication.palette()
        # 这里无需手动 setPalette（铁律 5：开箱即用）

    def _on_toggle(self):
        ThemeProvider.instance().toggle()

    def _set_mode(self, mode: str):
        ThemeProvider.instance().set_mode(mode)

    def _update_status(self, theme: str):
        p = ThemeProvider.instance()
        self._status.setText(f"当前模式: {p.mode} → {theme}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec())
