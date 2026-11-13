# ARCH-02 跨组件共享能力的归属：完成记录

状态：**已完成**。实施日期：2026-11-13。实施基线：0.17.1、提交 `e5b77e7`。

## 问题是什么

一个组件要用另一个组件的东西，却没有稳定的入口，只能伸手去拿对方的私有模块或私有字段。核对代码后，实际情况比旧文档记录的更广：

| 类型                       | 旧文档记录      | 实际核对                                                                                                                                          |
| -------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 跨组件导入私有模块         | 19 处，8 个组件 | 21 条导入语句，8 个组件                                                                                                                           |
| 直接读写别的组件的私有字段 | 未记录          | 62 行代码：Select、Autocomplete、Dropdown 伸进 Listbox、Popover、Input；DateInput 与范围输入伸进 DateFieldState；输入类组件读取动画对象的私有进度 |
| 同一段逻辑复制多份         | 未记录          | Select 与 Autocomplete 的下拉高度计算逐字相同；DatePicker 与 DateRangePicker 各写一份 Calendar 子类；范围输入重写了一遍 DateInput 的段构建        |

影响：改动 Input、Listbox、Popover 的内部实现，会悄悄弄坏别的组件；用户文档甚至教人从 `calendar._date` 这类私有路径导入 `CalendarDate`。

## 能力、拥有者与消费者

所有共享实现放在 `hero_side_ui/_shared/` 下，按家族分目录。它们是内部基础设施，不扩大顶层公开 API。

| 能力                                                                  | 拥有者                                  | 已迁移的消费者                                                                              |
| --------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------- |
| 全屏遮罩（淡入淡出、模糊快照）                                        | `_shared/overlays` 的 `Backdrop`        | Popover、Drawer                                                                             |
| Select 与 Autocomplete 的下拉高度计算                                 | `_shared/selection/popup_height.py`     | Select、Autocomplete                                                                        |
| 输入外框、清除按钮、标签几何、样式决策                                | `_shared/fields`                        | Input（含 NumberInput）、DateInput（含 TimeInput、范围输入）；Textarea 只使用外框与清除按钮 |
| 图源加载（URL 节流、本地路径、QPixmap）                               | `_shared/images` 的 `ImageLoader`       | Image、Avatar                                                                               |
| 语义色块配色                                                          | `_shared/colors` 的 `build_chip_styles` | Chip、Badge                                                                                 |
| 等宽字体、pygments token 配色                                         | `_shared/code`                          | CodeBlock、CodeEditor                                                                       |
| 日期模型：`CalendarDate`、`DateTimeValue`、分段模式、`DateFieldState` | `_shared/dates`                         | Calendar 家族、DateInput 家族、DatePicker 家族                                              |

没有迁移的内容：只有一个组件使用的子部件（如 `_LineEdit`、`_DateSegment`）仍留在原组件包内。

## 改为公开接口的私有访问

| 拥有者                               | 新增的公开接口                                                                                                                                                                   | 替代了谁的私有访问                                         |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Popover                              | `frame_margins()`、`set_fade_durations()`                                                                                                                                        | Select、Autocomplete、Dropdown                             |
| `FadeScaleAnimation`、`BackdropFade` | `set_durations()`、`settle()`                                                                                                                                                    | Popover、Drawer                                            |
| Listbox                              | `focused_index()`、`set_focus_index()`、`move_focus()`、`first_enabled_index()`、`last_enabled_index()`、`activate_focused()`、`set_empty_visible()`、`visible_content_height()` | Select、Autocomplete                                       |
| Input                                | `is_readonly()`、`click_targets()`、`refresh_filled_state()`                                                                                                                     | Select、Autocomplete                                       |
| `LabelFloatAnimation`                | `progress_value()`                                                                                                                                                               | 输入类 Mixin、Textarea                                     |
| `DateFieldState`                     | `placeholder`、`min_value`、`max_value`、`force_zeros`、`set_segment()`                                                                                                          | DateInput、范围输入                                        |
| Calendar                             | 构造参数与 `set_surface()`（`default` / `popover`）                                                                                                                              | DatePicker、DateRangePicker 各自的 Calendar 子类（已删除） |
| DateInput                            | 受保护的 `_add_segments()`、`_add_literal()`                                                                                                                                     | 范围输入重复的段构建                                       |

## 有意保留的差异

