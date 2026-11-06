# HeroSideUI 架构审查验证明细

架构整理的主线、公共能力抽取与接入规则见 [架构整理与演进规则](architecture.md)。本文保存 2026-11-06 审查中的具体事实、运行复现、配置风险与验证边界，作为架构判断和后续修复的证据。

## 审查基线与结论

| 项目     | 基线                                                                 |
| -------- | -------------------------------------------------------------------- |
| 审查日期 | 2026-11-06，Asia/Shanghai                                            |
| 版本     | 0.16.1                                                               |
| 提交     | `887be09d53ed216cac57e4fe6d437afecbb1f454`                           |
| 状态     | 初次审查记录，整改尚未实施                                           |
| 方法     | 全库静态扫描、关键路径人工审查、独立进程复现、构建产物安装与冒烟验证 |

当前问题涉及初始化、对象生命周期、状态更新、组件依赖、宿主集成、桌面交互以及发布验证。动画整理只是其中一部分，应先建立可验证的公共契约，再依据真实重复调整实现和目录。

本记录用于后续整改和复验，不代表全部组件行为已经检查完毕。源码位置和统计对应上述提交；后续修复应保留原始现象，并补充修复提交与验收结果。

判断边界如下：

- 组件直接使用 `QPropertyAnimation`、专有效果只有一个调用方，都不足以单独判定架构错误。
- 对象释放、初始化时序、状态终态等具体缺陷应先修复；跨组件反复出现的同类缺陷，需要公共契约约束。
- 跨组件私有引用需要逐项评估拥有者，组件家族共享实现可以合理保留。
- 目录移动、减少文件行数、减少 Qt 动画构造次数不作为独立验收标准。

历史重构过程见 [REFACTORING.md](../REFACTORING.md)。其中的完成状态和统计属于当时版本，当前整改以本次基线和复验结果为准。

## 验证范围与结果

### 静态盘点

| 范围                   | 结果                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| 主库 Python 文件       | 301 个                                                              |
| 组件包                 | 45 个；与 README 的 51 个组件统计口径不同，组合组件可位于同一个包   |
| 公共动画               | 16 个实现文件、20 个导出，全部有主库引用                            |
| 动画使用文件           | 9 个导出被多个文件使用，11 个只有单一使用文件；该数量不代表抽象质量 |
| 组件内直接创建 Qt 动画 | 23 个文件、33 个构造位置，分布在 16 个组件包                        |
| 跨组件私有模块引用     | 19 个导入位置，涉及 8 个引用方组件包                                |
| 测试收集               | 2819 项，收集成功；未全量执行                                       |

### 已执行验证

| 验证                                    | 环境                                    | 结果                                                        |
| --------------------------------------- | --------------------------------------- | ----------------------------------------------------------- |
| 主题与字体核心测试                      | Windows，Python 3.11.15，PySide6 6.11.0 | 117 项通过                                                  |
| tween 单元测试                          | Windows，Python 3.11.15，PySide6 6.11.0 | 11 项通过；属于前一轮动画盘点，未覆盖本记录中的新增边界复现 |
| sdist 与从 sdist 构建 wheel             | 当前提交                                | 成功                                                        |
| wheel 资源检查                          | `herosideui-0.16.1-py3-none-any.whl`    | 包含 52 个 SVG、2 个字体及项目 LICENSE                      |
| 全新虚拟环境安装 wheel 与依赖一致性检查 | Windows，Python 3.11.15，PySide6 6.12.0 | 成功                                                        |
| 安装后在源码目录外运行                  | 上述新环境                              | 公开导出均可获取；Button 构造、字体加载、内置图标加载通过   |

117 项核心测试通过与新增复现同时成立：现有测试验证了已有断言，不足以证明初始化顺序、跨组件字体同步或可访问名称等未覆盖的契约正确。

### 依赖解析边界

以下为 2026-11-06 使用 uv 0.11.7 对 `pyproject.toml` 进行目标平台解析的结果，不等同于目标系统安装或 GUI 运行测试。

| 参数与目标                                                              | Python | 结果                                            |
| ----------------------------------------------------------------------- | ------ | ----------------------------------------------- |
| `--python-platform windows`                                             | 3.10   | 通过                                            |
| `--python-platform windows`                                             | 3.14   | 通过                                            |
| `--python-platform x86_64-unknown-linux-gnu`，本次解析目标为 glibc 2.28 | 3.11   | 失败，当前 `pyside6>=6.11.0` 无匹配目标的 wheel |
| `--python-platform aarch64-apple-darwin`，本次解析目标为 macOS 13 ARM64 | 3.11   | 失败，`pyicu-wheels>=2.15.2` 无匹配目标的 wheel |

