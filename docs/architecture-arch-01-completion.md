# ARCH-01 公共能力与消费者迁移记录

状态：**已完成**。实施日期：2026-11-06。实施基线：0.17.0、提交 `3ab9fd1`。

本次完成公共动画、选择框箭头和已接入图标能力的抽取与消费者迁移。ARCH-02～ARCH-06 中的私有依赖归属、主题与字体契约、Provider 生命周期和宿主集成，仍按各自工作项追踪。

## 能力、拥有者与消费者

| 能力 | 维护入口 | 已接入消费者 |
| --- | --- | --- |
| 单次数值与颜色过渡 | [tween_value](../hero_side_ui/animation/tween.py) | Calendar、Link、Listbox、Pagination、Slider、Switch、Table、Tabs、Skeleton、共享箭头与 core.ScrollStyle |
| Qt 属性与几何过渡 | 同文件的 `tween_property` / `tween_geometry` | Accordion、Avatar、AvatarGroup、Badge、Card、Checkbox、Drawer、Image、Input 家族部件、InputOTP、Progress、Radio、Skeleton、Slider、Toast、Tabs |
| 通道抢占、完成、取消和释放 | [_runner.py](../hero_side_ui/animation/_runner.py) | 上述入口与 Pagination 两阶段光标；调用者不再重复维护连接和释放逻辑 |
| 边距展开与收拢 | [PaddingSqueezeAnimation](../hero_side_ui/animation/padding_squeeze.py) | Popover；保留边距换算，驱动与释放使用公共 tween |
| 循环进度与可见性 | [LoopDriver](../hero_side_ui/animation/loop.py) | 五种效果适配器，由 Spinner、Skeleton、Progress、CircularProgress 消费 |
| 对勾绘制、延迟与取消 | [check_draw.py](../hero_side_ui/animation/check_draw.py) | Checkbox、Listbox 均使用 CheckDrawAnimation 与共享绘制函数 |
| 选择框箭头按钮 | [_shared/selection/SelectorButton](../hero_side_ui/_shared/selection/selector_button.py) | Select、Autocomplete；父组件提供图像和展开状态 |
| 图标资源与渲染 | [icons/](../hero_side_ui/icons/__init__.py)、[Icon](../hero_side_ui/components/icon/icon.py)、pyside-iconify | 新 Icon 与所有旧 load_svg_icon 消费者，详见 [Icon 文档](icon.md) |

Input 的背景、边框与清除按钮也被 Textarea、DateInput 等间接复用。本次统一这些部件内部的动画；其仍位于 Input 私有包的归属问题继续由 ARCH-02 处理。

## 单次过渡契约

每个 `(owner, runner_attr)` 是独立通道，同一控件可以并行持有颜色、透明度和几何等过渡。

| 操作 | 行为 |
| --- | --- |
| 新请求 | 先取消旧请求，再从当前值开始 |
| 同值请求 | 取消旧请求，不创建动画、不派发帧更新；存在完成回调时同步通知 |
| `animated=False` 或 `duration<=0` | 取消旧请求，应用终态后通知完成 |
| `stop_tween()` | 取消并保留当前值，不调用完成回调 |
| 自然完成 | 清空通道、断开内部连接、安排 deleteLater；只通知当前请求完成 |
| 回调重入 | 新请求优先，旧请求不覆盖画面、不误清新通道、不发出过期完成通知 |
| 宿主或属性目标销毁 | 停止更新及完成通知，按 Qt 所有权释放 |
| 多阶段效果 | 保留组合编排，通道所有权与释放仍使用公共实现 |

`owner` 通常是 QObject。`tween_property` 也接受支持弱引用和属性赋值的普通运行态对象，例如 Toast 条目；此时 Qt 动画以目标对象为父对象。业务队列仍由 Toast 管理。

```python
from hero_side_ui.animation import tween_value, tween_property, stop_tween

tween_value(
    widget, "_fade_runner", current_opacity, target_opacity, apply_opacity,
    duration=150, animated=not disable_animation,
)
tween_property(
    effect, "_opacity_runner", b"opacity", 1.0,
    owner=widget, duration=150, animated=not disable_animation,
)
stop_tween(widget, "_opacity_runner")
```

### 返回句柄与兼容说明

保留原有公开类名、导入和参数，新增 `tween_property`、`LoopDriver` 与过渡的 `animated` 选项。

**完成或取消后的 Qt 动画句柄将在延迟删除事件中失效。** 调用方应通过通道取消动画，避免完成后继续调用旧句柄的方法。过去“字段清空但 Qt 子对象一直保留”的行为已修正。

同值请求会同步通知完成。调用方不能以“必须返回动画对象”作为执行业务清理的条件。

## 循环机制与效果适配

五种类保留原有名称和读取接口，内部共用 LoopDriver：

| 适配器 | 进度换算 | 消费者 |
| --- | --- | --- |
| PhaseDriver | 0～1 进度 | Spinner；default 使用两个实例，其余变体使用一个 |
| SpinAnimation | 进度 × 360° | CircularProgress |
| SkeletonShimmerAnimation | 0～1 扫光进度，InOutCubic | Skeleton |
| StripeFlowAnimation | 进度 × 图案周期 | Progress |
| IndeterminateBarAnimation | 从 -bar_ratio 到 1 的位置，InOutSine | Progress |

