# Avatar 头像组件

> 对齐 [HeroUI v2 Avatar](https://v2.heroui.com/docs/components/avatar)。
>
> - 样式锚点：`packages/core/theme/src/components/avatar.ts`
> - 组件锚点：`packages/components/avatar/src/{avatar.tsx,use-avatar.ts,avatar-group.tsx}`

`Avatar` 用于展示用户头像，支持图片、姓名首字母缩写、默认人像图标三级兜底，并可组成 `AvatarGroup` 重叠头像组。

## 快速上手

```python
from hero_side_ui import Avatar, AvatarGroup

Avatar()                                     # 默认人像图标
Avatar(name="Jane Wu")                       # 首字母缩写 → JW
Avatar(src="https://.../photo.jpg")          # 图片头像
Avatar(name="JW", color="danger", is_bordered=True, size="lg")

# 自定义点击 / hover
Avatar(name="Me", is_pressable=True,
       on_click=lambda: print("clicked"),
       on_hover=lambda h: print("hover" if h else "leave"))
# 或用信号
av = Avatar(name="Me", is_pressable=True)
av.clicked.connect(handler)
av.hovered.connect(on_enter)

# 头像组：重叠堆叠，超出以 +N 收尾
AvatarGroup([Avatar(src=u) for u in urls], color="primary", is_bordered=True, max=3, total=10)
```

## Avatar 构造参数

| 参数                | 类型                                       | 默认        | 说明                                           |
| ------------------- | ------------------------------------------ | ----------- | ---------------------------------------------- |
| `src`               | `str \| QPixmap \| QImage \| None`         | `None`      | 图源：本地路径 / Qt 资源 / http(s) URL         |
| `name`              | `str \| None`                              | `None`      | 姓名；无图时生成首字母缩写                     |
| `icon`              | `str \| None`                              | 默认人像    | 无图无 name 时的兜底图标（内置名 / SVG 路径）  |
| `fallback`          | `QWidget \| None`                          | `None`      | 自定义兜底控件（优先级高于 name/icon）         |
| `color`             | `str`                                      | `"default"` | 语义色                                         |
| `radius`            | `"none" \| "sm" \| "md" \| "lg" \| "full"` | `"full"`    | 圆角；`full` 按盒子一半动态算                  |
| `size`              | `"sm" \| "md" \| "lg"`                     | `"md"`      | 尺寸：sm=32 / md=40 / lg=56                    |
| `is_bordered`       | `bool`                                     | `False`     | 彩色描边环（ring + offset 缝隙）               |
| `is_disabled`       | `bool`                                     | `False`     | 禁用态（整控件半透明）                         |
| `show_fallback`     | `bool`                                     | `False`     | 有图时，在加载中/失败仍显示兜底                |
| `disable_animation` | `bool`                                     | `False`     | 关闭图片 fade-in                               |
| `is_pressable`      | `bool`                                     | `False`     | 可点击（手型光标 + 点击/按压信号）             |
| `on_click`          | `Callable[[], None] \| None`               | `None`      | 点击回调，等价于 `connect(clicked)`            |
| `on_hover`          | `Callable[[bool], None] \| None`           | `None`      | hover 回调 `fn(hovered)`：进入 True/离开 False |
| `theme`             | `"auto" \| "light" \| "dark"`              | `"auto"`    | 主题模式；auto 跟随 `ThemeProvider`            |
| `parent`            | `QWidget \| None`                          | `None`      | 父级                                           |

### 兜底优先级

1. 有 `src` 且加载成功 → 显示图片
2. 否则（无 src / 加载中 / 失败）：`fallback` 控件 → `name` 首字母 → 默认人像图标
3. `show_fallback=False` 且有 `src` 时，加载完成前不显示兜底（保持 solid 背景）

## Avatar 信号

| 信号        | 说明                              |
| ----------- | --------------------------------- |
| `loaded`    | 图片加载成功时触发                |
| `failed`    | 图片加载失败时触发                |
| `pressed`   | `is_pressable` 时鼠标左键按下     |
| `released`  | `is_pressable` 时鼠标左键释放     |
| `clicked`   | `is_pressable` 时在头像内完成点击 |
| `hovered`   | 鼠标进入（未禁用时）              |
| `unhovered` | 鼠标离开（未禁用时）              |

> 自定义点击/hover 有两种写法：① 构造时传 `on_click` / `on_hover` 回调；② 事后 `avatar.clicked.connect(fn)` / `avatar.hovered.connect(fn)`。`hovered`/`unhovered` 与 `is_pressable` 无关，任何头像都会发出。

## Avatar 公共方法

| 方法                      | 说明                                   |
| ------------------------- | -------------------------------------- |
| `set_src(src)`            | 更换图源                               |
| `set_name(name)`          | 更换姓名（重算首字母）                 |
| `set_icon(icon)`          | 更换兜底图标                           |
| `set_color(color)`        | 切换语义色                             |
| `set_radius(radius)`      | 切换圆角                               |
| `set_size(size)`          | 切换 sm / md / lg                      |
| `set_bordered(bool)`      | 切换描边环                             |
| `set_disabled(bool)`      | 切换禁用态                             |
| `set_show_fallback(bool)` | 切换兜底显隐策略                       |
| `set_pressable(bool)`     | 切换可点击态                           |
| `status()`                | 图源状态 pending/loading/loaded/failed |
| `pixmap()`                | 已加载的 `QPixmap`（无则 None）        |
| `set_theme(theme)`        | `"auto" \| "light" \| "dark"`          |

## AvatarGroup 构造参数

| 参数                | 类型                          | 默认     | 说明                               |
| ------------------- | ----------------------------- | -------- | ---------------------------------- |
| `avatars`           | `list[Avatar]`                | `[]`     | 头像列表                           |
| `max`               | `int`                         | `5`      | 最多显示数量，超出以 `+N` 计数收尾 |
| `total`             | `int \| None`                 | `None`   | 手动指定"未显示数量"，覆盖自动计算 |
| `color`             | `str \| None`                 | `None`   | 组级语义色，下发给子 Avatar        |
| `radius`            | `str \| None`                 | `None`   | 组级圆角                           |
| `size`              | `str \| None`                 | `None`   | 组级尺寸                           |
| `is_bordered`       | `bool`                        | `False`  | 组级描边环                         |
| `is_disabled`       | `bool`                        | `False`  | 组级禁用态                         |
| `is_grid`           | `bool`                        | `False`  | 网格排布（正间距，不重叠）         |
| `render_count`      | `Callable[[int], QWidget]`    | `None`   | 自定义计数控件工厂                 |
| `disable_animation` | `bool`                        | `False`  | 关闭 hover 平移动画                |
| `theme`             | `"auto" \| "light" \| "dark"` | `"auto"` | 主题模式                           |

## 可选值

### color

`"default"` `"primary"` `"secondary"` `"success"` `"warning"` `"danger"`

### radius

`"none"` `"sm"` `"md"` `"lg"` `"full"`

### size

`"sm"`(32) `"md"`(40) `"lg"`(56)

## 特殊行为

- **首字母缩写**：`safe_initials(name)` 取首个单词与末个单词的首字符，最多两字母大写；无空格（如中文）取首字符。
- **图片 fade-in**：加载完成后图像 opacity 0→1，对齐 HeroUI `transition-opacity duration-500`；`disable_animation=True` 时直接显示。
- **描边环**：`is_bordered` 时头像盒子外加 `ring(2px) + offset(2px)` 一圈，缝隙用页面背景色，对齐 `ring-2 ring-offset-2`。
- **组级下发**：`AvatarGroup` 的 color/radius/size/is_bordered/is_disabled 会应用到所有子 Avatar。
- **重叠堆叠**：`AvatarGroup` 用绝对定位让相邻头像重叠（越靠后的头像 z 越高，压在前面之上）；hover 其中一个时该头像浮到最顶并向左平移让出缝隙（`-translate-x-3`，带 250ms 动画，`disable_animation=True` 关闭）。

## 示例

`examples/avatar/demo.py` 覆盖：Default / Sizes / Colors / Radius / Bordered / Disabled / With Text / With Image / Fallback / Group / Group Grid / Custom Count。

## 与 HeroUI 差异

1. HeroUI 的 `classNames`（base/img/name/icon/fallback）是 tailwind-variants slot；Qt 版为内部自绘/子控件，外部无需关心 slot 名。
2. 图片裁剪：Web 用 CSS `object-cover` + `overflow-hidden`；Qt 版在 `paintEvent` 内 `QPainterPath` 圆角裁剪 + cover 缩放。
3. 描边环：Web 用 `ring` + `ring-offset`；Qt 版自绘两层圆角矩形模拟。
4. `AvatarGroup` 的 hover 让位动画（`-translate-x-3`）以绝对定位 + `QPropertyAnimation(pos)` 实现（250ms）。
5. 焦点环 / `isFocusable` 未复刻（桌面头像通常非可聚焦交互元素）。
