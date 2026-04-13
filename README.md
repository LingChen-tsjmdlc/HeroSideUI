# HeroSideUI

使用 PySide6 复刻 [HeroUI v2](https://v2.heroui.com/) 设计系统的 Python 桌面组件库。

> **只改样式，不改逻辑** —— 所有组件继承自 PySide6 原生控件，保持完整的 Qt API 兼容性。
> 你可以像使用 QPushButton 一样使用 Button，只是它看起来更好看了。

---

## 设计理念

HeroSideUI 不是一个全新的组件框架，而是一层**纯样式外壳**：

- **零学习成本**: 所有组件继承自 PySide6 原生控件，Qt 的信号/槽、布局、属性系统全部可用
- **只做样式**: 颜色、圆角、字体、间距、动画，都通过 QSS + QPainter 实现，不改底层逻辑
- **设计一致性**: 颜色系统、圆角规范、字体栈全部集中在 `themes/` 目录，所有组件共享同一套 token
- **亮暗双主题**: 每个组件内置 `theme="light"` / `"dark"` 支持

---

## 设计规范

### 参考来源

| 来源               | 链接                                                                                                       | 用途                             |
| ------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------- |
| HeroUI v2 设计系统 | [heroui.com](https://heroui.com/)                                                                          | 整体设计语言、组件交互规范       |
| HeroUI 颜色系统    | [GitHub - colors/](https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/colors/)         | 6 种语义色 × 10 级色阶 (50-900)  |
| HeroUI 组件主题    | [GitHub - components/](https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/) | 各组件的变体/尺寸/状态样式定义   |
| HeroUI Ripple 组件 | [GitHub - ripple/](https://github.com/heroui-inc/heroui/blob/main/packages/components/ripple/src/)         | 水波纹动画的实现参考             |
| Tailwind CSS       | [tailwindcss.com](https://tailwindcss.com/)                                                                | HeroUI 底层使用的原子化 CSS 框架 |

### 颜色系统

来自 HeroUI v2 官方色板，每种颜色 10 个色阶（50 最浅 → 900 最深）：

| 颜色        | 用途      | 500 主色值 | 色系      |
| ----------- | --------- | ---------- | --------- |
| `default`   | 中性操作  | `#71717a`  | Zinc 灰   |
| `primary`   | 主要操作  | `#006FEE`  | Blue 蓝   |
| `secondary` | 辅助操作  | `#7828c8`  | Purple 紫 |
| `success`   | 成功/确认 | `#17c964`  | Green 绿  |
| `warning`   | 警告提示  | `#f5a524`  | Yellow 黄 |
| `danger`    | 危险/删除 | `#f31260`  | Red 红    |

颜色定义位于 [`hero_side_ui/themes/colors.py`](hero_side_ui/themes/colors.py)。

### 圆角系统

| 级别   | 像素 | 说明                   |
| ------ | ---- | ---------------------- |
| `none` | 0px  | 直角                   |
| `sm`   | 4px  | 小圆角                 |
| `md`   | 8px  | 中圆角（多数组件默认） |
| `lg`   | 14px | 大圆角                 |
| `full` | 动态 | 胶囊形（高度 ÷ 2）     |

圆角定义位于 [`hero_side_ui/themes/radius.py`](hero_side_ui/themes/radius.py)。

### 字体系统

```
Inter → SF Pro Display → -apple-system → Segoe UI → Helvetica Neue → Arial → sans-serif
```

优先使用 [Inter](https://rsms.me/inter/) 字体，逐级降级到系统默认无衬线字体。

字体定义位于 [`hero_side_ui/themes/font.py`](hero_side_ui/themes/font.py)。

### 动画系统

| 动画                   | 效果                 | 时长                   | 缓动     | 参考                  |
| ---------------------- | -------------------- | ---------------------- | -------- | --------------------- |
| 水波纹 (Ripple)        | 点击位置扩散半透明圆 | 500-900ms              | OutQuad  | HeroUI Ripple 组件    |
| 按压缩放 (Press Scale) | 按下缩小到 97%       | 按下 80ms / 松开 150ms | OutCubic | HeroUI `scale-[0.97]` |

动画封装在 [`hero_side_ui/animation/`](hero_side_ui/animation/) 目录，独立于组件，可复用。

---

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装与运行

```bash
# 克隆项目
git clone <repo-url>
cd HeroSideUI

# 安装依赖
uv sync

# 运行亮色模式示例
uv run python examples/button/light_mode.py

# 运行暗色模式示例
uv run python examples/button/dark_mode.py
```

### 基本用法

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
│   │   └── button.py            #   Button 按钮
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
│   └── button.md                #   Button 详细文档
├── examples/                    # 组件使用示例
│   └── button/
│       ├── light_mode.py        #   亮色模式全展示
│       └── dark_mode.py         #   暗色模式全展示
├── resources/                   # 静态资源
│   ├── fonts/
│   └── icons/
├── tests/                       # 测试
├── pyproject.toml
├── LICENSE                      # MIT
└── README.md
```

---

## 组件文档

各组件的详细 API、参数说明、代码示例请查看 **[docs/](docs/)** 目录：

| 组件                | 文档                             | 状态    |
| ------------------- | -------------------------------- | ------- |
| Button 按钮         | [docs/button.md](docs/button.md) | ✅ 完成 |
| _更多组件开发中..._ |                                  |         |

---

## 技术栈

| 技术                                        | 用途                |
| ------------------------------------------- | ------------------- |
| [Python 3.10+](https://python.org/)         | 运行环境            |
| [PySide6](https://doc.qt.io/qtforpython-6/) | Qt 官方 Python 绑定 |
| [uv](https://docs.astral.sh/uv/)            | 包管理与虚拟环境    |
| [hatchling](https://hatch.pypa.io/)         | 构建后端            |

---

## 鸣谢

- [HeroUI](https://heroui.com/) (原 NextUI) — 本项目的设计灵感和样式规范来源，优秀的 React 组件库
- [Qt / PySide6](https://doc.qt.io/qtforpython-6/) — 强大的跨平台桌面 UI 框架
- [uv](https://docs.astral.sh/uv/) — 极速 Python 包管理器

---

## License

[MIT](LICENSE)
