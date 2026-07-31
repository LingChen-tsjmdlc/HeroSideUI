# HeroSideUI

使用 PySide6 复刻 [HeroUI v2](https://v2.heroui.com/) 设计系统的 Python 桌面组件库。

> **只改样式，不改逻辑** —— 所有组件继承自 PySide6 原生控件，保持完整的 Qt API 兼容性。
> 你可以像使用 QPushButton 一样使用 Button，只是它看起来更好看了。

---

## 设计理念

HeroSideUI 不是一个全新的组件框架，而是一层**纯样式外壳**：

- **零学习成本**: 所有组件继承自 PySide6 原生控件，Qt 的信号/槽、布局、属性系统全部可用
- **只做样式**: 颜色、圆角、字体、间距、动画，都通过 QSS + QPainter 实现，不改底层逻辑
- **设计一致性**: 颜色/圆角/字体等通用 Token 放在 `themes/` 顶层，组件独有的尺寸与阴影预设收纳在 `themes/component_presets/`，所有组件共享同一套规范
- **亮暗双主题**: 每个组件内置 `theme="light"` / `"dark"` 支持

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

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装与运行

```bash
# 克隆项目
git clone https://github.com/LingChen-tsjmdlc/HeroSideUI
cd HeroSideUI

# 安装依赖
uv sync

# 运行亮色模式示例（以按钮组件作为示例）
uv run python examples/button/light_mode.py

# 运行暗色模式示例（以按钮组件作为示例
uv run python examples/button/dark_mode.py
```

### 基本用法（以按钮组件作为示例）

```python
from hero_side_ui import Button

# 一行创建一个好看的按钮
btn = Button("Click me", color="primary", variant="solid")

# 暗色模式
btn_dark = Button("Dark", color="primary", variant="flat", theme="dark")

# Qt 原生 API 正常使用
btn.clicked.connect(lambda: print("clicked!"))
```

---

## 项目结构

```
HeroSideUI/
├── hero_side_ui/                # 主库
│   ├── __init__.py
│   ├── components/              # 组件实现
│   │   ├── __init__.py
│   │   ├── button.py            #   Button 按钮
│   │   └── ......               #   更多组件...
│   ├── themes/                  # 主题与设计 Token
│   │   ├── colors.py            #   颜色系统 (6色 × 10阶) —— 通用
│   │   ├── radius.py            #   圆角系统 —— 通用
│   │   ├── font.py              #   字体系统 —— 通用
│   │   └── component_presets/   #   组件级主题预设（尺寸/阴影等）
│   │       ├── button.py        #     BUTTON_SIZES
│   │       ├── card.py          #     CARD_SHADOWS
│   │       ├── popover.py       #     POPOVER_SHADOWS
│   │       └── ......           #     更多组件...
│   ├── animation/               # 动画效果
│   │   ├── ripple.py            #   水波纹
│   │   └── press_scale.py       #   按压缩放
│   ├── utils/                   # 工具函数
│   │   └── color_utils.py       #   颜色转换 (hex→rgba)
│   └── resources/               # 随包分发的静态资源
│       └── icons/               #   内置 SVG 图标（打进 wheel）
├── docs/                        # 组件 API 文档
│   ├── button.md                #   Button 详细文档
│   └── ......                   #   更多组件详细文档
├── examples/                    # 组件使用示例
│   ├── button/
│   │   ├── light_mode.py        #   亮色模式全展示
│   │   └── dark_mode.py         #   暗色模式全展示
│   └── ....../                  #   更多组件示例
├── tests/                       # 测试
├── pyproject.toml               # 项目配置
├── LICENSE                      # MIT
└── README.md                    # 本文档
```

---

## 组件文档

各组件的详细 API、参数说明、代码示例请查看 **[docs/](docs/)** 目录。

### 已完成组件（对标 HeroUI v2）

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
| CodeBlock 代码块         | [code_block.md](docs/code_block.md)         | ✅   |
| Markdown 渲染器          | [markdown.md](docs/markdown.md)             | ✅   |

### 待开发组件 — HeroUI v2 复刻

| 组件                   | 说明                        | 难度       | 必要性     | 状态      |
| ---------------------- | --------------------------- | ---------- | ---------- | --------- |
| Dropdown 下拉菜单      | 触发式下拉面板（键盘导航）  | ⭐⭐⭐⭐⭐ | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| Toast 轻提示           | 自动消失的通知气泡          | ⭐⭐⭐     | ❤️❤️❤️❤️❤️ | 🔲 待开发 |
| Drawer 抽屉            | 侧滑面板 + 遮罩 + Esc 关闭  | ⭐⭐⭐⭐   | ❤️❤️❤️     | 🔲 待开发 |
| TimeInput 时间选择器   | 时:分（秒）段选择输入       | ⭐⭐⭐     | ❤️❤️❤️     | 🔲 待开发 |
| NumberInput 数字输入框 | 带步进/步退的数字输入       | ⭐⭐⭐     | ❤️❤️❤️     | 🔲 待开发 |
| RadioGroup 单选按钮组  | 多个 Radio 的互斥分组容器   | ⭐⭐       | ❤️❤️❤️     | 🔲 待开发 |
| Badge 徽章             | 小型状态标签（点/圆角变体） | ⭐         | ❤️❤️❤️     | 🔲 待开发 |
| Navbar 导航栏          | 顶部导航条（组合型容器）    | ⭐⭐⭐     | ❤️❤️       | 🔲 待开发 |
| InputOTP 验证码输入框  | 等宽分格 OTP / 验证码输入   | ⭐⭐⭐     | ❤️❤️       | 🔲 待开发 |
| Breadcrumbs 面包屑导航 | 路径层级指示                | ⭐⭐       | ❤️❤️       | 🔲 待开发 |
| Spacer 间距填充器      | 弹性空白占位                | ⭐         | ❤️         | 🔲 待开发 |

### 待开发组件 — 桌面端专属或者是额外组件

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

| 组件                   | 原因                                                      |
| ---------------------- | --------------------------------------------------------- |
| Form 表单容器          | 纯组合语义，用 QLayout + 现有输入类组件即可，无需额外抽象 |
| User 用户信息卡片      | Avatar + Text 的简单组合，使用方自行拼装更灵活            |
| Modal 模态框（HeroUI） | 桌面端由 Dialog 统一覆盖，无需单独组件                    |
| Segmented 分段控件     | 与 Tabs 功能重复，选项级互斥切换 Tabs 加 variant 即可覆盖 |
| DotPagination 圆点分页 | 已有 Pagination，圆点指示器只是视觉换皮                   |
| Router 路由            | Web 概念，桌面端 Tabs + QStackedWidget 即可实现页面切换   |

> **进度**：已完成 **40** 个组件，待开发 **26** 个（含桌面端专属 15 个），不计划开发 **6** 个。

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
uv run python -m pytest tests/test_button.py -v
uv run python -m pytest tests/test_accordion.py -v
```

测试覆盖构造参数、颜色/变体/尺寸遍历、动态 API、展开收起逻辑、信号触发等。视觉效果和动画通过 `examples/` 目录的示例人工验证。

---

## 发布新版本

本仓库已接入 **GitHub Actions + PyPI Trusted Publisher (OIDC)**，发包零 Token、任何电脑都能触发。

最简流程：

```bash
# 1. bump 版本号（pyproject.toml + hero_side_ui/__init__.py）
# 2. commit + push
git commit -am "chore: release v0.0.22"
git tag v0.0.22 && git push origin main --tags
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
