# 主题定制：颜色、圆角、底色（设计草案）

状态：设计已确定，尚未实现。一次性完成，不分期。实现前以此为准。

## 要解决什么

默认设计语言是 HeroUI v2。用户想在 `HeroSideUIProvider.setup()` 里直接改色板、圆角、底色和文字色，不需要额外的配置文件。

## 已确定

| 事项                      | 结论                                                                               |
| ------------------------- | ---------------------------------------------------------------------------------- |
| 配置入口                  | 只用 `HeroSideUIProvider.setup()`，配置直接写在调用处，不引入额外文件              |
| 色板                      | 必须手写完整 10 阶，不自动生成，不补全                                             |
| 实色上的字色              | 单独参数 `color_foreground`；改了某个色的色阶，必须同时写它的字色                  |
| 圆角                      | 只接受 `{"sm": 2, "md": 6, "lg": 10}` 这种数值，三个必须全写，不做预设档名         |
| 四个面/字 token           | `background`、`foreground`、`content_background`、`popup_background`，亮暗各写一个 |
| 文字色默认值              | 统一成官方 HeroUI 的 `#11181C` / `#ECEDEE`                                         |
| 参数形式                  | 全部 keyword-only，现有参数一个不动，旧调用不受影响                                |
| 不提供 `default_tokens()` | 默认值写在本文档和用户文档里，不加新 API                                           |

### 用法示例

```python
HeroSideUIProvider.setup(
    app,
    theme="auto",
    colors={
        # 顺序固定：50, 100, 200 ... 900
        "primary": ["#fff1f2", "#ffe4e6", "#fecdd3", "#fda4af", "#fb7185",
                    "#e11d48", "#be123c", "#9f1239", "#881337", "#4c0519"],
    },
    color_foreground={"primary": "#FFFFFF"},
    radius={"sm": 2, "md": 6, "lg": 10},
    background={"light": "#FFFFFF", "dark": "#0A0A0A"},
    foreground={"light": "#11181C", "dark": "#ECEDEE"},
    content_background={"light": "#FFFFFF", "dark": "#18181B"},
    popup_background={"light": "#FFFFFF", "dark": "#27272A"},
)
```

没写的参数保持默认。

### colors

- 写法一：10 个 hex 的列表，按 50 到 900 的顺序。一个色一行，最省篇幅。
- 写法二：`{50: "...", ..., 900: "..."}` 字典，更直观但更长。两种等价。
- 色名只能是现有的：`default`、`primary`、`secondary`、`success`、`warning`、`danger`（内部用的 `neutral` 也在内）。不能新增色名。
- 写了哪个色，这个色就必须 10 阶写全；没写的色保持默认。
- hex 只接受 `#RRGGBB`。
- 暗色不用另写。库里暗色是把亮色阶按索引镜像反转（50 对 900，100 对 800 ……），所以亮色阶必须从浅到深排列。不满足时给一条警告，不报错。

### color_foreground（实色上的字色）

指 solid 按钮、实色 Chip、Alert、Avatar、Toast 等"实色底上的文字/图标"的颜色。

现状：这条规则散在 7 处各写一份（`button` 两处、`chip_styles`、`alert`、`avatar`、`toast`、`calendar`），另有 `checkbox` 的勾号图标：

| 色                                     | 亮色      | 暗色                                                      |
| -------------------------------------- | --------- | --------------------------------------------------------- |
| primary / secondary / success / danger | `#FFFFFF` | `#FFFFFF`                                                 |
| warning                                | `#000000` | `#000000`                                                 |
| default                                | `#FFFFFF` | `#D4D4D8`（暗色下 default 实色底用的是 700 档，不是 500） |

官方 HeroUI 是按 500 档底色自动算黑字或白字。本库不自动算，改成显式配置。

写法：

```python
color_foreground={
    "primary": "#FFFFFF",                                # 写一个 hex：亮暗通用
    "default": {"light": "#FFFFFF", "dark": "#D4D4D8"},  # 写字典：亮暗分开
}
```

规则：