本次解析器报告的 PySide6 6.12.0 Linux x86_64 wheel 标签为 `manylinux_2_34_x86_64`；检查到的 pyicu-wheels 2.15.2 macOS wheel 标签为 `macosx_15_0`。这些结果说明需要明确最低系统与 ABI 边界，不能据此推断所有 Linux 或 macOS 环境均不受支持。依赖发布变化后应重新验证。

## 问题分类与优先级

| 类别               | 判定依据                                                           |
| ------------------ | ------------------------------------------------------------------ |
| 已复现缺陷         | 给定条件下，运行结果与组件或基础设施的预期契约存在明确冲突         |
| 已复现不一致或限制 | 运行差异已确认；修复方式仍需统一公开契约                           |
| 配置缺口           | 仓库配置及工具行为能够证明验证链条缺失，不推断未查看的远端任务结果 |
| 设计风险           | 已存在的依赖或策略增加维护、集成成本，需要明确设计选择             |
| 待验证             | 证据不足，不能作为已确认缺陷或整改收益                             |

P1 表示优先处理的行为正确性或验证链条问题；P2 表示随后处理的一致性、集成和维护问题。优先级是本次整改建议，不表示已经确认线上故障。

以下条目的初始状态均为**待处理**。新增共享层、改变依赖分组、调整公开 API 等方案尚未定稿。

## 已复现缺陷与行为不一致

### INIT-01 初始化完成状态受调用顺序影响

**类别：已复现缺陷。优先级：P1。**

在创建 `QApplication` 前调用 `ThemeProvider.instance()`，随后创建应用并正常调用 `HeroSideUIProvider.setup()`。此时 `_booted` 已为 `True`，全局滚动样式和滚动过滤器却没有安装；对照进程先创建应用再调用 setup，两者均正常安装。

相关实现：[启动状态管理](../hero_side_ui/core/_boot.py)、[ThemeProvider 单例](../hero_side_ui/core/theme_provider.py)。

建议仅在设施实际就绪后记录完成状态，并明确应用未创建、部分初始化失败和重复 setup 的处理方式。验收应覆盖先读 Provider、后创建应用、失败后重试及重复初始化。

### MOTION-01 已完成的补间对象持续由宿主持有

**类别：已复现缺陷。优先级：P1。**

对同一宿主连续执行并完成 20 次 `tween_value`，runner 属性已清空，宿主下仍有 20 个 `QVariantAnimation` 子对象。清空 Python 属性并未解除 Qt 父子持有关系。

相关实现：[tween.py](../hero_side_ui/animation/tween.py)。

应确定单次动画的释放或复用规则，检查完成、抢占和取消三条路径。回归测试应验证重复交互后对象数量保持有界，并覆盖 finished 回调内启动新动画的重入情况。

### MOTION-02 同值请求未抢占旧动画

**类别：已复现缺陷。优先级：P1。**

已有 tween 运行到中间值后，以该值作为新请求的起止值再次调用 `tween_value`。函数返回 `None`，旧动画仍为 `Running`，宿主仍持有旧 runner。

相关实现：[tween.py 中的相等值提前返回](../hero_side_ui/animation/tween.py)。

需要明确同值请求是否取消旧动画，以及立即结束时是否触发完成回调。验收覆盖运行中同值请求、连续反向请求、重复停止和旧回调干扰新 runner 的情况。

### MOTION-03 循环动画的可见性规则不一致

**类别：已复现不一致。优先级：P2。**

Spinner 显示后再隐藏，两个循环驱动仍在运行；同条件下 Skeleton 会停止扫光。应明确隐藏、再次显示、切换变体和宿主销毁时的循环动画规则。

相关实现：[Spinner](../hero_side_ui/components/spinner/spinner.py)、[Skeleton](../hero_side_ui/components/skeleton/skeleton.py)。显示恢复时采用续播还是重置，应在契约中明确并保持视觉语义。

### STATE-01 禁用动画时初始选中状态未同步到绘制值

**类别：已复现缺陷。优先级：P1。**

构造 `is_selected=True, disable_animation=True` 的 Checkbox 和 Radio 时，`isChecked()` 为 `True`，Checkbox 的填充与对勾进度、Radio 的控制进度却仍为 `0.0`。