每个控件仍独立持有动画实例。共用控制实现，保留各效果的周期、曲线和绘制。

- start 记录运行意图，宿主显示时才实际运行。
- 隐藏时停止；重新显示且仍有运行意图时，从周期起点重启。
- stop 取消运行意图，后续显示不会自动重启。
- 隐藏时修改周期或 Spinner 变体，不启动后台循环。
- 宿主销毁时停止，即使驱动器另有显式 Qt 父对象。
- 宿主持有驱动器的 Python 包装器，Qt 父子关系负责 C++ 所有权。

可见性指实际 Qt 显示/隐藏，不包含被其他窗口遮挡或滚动出视口。

### 动画开关保留差异

- Checkbox、Radio 在禁用动画时同步逻辑状态与绘制终态，切换开关时取消旧过渡。
- Skeleton 的开关同时关闭扫光与交叉淡入淡出，立即应用加载状态。
- Progress 与 CircularProgress 保留公开语义：关闭确定值过渡；Progress 同时关闭斜纹流动，未定加载指示仍可运行。隐藏时遵循公共停止规则。
- Spinner 保留既有 API。
- Icon 动画由 pyside-iconify 管理，不在 HeroSideUI 增加第二套计时器。

未来是否提供统一的全局“减少动态效果”策略，继续由 ARCH-04 讨论。

## 对勾与箭头迁移

Checkbox 删除独立描勾动画与不可取消的 singleShot，使用 CheckDrawAnimation 管理延迟、取消和立即终态；Listbox 继续使用相同控制器。

| 消费者 | 选中 | 取消 |
| --- | --- | --- |
| Checkbox | 延迟 100ms，500ms 描出 | 完整对勾配合填充淡出 |
| Listbox | 延迟 80ms，400ms 描出 | 120ms 反向擦除 |

停止和立即终态会清理待执行目标。Checkbox 进入未定态、关闭动画时也取消待执行描勾。

Select、Autocomplete 的旧 _selector_button 模块只保留兼容导入，实际组件直接使用内部共享 SelectorButton。没有增加顶层用户组件 API。

## 保留的专属职责

| 拥有者 | 保留职责与消费者 |
| --- | --- |
| PressScaleEffect | 图形效果安装与按压缩放；Button、Card、Pagination |
| RippleOverlay | 每个水波纹的绘制、覆盖层与退场释放；Button、Card |
| CollapseAnimation | 高度与透明度组合时序；Accordion |
| FadeScaleAnimation | 淡入缩放联动及透明度适配；Popover、Tooltip |
| LabelFloatAnimation | 浮动标签语义与回调；Input、Textarea、DateInput |
| UnderlineBar | 输入下划线效果；Input、DateInput |
| BackdropFade | 遮罩透明度；Popover 及复用遮罩的 Drawer 家族 |
| PixmapScaleProxy | 截图代理与缩放显示；Popover、Tooltip |
| start_cursor_slide | 两阶段位置与缩放换算；Pagination，通道释放交给公共 runner |
| Calendar 翻页控制器 | 旧网格截图、新内容渲染、覆盖层清理；位置过渡已接公共入口 |
| ToastRegion | 队列、折叠、拖拽、进出场与条目移除；几何和透明度已接公共入口 |
| InputOTP 光标、Toast 倒计时等 QTimer | 焦点、输入与业务计时，不承担重复的连续插值 |

已有语义效果可在自身生命周期内持有固定数量、重复使用的 Qt 动画；水波纹按整个效果对象退场释放。一次性过渡请求统一通过公共 runner 释放。公共效果不反向读取具体组件的私有业务状态。

## 持续检查与验证

[test_architecture.py](../tests/animation/test_architecture.py) 已进入现有 animation CI 分组：

1. 当前组件和家族共享部件使用公共过渡或语义效果，不再直接构造基础 QPropertyAnimation / QVariantAnimation。
2. setLoopCount 仅由公共循环驱动实现。
3. 两个旧箭头路径转发到同一个共享类。

后续若确需新的专属 Qt 动画，应明确职责、消费者与生命周期，补真实消费者验证后调整边界检查。

[test_shared_contracts.py](../tests/animation/test_shared_contracts.py) 覆盖对象释放、同值抢占、立即终态、回调重入、目标销毁、五种适配器，以及真实组件的隐藏、恢复和快速勾选。既有组件回归继续验证公开行为。

CI 显式选择 Python 矩阵版本、按锁文件安装，不再在验证过程中执行 uv add。远端平台与多版本结果以推送后的 CI 为准。

animation 目录的 19 个 Python 文件统一为 Google 风格 docstring，删除重复示例与装饰性注释；本次注释整理前后的非文档 AST 一致。

本次验收范围为受影响的动画及组件。Windows / PySide6 6.11 环境中，为避免已有跨模块 Qt 回调崩溃，相关模块按独立进程执行。

验证结果：24 项共享契约测试、3 项架构检查通过；追加的 Switch、Table、Tabs、Pagination、Spinner、Textarea 共 611 项回归通过，Toast 的 14 项相关动画回归通过。此前已通过的受影响模块结果继续保留，不重复执行。wheel / sdist 构建通过，并在独立 PySide6 6.12 安装环境中验证共享驱动与真实组件的启动、隐藏恢复和销毁。

```bash
uv run --locked python -m pytest tests/animation/test_architecture.py tests/animation/test_shared_contracts.py -q
```
