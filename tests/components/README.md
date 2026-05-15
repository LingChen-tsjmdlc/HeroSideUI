# tests/components — 组件层测试

对应源码：`hero_side_ui/components/`

## 这层测什么

组件是用户面对面接触的 API 表层。这层测试的目标：**保证组件的公共契约不破**。

每个组件一个测试文件，文件名 = `test_<component>.py`，与 `hero_side_ui/components/<component>/` 一一对应。

### 必测维度

1. **构造参数全合法值的笛卡尔积 smoke**：组件不崩、能 show / hide / resize。
2. **每个 prop 的动态 setter**：`set_color / set_variant / set_size / set_radius / set_theme / set_disabled ...` 调用后状态被更新且**所有视觉/子组件同步刷新**（铁律 4 第 3 条）。
3. **信号契约**：`clicked / value_changed / opened / closed / selection_changed ...` 在用户交互（或代码调用）时被精确发射一次、参数正确。
4. **状态机**：disabled / hover / focus / pressed / selected / invalid / readonly 等状态切换后内部 flag 与可视化标志一致（不验证像素，但验证 `objectName / property / palette` 等机器可读标志）。
5. **代理 API（如适用）**：Input 暴露 `.line_edit`、Tabs 暴露 `add_tab`、Accordion 暴露 `add_item` 等的转发逻辑。
6. **主题切换联动**：`ThemeProvider.toggle()` 后 `theme="auto"` 组件的 `_theme` / 内部颜色被切换；`theme="light/dark"` 的组件不受影响。

### _不_ 在这层测的东西

- ❌ 单个动画的边界行为 → 归 `tests/animation/`
- ❌ StatePalette 静态值 → 归 `tests/core/`
- ❌ 像素级视觉对比 → 由 `examples/` 人工跑、未来视觉回归基线工具自动跑

## 测试写法范式

### 1. 文件骨架

```python
"""<Component> 单元测试"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from hero_side_ui import <Component>


class TestConstruct:
    """构造、默认值、不同参数组合"""
    def test_default(self, qtbot):
        w = <Component>()
        qtbot.addWidget(w)
        assert w._color == "default"
        assert w._size == "md"


class TestSetters:
    """动态 API 改后视觉/状态同步"""
    def test_set_color_refreshes_qss(self, qtbot):
        w = <Component>(); qtbot.addWidget(w)
        w.set_color("primary")
        assert w._color == "primary"
        assert "006FEE" in w.styleSheet().upper() or w.property("colorVariant") == "primary"


class TestSignals:
    def test_clicked_signal(self, qtbot):
        w = <Component>(); qtbot.addWidget(w)
        with qtbot.waitSignal(w.clicked, timeout=500):
            qtbot.mouseClick(w, Qt.LeftButton)


class TestStates:
    def test_disabled_blocks_clicks(self, qtbot):
        ...


class TestThemeIntegration:
    """与 ThemeProvider 的联动"""
    def test_auto_follows_provider(self, qtbot):
        from hero_side_ui import ThemeProvider
        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance(); p.set_mode("light")
        w = <Component>(); qtbot.addWidget(w)
        p.toggle()
        assert w._theme == "dark"
        ThemeProvider._reset_for_test()
```

### 2. 参数化遍历

```python
COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
SIZES  = ("sm", "md", "lg")
VARIANTS = ("solid", "bordered", "flat", "light", "faded", "ghost")

@pytest.mark.parametrize("color", COLORS)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("variant", VARIANTS)
def test_construct_all_combos(qtbot, color, size, variant):
    w = Button("X", color=color, size=size, variant=variant)
    qtbot.addWidget(w)
    w.show()
    # 不崩、能 show 就算 pass
```

笛卡尔积爆炸时（>200 case）就降级到 representative subset：颜色取 default/primary/danger 三个有代表性的，尺寸全跑，变体全跑。

### 3. 浮层/Tool 窗口组件（Popover / Tooltip / Autocomplete）

```python
def test_popover_open_close(qtbot):
    from hero_side_ui import Popover, Button
    btn = Button("Trigger"); qtbot.addWidget(btn); btn.show()
    pop = Popover(); pop.attach(btn, event="manual")
    with qtbot.waitSignal(pop.opened, timeout=1000):
        pop.open()
    with qtbot.waitSignal(pop.closed, timeout=1000):
        pop.close()
    qtbot.wait(50)  # 让 Qt 把 restore-focus 等副作用跑完
```

要点：

- 顶层 Tool 窗口关闭后会 restore focus 给打开前的 widget，可能触发链式打开（铁律 38）。测试 commit 类操作时必须 `qtbot.wait(>animDuration+100)` 验证不会循环打开。
- 浮层主题切换有专门链路（铁律 31），任何"内容里有 QLabel 用 setStyleSheet 写死 hex"的组件，测试必须覆盖 `ThemeProvider.toggle()` 后内容文字色被刷新。

### 4. 子组件 reparent / show 坑（铁律 36）

```python
def test_external_widget_visible_after_attach(qtbot):
    from PySide6.QtWidgets import QLabel
    from hero_side_ui import Input
    inp = Input(label="X", end_content=QLabel("END"))
    qtbot.addWidget(inp); inp.show()
    qtbot.wait(30)
    # 外部 widget 经历 reparent 后必须仍 visible
    end = inp.findChild(QLabel)
    assert end is not None and end.isVisible()
```

## 常见坑（必读）

1. **跨测试 QApplication 状态污染**：conftest autouse fixture 已自动 reset，但**用了 ThemeProvider 单例的测试自己也要 reset**（在 fixture 里 `ThemeProvider._reset_for_test()`）。
2. **不要直接断言像素**：除非你在测自绘组件的 paintEvent，否则像素断言会被 OS 字体渲染差异打爆。
3. **不要 `time.sleep`** → 用 `qtbot.wait(ms)`，否则事件循环不跑。
4. **Window 下跨文件偶发 access violation**：往往是上一个测试遗留了 active 动画。检查测试结束前是否 `w.close()` 或等动画 finished。
5. **`Input._LineEdit` 的 palette.Base 坑**（铁律 22）：任何把 Input 嵌入容器的测试，写 `setStyleSheet("QWidget {...}")` 之前先停 —— 这会传染。改用 `setAutoFillBackground` + palette。
