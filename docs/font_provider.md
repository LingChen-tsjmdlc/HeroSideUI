# FontProvider — 全局字体管理器

> 中央化管理 HeroSideUI 的字体加载、字重路由与组件刷新。

## 设计原则

**尊重物理字重**。HeroSideUI 内置字体 `SourceHanSansCN-VF.ttf` 物理上只有 6 个原生 instance：

| Instance   | Qt weight | 说明     |
| ---------- | --------- | -------- |
| ExtraLight | 200       | 极细     |
| Light      | 300       | 细       |
| Regular    | 400       | 标准常规 |
| Medium     | 500       | 中粗     |
| Bold       | 700       | 粗       |
| Heavy      | 900       | 极粗     |

我们**只用这 6 档原生 instance**，不做：

- ❌ Qt fake bold 算法合成（在 CJK 字形上视觉翻车）。
- ❌ wght 轴连续插值（Qt 6.11 在思源 VF 上对 SemiBold/ExtraBold 视觉不分明）。
- ❌ 9 档独立假装（思源 VF 物理不提供 Thin/SemiBold/ExtraBold 三档，勉强提供 token 反而让用户误以为能看到独立粗细）。

### Text 层 token 收敛到 6 个

`Text(weight=...)` 仅接受与 VF 原生 instance 一一对应的 6 个 token。传任何伪档位会直接抛 `ValueError`：

| token        | Qt weight | 原生 instance    |
| ------------ | --------: | ---------------- |
| `extralight` |       200 | ExtraLight       |
| `light`      |       300 | Light            |
| `normal`     |       400 | Regular          |
| `regular`    |       400 | Regular（alias） |
| `medium`     |       500 | Medium           |
| `bold`       |       700 | Bold             |
| `black`      |       900 | Heavy            |
| `heavy`      |       900 | Heavy（alias）   |

> 传 `int` weight（例如 `weight=600`）仍然合法，会按区间兜底到最近原生档（详见下表）。这个设计是为了让第三方代码可以直接传 `QFont.Weight` 枚举值；**但 token 接口永远不会有 9 档表达力**。

> 想要 9 档真分明粗细，需要换 Latin VF 字体（如 Inter VF）——思源 VF 物理上没有这些档。

## 核心 API

### `FontProvider.instance() -> FontProvider`

获取全局单例。每次调用都触发 `ensure_loaded`（幂等），保证模块 import 期没有 `QGuiApplication` 时也不会爆。

### `provider.family: str`

当前主 family 名。默认 `"Source Han Sans CN VF"`，`set_family(...)` 后变成用户指定的家族。

### `provider.builtin_loaded: bool`

VF 字体是否成功注册。`False` 时 `style_for_weight` / `resolve_qfont_weight` 会原值传出，不再做 6 档兜底。

### `provider.native_instances: dict[str, int]`

只读视图，返回 VF 文件的 6 个原生 instance 与对应 Qt weight。

### `provider.font_family_css() -> str`

返回 QSS `font-family:` 用的字体栈字符串，主 family 后缀 Inter/系统 fallback。

### `provider.set_family(family: str)`

切换全局主字体；空串恢复内置 VF。change 时广播刷新所有已注册组件 + 发射 `family_changed` 信号。

### `provider.style_for_weight(weight: int) -> str | None`

把任意 1~1000 weight 兜底到 VF 6 档原生 instance 的 styleName：

| weight 范围 | 返回 styleName |
| ----------- | -------------- |
| 1~250       | ExtraLight     |
| 251~350     | Light          |
| 351~450     | Regular        |
| 451~600     | Medium         |
| 601~800     | Bold           |
| 801~1000    | Heavy          |

切到第三方字体或 VF 加载失败时返回 `None`。

### `provider.resolve_qfont_weight(weight: int) -> int`

把任意 1~1000 weight 兜底到 VF 6 档原生的 Qt weight 值（200/300/400/500/700/900）。

### `provider.set_base_size_px(px: int)`

设置基准字号（像素），广播刷新已注册组件 + 发射 `base_size_changed`。

### `provider.register(widget) / unregister(widget)`

把组件加入广播订阅列表（`WeakSet`，自动清理）。组件需提供 `_apply_font()` 方法（推荐）或 `set_font_family(family)` 旧接口。

### `make_qfont(*, size_px=None, weight=400) -> QFont`

便捷工厂。VF 模式下：

```python
f = QFont("Source Han Sans CN VF")
f.setPixelSize(size_px or provider.base_size_px)
f.setWeight(QFont.Weight(provider.resolve_qfont_weight(weight)))
f.setStyleName(provider.style_for_weight(weight))   # 精确选档
```

切到第三方字体时不会调 `setStyleName`，让 Qt 自己决议。

## 在自定义组件里使用

```python
from PySide6.QtWidgets import QLabel
from hero_side_ui.core import FontProvider, make_qfont


class MyLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._weight = 400
        FontProvider.instance().register(self)
        self._apply_font()

    def _apply_font(self):
        # FontProvider 切 family 或 base_size 时会回调本方法
        self.setFont(make_qfont(weight=self._weight))

    def closeEvent(self, e):
        FontProvider.instance().unregister(self)
        super().closeEvent(e)
```

## QSS 集成

```python
from hero_side_ui.core import FontProvider

provider = FontProvider.instance()
qss = f"""
QWidget {{
    font-family: {provider.font_family_css()};
    font-size: {provider.base_size_px}px;
}}
"""
QApplication.instance().setStyleSheet(qss)
```

## FAQ

### Q: 传 `Text(weight="semibold")` 会怎么样？

会直接抛 `ValueError`。思源 VF 物理上没有 SemiBold instance，早期版本曾悔过静默兜底到 Medium，但这会让用户误以为有 9 档独立粗细；Demo 中 9 个 token 看起来只有 6 种粗细才变报 bug。现收敛为“只说话算数”：API 只提供 6 个与物理 instance 一一对应的 token。

### Q: 那 `Text(weight=600)`（传 int）会怎样？

合法，会按区间兜底到最近原生档（600 → Medium）。这个接口主要为了让第三方代码可以直接传 `QFont.Weight` 枚举值。想要可读性请用 token 接口。

### Q: 我硬要 9 档分明粗细怎么办？

换 Latin VF 字体（如 Inter VF），它有完整 Thin/SemiBold/ExtraBold 等原生 instance。或保留思源做中文，Latin 字体单独走另一个字体管理器。

### Q: `set_family("Microsoft YaHei")` 后字重路由还能用吗？

不能。切到第三方字体后 `style_for_weight` 返回 `None`、`resolve_qfont_weight` 原值传出，`make_qfont` 不再调 `setStyleName`，weight 完全由 Qt 决议。

### Q: 字体没加载（`builtin_loaded == False`）怎么办？

检查：

1. `hero_side_ui/resources/fonts/SourceHanSansCN-VF.ttf` 是否存在。
2. import HeroSideUI 时是否有 `QGuiApplication`（`provider.instance()` 第一次访问点必须在 `QApplication(...)` 之后）。
3. 看 stderr 有没有 `[HeroSideUI] FontProvider:` 开头的 warning。

加载失败时会自动 fallback 到 `"Inter", "SF Pro Display", -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif`。

## 诊断脚本

```bash
uv run python examples/text/diag.py
```

输出 `builtin_loaded` / `main family` / `native instances` / 6 档语义 token 的实际渲染档。
