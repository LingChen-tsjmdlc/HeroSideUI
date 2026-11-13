# ARCH-04 组件接入与状态更新契约：完成记录

状态：**已完成**（范围见下）。实施日期：2026-11-13。实施基线：0.17.2（ARCH-03 之后）。

## 问题是什么

全局字体（family、基准字号）和全局主题是应用级状态，由管家（`FontProvider`、`ThemeProvider`）持有。组件要做到：管家状态变了，自己的外观和尺寸跟着变。核对结果：

| 状态 | 接入情况                                                                                                                                                  |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 主题 | 46 个组件包中，40 个直接登记；NumberInput、TimeInput、ThemeSwitcher 继承父类的登记；DatePicker 是容器，内部组件各自登记；Image、Spacer 没有颜色。没有缺口 |
| 字体 | **只有 `Text` 登记**。其他在创建或刷新样式时写死字体的组件，运行时切换字体后保持旧字体、旧尺寸                                                            |

实测（改前）：把全局字体切到 Arial，`Text` 变了，Button、Checkbox、Radio、Switch 没变。

另外发现 4 个由同一原因引起的连带问题：

| 组件                                         | 表现                                                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| DateInput 的段、Input 与 Textarea 的浮动标签 | 内部是 `Text`，会响应广播并按默认字号重建，把外层 `setFont` 设置的字号覆盖：段 14 变 16，标签 11 变 13 |
| CodeBlock 的代码区                           | 内部是 `Text`，广播后等宽字体被正文字体覆盖                                                            |
| Link                                         | 广播后 `Text` 重建字体，下划线丢失                                                                     |
| Breadcrumbs                                  | 创建时用 Qt 默认字体，从未使用 HeroSideUI 字体                                                         |

## 接入契约

| 项目                     | 规则                                                                                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 事实来源                 | 字体族与基准字号由 `FontProvider` 持有；组件字号和字重由自己的尺寸 token 决定                                                                                  |
| 接入方式                 | 组件提供 `_apply_font()` 并在构造末尾 `FontProvider.instance().register(self)`；管家变化时调用它。登记使用弱引用，组件销毁后自动脱离，广播对已销毁对象不会抛错 |
| `_apply_font()` 的职责   | 按当前字体重算自己的字体；字体影响尺寸时同时更新几何（`updateGeometry`、重算最小宽高）并重绘                                                                   |
| 内部使用 `Text` 的组件   | 字号和字重通过 `Text.set_size`、`Text.set_weight` 设置，不再对 `Text` 调用 `setFont`，否则会被广播覆盖。`Text` 自身重建字体时保留下划线                        |
| 刻意独立于全局字体的组件 | CodeBlock、CodeEditor 使用等宽字体，不跟随；CodeBlock 把内部 `Text` 从管家注销                                                                                 |
| 继承                     | 子类使用父类的登记与 `_apply_font`，不重复登记                                                                                                                 |

## 接入清单

| 组件                                | `_apply_font()` 做什么                                             |
| ----------------------------------- | ------------------------------------------------------------------ |
| Button                              | 重设字体并 `updateGeometry`                                        |
| Checkbox、Radio（经 `RadioBase`）   | 重设字体并重算尺寸                                                 |
| Switch                              | 重设字体，更新几何与重绘                                           |
| Tabs 的 `TabItem`                   | 重算宽度并重绘                                                     |
| Input（含 NumberInput）             | 重设输入框字体，重排浮动标签                                       |
| Textarea                            | 重跑样式并重算输入区高度                                           |
| DateInput（含 TimeInput、范围输入） | 重跑样式以重算最小宽度；各段通过 `Text.set_size` 管理字号          |
| InputOtp                            | 重建段字体并重算段行尺寸                                           |
| Divider                             | 重算带文字分割线的高度                                             |
| Breadcrumbs                         | 各项宽高来自字体度量，整体重建；改用统一字体入口 `make_text_qfont` |
| Slider                              | 按新 marks 行高重算画布尺寸                                        |
| Pagination、Calendar                | 文字每次绘制时取当前字体，字体变化后重绘全部子件                   |
| Link                                | 其内部 `Text` 已登记，无需自己登记；下划线保留                     |

## 有意保留的差异

| 保留项                                            | 原因                                                                                                            |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| CodeBlock、CodeEditor 不跟随全局字体              | 等宽字体是功能需要，设计上独立于正文字体，见 [CodeBlock 文档](code_block.md)                                    |
| Calendar 的星期名列宽仍在创建时计算               | 列宽由尺寸 token 决定，只有长星期名样式才可能受字体影响；重建整个日历得不偿失。字体变化后日期格会重绘，列宽不变 |
| Textarea、DateInput 的 `_apply_font` 重跑整套样式 | 这两处字体与输入区高度、最小宽度在同一个方法里计算，拆开只会增加重复；字体切换是低频操作                        |
| 局部字体覆盖                                      | 目前没有组件提供“某个组件使用与全局不同的字体”的公开参数，本次不新增                                            |

## 兼容说明

| 项目     | 说明                                                                                                                                 |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 公开 API | 无变化。新增的 `_apply_font` 是内部方法                                                                                              |
| 视觉     | 运行时切换字体后，以上组件现在会跟随；未切换时外观不变。Breadcrumbs 现在使用 HeroSideUI 字体而不是 Qt 默认字体，字体族可能与之前不同 |
| `Text`   | 重建字体时保留下划线                                                                                                                 |

## 验证

| 检查        | 范围                                                                                                                                                                                                                                                                                                |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 字体契约    | `tests/shared/test_font_contract.py`：13 种组件（含继承的 NumberInput、TimeInput）切换字体后缓存字体变为新 family；Pagination、Slider、Calendar 已登记且重绘不抛异常；DateInput 段与 Input 标签字号保持不变；Link 下划线保持；Button 宽度与新建的一致；已销毁组件不影响广播；CodeBlock 保持等宽字体 |
| Button 几何 | 切换尺寸后 `sizeHint` 与重新创建的按钮一致（图标按钮与文字按钮均一致），文档中“QSS 尺寸约束改变几何”没有复现                                                                                                                                                                                        |
| 主题        | 对照 40+ 个组件包的登记与继承关系，确认没有缺口                                                                                                                                                                                                                                                     |
| 既有测试    | 维护者在本地运行下列四组命令，全部通过                                                                                                                                                                                                                                                              |

四组命令覆盖共享层、字体管家、本次接入字体契约的全部组件：

```
.venv\Scripts\python.exe -m pytest tests/shared tests/core/test_font_provider.py -q
.venv\Scripts\python.exe -m pytest tests/components/test_button.py tests/components/test_checkbox.py tests/components/test_radio.py tests/components/test_switch.py tests/components/test_tabs.py -q
.venv\Scripts\python.exe -m pytest tests/components/test_input.py tests/components/test_textarea.py tests/components/test_date_input_widget.py tests/components/test_time_input.py -q
.venv\Scripts\python.exe -m pytest tests/components/test_divider.py tests/components/test_pagination.py tests/components/test_slider.py tests/components/test_input_otp.py tests/components/test_breadcrumbs.py tests/components/test_link.py tests/components/test_text.py -q
```
