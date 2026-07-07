# Link 链接组件

> 对齐 [HeroUI v2 Link](https://v2.heroui.com/docs/components/link)。
>
> - 样式锚点：`packages/core/theme/src/components/link.ts`
> - 组件锚点：`packages/components/link/src/{link.tsx,use-link.ts,link-icon.tsx}`

`Link` 用于在文本中嵌入可点击的超链接。

视觉规格：

- 行内 inline-flex + items-center
- 6 种语义颜色：`foreground / primary / secondary / success / warning / danger`
- 3 档字号：`sm` (14px) / `md` (16px) / `lg` (18px)
- 5 档下划线：`none / hover / always / active / focus`
- `is_block=False`（默认）：hover→opacity 0.8（暗 0.9）；active→opacity 0.5
- `is_block=True`：内边距 `px-2 py-1`，hover 时绘制 `rounded-xl`(12px) 的色块（foreground/10、其余 5 色 /20）
- `is_disabled=True`：opacity 0.5 + 鼠标箭头光标 + 不响应交互

## 快速上手

```python
from hero_side_ui import Link

Link("HeroUI", href="https://heroui.com")
Link("External", href="https://heroui.com", is_external=True, show_anchor_icon=True)
Link("Block", color="primary", is_block=True)
Link("Disabled", is_disabled=True)
```

## 构造参数

| 参数                | 类型                                                                             | 默认        | 说明                                                          |
| ------------------- | -------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------- |
| `children`          | `str`                                                                            | `""`        | 显示的文本                                                    |
| `href`              | `str`                                                                            | `""`        | 链接地址；`is_external=True` 时点击会用浏览器打开             |
| `size`              | `"sm" \| "md" \| "lg"`                                                           | `"md"`      | 字号                                                          |
| `color`             | `"foreground" \| "primary" \| "secondary" \| "success" \| "warning" \| "danger"` | `"primary"` | 文字 / 块底色                                                 |
| `underline`         | `"none" \| "hover" \| "always" \| "active" \| "focus"`                           | `"none"`    | 下划线触发时机                                                |
| `is_block`          | `bool`                                                                           | `False`     | True 时启用 block 模式：padding + hover 色块                  |
| `is_external`       | `bool`                                                                           | `False`     | True 时点击调 `webbrowser.open(href)` 在系统浏览器打开        |
| `is_disabled`       | `bool`                                                                           | `False`     | 禁用：半透明 + 不响应点击/键盘                                |
| `show_anchor_icon`  | `bool`                                                                           | `False`     | 文字右侧追加锚点图标                                          |
| `anchor_icon`       | `str \| QWidget \| None`                                                         | `None`      | 自定义锚点图标；str 为内置 SVG 名 / 文件路径；None 用默认分享 |
| `disable_animation` | `bool`                                                                           | `False`     | 关闭 hover/active 透明度过渡 + block 背景过渡                 |
| `is_text_selectable`| `bool`                                                                           | `False`     | 允许框选/复制链接文字（默认不可选，仅点击）                   |
| `theme`             | `"auto" \| "light" \| "dark"`                                                    | `"auto"`    | 主题模式；auto 跟随 `ThemeProvider`                           |
| `parent`            | `QWidget`                                                                        | `None`      | 父级                                                          |

## 信号

| 信号         | 说明                                          |
| ------------ | --------------------------------------------- |
| `clicked()`  | 鼠标释放在 widget 内，或键盘 Space/Enter 触发 |
| `pressed()`  | 鼠标按下                                      |
| `released()` | 鼠标释放（无论是否在 widget 内）              |

## 公共方法

| 方法                                      | 说明                          |
| ----------------------------------------- | ----------------------------- |
| `set_children(text)`                      | 修改文本                      |
| `set_href(href)`                          | 修改链接地址                  |
| `set_size(size)`                          | 切换 sm/md/lg                 |
| `set_color(color)`                        | 切换 6 种颜色                 |
| `set_underline(u)`                        | 切换 5 档下划线               |
| `set_is_block(bool)`                      | 切换 block 模式               |
| `set_is_external(bool)`                   | 是否点击时打开浏览器          |
| `set_is_disabled(bool)`                   | 切换禁用                      |
| `set_show_anchor_icon(bool)`              | 显示/隐藏锚点图标             |
| `set_anchor_icon(str \| QWidget \| None)` | 自定义锚点图标                |
| `set_disable_animation(bool)`             | 启用/关闭过渡动画             |
| `set_theme(theme)`                        | `"auto" \| "light" \| "dark"` |
| `Link.valid_sizes()`                      | 静态：`("sm","md","lg")`      |
| `Link.valid_colors()`                     | 静态：6 种                    |
| `Link.valid_underlines()`                 | 静态：5 档                    |

## 主题适配

- `foreground`：亮色 `#18181b` / 暗色 `#ECEDEE`
- 5 个语义色：取 `HEROUI_COLORS[color][500]`，亮暗一致（与 HeroUI 原版保持）
- block 模式 hover 色：基于当前 color 取 alpha=0.10（foreground）或 0.20（其余）

## 与 HeroUI 差异

1. HeroUI 的 `as` prop（自定义渲染元素）不适用：Qt 没有 anchor 标签语义，组件直接是可点击 QFrame。
2. HeroUI 的 `onPress / onPressStart / onPressEnd` 系列对应 Qt 信号：`clicked / pressed / released`。
3. 默认 anchor icon 来自项目内置 [`icon-park-outline--share.svg`](../hero_side_ui/resources/icons/icon-park-outline--share.svg)（与 HeroUI 自带 LinkIcon 同语义：外部分享小箭头）。
4. `is_external=True` 时通过 Python `webbrowser` 模块打开 `href`，等价于浏览器 `target="_blank"`。
5. `underline-offset-4` 在 Qt QFont 下没有原生 API，文字下划线沿用 Qt 默认偏移；视觉上与 web 略有差异。
6. 焦点环（focus ring）：Qt 自带 `FocusRect`，`focus` underline 模式可以独立看到下划线效果。

## 演示

`examples/link/demo.py` 共 11 节：Default / Sizes / Colors / Underline / isBlock / External / 自定义 anchor / Disabled / disable_animation / 行内嵌入 / clicked 信号。