相关实现：[Checkbox 初始状态](../hero_side_ui/components/checkbox/checkbox.py)、[RadioBase 初始状态](../hero_side_ui/components/radio/_base.py)。

禁用动画应立即应用视觉终态。验收应同时检查逻辑状态和绘制状态，覆盖初始选中、取消、未定态、禁用与动态切换。

### FONT-01 全局字体变化的组件接入不一致

**类别：已复现不一致。优先级：P2。**

同时创建 Text 和 Button，再调用 `FontProvider.set_family("Courier New")`：Text 立即更新，Button 保留旧字体；随后调用 Button 的 `set_color()`，字体才更新。静态扫描中，直接调用 `FontProvider.instance().register(self)` 的组件入口仅见于 Text。

相关实现：[Text 字体订阅](../hero_side_ui/components/text/text.py)、[Button 样式刷新](../hero_side_ui/components/button/button.py)、[FontProvider](../hero_side_ui/core/font_provider.py)。

应明确哪些组件参与运行时全局字体更新，以及显式字体覆盖的优先级。验收不应依赖颜色、主题等无关 setter 来触发刷新。

### LIFETIME-01 Python 弱引用注册不能代表 C++ 对象仍有效

**类别：已复现陈旧注册与诊断缺口。优先级：P2。**

保留子 Button 的 Python 引用，销毁其 Qt 父控件并处理延迟删除后，`shiboken6.isValid(button)` 为 `False`，主题 Provider 仍报告其已注册。主题广播中的异常被静默捕获。

相关实现：[ThemeProvider 注册与广播](../hero_side_ui/core/theme_provider.py)。

应将 Qt 对象有效性纳入清理规则，并为非预期广播失败提供可诊断信息。验收覆盖父对象销毁但包装器仍被引用的情况；不能将弱引用集合大小直接视为有效 C++ 控件数。

### A11Y-01 Calendar 日期按钮缺少可访问名称

**类别：已复现缺陷。优先级：P1。**

通过 `QAccessible.queryAccessibleInterface()` 检查默认 Calendar，本次样本中 30 个有效日期按钮均为 Button 角色，但 Name 文本为空。日期格子数随月份变化，缺少名称的事实不依赖本次样本恰好为 30 个。

相关实现：[Calendar 日期格子](../hero_side_ui/components/calendar/_cell.py)。

应提供可识别的本地化日期名称，并检查选中、不可用、范围边界等状态如何传达。查询接口的检查还需辅以键盘及实际读屏验证。

### DPI-01 SVG 栅格化未提供高分辨率资源

**类别：已复现渲染资源限制。优先级：P2。**

在 `QT_SCALE_FACTOR=2` 的独立进程中，屏幕 DPR 为 `2.0`，`load_svg_icon(..., size=24)` 返回的位图物理尺寸仍为 `24×24`，位图 DPR 为 `1.0`。本次确认了资源分辨率限制，没有测量实际模糊程度。

