# SmoothScroll 平滑滚动

`SmoothScroll` 是 **core 工具**，给任意 `QAbstractScrollArea`（`QPlainTextEdit` / `QTextEdit` / `QScrollArea` / `QListView` / ...）挂上**滚轮平滑过渡**。

## 为什么需要它

PySide/Qt 默认的滚动行为是**整行跳跃** —— 滚轮转一格 = `scrollbar.singleStep`（默认一行字高），没有动画。所以体感"咔哒咔哒"地一跳一跳，特别是多行文本里很明显。

`SmoothScroll` 拦截 `wheelEvent`，自己接管滚动 —— 用 `QPropertyAnimation` 在 scrollbar value 上做 0→target 的丝滑过渡。

## 导入

```python
from hero_side_ui import SmoothScroll
```

## 基本用法

```python
# 给一个 QPlainTextEdit 挂上平滑滚动 —— 一行调用
edit = QPlainTextEdit()
SmoothScroll.attach(edit)

# 自定义参数
SmoothScroll.attach(edit, lines_per_step=5, duration=250)

# 卸载
SmoothScroll.detach(edit)
```

> `Textarea` 内部已经自动 `attach` 了，你不需要手动调。这个 API 主要是给你**自己的滚动 widget** 用的。

## 参数

| 参数             | 类型                | 默认值     | 说明                                                        |
| ---------------- | ------------------- | ---------- | ----------------------------------------------------------- |
| `lines_per_step` | `int`               | `3`        | 滚轮一格滚多少个 `singleStep`（适配各种 widget 的单位语义） |
| `duration`       | `int`               | `300`      | 动画时长 ms。0 = 关闭动画                                   |
| `easing`         | `QEasingCurve.Type` | `OutCubic` | 缓动曲线                                                    |

> ⚠️ `lines_per_step` 不是像素！QScrollBar 的 value 单位由 widget 自己定义：
>
> - `QPlainTextEdit / QTextEdit / QListView`：value 是行号/项目编号，`singleStep = 1`，所以 `lines_per_step = 3` ≈ 3 行
> - `QScrollArea / QGraphicsView`：value 是像素，`singleStep ≈ 20`，所以 `lines_per_step = 3` ≈ 60 像素
>
> 这种"用 widget 自己的 step 单位 × 倍率"的设计天然适配各种 widget，不会出现"一滚就到底"的现象。

## 全局默认

```python
SmoothScroll.set_global_default(
    lines_per_step=5,
    duration=250,
    enabled=False,        # 一键关闭：之后所有 attach() 调用什么都不做
)
```

后续 `attach()` 没显式传参时会读这些默认值。**已挂载的 area 不受影响**。

## 工作原理

1. 给 area 的 `viewport()` 装一个 `_SmoothScrollFilter` (eventFilter)
2. 拦截 `QEvent.Wheel`，根据 `angleDelta` 算出像素 delta
3. 用 `QPropertyAnimation(scrollbar, b"value")` 在 `current → target` 间过渡
4. 若动画进行中又来一个 wheel 事件，target 在**当前 target 基础上累加**，重启动画从"当前实际值"到新 target —— 连续滚动顺畅，不会跳回起点

## 与 ScrollStyle 的关系

- `ScrollStyle`：控制滚动条**外观**（细线 + hover 加粗变色）
- `SmoothScroll`：控制滚动条**行为**（滚轮平滑过渡）

两者完全独立，可以单独/一起用。

## 已接入

- `Textarea` 在 `__init__` 末尾自动 `SmoothScroll.attach(self.text_edit)`
