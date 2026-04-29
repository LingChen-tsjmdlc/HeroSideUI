# HeroSideUI

使用 PySide6 复刻 [HeroUI v2](https://v2.heroui.com/) 设计系统的 Python 桌面组件库。

> **只改样式，不改逻辑** —— 所有组件继承自 PySide6 原生控件，保持完整的 Qt API 兼容性。
> 你可以像使用 QPushButton 一样使用 Button，只是它看起来更好看了。

---

## 设计理念

HeroSideUI 不是一个全新的组件框架，而是一层**纯样式外壳**：

- **零学习成本**: 所有组件继承自 PySide6 原生控件，Qt 的信号/槽、布局、属性系统全部可用
- **只做样式**: 颜色、圆角、字体、间距、动画，都通过 QSS + QPainter 实现，不改底层逻辑
- **设计一致性**: 颜色系统、圆角规范、字体栈全部集中在 `themes/` 目录，所有组件共享同一套规范
- **亮暗双主题**: 每个组件内置 `theme="light"` / `"dark"` 支持

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
│   ├── themes/                  # 全局设计 Token
│   │   ├── colors.py            #   颜色系统 (6色 × 10阶)
│   │   ├── radius.py            #   圆角系统
│   │   ├── font.py              #   字体系统
│   │   └── sizes.py             #   组件尺寸配置
│   ├── animation/               # 动画效果
│   │   ├── ripple.py            #   水波纹
│   │   └── press_scale.py       #   按压缩放
│   └── utils/                   # 工具函数
│       └── color_utils.py       #   颜色转换 (hex→rgba)
├── docs/                        # 组件 API 文档
│   ├── button.md                #   Button 详细文档
│   └── ......                   #   更多组件详细文档
├── examples/                    # 组件使用示例
│   ├── button/
│   │   ├── light_mode.py        #   亮色模式全展示
│   │   └── dark_mode.py         #   暗色模式全展示
│   └── ....../                  #   更多组件示例
├── resources/                   # 静态资源
│   ├── fonts/                   #   字体文件
│   └── icons/                   #   图标文件
├── tests/                       # 测试
├── pyproject.toml               # 项目配置
├── LICENSE                      # MIT
└── README.md                    # 本文档
```

---

## 组件文档

各组件的详细 API、参数说明、代码示例请查看 **[docs/](docs/)** 目录：

| 组件                | 文档                                   | 状态    |
| ------------------- | -------------------------------------- | ------- |
| Button 按钮         | [docs/button.md](docs/button.md)       | ✅ 完成 |
| Accordion 手风琴    | [docs/accordion.md](docs/accordion.md) | ✅ 完成 |
| Input 输入框        | [docs/input.md](docs/input.md)         | ✅ 完成 |
| _更多组件开发中..._ |                                        |         |

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
