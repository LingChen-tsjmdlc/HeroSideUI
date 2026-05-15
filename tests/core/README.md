# tests/core — 核心基础设施测试

对应源码：`hero_side_ui/core/`

## 这层测什么

core 是组件库的"地基"，是所有组件共享的全局服务和静态规则集。
特点：**没有视觉**、**没有动画**、**主要是状态机和纯计算**。

| 文件                     | 被测对象                      | 关注点                                                                                                                                      |
| ------------------------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_theme_provider.py` | `ThemeProvider` 单例          | 单例、`set_mode/toggle`、register/unregister/weakref 清理、`theme_changed/mode_changed` 信号广播                                            |
| `test_state_palette.py`  | `StatePalette` 静态色板       | bg/border/text 在 variant × color × theme × state 笛卡尔积下的精确返回值；resting/disabled 透明；focus≡hover；未知 color 静默降级到 default |
| `test_scroll_style.py`   | `ScrollStyle` 滚动条 QSS 工厂 | 不同 variant/theme/size 下 QSS 拼接正确、QScrollBar 实例属性挂载                                                                            |
| `test_smooth_scroll.py`  | `SmoothScroll` 滚轮平滑包装   | wheel event 入参合并、tick 速度衰减、target 在边界处 clamp                                                                                  |

## 这层 _不_ 测什么

- ❌ 任何 paint / 像素 / QSS 视觉验证 → 归 `examples/` 人工
- ❌ 组件层调用 core 后的整体行为 → 归 `tests/components/`
- ❌ 动画曲线、值域过渡 → 归 `tests/animation/`

## 测试写法范式

### 1. ThemeProvider（带全局状态，必须 reset）

```python
import pytest
from hero_side_ui import ThemeProvider

@pytest.fixture(autouse=True)
def reset_provider():
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()

class TestSetMode:
    def test_set_mode_dark(self, qtbot):
        p = ThemeProvider.instance()
        p.set_mode("dark")
        assert p.current_theme == "dark"
```

要点：

- ThemeProvider 是单例，**任何 case 跑完都必须把单例 reset 回干净状态**，否则会污染下一测试。
- `qtbot` 参数即使不用也要写 —— 单例创建期间会同步 `QApplication.palette`，需要 QApplication 就绪。

### 2. 静态色板（纯函数，零 Qt 依赖）

```python
from PySide6.QtGui import QColor
from hero_side_ui import StatePalette
from hero_side_ui.themes import HEROUI_COLORS

class TestSpecificBgValues:
    def test_solid_primary(self):
        c = StatePalette.bg("solid", "primary", "light", "hover")
        assert c.name() == HEROUI_COLORS["primary"][500].lower()
```

要点：

- 静态色板不需要 widget，断言用 `QColor.name()` 拿小写 hex 比较。
- 用 `(variants × colors × themes)` 笛卡尔积做 smoke 覆盖；逐个值锁定时挑代表（default / primary / danger）即可。
- **测"等价关系"**（如 `focus ≡ hover`）和 **"边界降级"**（如未知 color 不抛 KeyError）。

### 3. 滚动样式 / 平滑滚动（需要 widget）

```python
def test_apply_to_scrollarea(qtbot):
    from PySide6.QtWidgets import QScrollArea
    from hero_side_ui import ScrollStyle
    area = QScrollArea()
    qtbot.addWidget(area)
    ScrollStyle.apply(area, variant="default", theme="light")
    assert "QScrollBar" in area.styleSheet()
```

要点：

- 用 `qtbot.addWidget(...)` 让 conftest 的清理 fixture 接管，**不要手动 `del` 或 `close`**。
- 行为类断言（"应用后 styleSheet 非空"、"信号被发射 N 次"），不验证字节级 QSS 内容。
