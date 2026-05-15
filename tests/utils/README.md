# tests/utils — 工具函数测试

对应源码：`hero_side_ui/utils/`

## 这层测什么

utils 是**无状态纯函数**的集合，被组件、动画、core 多处复用。这里的测试应该是最快、最稳的一层。

| 文件                          | 被测对象                           | 关注点                                                                                                                                  |
| ----------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `test_color_utils.py`（待补） | `hex_to_rgba(hex, alpha)`          | 各种合法 HEX 输入（带/不带 `#`、3 位/6 位、大小写）、边界 alpha（0、1、超出范围处理）                                                   |
|                               | `aligned_color_pair(start, end)`   | alpha=0 一端被改写为另一端 RGB；两端都不透明时原样返回；都透明时返回原值；返回新 QColor 不污染入参                                      |
| `test_icon_utils.py`（待补）  | `load_svg_icon(name, size, color)` | 内置 heroicons 能找到；外部路径能加载；着色后 QIcon 的 pixmap 像素被替换；不存在的 name 抛 FileNotFoundError；size 影响输出 pixmap 尺寸 |

## 这层 _不_ 测什么

- ❌ 组件如何调用工具（如 Button 用 `load_svg_icon` 拼装内部 icon）→ 归 `tests/components/`
- ❌ 任何主题/状态机相关 → 归 `tests/core/`

## 测试写法范式

### 1. 纯函数：参数化遍历 + 边界值

```python
import pytest
from PySide6.QtGui import QColor
from hero_side_ui.utils import hex_to_rgba, aligned_color_pair


@pytest.mark.parametrize("hex_in, alpha, expected", [
    ("#006FEE", 0.5, "rgba(0, 111, 238, 0.5)"),
    ("006FEE",  1.0, "rgba(0, 111, 238, 1.0)"),
    ("#FFFFFF", 0.0, "rgba(255, 255, 255, 0.0)"),
])
def test_hex_to_rgba(hex_in, alpha, expected):
    assert hex_to_rgba(hex_in, alpha) == expected
```

### 2. QColor 工具：用 `name()` / `alpha()` 断言

```python
def test_aligned_color_pair_start_transparent():
    start = QColor(0, 0, 0, 0)
    end   = QColor("#006FEE")
    s, e = aligned_color_pair(start, end)
    # 透明端 RGB 应被改写成 end 的 RGB
    assert (s.red(), s.green(), s.blue()) == (end.red(), end.green(), end.blue())
    assert s.alpha() == 0
    # end 不变
    assert e.name() == end.name()
    # 不污染入参
    assert (start.red(), start.green(), start.blue()) == (0, 0, 0)
```

### 3. 资源加载（icon_utils）：用 QImage 像素采样验证

```python
from PySide6.QtGui import QImage
from hero_side_ui.utils import load_svg_icon

def test_load_builtin_icon_color(qtbot):
    icon = load_svg_icon("heroicons--chevron-right-solid", size=24, color="#FF0000")
    pix = icon.pixmap(24, 24)
    img: QImage = pix.toImage()
    # 中心区域应该有红色像素（被着色成功）
    found_red = any(
        img.pixelColor(x, y).red() > 200 and img.pixelColor(x, y).green() < 50
        for x in range(8, 16) for y in range(8, 16)
    )
    assert found_red
```

要点：

- utils 测试**不应该需要 qtbot**（除了涉及 QIcon/QPixmap 这种需要 QGuiApplication 的）。能不要就不要。
- 任何 helper 一旦"被第二个组件复用"，就必须先在 utils 里加测试 → 再在组件里 import 使用（参考长期记忆铁律 35）。
- 输入边界要覆盖：空字符串、None、超出值域、非法格式。**核心承诺**：utils 不抛奇怪异常，对非法输入要么稳定 fallback，要么抛清晰的 `ValueError/TypeError`。
