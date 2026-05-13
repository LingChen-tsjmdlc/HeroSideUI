# ScrollStyle 全局滚动条样式

`ScrollStyle` 是一个 **core 单例**，为整个应用提供统一的细线条滚动条外观（HeroUI 风格），并在 [`ThemeProvider`](./theme_provider.md) 切换主题时自动跟随。

效果：
- 默认细 6px，鼠标进入时变粗到 8px（可配）
- 默认色用 `default` 色阶 300（亮）/ 700（暗），hover 加深到 500
- 支持切换其它颜色（primary / secondary / success / warning / danger）

## 导入

```python
from hero_side_ui import ScrollStyle, ThemeProvider
```

## 基本用法

```python
from PySide6.QtWidgets import QApplication
from hero_side_ui import ThemeProvider, ScrollStyle

app = QApplication([])

# 1. 必须先初始化 ThemeProvider（会自动同步全局 palette）
ThemeProvider.instance()

# 2. 应用全局滚动条样式（一次调用即可）
ScrollStyle.instance().apply_global()

# 之后所有 QScrollArea / QPlainTextEdit / QTextEdit 等内的 QScrollBar 都会自动用这套样式
```

## 自定义参数

```python
ss = ScrollStyle.instance()

# 调整粗细
ss.set_thickness(8)               # 默认 6
ss.set_hover_thickness_delta(3)   # hover 加粗 +3 = 11px（默认 +2）

# 切换主题色（hover 加深 ramp 跟着切）
ss.set_color("primary")

# 调整 handle 最小长度（防止内容很长时 handle 缩成点）
ss.set_min_handle_length(32)      # 默认 24

# 调整轨道两端 margin（让 handle 不贴 widget 边缘）
ss.set_track_padding(6)           # 默认 4

# 调整 hover 进出过渡时长
ss.set_duration(200)              # 默认 150ms，0 = 无动画
ss.set_easing(QEasingCurve.Type.OutQuart)  # 默认 OutCubic

# 调整 handle 阴影（border 模拟）—— normal 状态有阴影，hover 时渐隐到 0
ss.set_shadow_alpha(light=40, dark=120)  # 默认 15(亮)/50(暗)，0=完全无阴影
```

> 所有 setter 都会自动 re-apply（前提是已经调过 `apply_global()`）。

## 在自定义组件里复用 QSS

```python
qss = ScrollStyle.instance().build_qss(color="primary")  # 拿 primary 色的 QSS 片段
my_widget.setStyleSheet(my_widget.styleSheet() + qss)
```

`build_qss(color, is_dark)` 两个参数都可省略：默认用全局配置和 `ThemeProvider.current_theme`。

> 注意：`build_qss` 出来的 QSS 没有 hover 动画过渡（QSS 不支持 transition）。
> 推荐做法：直接用 `set_bar_color()` 方式（见下文）让单条 bar 跟随特定色，
> 这样 hover 进出依然有动画。

## 让单条 ScrollBar 跟随组件色（典型用例: Textarea）

`Textarea(color="primary")` 时，**它内部的滚动条会自动用 primary 色**——这是组件内部已经为你做好的。原理：

```python
# Textarea._apply_styles() 末尾会自动调用：
ScrollStyle.instance().set_bar_color(
    self.text_edit.verticalScrollBar(),
    self._color,   # 组件自己的 color 属性
)
```

`set_bar_color(bar, color)` 把意图存在 bar 的 QObject 属性 `_hs_scroll_color` 上，动画层 hover 进出时会优先读它而不是全局色。

如果你写自己的滚动 widget 也想这么干，照同样模式调一下即可：

```python
from hero_side_ui import ScrollStyle

# 让某个 QScrollArea 的滚动条用 success 色
ScrollStyle.instance().set_bar_color(
    my_scroll_area.verticalScrollBar(), "success"
)

# 撤销覆盖回到全局色
ScrollStyle.instance().set_bar_color(my_scroll_area.verticalScrollBar(), None)
```

## 卸载

```python
ScrollStyle.instance().remove_global()
```

## 主题联动

`ScrollStyle` 在 `__init__` 时订阅 `ThemeProvider.theme_changed`，主题切换会自动重新 apply。**用户什么都不用做。**

## 颜色规则

| 主题 | normal handle | hover handle |
| --- | --- | --- |
| 亮色 | `<color>-300` | `<color>-400` |
| 暗色 | `<color>-700` | `<color>-600` |

`<color>` 走 HeroUI v2 色阶。可选值：`neutral` (默认) / `default` / `primary` / `secondary` / `success` / `warning` / `danger`。

> **默认 `neutral`**：纯灰、无色相偏移（来自 Tailwind v3 neutral 色阶）。
> 比 `default` (zinc，略带冷色) 更适合"中性元素"如滚动条 handle，
> 不会和组件主色串调色。500 色号视觉过重，hover 用 400/600 更柔和。