1. 值可以是 `"#RRGGBB"`（亮暗通用），或 `{"light": ..., "dark": ...}`。
2. **改了 `colors` 里某个色，就必须在 `color_foreground` 里写它**，否则报错，提示"primary 的色阶已改，请同时指定 color_foreground"。理由：色阶一变，原来的白字可能就看不清，不能让它悄悄沿用。
3. 没改色阶的色，字色保持上表默认；也允许只改字色不改色阶。
4. 校验只提示、不改写：字色与底色（500 档，暗色下的 default 用 700 档）的对比度低于 4.5:1 时给一条警告，写明实际比值。不会替你换字色。
5. 统一入口 `get_color_foreground(color, theme)`，上面 7 处加勾号图标全部改成走它。

### radius

- 组件的 `radius="lg"` 是档位名，永远不变。`setup` 里的 `"lg": 10` 是这个档位的像素值。名字固定、数值可配，所以不存在"预设档冲突"。
- `sm`、`md`、`lg` 三个必须全写，缺一个报错。值是非负整数 px，要求 `sm <= md <= lg`。
- `none` 恒为 0，`full` 按高度动态算，两者不可配。
- 内部的 `no/small/medium/large` 长名别名要跟着一起改。别名现在是 import 时复制的字符串，不同步会读到旧值。

### background / foreground / content_background / popup_background

四个参数写法一致：`{"light": "#RRGGBB", "dark": "#RRGGBB"}`，亮暗两个都要写。

| 参数                 | 含义                         | 默认亮    | 默认暗    | 谁在用                                                                                 |
| -------------------- | ---------------------------- | --------- | --------- | -------------------------------------------------------------------------------------- |
| `background`         | 窗口底色，页面最底层         | `#FAFBFD` | `#0B0D12` | `ThemeProvider` 同步到 `QApplication` 调色板                                           |
| `foreground`         | 所有文字、图标的默认色       | `#11181C` | `#ECEDEE` | 所有组件的文字色                                                                       |
| `content_background` | 内容面底色，浮在窗口上的"面" | `#FFFFFF` | `#18181B` | Card、Toast、Radio 卡片、Accordion、Drawer、Calendar 头部                              |
| `popup_background`   | 弹出层底色，浮在内容面上的层 | `#FFFFFF` | `#27272A` | Popover、Tooltip、Slider 浮标，以及基于 Popover 的 Dropdown、Select、Autocomplete 弹层 |

要点：

- `content_background` 对应官方 content1。官方 content2 到 content4 是 hover、层叠用的，仍从 `default` 色阶取，不开放。
- `popup_background` 是桌面端的有意偏离：官方 Popover 与 Card 同色，本库暗色下弹层比 Card 亮一档，贴在 Card 上才分得出层级。命名不用 `overlay`，官方里它是模态遮罩的 `#000`。
- 暗色下层级靠"窗口底 < 内容面 < 弹层"逐级变亮，改暗色值时要三个一起看。
- Card 暗色底原来是 `default[900]`，改完后是 `content_background`。默认值相同，但此后 Card 底色不再跟随 `default` 色阶，一个来源、一个入口。
- 所有文字统一用 `foreground`，不做"每层各自的前景色"。

### hover / 按下色

不新增配置，保持从 `default` 色阶派生（官方 content2 到 content4 也是如此）。唯一影响：`state_palette.py` 的 hover 色是按"暗色 content1 = `#18181B`"标定的。用户把 `content_background` 改成明显偏离的颜色时，hover 色可能不协调；此时用户可以通过改 `default` 色阶来调。用户文档里写一句说明即可，代码不动。

### 生效规则

1. 先校验、后生效。任何一项不合法，整个 `setup` 抛一个 `ValueError`，一次列出所有问题，不会出现配置一半生效。
2. 在 `ThemeProvider` 初始化之前应用，首屏的底色就是对的。
3. 原地改写 `HEROUI_COLORS` 和 `RADIUS`；其余 token 存进统一的 token 注册表。组件运行时读，不在 import 时缓存。
4. 保存原始默认值，`teardown()` 时还原，保证重复 `setup` 和测试可复现。
5. 创建组件之后才调用 `setup` 时，给一次警告：已有组件不会刷新。

