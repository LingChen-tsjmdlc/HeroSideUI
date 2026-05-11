# ScrollShadow

对齐 HeroUI v2 [`ScrollShadow`](https://v2.heroui.com/docs/components/scroll-shadow) 的滚动阴影容器。

在可滚动容器的起/止端绘制一条"背景色淡出"的渐变蒙版，暗示"还有更多内容可滚"。当用户滚到顶/底时，对应端的阴影自动消失。

## 基本用法（插槽装配，推荐）

`ScrollShadow` 是**可装配的滚动容器**，内置 layout，直接往里塞内容：

```python
from hero_side_ui import ScrollShadow, Body

sc = ScrollShadow(orientation="vertical", size=40)
sc.add_widget(Body("段落 1..."))
sc.add_widget(Body("段落 2..."))
sc.add_widget(other_widget)
sc.setFixedSize(400, 260)
```

内部 layout 根据 `orientation` 自动选：`vertical` → `QVBoxLayout`，`horizontal` → `QHBoxLayout`。

### 插槽 API

| 方法 | 作用 |
| --- | --- |
| `sc.add_widget(w)` | 追加一个子 widget |
| `sc.insert_widget(index, w)` | 在指定位置插入 |
| `sc.add_stretch(stretch=1)` | 追加弹性空间 |
| `sc.layout()` | 返回内置 layout，可用 `.addLayout(...)` 等 |
| `sc.content()` | 返回内置 content QWidget（高级用法） |

### 高级用法：替换整个内容容器

如需完全自定义容器（例如用 `QGridLayout`），用 `setWidget()` 覆盖：

```python
custom = QWidget()
grid = QGridLayout(custom)
grid.addWidget(...)
sc.setWidget(custom)    # 覆盖插槽,add_widget 不再指向原容器
```

## Props

| 参数             | 类型                                                                               | 默认         | 说明                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------- |
| `orientation`    | `"vertical"` \| `"horizontal"`                                                     | `"vertical"` | 滚动方向                                                                               |
| `size`           | `int`                                                                              | `40`         | 阴影渐变宽度（像素）                                                                   |
| `offset`         | `int`                                                                              | `0`          | 进入"到顶/到底"判定的容差（像素）                                                      |
| `visibility`     | `"auto"` \| `"both"` \| `"top"` \| `"bottom"` \| `"left"` \| `"right"` \| `"none"` | `"auto"`     | 显隐模式                                                                               |
| `is_enabled`     | `bool`                                                                             | `True`       | 是否启用阴影                                                                           |
| `hide_scrollbar` | `bool`                                                                             | `False`      | 是否隐藏原生滚动条                                                                     |
| `fade_color`     | `str` \| `None`                                                                    | `None`       | 淡出渐变目标色（hex 字符串）。**同时**把 ScrollShadow 自身+viewport 背景填为同色，保证阴影与底色严丝合缝；`None` 时回到"跟随 palette 自动决策"模式（背景透明让父容器穿透） |
| `theme`          | `"auto"` \| `"light"` \| `"dark"`                                                  | `"auto"`     | 主题模式                                                                               |

### `visibility` 语义

- `"auto"`: 按滚动位置自动显隐（默认）
- `"both"`: 两端始终显示
- `"top"` / `"bottom"`: 仅在 `vertical` 方向下生效，强制只显示某一端
- `"left"` / `"right"`: 仅在 `horizontal` 方向下生效
- `"none"`: 不显示任何阴影

## 信号

| 信号                      | 参数                                                              | 说明                       |
| ------------------------- | ----------------------------------------------------------------- | -------------------------- |
| `visibility_changed(str)` | `"top"` / `"bottom"` / `"both"` / `"none"` / `"left"` / `"right"` | 当前有效显隐组合变化时发射 |

## Setter

```python
sa.set_orientation("horizontal")
sa.set_size(60)
sa.set_offset(10)
sa.set_visibility("both")
sa.set_is_enabled(False)
sa.set_hide_scrollbar(True)
sa.set_fade_color("#18181b")   # 嵌在自定义背景容器里时手动指定
sa.set_theme("dark")
```

## 实现要点

Web 端 HeroUI 用 CSS `mask-image: linear-gradient(...)` 把容器自身的边缘做 alpha 渐变。Qt 里没有 CSS mask，改为在 `viewport()` 之上叠一个透明覆盖层 `_ShadowOverlay`，用 `QLinearGradient` 画"背景色 → 透明"的渐变，视觉效果与 `mask-image` 完全一致。

阴影的"淡出目标色"决策（三级 fallback）：

1. 若用户通过 `fade_color=` 显式指定 → 直接用，**并同时**把 ScrollShadow 自身+viewport 背景填成该色，保证阴影与底色严丝合缝；
2. 否则沿 parent 链向上找第一个提供 `current_bg_color()` 方法的祖先容器（duck typing；例如 `Card`），读其返回值作为淡出色 —— 主题 / hover 切换时自动跟随，不需要用户做任何同步工作；
3. 最后回退读自身 `palette().color(Window)`（`ThemeProvider` 同步的当前主题窗口色）。

此外，`ScrollShadow` 监听 `QEvent.PaletteChange`：只要 `QApplication` 或任何父 widget 的 palette 发生变化（主题切换、用户手动 `setPalette`），阴影都会**实时重绘**，始终跟随当前背景。

### 嵌在 Card 内 —— 零配置

`Card` 暴露公共 `current_bg_color() -> QColor`，ScrollShadow 自动识别并实时跟随：

```python
from hero_side_ui import Card, CardBody, ScrollShadow

card = Card()
cb = CardBody()
sc = ScrollShadow()         # 不传 fade_color
sc.setWidget(content)
cb.layout().addWidget(sc)
card.add_body(cb)           # 放进 Card 即完成
```

切换主题、Card hover 期间，ScrollShadow 的阴影淡出色自动跟 Card 底色同步。

覆盖层设置 `WA_TransparentForMouseEvents`，不会干扰内部内容的点击/滚动。

