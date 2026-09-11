# Breadcrumbs 面包屑导航

层级路径指示。对照官方 `Breadcrumbs` / `BreadcrumbItem`（use-breadcrumbs.ts + breadcrumbItem/breadcrumbs 主题）复刻。

## 构造参数（Breadcrumbs）

| 参数                    | 类型                    | 默认           | 说明                                                                      |
| ----------------------- | ----------------------- | -------------- | ------------------------------------------------------------------------- |
| `items`                 | `List[BreadcrumbItem]`  | `[]`           | 面包屑项列表                                                              |
| `variant`               | `str`                   | `"light"`      | `solid` / `bordered` / `light`                                            |
| `color`                 | `str`                   | `"foreground"` | `foreground` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`                  | `str`                   | `"md"`         | `sm` / `md` / `lg`                                                        |
| `radius`                | `str`                   | `"sm"`         | `none` / `sm` / `md` / `lg` / `full`（solid/bordered 变体下可见）         |
| `underline`             | `str`                   | `"hover"`      | `none` / `active` / `hover` / `focus` / `always`                          |
| `separator`             | `QWidget \| str`        | `None`         | 全局分隔符（默认 chevron 图标）；str 渲染为文本                           |
| `max_items`             | `int`                   | `8`            | 超过后折叠为省略号                                                        |
| `items_before_collapse` | `int`                   | `1`            | 省略号前保留项数                                                          |
| `items_after_collapse`  | `int`                   | `2`            | 省略号后保留项数                                                          |
| `hide_separator`        | `bool`                  | `False`        | 隐藏所有分隔符                                                            |
| `is_disabled`           | `bool`                  | `False`        | 禁用（**last 项保持可用**）                                               |
| `disable_animation`     | `bool`                  | `False`        | 关闭过渡                                                                  |
| `render_ellipsis`       | `Callable[[], QWidget]` | `None`         | 自定义省略号渲染（返回 QWidget）                                          |
| `on_action`             | `Callable[[str], None]` | `None`         | 任一项被点击（对齐 `onAction(key)`）                                      |
| `theme`                 | `str`                   | `"auto"`       | `light` / `dark` / `auto`                                                 |

## BreadcrumbItem

| 参数                            | 类型             | 默认    | 说明                                          |
| ------------------------------- | ---------------- | ------- | --------------------------------------------- |
| `label`                         | `str`            | 必填    | 项文字                                        |
| `key`                           | `str`            | `None`  | 项标识（`action_triggered` 发出；缺省用索引） |
| `color` / `size` / `underline`  | `str`            | `None`  | 项级覆盖（缺省跟随 Breadcrumbs）              |
| `start_content` / `end_content` | `QWidget`        | `None`  | 项首/尾附加内容（图标等）                     |
| `separator`                     | `QWidget \| str` | `None`  | 项级分隔符                                    |
| `is_current`                    | `bool`           | `False` | 当前页（非 last 也可声明；文字转全色）        |
| `hide_separator`                | `bool`           | `False` | 隐藏该项后的分隔符                            |
| `is_disabled`                   | `bool`           | `False` | 项级禁用                                      |
| `on_press`                      | `Callable`       | `None`  | 项点击回调                                    |

## 信号

| 信号                    | 参数           | 说明                |
| ----------------------- | -------------- | ------------------- |
| `action_triggered(str)` | 项 key         | 对齐官方 `onAction` |
| `item_pressed(object)`  | BreadcrumbItem | 被点击项配置对象    |

## 自动推断规则（对照官方 breadcrumbs.tsx）

- `is_last`：自动推断（最后一项）
- `is_current`：`isLast || 显式 is_current`——非 last 也可声明 current（官方 `isCurrent = isLast || child.props.isCurrent`）
- `is_disabled`：全局 `is_disabled && !isLast`（官方同款；last 永不禁用）
- 项 `key` 缺省用索引字符串

## 折叠规则

- 项数 `>= max_items` 且 `before + after < 项数` 时折叠：显示前 `before` 项 + 省略号 + 后 `after` 项
- 省略号 = **第一个被折叠项**的占位（官方 `cloneElement(itemsInEllipsis[0], {children: ellipsisIcon})`），点击它触发该项的 press/key
- `before + after >= 项数` 时官方 warn 并跳过折叠，桌面端直接不折叠

## 视觉规格

| 项                  | 值                                                                          |
| ------------------- | --------------------------------------------------------------------------- |
| 非 current 文字     | foreground 50% / 语义色 80%（官方 `text-foreground/50`、`text-primary/80`） |
| current 文字        | 全色                                                                        |
| hover（非 current） | 提亮到全色（官方 `hover:opacity-hover` 的桌面着色近似）                     |
| 按下（非 current）  | 50%（官方 `active:opacity-disabled`）                                       |
| 分隔符              | 默认 chevron-right 图标，`text-default-400`                                 |
| solid               | 列表底 `default-100` + 内边距（md: 10×6）                                   |
| bordered            | 2px `default-200` 边框 + 内边距                                             |
| underlined 偏移     | 4px（官方 `underline-offset-4`）                                            |

## 与 HeroUI 差异

1. 官方 `children` 为 `BreadcrumbItem` React 元素；桌面端 `BreadcrumbItem` 为纯配置类（非 widget），由 Breadcrumbs 渲染。
2. 官方 `renderEllipsis` 接收完整 props 对象；桌面端 `render_ellipsis()` 无参回调，返回 QWidget。
3. 官方 `onPress/onPressStart/onPressEnd/onKeyDown/onKeyUp` 五个事件；桌面端提供 `on_press` + `item_pressed` 信号。
4. 官方 `classNames`/`itemClasses` slot 机制不采纳。
5. 官方 hover/active 用 opacity 过渡；桌面端为着色变化（无透明度动画）。
6. `text_align`/`href` 导航语义桌面端不采纳（无页面跳转）。