## 现状：为什么要抽 token

### 文字色

没有统一来源，各组件自己写死，而且有两套值：

| 亮 / 暗               | 使用位置                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `#18181b` / `#fafafa` | `theme_provider`、`text_style`、`icon_utils`；`link`、`progress` 的亮色                                       |
| `#11181C` / `#ECEDEE` | `checkbox`、`radio`、`switch`、`slider`、`tooltip`、`popover`、`calendar`、`toast`；`link`、`progress` 的暗色 |

`link` 和 `progress` 亮色用第一套、暗色用第二套，同一组件内就不一致。统一成第二套后，第一套那几处会有轻微色差，属于修正。做法：新增唯一入口 `get_foreground(theme)`，约 20 处字面量逐个改成走它。

### 内容面底色与弹层底色

当时做组件不是没考虑底色，而是每个组件各自决定，没有抽成 token：

| 组件                            | 亮色      | 暗色           | 写法                                            |
| ------------------------------- | --------- | -------------- | ----------------------------------------------- |
| Card                            | `#ffffff` | `default[900]` | 字面量 + 色阶索引混用                           |
| Toast                           | `#FFFFFF` | `#18181b`      | 字面量                                          |
| Radio 卡片                      | `#ffffff` | `default[900]` | 字面量 + 色阶索引                               |
| Accordion 容器                  | `#ffffff` | `default[900]` | 同上                                            |
| Accordion splitted 条目         | `#ffffff` | `default[800]` | 见下，遗漏                                      |
| Drawer                          |           |                | 代码注释写明"无独立 token，用 default 色阶换算" |
| Popover / Tooltip / Slider 浮标 | `#ffffff` | `#27272a`      | 字面量                                          |

后果：改 `background` 后 Card 不跟着变；同一份配置下，Card 跟着 `default` 色阶变，Toast 不跟。

做法：新增入口 `get_content_background(theme)` 和 `get_popup_background(theme)`，上表组件统一从它们取。

### Accordion 暗色不一致：确认为遗漏

`accordion.py`（shadow 变体容器）暗色底用 `default[900]`；`item.py`（splitted 变体的每个条目，注释写"每项独立 Card"）用 `default[800]`。官方 splitted 条目是 `bg-content1`，与 Card 同色，所以 800 是遗漏。

处理：条目改走 `content_background`。边框同步核对：容器暗色边框用 `default[800]`，条目用 `default[700]`，这里一并统一。注意这会让暗色下 splitted 条目的底色比现在略深（800 变 900），是修正，实现时会如实告知。

## 实现前要处理的硬编码

动手前先逐个确认，不处理的话配置会漏网。

| 类别                    | 位置                                                                                             | 处理方式                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| 圆角写死数字            | `accordion/accordion.py`、`accordion/item.py`、`listbox/item.py`、`slider/_thumb_tip.py` 共 4 处 | 逐个判断是否应走 `RADIUS`                                    |
| 文字色字面量            | 见上方"文字色"表，约 20 处                                                                       | 改走 `get_foreground`                                        |
| 实色字色                | `button`（两处）、`chip_styles`、`alert`、`avatar`、`toast`、`calendar`、`checkbox` 勾号         | 改走 `get_color_foreground`                                  |
| 内容面 / 弹层底色字面量 | 见上方表，约 12 处                                                                               | 改走 `get_content_background` / `get_popup_background`       |
| 白色字面量              | 约 26 个文件含 `#fff` / `white`                                                                  | 逐个归类：实色字色、内容面、弹层，或确实与主题无关（如描边） |
| 磨砂态半透明底          | `card.py` 的 `#18181b` / `#ffffff` 带透明度                                                      | 由 `content_background` 加透明度派生，不再写字面量           |

## 不在范围内

- 运行时热切换：`theme="light"` / `"dark"` 硬锁的组件不在主题广播里，是独立的另一个功能，不属于本次"启动时配置"。
- 新增自定义色名。
- 阴影、字号体系的配置。
- 局部子树主题：Qt 没有层叠机制，成本过高。
