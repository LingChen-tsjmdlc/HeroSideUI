# ThemeSwitcher — 主题切换按钮

一键切换全局亮暗色模式的图标按钮组件。基于 HeroSideUI 自己的 `Button` 实现，与 `ThemeProvider` 配合。

## 快速开始

```python
from hero_side_ui import ThemeSwitcher

# 默认: 亮色模式显示太阳（金黄色），暗色模式显示月亮（浅蓝色）
switcher = ThemeSwitcher()
layout.addWidget(switcher)
```

点击按钮 → 调用 `ThemeProvider.instance().toggle()` → 全局所有 `theme="auto"` 的组件自动切换。

## 自定义颜色

```python
# 用你喜欢的颜色
switcher = ThemeSwitcher(
    sun_color="#FF8800",       # 橙色太阳
    moon_color="#88CCFF",      # 浅蓝月亮
)

# 或用 QColor
from PySide6.QtGui import QColor
switcher = ThemeSwitcher(
    sun_color=QColor(255, 200, 0),
    moon_color=QColor(100, 150, 255),
)
```

## 自定义 icon

```python
# 用 HeroSideUI 内置的其他 icon
switcher = ThemeSwitcher(
    sun_icon="heroicons--eye-solid",
    moon_icon="heroicons--eye-slash-solid",
)

# 或用任意 SVG 文件路径
switcher = ThemeSwitcher(
    sun_icon="C:/my_icons/light.svg",
    moon_icon="C:/my_icons/dark.svg",
)
```

注意：自定义 SVG 最好使用 `fill="currentColor"`，这样 `sun_color`/`moon_color` 才能正确生效。

## 自定义按钮外观

ThemeSwitcher 继承自 `Button`，所以接受所有 Button 的样式参数：

```python
switcher = ThemeSwitcher(
    variant="flat",      # solid / bordered / flat / light（默认） / faded / ghost
    color="primary",     # default（默认） / primary / secondary / success / warning / danger
    size="lg",           # sm（28×28） / md（36×36，默认） / lg（44×44）
    radius="md",         # full（默认 圆形） / lg / md / sm / none
)
```

## API 参考

### 构造参数

| 参数         | 类型            | 默认                    | 说明                                   |
| ------------ | --------------- | ----------------------- | -------------------------------------- |
| `sun_icon`   | `str`           | `"flowbite--sun-solid"` | 亮色模式 icon（内置图标名或 SVG 路径） |
| `moon_icon`  | `str`           | `"ri--moon-clear-fill"` | 暗色模式 icon                          |
| `sun_color`  | `str \| QColor` | `"#F5A524"`             | 太阳 icon 颜色                         |
| `moon_color` | `str \| QColor` | `"#7DD3FC"`             | 月亮 icon 颜色                         |
| `icon_size`  | `int \| None`   | None（按 size 自动）    | icon 像素尺寸                          |
| `variant`    | `str`           | `"flat"`                | Button 变体                            |
| `color`      | `str`           | `"default"`             | Button 色调                            |
| `size`       | `str`           | `"md"`                  | Button 尺寸                            |
| `radius`     | `str`           | `"full"`                | Button 圆角                            |

注：`icon_only` 被 ThemeSwitcher 强制设为 `True`（正方形按钮），不允许用户覆盖。

### 动态 API

| 方法                          | 说明          |
| ----------------------------- | ------------- |
| `set_sun_icon(name_or_path)`  | 切换亮色 icon |
| `set_moon_icon(name_or_path)` | 切换暗色 icon |
| `set_sun_color(color)`        | 改太阳颜色    |
| `set_moon_color(color)`       | 改月亮颜色    |
| `set_icon_size(px)`           | 改 icon 尺寸  |

### 行为说明

- **始终 auto 模式** — ThemeSwitcher 永远跟随 ThemeProvider，不允许硬锁。`set_theme("dark")` 会被忽略。
- **icon 自动切换** — 当全局主题变化时（无论是 ThemeSwitcher 自己点击还是其他来源），icon 自动从太阳/月亮间切换。
- **方形/圆形按钮** — 默认 `setFixedSize(h, h)` 让按钮是正方形，`radius="full"` 配合得到圆形按钮效果。

## 完整示例

见 `examples/theme_toggle/demo.py`：

```python
from PySide6.QtWidgets import QHBoxLayout
from hero_side_ui import ThemeSwitcher, Button

# 顶栏放一个 ThemeSwitcher
header = QHBoxLayout()
header.addStretch()
header.addWidget(ThemeSwitcher())
```
