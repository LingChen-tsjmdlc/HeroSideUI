# Icon 图标

`Icon` 是 [pyside-iconify](https://github.com/LingChen-tsjmdlc/pyside-iconify) 的 `IconWidget` 子类，增加 HeroSideUI 内置资源、尺寸与颜色 Token、局部主题支持。渲染、在线加载、缓存、hover 和图标动画由依赖库负责。

安装 HeroSideUI 会同时安装 `pyside-iconify>=1.2.0,<2`。应用可以直接使用 `pyside_iconify` 的公开 API。

## 基本用法

```python
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from hero_side_ui import HeroSideUIProvider, Icon

app = QApplication([])
HeroSideUIProvider.setup(app, theme="light")
window = QWidget()
layout = QHBoxLayout(window)
layout.addWidget(Icon("heroicons--check-solid", color="success", size="lg"))
layout.addWidget(Icon("heroicons:eye-solid", hover_color="primary"))
window.show()
app.exec()
```

所有 Qt 控件与位图都应在 `QApplication` 创建后、Qt 主线程中使用。

## 内置离线图标与在线生态

组件依赖的 52 个 SVG 随包分发，来自 `hero_side_ui/resources/icons/`。首次使用时读取本地资源，转换为 `IconData`，通过公开的 `add_icon()` 注册，再交给依赖库绘制。无需提前联网，也不依赖用户磁盘缓存。

以下三种写法指向同一份本地图标：

```python
Icon("heroicons--eye-solid")             # 兼容已有组件的名称
Icon("heroicons:eye-solid")              # 已随包提供的 Iconify 名称
Icon("herosideui:heroicons-eye-solid")    # 库保留的实际注册名称
```

可用名称可以枚举：

```python
from hero_side_ui.icons import builtin_icon_names
print(builtin_icon_names())
```

HeroSideUI 的适配入口将上述名称解析到保留命名空间 `herosideui:`，不会覆盖应用注册的 `heroicons:` 等普通命名空间。`Icon.iconName()` 返回解析后的实际名称；加载信号中的名称也沿用依赖库的实际名称。

其他 `prefix:name` 原样交给依赖库，缺少本地数据时使用其正常异步加载流程：

```python
from hero_side_ui import Icon
from pyside_iconify import IconWidget, get_icon

online = Icon("mdi:home", size=24)
native = IconWidget("mdi:home", size=24)
native_qicon = get_icon("mdi:home", size=20)
```

这里仍使用依赖库的共享默认客户端。HeroSideUI **不调用全局离线开关，也不修改其默认配置**；内置图标无需请求网络，用户的其他图标仍可联网。直接使用 `pyside_iconify` 时，HeroSideUI 的资源别名、主题和语义颜色适配不会自动生效。

应用可以自行使用 `pyside_iconify.set_offline(True)` 实施全应用严格离线策略；这会影响该默认客户端的在线加载。需要离线分发更多图标时，使用依赖库公开的 `add_icon()`、`load_bundle()` 等接口提供数据。`herosideui:` 由组件库保留，请为应用自定义资源选择其他前缀。

## 参数

除 `icon` 外均为关键字参数。未列出的参数会报错。

| 参数                                                 | 默认值           | 说明                                                                                                                               |
| ---------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `icon`                                               | 必填             | 内置名称、Iconify 名称、本地 SVG 路径（`str` / `Path`）或公开的 `IconData`                                                         |
| `size`                                               | `"md"`           | `sm=16` / `md=24` / `lg=32`，也接受原生数值、`QSize`、宽高元组、`"24px"`、`"1.5em"`；单位为逻辑像素                                |
| `color`                                              | `None`           | HeroUI 颜色 Token（如 `primary` / `danger-600`）或依赖库支持的颜色、颜色映射；未指定时遵循依赖库默认配置，仍未指定则读取控件前景色 |
| `color_light_theme` / `color_dark_theme`             | `None`           | 浅色 / 深色专用颜色，支持相同 Token；优先于通用颜色                                                                                |
| `hover_color`                                        | `None`           | hover 颜色，支持 Token                                                                                                             |
| `hover_color_light_theme` / `hover_color_dark_theme` | `None`           | 浅色 / 深色专用 hover 颜色，支持 Token                                                                                             |
| `opacity`                                            | `None`           | 0～1；未指定时使用依赖库默认值                                                                                                     |
| `width` / `height`                                   | `None`           | 原生宽高覆盖，接受依赖库的尺寸形式                                                                                                 |
| `rotate` / `rotate_overflow`                         | `0` / `False`    | 旋转角度及是否扩大旋转画布                                                                                                         |
| `h_flip` / `v_flip`                                  | `False`          | 水平 / 垂直翻转                                                                                                                    |
| `spin` / `spin_period`                               | `False` / `None` | 持续旋转及周期（秒）                                                                                                               |
| `animation`                                          | `None`           | 原生 `spin` / `pulse` / `breathe` / `ping` / `bounce` 动画                                                                         |
| `animation_period` / `animation_depth`               | `None`           | 原生动画周期与幅度                                                                                                                 |
| `autoplay` / `speed`                                 | `True` / `1.0`   | 原生播放选项；`autoplay` 控制 SVG 内嵌动画                                                                                         |
| `fallback`                                           | 未传             | 未传时沿用依赖库配置与占位策略；显式 `None` 在失败时显示空白；本地名称或路径也可作为备用图标                                       |
| `qss`                                                | `None`           | 传递给依赖库的 Qt 动态属性，可用于 QSS 选择器                                                                                      |
| `is_disabled`                                        | `False`          | 对应原生 `setEnabled(False)`                                                                                                       |
| `theme`                                              | `"auto"`         | 跟随 Provider，或用 `"light"` / `"dark"` 局部覆盖                                                                                  |
| `parent`                                             | `None`           | Qt 父控件                                                                                                                          |

`primary` 等无色阶 Token 使用 500 色阶。颜色映射中的键和值遵循依赖库原生规则；HeroSideUI 不递归替换映射中的语义 Token。多色 SVG 保留依赖库的颜色映射规则，可用 `color={}` 保留原色。

图标大小由原生 `sizeHint()` 提供给布局，保留 `QWidget.size()` 的实际控件尺寸语义。`theme` 通过控件自身的 palette 接入，不为单个图标修改应用全局 palette。调用方 QSS 也可能覆盖 palette，应避免与局部主题设置冲突。

## 动态更新与加载信号

```python
icon = Icon("heroicons--eye-solid", color="primary")
icon.set_icon("heroicons--check-solid")
icon.set_size("lg")
icon.set_color("success")
icon.set_theme("dark")

# 原生接口和信号继续可用
icon.setIcon("mdi:home")
icon.setSize(28)
icon.setColorLightTheme("primary-600")
icon.setColorDarkTheme("primary-300")
icon.setEnabled(False)
icon.loaded.connect(lambda name: print("loaded:", name))
icon.failed.connect(lambda name, error: print("failed:", name, error))
icon.statusChanged.connect(lambda status: print("status:", status))
```

资源已在本地时，构造过程就可能就绪，不应依赖构造后连接的 `loaded` 信号补发通知。在线加载由依赖库负责，`Icon` 不增加第二套请求状态机。

```python
animated = Icon("heroicons--clock", animation="spin", animation_period=1.0)
animated.setAnimation(None)  # 关闭合成动画
```

图标动画由 `pyside-iconify` 持有；SVG 内嵌动画的 `play()` / `pause()` / `replay()`、`setSpeed()` 与原生语义一致。不要为图标另建 HeroSideUI 定时器或补间控制器。

## QIcon、静态位图与旧组件兼容

需要原生 `QIcon` 或静态 `QPixmap` 时，使用同一资源入口：

```python
from PySide6.QtWidgets import QPushButton
from hero_side_ui.icons import get_icon, get_pixmap

button = QPushButton("Save")
button.setIcon(get_icon("heroicons--check-solid", size=20, color="#006fee"))
snapshot = get_pixmap("heroicons--eye-solid", size=24, color="red")
```

这两个函数只适配图标来源与可选的 `stroke_width`，其余选项直接交给依赖库验证；`sm` / `primary` 等 HeroUI Token 是 `Icon` 控件的能力。`get_icon()` 保留原生 QIcon 的高 DPI 渲染能力。静态快照没有异步完成后的自动刷新逻辑。

已有组件仍可使用兼容 API：

```python
from hero_side_ui import Button
from hero_side_ui.utils import load_svg_icon

button = Button("Save", icon="heroicons--check-solid")
pixmap = load_svg_icon("heroicons--chevron-down", size=20, stroke_width=2.5)
original = load_svg_icon("/path/to/logo.svg", color="original")
```

`load_svg_icon()` 已改为调用共享入口，没有保留旧的独立 SVG 渲染器。内置名称、外部路径、原色、描边覆盖、缺失图标返回透明位图，以及默认主题对比色保持兼容。它继续返回 `size × size`、DPR=1 的静态快照，以兼容现有组件的像素几何。

旧组件的字符串图标槽位（如 `Button(icon=...)`）仍是静态加载契约。如果要在这些槽位使用远程图标，应先通过依赖库公开的 `load_icons()` 完成预加载，再设置图标；不会因本次底层迁移自动获得异步刷新。需要随请求结果刷新的独立图标请使用 `Icon`。`stroke_width` 覆盖也要求本地或已注册的数据。

## 示例与验证

```bash
uv run python examples/icon/demo.py
uv run pytest tests/components/test_icon.py tests/utils/test_icon_resources.py tests/utils/test_icon_utils.py
```

示例包含离线图标、颜色和尺寸、hover、局部主题、动画，以及按按钮后才创建的在线图标。回归验证覆盖全部 52 个内置图标与旧绘制的像素一致性、无网络加载、在线共存、资源缓存淘汰、主题切换、描边覆盖与高 DPI。
