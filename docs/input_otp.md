# InputOtp 验证码输入框

多段等宽的一次性验证码输入。对照官方 `InputOtp`（基于 input-otp 库 + HeroUI `inputOtp` 主题）复刻：桌面端由段行容器自处理键盘/粘贴/光标，段、光标、密码点全部自绘。

## 构造参数

| 参数                | 类型   | 默认         | 说明                                                                   |
| ------------------- | ------ | ------------ | ---------------------------------------------------------------------- |
| `length`            | `int`  | `4`          | 段数（≥1，即验证码位数）                                               |
| `allowed_keys`      | `str`  | `"^[0-9]*$"` | 允许字符的正则（逐字符 `fullmatch`）                                   |
| `variant`           | `str`  | `"flat"`     | `flat` / `bordered` / `faded` / `underlined`                           |
| `color`             | `str`  | `"default"`  | `default` / `primary` / `secondary` / `success` / `warning` / `danger` |
| `size`              | `str`  | `"md"`       | `sm` / `md` / `lg`                                                     |
| `radius`            | `str`  | `"md"`       | `none` / `sm` / `md` / `lg` / `full`                                   |
| `value`             | `str`  | `""`         | 初始值                                                                 |
| `description`       | `str`  | `""`         | 底部辅助说明（灰色）                                                   |
| `error_message`     | `str`  | `""`         | 错误文案（红色，仅 `is_invalid=True` 时显示）                          |
| `full_width`        | `bool` | `False`      | 水平方向随布局拉伸                                                     |
| `is_required`       | `bool` | `False`      | 必填标记（桌面端仅语义占位）                                           |
| `is_read_only`      | `bool` | `False`      | 只读：拒绝编辑、光标透明、active 不缩放                                |
| `is_disabled`       | `bool` | `False`      | 禁用：整组半透明、不可聚焦                                             |
| `is_invalid`        | `bool` | `False`      | 错误态（段配色转 danger + 显示 errorMessage）                          |
| `disable_animation` | `bool` | `False`      | 关闭过渡动画（桌面端当前无段过渡动画，语义占位）                       |
| `auto_focus`        | `bool` | `False`      | 显示后自动聚焦                                                         |
| `text_align`        | `str`  | `"center"`   | 段内字符对齐：`left` / `center` / `right`                              |
| `type`              | `str`  | `"text"`     | `"password"` 时已填段渲染实心圆点                                      |
| `theme`             | `str`  | `"auto"`     | `light` / `dark` / `auto`                                              |

## 信号

| 信号                 | 参数   | 说明                                              |
| -------------------- | ------ | ------------------------------------------------- |
| `value_changed(str)` | 当前值 | 值变化（对齐官方 `onValueChange`）                |
| `text_changed(str)`  | 当前值 | 值变化（对齐官方 `onChange` 的可用子集）          |
| `completed(str)`     | 完整值 | 值达到 `length` 位时触发（对齐官方 `onComplete`） |

## 公共方法

| 方法                                                                       | 说明                                        |
| -------------------------------------------------------------------------- | ------------------------------------------- |
| `value() -> str`                                                           | 当前值                                      |
| `set_value(str)`                                                           | 外部设值（自动过滤非法字符并截断到 length） |
| `set_length(int)`                                                          | 改段数（值与光标截断）                      |
| `set_allowed_keys(str)`                                                    | 更新字符白名单正则                          |
| `set_variant/set_color/set_size/set_radius`                                | 视觉变体                                    |
| `set_description/set_error_message/set_invalid`                            | helper 行                                   |
| `set_text_align/set_type/set_read_only/set_disabled/set_disable_animation` | 行为开关                                    |
| `focus_input()`                                                            | 编程式聚焦                                  |

## 交互

| 操作                      | 行为                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 输入合法字符              | 插入光标处并右移（非法字符丢弃）                                                                                         |
| Backspace                 | 删除光标前一字符并左移                                                                                                   |
| Delete                    | 删除光标处字符                                                                                                           |
| Left / Right / Home / End | 移动光标（钳制在 `[0, length]`）                                                                                         |
| Ctrl+V / 中键粘贴         | 剪贴板文本过滤合法字符后从光标处批量插入                                                                                 |
| 点击任意段                | 聚焦并把光标钉到第一个空段（值末尾；对齐官方 input-otp：透明输入层文本挤在左端，点击不定位具体段）；精确移动靠键盘方向键 |
| 值填满                    | 触发 `completed`                                                                                                         |

## size 规格

| size | 段  | 字号 |
| ---- | --- | ---- |
| `sm` | 32  | 10px |
| `md` | 40  | 14px |
| `lg` | 48  | 16px |

## 特殊行为

- **isInvalid 配色**（对照官方 compound）：`flat` 底/active 转 danger-50/100；`bordered` / `underlined` 边框转 danger-200、active danger-400；`faded` 保留原 variant 配色只覆盖文字；光标与密码点一律 danger。
- **bordered / underlined 的 default 色**：段有字符后文字转 `default-foreground`（官方 `data-[has-value=true]:text-default-foreground`）。
- **underlined**：静止时段内仅有 2px 短下划线，活动段下划线全宽展开（官方 `after` 过渡的静态化）。
- **active 段**：边框/底色加深并外扩 1px（近似官方 `scale-110`）；readonly 时不缩放、光标透明。
- **光标**：活动空段中央 1px×50% 竖线，500ms 闪烁（官方 1s 循环的桌面简化）。
- **禁用**：整组 `opacity 0.5`（官方 `opacity-disabled`）。

## 与 HeroUI 差异

1. 官方用隐藏 `<input>`（input-otp 库）承接输入；桌面端由段行容器自处理键盘/粘贴/光标。
2. 官方 `hover:bg-danger`（源码瑕疵：悬停段变红）桌面端不采纳。
3. 官方 `classNames` / `containerClassName` / `noScriptCSSFallback` 为 React slot 机制，桌面端不需要。
4. `pushPasswordManagerStrategy`（浏览器密码管理器对策）桌面端无意义，不采纳。
5. 官方 `errorMessage` 支持 `ValidationResult => ReactNode` 回调；桌面端为纯文本。
6. 官方 active 段 `scale-110` + 150ms transition；桌面端为外扩 1px 的静态近似。
7. 官方 segment `font-semibold`(600)；项目字重表无 semibold，使用 medium(500)。
8. 字号 sm 10 / md 14 / lg 16 为桌面档（官方 text-small/small/medium 14/14/16）。
