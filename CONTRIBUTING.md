# 贡献指南

感谢你愿意为 HeroSideUI 做贡献。无论是报告问题、改进文档，还是新增组件，都欢迎。

开始之前，建议先读一下 [README](README.md)，了解项目是什么、怎么使用；想知道代码为什么这样组织，见 [架构整理与演进规则](docs/architecture.md)。

## Issues

提问、建议功能、报告问题，请直接[新建 Issue](https://github.com/LingChen-tsjmdlc/HeroSideUI/issues)。

报告问题时请尽量带上：

- 复现问题的最小代码；
- 期望的结果与实际的结果；
- 运行环境：操作系统、Python 版本、PySide6 版本、HeroSideUI 版本。

可以用下面这条命令一次取到版本信息：

```bash
python -c "import sys, PySide6, hero_side_ui; print(sys.version, PySide6.__version__, hero_side_ui.__version__)"
```

## Pull Requests

小的改动（错别字、文档润色、明显的 bug）可以直接提 PR。较大的改动，比如新增组件、改变公开接口，请先开一个 Issue 讨论，避免白费功夫。

### 环境要求

- Python 3.10 到 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- git

项目不需要编译，也不依赖数据库等外部服务。

### 安装

先在 GitHub 上 Fork 本仓库，再克隆你的 Fork：

```bash
git clone git@github.com:<你的用户名>/HeroSideUI.git
cd HeroSideUI

# 安装依赖（含测试与开发工具）
uv sync

# 安装 Git 钩子
uv run pre-commit install --hook-type commit-msg --hook-type pre-commit
```

### 新建分支

```bash
git switch -c my-new-feature
```

### 运行测试与检查

```bash
# 全部测试
uv run python -m pytest tests/ -v

# 只跑某个组件
uv run python -m pytest tests/components/test_button.py -v

# 只跑架构检查（见下文“架构规则”）
uv run python -m pytest tests/shared -v

# 代码规范：检查与格式化
uvx ruff check hero_side_ui/ examples/ tests/
uvx ruff format hero_side_ui/ examples/ tests/
```

提交时 pre-commit 会自动运行 Ruff、检查单文件行数（不超过 1000 行）等。CI 在 GitHub 上运行同样的检查，外加完整测试。

视觉效果和动画靠 `examples/` 下的示例人工确认，改动涉及外观时，请自己跑一下对应的示例。

## 项目结构

| 目录                            | 内容                                                                                   |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `hero_side_ui/components/`      | 组件实现，一个组件一个目录                                                             |
| `hero_side_ui/_shared/`         | 同一类组件共用的内部实现，按家族分目录（输入类、浮层、日期、图片、配色、代码等）       |
| `hero_side_ui/core/`            | 全局主题、字体、启动和滚动等运行时设施                                                 |
| `hero_side_ui/themes/`          | 设计 Token：颜色、圆角、字体常量、各组件的尺寸预设                                     |
| `hero_side_ui/animation/`       | 通用动画                                                                               |
| `hero_side_ui/icons/`、`utils/` | 图标资源接口、工具函数                                                                 |
| `docs/`                         | 组件文档，一个组件一个同名 md；`architecture*.md` 是架构说明                           |
| `examples/`                     | 示例，路径为 `examples/<组件>/demo.py`                                                 |
| `tests/`                        | `components/` 测组件，`core/`、`animation/`、`utils/` 测基础设施，`shared/` 测架构规则 |

## 架构规则

下面六条规则保证各部分不会互相牵连。其中 1 到 4 条有自动测试，在 `tests/shared/`，GitHub 上每次推送都会运行；5、6 条靠评审把关，请提交前自己对照。

1. **不要导入别的组件里带下划线的内容**，例如 `from ..input._wrapper import ...`。带下划线的是内部实现，改动时不会通知你。需要共用，就放到 `hero_side_ui/_shared/` 下，并把所有用到的地方一起改。
2. **不要直接读写别的组件的内部字段**，例如 `self._listbox._focused_index`。缺什么，就在被使用的组件上加公开方法。
3. **下层目录不能依赖上层：** `themes`、`utils`、`animation`、`icons` 不能用 `core` 和 `components`；`core` 不能用 `components`；`_shared` 运行时不能用 `components`。
4. **自己设置字体的组件，要提供 `_apply_font()` 并向 `FontProvider` 登记**，这样运行时切换全局字体，它才会跟着变。
5. **接收外部控件的方法**，如 `set_xxx_content(widget)`，在文档里写明替换时旧控件是被销毁，还是还给调用方。
6. **新增会改动整个应用的东西**，如改应用样式表、装全局事件过滤器，要同时提供撤销办法，并加进 `HeroSideUIProvider.teardown()`。

### 已登记的例外

下面这些是有意为之，原因写在这里。要新增例外，请改对应测试里的名单，并在这里补上原因。

| 位置                                                                  | 原因                                                                   |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `utils/icon_utils.py` 读取已存在的主题管家                            | 旧的图标函数默认跟随主题。它只读取，不会创建                           |
| `code_block`、`code_editor` 不登记全局字体                            | 代码要用等宽字体，不跟随正文字体                                       |
| `link` 不自己登记字体                                                 | 文字由已登记的内部文字组件负责                                         |
| Input、日期输入、多行输入、Badge、Slider 替换控件时把旧控件还给调用方 | 这些方法既收图标名字符串，也收控件，要区分库自己建的图标和调用方的控件 |

## 新增一个组件

1. 在 `hero_side_ui/components/<组件>/` 下建目录，包含 `<组件>.py` 和 `__init__.py`。
2. 在 `hero_side_ui/components/__init__.py` 和 `hero_side_ui/__init__.py` 里登记名字（两处的名字表要一致，测试会检查）。
3. 颜色、尺寸等设计数值放在 `hero_side_ui/themes/`，不要写死在组件里。
4. 在 `docs/<组件>.md` 写文档，在 `examples/<组件>/demo.py` 写示例，在 `tests/components/` 写测试。

## 代码风格

- 注释只写“做什么”，要简短；函数说明不超过 40 字。需要长篇解释的内容写进 `docs/` 下与组件同名的 md。
- 文件顶部可以有一段不超过 15 行的说明文档字符串，其余位置不写大段文档字符串。
- 不要把调试经过、踩坑记录写进注释，这是开源项目，注释只面向使用者与读代码的人。
- 不要手动修改版本号。`.hooks/commit_msg_bump.py` 会在提交后自动递增，提交信息末尾加 `(y)` 升次版本、加 `(x)` 升主版本。

## 提交与 PR

本仓库的提交信息按 VS Code 插件 [git-commit-plugin](https://marketplace.visualstudio.com/items?itemName=redjue.git-commit-plugin) 的默认格式书写：`图标 类型(范围): 中文说明`。这只是推荐，不强制；写得清楚、能看出改了什么即可，维护者合并时可以代为调整。

| 类型     | 图标 | 用在什么时候             |
| -------- | ---- | ------------------------ |
| feat     | ✨   | 新功能、新组件           |
| fix      | 🐞   | 修复问题                 |
| docs     | 📝   | 只改文档                 |
| style    | 🌈   | 只改格式，不改逻辑       |
| refactor | 🦄   | 重构，不加功能也不修问题 |
| perf     | 🎈   | 提升性能                 |
| test     | 🧪   | 增加或修改测试           |
| chore    | 🐳   | 构建、依赖、工具         |

例如：`🐞 fix(button): 修复图标按钮尺寸约束`。

PR 的标题可以沿用这个格式。正文建议写清楚三件事：改了什么、为什么改、怎么验证的。涉及外观的改动，附上截图会让评审轻松很多。如果它解决了某个 Issue，可以写上 `Fixes #编号`。

## 许可

提交代码即表示你同意以 [MIT 许可](LICENSE) 发布你的贡献。