| 保留项                                                                                         | 原因                                                                                                                                                       |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dropdown 自己的菜单高度计算                                                                    | 它要比较触发器上下两侧空间且可不设上限，与 Select、Autocomplete 的规则不同，强行合并需要大量分支。它只改用 `Popover.frame_margins()`                       |
| Textarea 自带样式实现                                                                          | 多行、缩放手柄使样式决策与单行输入差异大，只共享外框与清除按钮                                                                                             |
| `InputStylingMixin` 仍是 Mixin                                                                 | 它需要宿主提供约 40 个属性。拆成组合对象会重写样式与布局，风险高于收益。改为在 `tests/shared/test_fields_contract.py` 对每个宿主逐项校验，漏提供时测试失败 |
| 同一组件内部的协作类读取宿主私有字段（InputOtp 段、Slider 绘制、Popover 缩放监听、Toast 区域） | 属于同一组件的内部拆分，不是跨组件依赖                                                                                                                     |
| `_DateSegment` 留在 `date_input`                                                               | 它是控件，依赖 Text；范围输入通过 DateInput 的受保护方法复用                                                                                               |
| `_shared` 内允许引用 `animation`、`core`、`themes`、`utils`，不允许运行时引用 `components`     | 共享层不能反向依赖消费者；类型标注使用仅类型检查期导入                                                                                                     |

## 兼容说明

| 项目                       | 说明                                                                                                                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 旧路径                     | `components/calendar/_date.py`、`components/date_input/_value.py` 曾作为兼容垫片，已在 ARCH-06 中删除。`CalendarDate` 从 `hero_side_ui.components.calendar` 导入，日期值与解析函数从 `hero_side_ui.components.date_input` 导入 |
| 新增公开导出               | `CalendarDate` 可从 `hero_side_ui`、`hero_side_ui.components`、`hero_side_ui.components.calendar` 导入                                                                                                                         |
| 新增参数                   | `Calendar(surface="default")`，默认行为不变                                                                                                                                                                                    |
| 已删除的私有路径（无垫片） | `popover/_backdrop`、`drawer/_backdrop`、`input/_wrapper`、`input/_clear_button`、`input/_layout`、`input/_styling`、`image/_loader`、`chip/_styling`、`code_block/_font`、`date_input/_field_state`、`date_input/_pattern`    |
| 已改名的私有方法           | Listbox 的 `_set_focus_index` 等改为公开名，不留别名                                                                                                                                                                           |
| 视觉与交互                 | 未改变。Calendar 嵌入浮层时的底色与之前一致                                                                                                                                                                                    |

## 验证

| 检查                 | 范围                                                                                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 依赖边界             | `tests/shared/test_import_boundaries.py`：组件不得导入其他组件的私有模块；共享层不得运行时依赖组件；已清除的私有字段穿透不得回归。已注入违规验证检查确实会失败                                                                                                                                   |
| 宿主契约             | `tests/shared/test_fields_contract.py`：Input、NumberInput、DateInput、TimeInput 逐项校验 Mixin 所需属性                                                                                                                                                                                         |
| 公共接口与真实消费者 | `tests/shared/test_family_capabilities.py`：遮罩、Popover、Listbox、下拉高度、Input、日期模型、Calendar 底色、公开入口                                                                                                                                                                           |
| 既有消费者测试       | 日期家族（Calendar、RangeCalendar、DateInput、TimeInput、DatePicker）217 项；输入与展示（Input、Textarea、NumberInput、Avatar、Image、Badge、Chip、Markdown、标签与遮罩动画）388 项；选择类浮层（Select、Autocomplete、Dropdown、Popover、Drawer、Listbox）与 `tests/shared` 共 362 项。均已通过 |
| 其他检查             | 仓库 pre-commit 钩子（ruff lint 与 format、行数、空白、大文件）；全部 319 个模块逐个导入；旧兼容路径与新入口指向同一对象                                                                                                                                                                         |

未运行全量测试，只覆盖本次修改涉及的组件与共享层。ruff 在日期家族与输入展示两组测试之后重排了 10 个文件的格式与导入顺序，这部分由模块导入检查、共享层测试和选择类浮层测试覆盖。

## 持续约束

- 需要使用另一个组件的内部能力时，先判断它属于哪个家族，放入 `_shared/<家族>` 并同时迁移所有消费者；不要新增 `from ..其他组件._xxx import`。
- 需要读写其他组件的私有字段时，说明那个组件缺少公开接口，应在拥有者上补接口。
- 新增使用输入类 Mixin 的宿主，把它加入 `test_fields_contract.py` 的宿主列表。