相关实现：[SVG 栅格化](../hero_side_ui/utils/icon_utils.py)。建议区分逻辑尺寸与物理像素；缓存若引入，应包含 DPR、颜色和描边参数。验收覆盖多种缩放比例及跨屏后的资源更新，参见 [Qt High DPI](https://doc.qt.io/qt-6/highdpi.html)。

### BUTTON-01 纯图标按钮的外部固定尺寸仍可能被重置

**类别：已复现缺陷。优先级：P2。**

纯图标按钮完成样式初始化后执行 `setFixedSize(32, 32)`，再调用 `set_color()`，最小和最大宽度重新变为 `46`。视觉与几何方法虽然已经分拆，QSS 的 min/max 约束仍参与几何计算。

相关实现：[Button QSS 与几何](../hero_side_ui/components/button/button.py)、[当前尺寸保证说明](button.md)。应明确外部 Qt 几何设置与 `set_icon_only_side()` 的优先级，并同步文档与布局下的回归验证。

### BUTTON-02 修改纯图标边长后图标未立即刷新

**类别：已复现缺陷。优先级：P2。**

默认 md 纯图标按钮的图标为 `23px`。调用 `set_icon_only_side(36)` 后仍为 `23px`；随后调用颜色 setter 才变为 `18px`。边长 override 已参与计算，但该 setter 未触发图标刷新。

相关实现：[Button 的边长 setter 与图标刷新](../hero_side_ui/components/button/button.py)。验收覆盖修改边长、恢复自动边长及显式 `icon_size` 覆盖。

## 配置缺口与设计风险

### CI-01 Python 矩阵安装与解释器选择未连接

**类别：配置缺口。优先级：P1。**

[CI 工作流](../.github/workflows/ci.yml)安装矩阵中的 Python，之后直接执行 `uv sync` 和 `uv run`；[.python-version](../.python-version) 固定为 `3.11`。本地存在可用的 3.13，在相同 Python 选择配置、尚无虚拟环境的最小项目中，uv 实际创建并运行了 3.11.15。

这证明了矩阵解释器未显式传递的缺口，不代表已核实每次历史远端任务的实际 Python 版本。应将矩阵版本传入所有相关 uv 步骤，并在任务中输出和断言实际解释器版本，参见 [uv Python 版本选择](https://docs.astral.sh/uv/concepts/python-versions/#python-version-files)。

CI 另有 `uv add --dev pytest pytest-qt` 步骤，会执行依赖添加或更新，可能改写配置与锁文件。后续应明确锁定依赖验证与依赖升级验证各自的职责，避免验证输入不透明。

### RELEASE-01 发布链条与公开使用说明脱节

**类别：发布验证和文档缺口。优先级：P1。**

[发布工作流](../.github/workflows/publish.yml)的发布任务只依赖本工作流的 build，构建后的检查仅确认 wheel 含 SVG；工作流内没有测试结果或安装后冒烟检查作为前置。外部 GitHub 保护规则不在本次核查范围内。

同时存在以下公开说明偏差：

- README 描述 `herosideui[pyside6]`、`herosideui[pyside2]`，但构建产物只声明 `dev` extra，运行依赖固定为 PySide6。这些 extra 名称不能提供描述的绑定选择。
- [迁移文档](migration.md)明确双绑定暂缓，README 仍宣称 PySide2 best-effort 兼容。
- README 的版本递增说明仍指向 commit-msg；[pre-commit 配置](../.pre-commit-config.yaml)说明已移至 post-commit，仓库中的[递增脚本](../.hooks/commit_msg_bump.py)也按 post-commit 工作。公开安装步骤需要核对能否在新克隆中接通该钩子。

验收应包括：发布目标提交的验证结果、tag 与包版本一致性、从构建产物安装后运行，以及在新克隆中照文档操作成功。公开 API 的兼容和弃用规则也应在改变参数前明确。

### PLATFORM-01 系统与 ABI 支持边界不完整

**类别：已验证的依赖解析边界。优先级：P2。**

见前文目标平台解析结果。[项目元数据](../pyproject.toml)声明 Python 3.10–3.14，但系统版本、架构和依赖 wheel 的最低 ABI 条件也决定能否安装。仅有 Python 版本范围和 OS Independent 分类不足以表达这些条件。

应建立 Python、Qt、系统版本和架构的支持表，区分已实测、仅可解析和暂未验证。降低依赖下限、替换 ICU 依赖或收窄支持范围都需要单独验证；本次不预设其中哪一种方案正确。

### IMPORT-01 基础组件导入与全库依赖绑定

**类别：需要明确的架构取舍。优先级：P2。**

独立进程仅执行 `from hero_side_ui import Button`，仍加载全部 45 个组件包以及 ICU、Markdown 解析模块；用导入探针阻止 ICU 后，Button 导入失败。

相关实现：[顶层导出](../hero_side_ui/__init__.py)、[组件集中导出](../hero_side_ui/components/__init__.py)、[运行依赖](../pyproject.toml)。

由于 ICU 已被声明为必需依赖，该结果本身不等于依赖缺失的打包错误。需要先决定整包依赖还是基础与扩展分层，再评估延迟导入和 optional extras。验收关注导入成本、故障影响范围及既有公开导入路径兼容性。

### OWNERSHIP-01 共享能力仍由具体组件的私有模块拥有

**类别：维护边界风险。优先级：P2。**

19 个跨组件私有导入位置主要涉及以下能力：

| 当前引用                                | 应评估的共享能力                         |
| --------------------------------------- | ---------------------------------------- |
| Textarea、DateInput 引用 Input 私有文件 | 输入容器、清除按钮、布局和样式的共享边界 |
| Drawer 继承 Popover 私有遮罩            | 遮罩绘制、快照、模糊与开合控制           |
| Avatar 引用 Image 私有加载器            | 图像加载服务与加载策略                   |
| 日期组件相互引用私有模块                | 日期值、段编辑、日历计算的拥有者         |
| Badge 引用 Chip 私有配色                | 语义配色规则                             |
| CodeEditor 引用 CodeBlock 私有文件      | 等宽字体、语法高亮配色                   |

应逐项确定哪些是稳定的组件家族内部约定、哪些应下沉为共享能力。`_shared/fields`、`_shared/overlays`、`_shared/dates` 等名称仅为候选，目录和迁移边界尚未定稿。

验收应验证依赖方向、公共 API 不变、组件可独立测试，以及抽取后实际消除的重复。共享层不应反向依赖具体消费组件。

### HOST-01 全局设施缺少统一的宿主集成与恢复契约

**类别：集成与可逆性风险。优先级：P2。**

默认路径涉及全局 palette、QSS、事件过滤器和字体设施；显式 setup 还默认安装 stderr 过滤器，通过 `os.dup2` 重定向文件描述符并启动 daemon 线程。

部分设施已有关闭选项或移除方法，不能据此认定完全没有开关。但尚缺少统一的安装范围、所有权、重复调用、失败恢复和卸载约定；stderr 过滤模块目前只有安装入口。

相关实现：[Provider](../hero_side_ui/core/provider.py)、[启动管理](../hero_side_ui/core/_boot.py)、[stderr 过滤](../hero_side_ui/core/_libpng_filter.py)。

应以嵌入既有 Qt 应用为验收场景：宿主已有 palette、样式和事件处理时，明确哪些改变属于库、如何关闭，以及移除库设施后如何保留宿主设置。全局设施安装失败和组件广播失败也需要可诊断信息。

### NETWORK-01 通用图像加载内置了固定的全局限流策略

**类别：共享服务策略风险。优先级：P2。**

所有 ImageLoader 的 HTTP(S) 请求都经过全局队列，相邻请求发起间隔随机为 1000–1500ms，策略源于特定图源的限频需求。[相关实现](../hero_side_ui/components/image/_loader.py)。

这里限制的是请求发起间隔，不表示所有网络响应都串行完成。应将通用加载能力与具体服务限流策略分开，明确取消、超时、失败反馈及配置入口。实际并发、吞吐和缓存收益需要测量后决定。

## 复现与复验入口

以下命令从仓库根目录执行。GUI 探针可在 PowerShell 中先设置 `$env:QT_QPA_PLATFORM = 'offscreen'`；每种初始化顺序和缩放设置应使用独立进程。

### 现有测试与构建产物

```powershell
# 本轮执行的核心测试
.\.venv\Scripts\python.exe -m pytest tests/core/test_theme_provider.py tests/core/test_font_provider.py -q -p no:cacheprovider

# 前一轮执行的 tween 测试
.\.venv\Scripts\python.exe -m pytest tests/animation/test_tween.py -q -p no:cacheprovider

# 仅收集测试，不等于运行通过
.\.venv\Scripts\python.exe -m pytest tests --collect-only -q -p no:cacheprovider

# 生成 sdist，并从 sdist 构建 wheel
uv build
```

安装后验证需在新虚拟环境中安装生成的 wheel，运行目录切到源码目录以外，确认 `hero_side_ui.__file__` 指向安装目录，再检查公开导出、字体及图标。直接在源码根目录 import 不能替代这一步。

### 初始化顺序

```python
from PySide6.QtWidgets import QApplication
from hero_side_ui import HeroSideUIProvider, ThemeProvider
from hero_side_ui.core import SmoothScroll

ThemeProvider.instance()  # 对照进程删除这一行，其余相同
app = QApplication([])
HeroSideUIProvider.setup(app, filter_libpng_warnings=False)
print("HEROSIDEUI_SCROLLSTYLE_BEGIN" in app.styleSheet())
print(SmoothScroll._global_filter is not None)
```

基线中，保留提前读取时输出为 `False / False`，对照进程为 `True / True`。使用私有字段仅用于定位，正式测试应尽量验证可观察的安装行为。

### 动画持有与同值请求

```python
from PySide6.QtCore import QEvent, QVariantAnimation
from PySide6.QtWidgets import QApplication, QWidget
from hero_side_ui.animation import tween_value

app = QApplication([])
owner = QWidget()
for _ in range(20):
    anim = tween_value(owner, "_runner", 0.0, 1.0, lambda v: None, duration=100)
    anim.setCurrentTime(anim.duration())
app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print(owner._runner is None)  # 基线为 True
print(len(owner.findChildren(QVariantAnimation)))  # 基线为 20

old = tween_value(owner, "_runner", 0.0, 1.0, lambda v: None, duration=1000)
old.setCurrentTime(300)
current = old.currentValue()
result = tween_value(owner, "_runner", current, current, lambda v: None, duration=1000)
print(result is None, old.state().name)  # 基线为 True Running
old.stop()
```

### 禁用动画时的初始选中状态

```python
from PySide6.QtWidgets import QApplication
from hero_side_ui import Checkbox, Radio

app = QApplication([])
checkbox = Checkbox(is_selected=True, disable_animation=True, theme="light")
radio = Radio(is_selected=True, disable_animation=True, theme="light")
print(checkbox.isChecked(), checkbox._fill_progress, checkbox._check_draw)
print(radio.isChecked(), radio._control_progress)
```

基线输出分别为 `True 0.0 0.0` 和 `True 0.0`。绘制私有值用于定位，修复后的测试还应验证用户可见状态。

## 整改顺序与验收

### 第一批 公共契约与验证基线

- 明确 Python、Qt、系统与架构的支持范围，以及公开 API 的兼容和弃用规则。
- 修复 CI 解释器选择，输出实际版本；明确固定依赖验证和依赖升级验证的入口。
- 将发布目标、测试结果、版本一致性和安装后冒烟检查连成可核查的发布链条。
- 为本记录的已复现问题增加有区分能力的回归测试，保留当前可复现结果作为基线。

**验收：**任务名称与实际解释器一致；构建产物能在声明支持的基线环境安装并运行；新增测试能识别整改前行为。

### 第二批 初始化与生命周期

- 处理 INIT-01、MOTION-01、MOTION-02、STATE-01，以及 Qt 对象销毁后的注册清理。
- 明确动画的抢占、取消、完成、立即终态和循环可见性语义。
- 明确全局设施的所有权和恢复规则，为异常提供可定位信息。

**验收：**改变调用顺序不遗漏设施；重复交互后对象数量有界；销毁和取消后不访问失效对象；无动画状态与逻辑状态一致。

### 第三批 桌面组件行为契约

- 统一动态字体接入和几何设置优先级，修复两项 Button 刷新问题。
- 为日期按钮等自绘交互控件补充可访问语义，核对键盘、焦点和选中状态。
- 明确逻辑尺寸、物理像素及缩放变化时的图标资源处理。

**验收：**字体与尺寸变化无需无关操作触发；键盘和辅助技术能够识别并操作控件；不同缩放比例下保持逻辑尺寸与资源分辨率契约。

### 第四批 共享能力与依赖归属

- 基于实际消费者抽取公共补间或循环驱动，保留专有效果的视觉换算和组件编排。
- 逐项治理输入类、浮层、日期、图像加载及配色的共享拥有者。
- 按明确的整包或分层策略调整导入与依赖，保持公开导入方式兼容。

**验收：**迁移前后的交互和视觉语义一致；共享能力有明确消费者、边界和测试；依赖方向可持续检查。无需将全部 Qt 动画构造迁出组件。

### 第五批 文档与贡献流程

- 同步 README、组件文档、示例、绑定说明、版本递增与发布操作。
- 清理无用导入和失效说明，为新增组件提供契约与测试清单。
- 若要对外声明完整类型支持，另行核对类型标注、`py.typed` 与类型检查流程；当前 wheel 无 `py.typed` 本身不作为运行缺陷。

**验收：**新克隆能够按照公开文档完成安装、测试、示例运行与发版准备；每项已关闭问题都能追溯到修复提交和验证结果。

## 待补充验证

- 全部 2819 项测试的运行，以及完整 Python、Qt 版本组合。
- Linux、macOS 的 GUI 实测；目标平台依赖解析不能替代安装和交互验证。
- 全组件键盘导航、焦点、输入法、读屏行为和多显示器缩放切换。
- 大数据、长期交互、重复重建及复杂组件嵌套下的性能和对象数量。
- 第三方字体、图标等资源的完整来源与许可清单。两个字体均含版权及许可元数据，不能仅凭缺少单独许可文本判定授权问题。
- [Divider 的既有布局限制](divider.md#已知设计限制与修复建议)：文档已记录带对齐标记时可能不可见，本轮未新增运行复现；其修复建议仍需通过具体布局测试确认。

## 后续维护方式

问题关闭时，在相应条目下追加修复版本或提交、测试入口和验证环境。设计风险可通过明确并记录契约关闭，不要求每一项都转化为目录重构。

新的运行问题应记录触发条件、预期行为、实际行为和复现环境，再判断属于局部实现缺陷还是公共架构约束缺失。尚未验证的范围继续保留为待验证项。
