# Kbd 键盘按键组件

> 对齐 [HeroUI v2 Kbd](https://v2.heroui.com/docs/components/kbd)，并按项目惯例扩展 `size` / `radius` / `platform` 三档。
>
> - 样式锚点：`packages/core/theme/src/components/kbd.ts`
> - 组件锚点：`packages/components/kbd/src/{kbd.tsx,use-kbd.ts,utils.ts}`

`Kbd` 用于在文档/帮助/快捷键提示等处展示键盘按键。视觉规格：

- 背景 `default-100`、文字 `foreground-600`
- `shadow-small` 轻投影 + `rounded-small` 圆角
- 内边距 `px-1.5 py-0.5`、按键间距 `space-x-0.5`
- 字号 `text-small` (14px)、字重 `normal`

## 快速上手

```python
from hero_side_ui import Kbd

Kbd(keys="command")                              # ⌘
Kbd(keys=["command", "shift"], children="N")     # ⌘ ⇧ + "N"
Kbd(children="Esc")                              # 纯文字
Kbd(keys="space", use_unicode=True)              # unicode 字符回退
Kbd(keys="fn", platform="mac")                   # 强制 mac 版 fn (地球仪)
Kbd(keys="command", radius="full", size="lg")    # 大号胶囊形
```

## 构造参数

| 参数          | 类型                                               | 默认     | 说明                                                                      |
| ------------- | -------------------------------------------------- | -------- | ------------------------------------------------------------------------- |
| `children`    | `str`                                              | `""`     | keys 之后追加的自定义文字（HeroUI children 等价）                         |
| `keys`        | `str \| Sequence[str] \| None`                     | `None`   | 单个 KbdKey 或多个组合（顺序即渲染顺序）                                  |
| `size`        | `"sm" \| "md" \| "lg"`                             | `"md"`   | 三档尺寸（影响 padding / 字号 / icon 大小）                               |
| `radius`      | `"none" \| "sm" \| "md" \| "lg" \| "full" \| None` | `None`   | 圆角；`None` 按 size 推断（sm/md→sm, lg→md）；`full` 走当前高度的一半     |
| `platform`    | `"auto" \| "mac" \| "win" \| "linux"`              | `"auto"` | 平台路由：影响 `fn` / `alt` 的 icon；`auto` 由 `sys.platform` 决定        |
| `theme`       | `"auto" \| "light" \| "dark"`                      | `"auto"` | 主题模式；auto 跟随 `ThemeProvider`                                       |
| `use_unicode` | `bool`                                             | `False`  | True → 用 unicode 字符（HeroUI 原版形态）；False → 用项目内置 SVG（默认） |
| `parent`      | `QWidget`                                          | `None`   | 父级                                                                      |

## KbdKey 全集（23 个）

| Key       | Label     | SVG (default)                                   | Glyph (use_unicode=True) |
| --------- | --------- | ----------------------------------------------- | ------------------------ |
| command   | Command   | carbon--mac-command                             | ⌘                        |
| shift     | Shift     | carbon--mac-shift                               | ⇧                        |
| ctrl      | Control   | qlementine-icons--key-ctrl                      | ⌃                        |
| option    | Option    | carbon--mac-option                              | ⌥                        |
| enter     | Enter     | boxicons--enter                                 | ↵                        |
| backspace | Backspace | material-symbols--backspace-outline             | ⌫                        |
| delete    | Delete    | material-symbols--delete-outline                | Del                      |
| escape    | Escape    | bi--escape                                      | ⎋                        |
| tab       | Tab       | octicon--tab-24                                 | ⇥                        |
| capslock  | Caps Lock | bi--capslock                                    | ⇪                        |
| up        | Up        | teenyicons--up-solid                            | ↑                        |
| right     | Right     | teenyicons--right-solid                         | →                        |
| down      | Down      | teenyicons--down-solid                          | ↓                        |
| left      | Left      | teenyicons--left-solid                          | ←                        |
| pageup    | Page Up   | iconoir--page-up                                | ⇞                        |
| pagedown  | Page Down | iconoir--page-down                              | ⇟                        |
| home      | Home      | mdi--arrow-top-left                             | ↖                        |
| end       | End       | mdi--arrow-bottom-right                         | ↘                        |
| help      | Help      | material-symbols--help-outline                  | ?                        |
| space     | Space     | tabler--space                                   | ␣                        |
| fn ★      | Fn        | mac: ion--globe-outline / win: tabler--function | Fn                       |
| win       | Win       | mingcute--windows-line                          | ⌘                        |
| alt ★     | Alt       | mac: carbon--mac-option / win: tabler--alt      | ⌥                        |

★ 标注的 key 走 platform 路由，`auto` 时由 `sys.platform` 决定。

> **`backspace` vs `delete`**：HeroUI 原版 `delete` 字符是 ⌫（实为退格）；本组件把这两个语义拆开 ——
> `backspace` (`⌫`) 用 `material-symbols--backspace-outline`，
> `delete` (Forward Delete) 用 `material-symbols--delete-outline`（垃圾桶语义）。
>
> 之所以默认走 SVG 而非 unicode 字符：Qt 在 Windows / Linux 默认字体下对 ⌘ ⇧ ⌃ 等控制字形支持参差，缺字时回退方块。SVG 跨平台一致并随主题着色。

## 公共方法

| 方法                    | 说明                                                          |
| ----------------------- | ------------------------------------------------------------- |
| `set_keys(keys)`        | 重设 keys（接受 None / str / 列表）                           |
| `keys()`                | 当前 keys 列表                                                |
| `set_children(text)`    | 重设 children 文字                                            |
| `children_text()`       | 当前 children 文字                                            |
| `set_use_unicode(bool)` | 切换 SVG / unicode 字符渲染                                   |
| `set_size(size)`        | 切换 sm / md / lg                                             |
| `set_radius(radius)`    | 切换 none / sm / md / lg / full；传 None 切回“跟随 size 推断” |
| `set_platform(p)`       | 切换 auto / mac / win / linux                                 |
| `set_theme(theme)`      | `"auto" \| "light" \| "dark"`                                 |
| `Kbd.valid_keys()`      | 静态：返回所有合法 key 名                                     |
| `Kbd.valid_sizes()`     | 静态：`("sm","md","lg")`                                      |
| `Kbd.valid_radii()`     | 静态：`("none","sm","md","lg","full")`                        |
| `Kbd.valid_platforms()` | 静态：`("auto","mac","win","linux")`                          |

## 主题适配

- 亮色：`bg=#f4f4f5`（default-100），`fg=#52525b`（default-600）
- 暗色：`bg=#27272a`（default-800），`fg=#d4d4d8`（default-300）
- SVG 走 `load_svg_icon(color=fg)` 自动跟随主题

## 与 HeroUI 差异

1. HeroUI 走 unicode 字符；本组件默认走内置 SVG，提供 `use_unicode=True` 还原原版形态。
2. HeroUI 的 `classNames`（base/abbr/content）是 React tailwind-variants slot；Qt 版改为内部 QFrame + QLabel 子控件，外部用户无需关心 slot 名。
3. HeroUI 原版无 `size` / `radius` / `platform` variant，本组件按项目惯例扩展。
4. 拆开 `backspace` 与 `delete` 两个 KbdKey（HeroUI 共用 `delete=⌫`）。
5. `fn` / `alt` 走平台敏感路由（HeroUI 不区分平台）。

## Radii 渲染上限

Qt 会把 `border-radius` 钳制到元素短边的一半。`md` size 高度 22px 时，`lg`(14px) / `full`(11px) 渲染结果都是 11px，视觉无差异。需要看清五档圆角差异，请用 `size="lg"`（高度 28px）演示。

## 演示

`examples/kbd/demo.py` 共 10 节：Default / KbdKey 全集 / Glyph 模式 / Combinations / WithChildren / 纯文字 Kbd / Sizes / Radii / Platform / 24 个新增 SVG 总览（4 列 Grid，主题感知染色）。