## API 一览

| 方法 / 属性                    | 说明                                                |
| ------------------------------ | --------------------------------------------------- |
| `ScrollStyle.instance()`       | 单例入口                                            |
| `apply_global()`               | 把样式注入 `QApplication.styleSheet()`              |
| `remove_global()`              | 卸载样式                                            |
| `build_qss(color=, is_dark=)`  | 生成 QSS 片段，便于组件局部使用                     |
| `set_bar_color(bar, color)`    | 给单条 QScrollBar 注册颜色覆盖，hover 动画也用该色  |
| `set_thickness(px)`            | 设置正常厚度                                        |
| `set_hover_thickness_delta(d)` | 设置 hover 时增加的厚度                             |
| `set_color(color)`             | 设置主题色                                          |
| `set_min_handle_length(px)`    | 设置 handle 最小长度                                |
| `set_track_padding(px)`        | 设置轨道两端 margin                                 |
| `set_duration(ms)`             | 设置 hover 进出过渡时长（默认 150ms，0=无动画）     |
| `set_easing(curve)`            | 设置过渡曲线（默认 `QEasingCurve.OutCubic`）        |
| `set_shadow_alpha(light=, dark=)` | 设置 normal 状态 handle 阴影 alpha（0-255）。hover 时渐变到 0 |
| `thickness` (property)         | 当前正常厚度                                        |
| `hover_thickness` (property)   | 当前 hover 厚度（= thickness + hover_delta）        |
| `color` (property)             | 当前主题色                                          |

## 实现细节

`ScrollStyle` 由两层组成：

1. **静态层（QApplication QSS）**：注入默认状态的 QSS 到 `QApplication.setStyleSheet()`，让全局 QScrollBar 都先有正确的"细 + 暗"初始外观。用 marker 注释 `/* HEROSIDEUI_SCROLLSTYLE_BEGIN/END */` 包裹注入段确保多次 apply 幂等。
2. **动画层（QApplication eventFilter）**：拦截所有 `QScrollBar` 的 `Enter`/`Leave` 事件，为每条 bar 启动 `QVariantAnimation` 在 0→1 之间插值，回调里把"thickness 当前值 + handle 颜色"算出来重新 `setStyleSheet` 到那条 bar 上（局部 QSS 覆盖全局 QSS）。

主题切换时（`ThemeProvider.theme_changed` 触发）自动重新 `apply_global()`，并清掉所有 bar 上残留的局部 stylesheet 让全局新色立即生效。

### 关键技术点（踩坑记录）

1. **hover 加粗用 margin 实现，不是 width**
   Qt QSS 的 `QScrollBar:hover { width: ... }` 不会触发布局重算（width 只在 widget 创建时被读一次）。所以 ScrollStyle 让 QScrollBar 始终保持 hover 厚度（最大值），handle 平时通过左右 margin "瘦身"成视觉上的 thickness，hover 时 margin 渐变到 0 让 handle 占满。

2. **过渡动画必须用 Python 驱动**
   Qt QSS 不支持 CSS `transition`，所以"hover 时滑过去"的过渡只能通过 `QVariantAnimation` 在 0→1 间插值，每帧重生成 QSS 并 setStyleSheet。这就是动画层的核心。

3. **圆角用 `thickness/2`（基于当前进度的瞬时值）**
   动画过程中圆角跟着 thickness 一起变，依然始终保持胶囊形。比固定圆角视觉更对（因为细的时候用 ht/2 会显得太圆，粗的时候用 t/2 又不够圆）。

4. **handle 阴影用 1px border 模拟（仅 neutral 色生效）**
   Qt QSS 不支持 `box-shadow`，`QGraphicsDropShadowEffect` 也不能套到 sub-control 上。用 border + 半透明黑色（normal alpha=15/亮 50/暗，hover alpha=0）是 Qt UI 库的标准做法。border alpha 跟 progress 反向插值（progress=0 满 alpha，progress=1 alpha=0），和粗细/颜色动画走**同一条进度线**，丝滑无缝。

   **仅当 bar 用全局色（默认 neutral）时才有阴影边框**——自定义语义色（primary/success/...）色阶本身鲜明，描边反而显得脏；所以 `Textarea(color="primary")` 滚动条无阴影，`Textarea(color="default")`（走全局 neutral）滚动条带阴影。

## 与 Textarea 等组件的关系

`Textarea` / 其它内置组件**不再自己写** `QScrollBar` 样式（之前 textarea 里那段已删除）。所有滚动条统一由 `ScrollStyle` 提供，保证视觉一致。如果你需要某个 widget 用不同色滚动条，把 `build_qss(color="...")` 的输出 append 到那个 widget 的 styleSheet 即可（组件局部 QSS 优先级高于 QApplication 全局）。
