# HeroSideUI

使用 PySide6 复刻 [HeroUI v2](https://v2.heroui.com/) 设计系统的 Python 桌面组件库。

> 把 HeroUI v2 的视觉与交互语义完整搬到 Qt 桌面端——外观对齐 Web 版，行为遵循桌面惯例。

- **HeroUI v2 全部组件复刻完成**（51 个，含 DateInput/DatePicker/Table/Calendar/Dropdown/Toast/Drawer/Markdown 等高复杂度组件）
- 另规划 15 个桌面端专属组件（Dialog / ContextMenu / Window / Tree 等）

---

## 设计理念

- **Qt 生态一等公民**：全部组件基于 PySide6 构建，信号/槽、布局、父子关系等 Qt 机制完全可用；交互原语（Button/Checkbox/Switch/Radio/Text 等）直接继承原生控件，原生 API 无损
- **复杂组件自绘复刻**：为达到与 Web 版逐像素对齐的视觉保真度，Toast/Table/Calendar/Markdown 等复杂组件采用 QWidget + QSS + QPainter 自绘实现，对外暴露 HeroUI 风格 API（如 `Input.value` / `value_changed`），而非原生控件 API
- **全局 Provider**：一行 `HeroSideUIProvider.setup()` 统一管理主题、字体、平滑滚动，组件自动注册、主题切换自动刷新
- **状态驱动视觉**：组件自监听 hover/press/focus/disabled 状态，无需调用方手动刷新
- **设计一致性**：颜色/圆角/字体等通用 Token 放在 `themes/` 顶层，组件独有的尺寸与阴影预设收纳在 `themes/component_presets/`，所有组件共享同一套规范

---

## 快速开始

### 环境要求

- Python 3.10+（3.10 ~ 3.14）
- [uv](https://docs.astral.sh/uv/) 包管理器（推荐）

### 安装

```bash
# 从 PyPI 安装
pip install herosideui[pyside6]

# 或从源码
git clone https://github.com/LingChen-tsjmdlc/HeroSideUI
cd HeroSideUI
uv sync
```

### 基本用法

```python
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

from hero_side_ui import HeroSideUIProvider, Button

app = QApplication(sys.argv)

# 一行初始化：主题 / 字体 / 平滑滚动 全局生效
HeroSideUIProvider.setup(app, theme="light")   # "auto" / "light" / "dark"

window = QWidget()
layout = QVBoxLayout(window)

btn = Button("Click me", color="primary", variant="solid")
btn.clicked.connect(lambda: print("clicked!"))
layout.addWidget(btn)

window.show()
app.exec()
```

> 组件在 `Provider.setup()` 之前创建也可以——会自动以默认配置降级初始化并给出 warning。
> 单个组件可用 `theme="light"` / `"dark"` 覆盖全局主题，`"auto"` 跟随 Provider。

### 运行示例

每个组件都有对应的交互式示例（含全参数展示）：

```bash
uv run python examples/button/demo.py     # Button
uv run python examples/input_otp/demo.py  # InputOTP
uv run python examples/spacer/demo.py     # Spacer
# ... 其余见 examples/ 目录，一律 examples/<组件>/demo.py
```

---

## 组件文档

各组件的详细 API、参数说明、代码示例请查看 **[docs/](docs/)** 目录。

### 已完成组件（51 / HeroUI v2 复刻全部完成）

| 组件                     | 文档                                        | 状态 |
| ------------------------ | ------------------------------------------- | ---- |
| Button 按钮              | [button.md](docs/button.md)                 | ✅   |
| Accordion 手风琴         | [accordion.md](docs/accordion.md)           | ✅   |
| Input 输入框             | [input.md](docs/input.md)                   | ✅   |
| Divider 分割线           | [divider.md](docs/divider.md)               | ✅   |
| Card 卡片                | [card.md](docs/card.md)                     | ✅   |
| Checkbox 复选框          | [checkbox.md](docs/checkbox.md)             | ✅   |
| Checkbox Group 复选框组  | [checkbox.md](docs/checkbox.md)             | ✅   |
| Progress 进度条          | [progress.md](docs/progress.md)             | ✅   |
| Circular Progress 环形   | [progress.md](docs/progress.md)             | ✅   |
| Spinner 加载指示器       | [spinner.md](docs/spinner.md)               | ✅   |
| Popover 弹出层           | [popover.md](docs/popover.md)               | ✅   |
| Tooltip 工具提示         | [tooltip.md](docs/tooltip.md)               | ✅   |
| Tabs 标签页              | [tabs.md](docs/tabs.md)                     | ✅   |
| ThemeSwitcher 主题切换   | [theme_switcher.md](docs/theme_switcher.md) | ✅   |
| Text 文字系（标题等）    | [text.md](docs/text.md)                     | ✅   |
| Switch 开关              | [switch.md](docs/switch.md)                 | ✅   |
| ScrollShadow 滚动阴影    | [scroll-shadow.md](docs/scroll-shadow.md)   | ✅   |
| Listbox 列表选择框       | [listbox.md](docs/listbox.md)               | ✅   |
| Autocomplete 自动补全    | [autocomplete.md](docs/autocomplete.md)     | ✅   |
| Textarea 多行输入框      | [textarea.md](docs/textarea.md)             | ✅   |
| Slider 滑块              | [slider.md](docs/slider.md)                 | ✅   |
| Select 下拉选择框        | [select.md](docs/select.md)                 | ✅   |
| Pagination 分页器        | [pagination.md](docs/pagination.md)         | ✅   |
| Alert 警告提示           | [alert.md](docs/alert.md)                   | ✅   |
| Skeleton 骨架屏          | [skeleton.md](docs/skeleton.md)             | ✅   |
| Image 图片               | [image.md](docs/image.md)                   | ✅   |
| Kbd 键盘按键             | [kbd.md](docs/kbd.md)                       | ✅   |
| Link 链接                | [link.md](docs/link.md)                     | ✅   |
| Chip 标签                | [chip.md](docs/chip.md)                     | ✅   |
| Table 表格               | [table.md](docs/table.md)                   | ✅   |
| Avatar 头像              | [avatar.md](docs/avatar.md)                 | ✅   |
| AvatarGroup 头像组       | [avatar.md](docs/avatar.md)                 | ✅   |
| Calendar 日历            | [calendar.md](docs/calendar.md)             | ✅   |
| RangeCalendar 范围日历   | [calendar.md](docs/calendar.md)             | ✅   |
| DateInput 日期选择器     | [date-input.md](docs/date-input.md)         | ✅   |
| DatePicker 日期选择器    | [date-picker.md](docs/date-picker.md)       | ✅   |
| DateRangePicker 范围日期 | [date-picker.md](docs/date-picker.md)       | ✅   |
| Radio 单选按钮           | [radio.md](docs/radio.md)                   | ✅   |
| RadioGroup 单选按钮组    | [radio.md](docs/radio.md)                   | ✅   |
| CodeBlock 代码块         | [code_block.md](docs/code_block.md)         | ✅   |
| CodeEditor 代码编辑器    | [code_editor.md](docs/code_editor.md)       | ✅   |
| Markdown 渲染器          | [markdown.md](docs/markdown.md)             | ✅   |
| Dropdown 下拉菜单        | [dropdown.md](docs/dropdown.md)             | ✅   |
| Toast 轻提示             | [toast.md](docs/toast.md)                   | ✅   |
| Drawer 抽屉              | [drawer.md](docs/drawer.md)                 | ✅   |
| TimeInput 时间选择器     | [time_input.md](docs/time_input.md)         | ✅   |
| NumberInput 数字输入框   | [number_input.md](docs/number_input.md)     | ✅   |
| Badge 徽章               | [badge.md](docs/badge.md)                   | ✅   |
| InputOTP 验证码输入框    | [input_otp.md](docs/input_otp.md)           | ✅   |
| Breadcrumbs 面包屑导航   | [breadcrumbs.md](docs/breadcrumbs.md)       | ✅   |
| Spacer 间距填充器        | [spacer.md](docs/spacer.md)                 | ✅   |

### 待开发组件 — 桌面端专属

> HeroUI 是 Web 组件库，以下为 HeroSideUI 针对桌面 GUI 场景自行补充的组件。

| 组件                        | 说明                                                                                      | 难度       | 必要性     | 状态      |
| --------------------------- | ----------------------------------------------------------------------------------------- | ---------- | ---------- | --------- |
| Dialog 对话框               | 模态无边框对话框：遮罩 + 居中弹窗 + Esc，用于消息提示/确认/提交内容，中断用户操作直到关闭 | ⭐⭐⭐⭐   | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| ContextMenu 右键菜单        | 右键弹出菜单 + 子菜单 + 分隔线 + 快捷键标注                                               | ⭐⭐⭐⭐   | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| Window 无边框窗口           | 自定义标题栏 + 窗口按钮 + 拖动/缩放/Aero Snap，现代桌面应用基底                           | ⭐⭐⭐⭐⭐ | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| Tree 树形控件               | 文件树 / 大纲视图 / 多级嵌套数据展示                                                      | ⭐⭐⭐⭐   | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| SystemTray 系统托盘         | 最小化到托盘 + 托盘菜单 + 桌面通知                                                        | ⭐⭐⭐     | ❤️❤️❤️❤️   | 🔲 待开发 |
| SplitView 分割面板          | 左右/上下可拖拽调整的分割视图，IDE / 文件管理器高频                                       | ⭐⭐⭐⭐   | ❤️❤️❤️❤️   | 🔲 待开发 |
| CommandBar 工具栏           | 工具栏操作按钮组 + 更多按钮折叠溢出                                                       | ⭐⭐⭐     | ❤️❤️❤️❤️   | 🔲 待开发 |
| ColorPicker 颜色选择器      | 取色板 + 预设色 + 自定义 HEX/RGB 输入 + 透明度                                            | ⭐⭐⭐⭐   | ❤️❤️❤️❤️   | 🔲 待开发 |
| Icon 图标                   | 基于 Iconify 的矢量图标，联网获取百万级图标库 + 颜色/尺寸/旋转                            | ⭐⭐⭐     | ❤️❤️❤️❤️   | 🔲 待开发 |
| AudioPlayer 音频播放器      | 播放控件 + 进度条 + 音量 + 支持主流格式                                                   | ⭐⭐⭐⭐   | ❤️❤️❤️❤️   | 🔲 待开发 |
| VideoPlayer 视频播放器      | 视频画面 + 播放控件 + 全屏 + 支持主流格式                                                 | ⭐⭐⭐⭐⭐ | ❤️❤️❤️❤️   | 🔲 待开发 |
| FlowLayout 流式布局         | 自动换行排列子控件，Chip/Tag/Badge 展示必备                                               | ⭐⭐       | ❤️❤️❤️     | 🔲 待开发 |
| Carousel 轮播图             | 图片画廊 / 内容卡片轮播展示 + 自动播放 + 指示器                                           | ⭐⭐⭐     | ❤️❤️❤️     | 🔲 待开发 |
| ShortcutEditor 快捷键选择器 | 录制键盘快捷键 + 冲突检测 + 显示当前绑定                                                  | ⭐⭐⭐     | ❤️❤️❤️     | 🔲 待开发 |
| SplashScreen 启动画面       | 应用启动时的品牌展示 + 进度指示                                                           | ⭐⭐       | ❤️❤️❤️     | 🔲 待开发 |

> **难度 ⭐**（1~5）：⭐ 复用现有组件直接拼装；⭐⭐⭐ 需新交互逻辑但可复用现有基础设施；⭐⭐⭐⭐⭐ 涉及焦点管理 / 键盘导航 / 架构级上下文。
> **必要性 ❤️**（1~5）：❤️❤️❤️❤️❤️ 高频刚需；❤️❤️❤️ 常用但可被组合替代；❤️ 偏 Web 语义或复用度低。

### 不计划开发

| 组件                   | 原因                                                                                                       |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| Form 表单容器          | 纯组合语义，用 QLayout + 现有输入类组件即可，无需额外抽象                                                  |
| User 用户信息卡片      | Avatar + Text 的简单组合，使用方自行拼装更灵活                                                             |
| Modal 模态框（HeroUI） | 桌面端由 Dialog 统一覆盖，无需单独组件                                                                     |
| Navbar 导航栏          | Web 导航语义，桌面端由 Window 标题栏 + CommandBar + 侧边栏覆盖；纯组合无独有逻辑，需要时用现有组件自行拼装 |
| Segmented 分段控件     | 与 Tabs 功能重复，选项级互斥切换 Tabs 加 variant 即可覆盖                                                  |
| DotPagination 圆点分页 | 已有 Pagination，圆点指示器只是视觉换皮                                                                    |
| Router 路由            | Web 概念，桌面端 Tabs + QStackedWidget 即可实现页面切换                                                    |

> **进度**：HeroUI v2 复刻 **51 / 51 全部完成**；桌面端专属待开发 **15** 个；不计划开发 **7** 个。

---

## 设计规范

所有样式参考自 [HeroUI v2](https://heroui.com/) 设计系统（[GitHub 源码](https://github.com/heroui-inc/heroui/tree/main/packages/core/theme/src)），包括颜色、圆角、动画等。

### 颜色系统

6 种语义颜色，每种包含 50-900 共 10 个色阶：

| 颜色        | 用途      | 主色值    |
| ----------- | --------- | --------- |
| `default`   | 中性操作  | `#71717a` |
| `primary`   | 主要操作  | `#006FEE` |
| `secondary` | 辅助操作  | `#7828c8` |
| `success`   | 成功/确认 | `#17c964` |
| `warning`   | 警告提示  | `#f5a524` |
| `danger`    | 危险/删除 | `#f31260` |

### 圆角系统

| 级别   | 像素 | 说明           |
| ------ | ---- | -------------- |
| `none` | 0px  | 直角           |
| `sm`   | 4px  | 小圆角         |
| `md`   | 8px  | 中圆角（默认） |
| `lg`   | 14px | 大圆角         |
| `full` | 动态 | 胶囊形         |

字体、动画等更多设计细节见 [`hero_side_ui/themes/`](hero_side_ui/themes/) 和 [`hero_side_ui/animation/`](hero_side_ui/animation/) 目录。

---

## 项目结构

```
HeroSideUI/
├── hero_side_ui/                # 主库
│   ├── __init__.py              #   顶层导出（含 __version__）
│   ├── components/              # 组件实现（目录式包，一组件一目录）
│   │   ├── button/              #   Button 按钮
│   │   │   ├── button.py        #     组件主体
│   │   │   ├── _styling.py      #     配色 token
│   │   │   └── __init__.py
│   │   └── ......               #   更多组件...
│   ├── core/                    # Provider / ThemeProvider / FontProvider
│   ├── themes/                  # 主题与设计 Token
│   │   ├── colors.py            #   颜色系统 (6 色 × 10 阶) —— 通用
│   │   ├── radius.py            #   圆角系统 —— 通用
│   │   ├── font.py              #   字体系统 —— 通用
│   │   └── component_presets/   #   组件级主题预设（尺寸/阴影/校验表）
│   ├── animation/               # 动画效果（水波纹 / 按压缩放 / 下划线展开等）
│   ├── utils/                   # 工具函数（颜色转换 / SVG 图标加载等）
│   └── resources/               # 随包分发的静态资源
│       └── icons/               #   内置 SVG 图标（打进 wheel）
├── docs/                        # 组件 API 文档（一组件一 md）
├── examples/                    # 使用示例（examples/<组件>/demo.py）
├── tests/                       # pytest + pytest-qt（tests/components/）
├── pyproject.toml               # 项目配置（hatchling 构建）
├── LICENSE                      # MIT
└── README.md                    # 本文档
```

---

## Qt 兼容性

HeroSideUI **以 PySide6 为一等公民**，并对 PySide2 提供 best-effort 兼容（DCC 插件、老 Qt5 桌面应用）。

```bash
# 推荐
pip install herosideui[pyside6]

# DCC 插件 / 老 Qt5 应用
pip install herosideui[pyside2]
```

> 完整迁移路线、重难点与撤退判定见 [`docs/migration.md`](docs/migration.md)。

---

## 技术栈

| 技术                                        | 用途                |
| ------------------------------------------- | ------------------- |
| [Python 3.10+](https://python.org/)         | 运行环境            |
| [PySide6](https://doc.qt.io/qtforpython-6/) | Qt 官方 Python 绑定 |
| [uv](https://docs.astral.sh/uv/)            | 包管理与虚拟环境    |
| [hatchling](https://hatch.pypa.io/)         | 构建后端            |

---

## 测试

使用 [pytest](https://docs.pytest.org/) + [pytest-qt](https://pytest-qt.readthedocs.io/) 进行组件测试。

```bash
# 运行全部测试
uv run python -m pytest tests/ -v

# 只测某个组件
uv run python -m pytest tests/components/test_button.py -v
uv run python -m pytest tests/components/test_breadcrumbs.py -v
```

测试覆盖构造参数、颜色/变体/尺寸遍历、动态 API、折叠/展开逻辑、信号触发等。视觉效果和动画通过 `examples/` 目录的示例人工验证。

---

## 发布新版本

本仓库已接入 **GitHub Actions + PyPI Trusted Publisher (OIDC)**，发包零 Token、任何电脑都能触发。

最简流程：

```bash
# 1. bump 版本号（pyproject.toml + hero_side_ui/__init__.py）
# 2. commit + push
git commit -am "chore: release v0.15.0"
git tag v0.15.0 && git push origin main --tags
# 3. 在 GitHub 网页 Releases → Draft a new release → 选 tag → Publish
# 4. 等 Actions 绿勾 → PyPI 有新版
```

首次配置、TestPyPI 试水、故障排查等完整文档见 **[docs/PUBLISHING.md](docs/PUBLISHING.md)**。

---

## Git 钩子

使用 [pre-commit](https://pre-commit.com/) 管理 Git 钩子。首次 clone 后安装：

```bash
uv run pre-commit install --hook-type commit-msg --hook-type pre-commit
```

内置钩子：

- **版本号自动递增**（commit-msg 阶段）
  - 默认提交 → `z+1`（0.0.1 → 0.0.2）
  - 消息末尾加 `(y)` → `y+1`（0.0.2 → 0.1.0）
  - 消息末尾加 `(x)` → `x+1`（0.1.0 → 1.0.0）
  - 支持中英文括号：`(y)` `（y）` `(Y)` `（Y）`
- **尾部空白清理** / **文件末尾换行** / **YAML/TOML 检查** / **大文件检查** / **合并冲突检查**

---

## 鸣谢

- [HeroUI](https://heroui.com/) (原 NextUI) — 本项目的设计灵感和样式规范来源，优秀的 React 组件库
- [Qt / PySide6](https://doc.qt.io/qtforpython-6/) — 强大的跨平台桌面 UI 框架
- [uv](https://docs.astral.sh/uv/) — 极速 Python 包管理器

---

## License

[MIT](LICENSE)
