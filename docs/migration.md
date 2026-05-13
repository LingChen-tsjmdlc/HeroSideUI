# PySide6 → 双绑定（PySide6 + PySide2）迁移指南

> **Status: DEFERRED（方案保留，暂不执行）**
>
> 经评估，PySide2 官方 wheel 仅支持 Python 3.5–3.10，而项目 `requires-python = ">=3.10,<3.15"`，
> 双绑定的唯一交集只有 Python 3.10 这一个版本。考虑到：
>
> 1. 主流 DCC（Maya 2026+ / Houdini 21+）已在迁移至 Qt6 + PySide6
> 2. 迁移成本 7.5–11.5 天 + 长期维护负担（视觉回归、CI 双矩阵、lint 约束）
> 3. 收益窗口期短（1–2 年后 PySide2 场景基本消失）
>
> **决定：项目保持纯 PySide6。本文档仅作为未来备选方案参考，不实施。**
>
> 若未来 DCC 用户需求激增，可考虑 fork `herosideui-qt5` 精简版，而非改造主线。

---

> 以下为原始方案设计文档（归档参考）：

> 这份文档是 HeroSideUI 从纯 PySide6 项目演进为"PySide6 优先、PySide2 best-effort 兼容"的双绑定库的**实施手册**。
> 它服务两类读者：
>
> - **维护者**：按文档分阶段执行迁移，是 PR 评审与节奏控制的依据
> - **使用者**：理解为什么有 `[pyside6]` / `[pyside2]` 两个 extras，以及怎么选

---

## 目录

- [一、定位与原则](#一定位与原则)
- [二、技术选型：为什么是 qtpy](#二技术选型为什么是-qtpy)
- [三、整体路线图](#三整体路线图)
- [四、Phase 1 — qtpy 接入与枚举扁平化](#四phase-1--qtpy-接入与枚举扁平化)
- [五、Phase 2 — PySide2 装载与烟囱测试](#五phase-2--pyside2-装载与烟囱测试)
- [六、Phase 3 — 像素级视觉回归（核心难点）](#六phase-3--像素级视觉回归核心难点)
- [七、Phase 4 — CI、发布与文档](#七phase-4--ci发布与文档)
- [八、重难点清单](#八重难点清单)
- [九、代价与撤退判定](#九代价与撤退判定)
- [十、用户视角：如何选择 / 排查](#十用户视角如何选择--排查)

---

## 一、定位与原则

### 1.1 项目定位（写入 README 与 PyPI 元数据）

> **A PySide6 component library inspired by HeroUI v2. Also compatible with PySide2 for DCC plugins (Maya/Houdini/Blender) and legacy Qt5 desktop apps.**

PySide6 是一等公民，PySide2 是 best-effort 兼容。

### 1.2 绑定优先级铁律（不可妥协）

> **PySide6 是一等公民，PySide2 是二等公民。当两者冲突时，永远优先保证 PySide6 体验，PySide2 接受合理降级。**

具体落地：

| 决策点          | 行为                                               |
| --------------- | -------------------------------------------------- |
| README 第一行   | 只写 PySide6 安装命令                              |
| dev extras 默认 | 拉 PySide6                                         |
| CI 失败语义     | PySide6 测试挂 = 阻塞 PR；PySide2 测试挂 = warning |
| 文档截图        | 全部用 PySide6 渲染                                |
| 视觉回归基线    | PySide6 是 ground truth，PySide2 向它对齐          |
| issue 优先级    | PySide6-only bug = P0；PySide2-only bug = P2       |
| 新功能开发顺序  | 先在 PySide6 上设计实现，再适配 PySide2            |
| Qt6 新 API      | 允许使用，PySide2 提供降级或 best-effort 替代      |

### 1.3 PySide2 破产线（明确退出条件）

满足任一条件即可正式降级 PySide2 支持（标记 Deprecated → 一年缓冲期 → 下个 major 移除）：

- PySide2 官方停止 bug 修复（已基本如此）
- 主流 DCC 全部升级到 Qt6（Maya 2026+ / Houdini 21+ 是观察窗口）
- HeroSideUI issue 中明确使用 PySide2 的占比 < 5%

---

## 二、技术选型：为什么是 qtpy

### 2.1 三种候选策略对比

| 策略                       | 代码组织   | 首次成本 | 维护成本       | 用户体验                |
| -------------------------- | ---------- | -------- | -------------- | ----------------------- |
| **A. qtpy 兼容层（采用）** | 单分支单源 | 8–10 天  | 低             | `pip install` 选 extras |
| B. 多分支隔离（zhiyiYo）   | 3 分支并行 | 5 天     | 高（每次同步） | clone 对应分支          |
| C. 完全切到 PySide2        | 单分支     | 5 天     | 中             | 失去 Qt6 优势           |

**选 A 的核心理由**：

- 项目仅需 PySide6 + PySide2 双覆盖，不碰 PyQt 系（无 GPL 协议障碍）
- 当前规模（17 个组件）适合单源，未来还要新增 ~15 个组件，单源能省 50% 重复工时
- 单人维护，心智压缩比代码量重要

### 2.2 qtpy 是什么

[qtpy](https://github.com/spyder-ide/qtpy) 是 Spyder/napari/QDarkStyle 等大型 Qt Python 项目使用的成熟兼容层：

- 启动期检测环境，自动绑定 PySide6 / PySide2 / PyQt6 / PyQt5 之一
- 提供 `qtpy.QtCore` / `qtpy.QtGui` / `qtpy.QtWidgets` 统一命名空间
- **不补齐 Qt6 强类型枚举** —— 这是优势：强迫使用 Qt5 风格扁平枚举（两边都成立）

### 2.3 为什么不学 zhiyiYo 走多分支

参考 [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 的 `master/PyQt5/PyQt6/PySide2/PySide6` 5 分支结构。它适合 zhiyiYo 的原因：

1. 项目 2021 年启动，当时 qtpy 不成熟
2. 重度依赖 Win32 DWM/acrylic 这种**结构性**平台 API，无法用枚举映射抹平
3. 同时支持 PyQt 系（GPL）+ PySide 系（LGPL），差异远不止枚举

**HeroSideUI 三条都不占**，所以走单源更优。

---

## 三、整体路线图

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1：qtpy 接入 + 枚举扁平化         │  1–2 天          │
│    └ 工作分支 feature/qtpy-migration                        │
│    └ 验收：PySide6 100% 等价，所有 import 走 qtpy           │
├─────────────────────────────────────────────────────────────┤
│  Phase 2：装载 PySide2，烟囱测试         │  0.5 天          │
│    └ 验收：PySide2 venv 能起窗、不崩、tests 全绿            │
├─────────────────────────────────────────────────────────────┤
│  Phase 3：像素级视觉回归（核心难点）      │  5–7 天         │
│    └ 工具：tools/visual_regression/                         │
│    └ 验收：13 个高风险 paintEvent diff ≤ 阈值               │
├─────────────────────────────────────────────────────────────┤
│  Phase 4：CI 矩阵 + 文档 + 发布           │  1–2 天         │
│    └ 验收：双绑定矩阵 CI 绿、PyPI 双 extras 可装            │
└─────────────────────────────────────────────────────────────┘
合计 7.5–11.5 天
```

**分支策略**：所有迁移在 `feature/qtpy-migration` 上完成，验收通过后一次性合回 `main`。`main` 保持纯 PySide6 直到 Phase 3 通过——这是逃生通道，撞墙时损失只有迁移投入。

---

## 四、Phase 1 — qtpy 接入与枚举扁平化

**目标**：项目源码完全走 qtpy 抽象，但仍以 PySide6 为默认运行后端，**视觉与功能 100% 等价**于迁移前。

### 4.1 改 `pyproject.toml`

```toml
[project]
name = "herosideui"
description = "A PySide6 component library inspired by HeroUI v2. Also compatible with PySide2 for DCC plugins."
requires-python = ">=3.8,<3.14"
dependencies = [
  "qtpy>=2.4,<3",
]

[project.optional-dependencies]
pyside6 = ["PySide6>=6.5"]                       # ★ 推荐
pyside2 = ["PySide2>=5.15.2"]                    # 兼容支持
dev = ["pytest>=7", "pytest-qt>=4", "PySide6>=6.5"]
```

**关键**：核心包不硬依赖任何 Qt 绑定（只依赖 qtpy）。例如 Maya/Houdini 用户在自带 PySide2 的环境里 `pip install herosideui` 不会污染 DCC Python。

### 4.2 import 替换脚本（一次性）

新建 `scripts/migrate_to_qtpy.py`（合并完成后从仓库删除）：

```python
import re
from pathlib import Path

REPLACEMENTS = [
    (r"from PySide6\.",   "from qtpy."),
    (r"import PySide6\.", "import qtpy."),
]

ROOT = Path("hero_side_ui")
for py in ROOT.rglob("*.py"):
    txt = py.read_text(encoding="utf-8")
    new = txt
    for pat, rep in REPLACEMENTS:
        new = re.sub(pat, rep, new)
    if new != txt:
        py.write_text(new, encoding="utf-8")
        print(f"updated: {py}")
```

### 4.3 枚举扁平化脚本（一次性）

新建 `scripts/flatten_enums.py`（合并完成后删除）：

```python
import re
from pathlib import Path

# 按出现频率从高到低排序（命中数据见迁移调研）
RULES = [
    (r"Qt\.WidgetAttribute\.",         "Qt."),    # 46 处
    (r"QEasingCurve\.Type\.",          "QEasingCurve."),  # 34 处
    (r"Qt\.AlignmentFlag\.",           "Qt."),    # 25 处
    (r"QPainter\.RenderHint\.",        "QPainter."),  # 21 处
    (r"QEvent\.Type\.",                "QEvent."),  # 20 处
    (r"Qt\.CursorShape\.",             "Qt."),    # 12 处
    (r"QPalette\.ColorRole\.",         "QPalette."),  # 9 处
    (r"QFont\.Weight\.",               "QFont."),  # 7 处
    (r"Qt\.WindowType\.",              "Qt."),    # 6 处
    (r"QFrame\.Shape\.",               "QFrame."),  # 5 处之一
    (r"QFrame\.Shadow\.",              "QFrame."),  # 5 处之二
    (r"Qt\.MouseButton\.",             "Qt."),    # 3 处
    (r"Qt\.FocusPolicy\.",             "Qt."),    # 3 处
    (r"QPainter\.CompositionMode\.",   "QPainter."),
    (r"Qt\.KeyboardModifier\.",        "Qt."),
    (r"QPalette\.ColorGroup\.",        "QPalette."),
    (r"QFont\.StyleHint\.",            "QFont."),
    (r"QSizePolicy\.Policy\.",         "QSizePolicy."),
    (r"QLineEdit\.EchoMode\.",         "QLineEdit."),
]

ROOT = Path("hero_side_ui")
for py in ROOT.rglob("*.py"):
    txt = py.read_text(encoding="utf-8")
    new = txt
    for pat, rep in RULES:
        new = re.sub(pat, rep, new)
    if new != txt:
        py.write_text(new, encoding="utf-8")
        print(f"updated: {py}")
```

跑完一次性处理 **191 处枚举**，分布在 25 个文件。

### 4.4 lint 防回退（长期）

新建 `scripts/lint_qt_compat.py`，纳入 pre-commit：

```python
import re
import sys
from pathlib import Path

FORBIDDEN = [
    (r"from PySide[26]\.",        "请使用 from qtpy.* 而不是直接 import PySide6/PySide2"),
    (r"import PySide[26]\.",      "请使用 import qtpy.* 而不是直接 import PySide6/PySide2"),
    (r"\.AlignmentFlag\.",        "请使用扁平枚举 Qt.AlignCenter，不要写 Qt.AlignmentFlag.AlignCenter"),
    (r"\.CursorShape\.",          "请使用扁平枚举 Qt.PointingHandCursor"),
    (r"\.WidgetAttribute\.",      "请使用扁平枚举 Qt.WA_*"),
    (r"\.WindowType\.",           "请使用扁平枚举 Qt.FramelessWindowHint 等"),
    (r"\.MouseButton\.",          "请使用扁平枚举 Qt.LeftButton 等"),
    (r"\.FocusPolicy\.",          "请使用扁平枚举 Qt.StrongFocus 等"),
    (r"QEvent\.Type\.",           "请使用扁平枚举 QEvent.MouseButtonPress 等"),
    (r"QPainter\.RenderHint\.",   "请使用扁平枚举 QPainter.Antialiasing 等"),
    (r"QEasingCurve\.Type\.",     "请使用扁平枚举 QEasingCurve.OutCubic 等"),
    (r"QPalette\.ColorRole\.",    "请使用扁平枚举 QPalette.Window 等"),
    (r"QFont\.Weight\.",          "请使用扁平枚举 QFont.Bold 等"),
    (r"QFrame\.Shape\.",          "请使用扁平枚举 QFrame.HLine 等"),
    (r"QFrame\.Shadow\.",         "请使用扁平枚举 QFrame.Plain 等"),
]

failed = False
for py in Path("hero_side_ui").rglob("*.py"):
    text = py.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), 1):
        for pat, msg in FORBIDDEN:
            if re.search(pat, line):
                print(f"{py}:{line_no}: {msg}\n    {line.strip()}")
                failed = True

sys.exit(1 if failed else 0)
```

`.pre-commit-config.yaml` 增加：

```yaml
- repo: local
  hooks:
    - id: lint-qt-compat
      name: lint Qt compat (qtpy + flat enums)
      entry: python scripts/lint_qt_compat.py
      language: system
      pass_filenames: false
      files: ^hero_side_ui/.*\.py$
```

### 4.5 引入 `hero_side_ui.qt_info()` 排查 API

在 `hero_side_ui/__init__.py` 增加：

```python
from qtpy import API_NAME, QT_VERSION, PYSIDE_VERSION, PYQT_VERSION

def qt_info() -> dict:
    """返回当前运行时 Qt 绑定信息，方便用户排查问题。"""
    info = {
        "binding": API_NAME,
        "qt_version": QT_VERSION,
        "pyside_version": PYSIDE_VERSION,
        "pyqt_version": PYQT_VERSION,
        "herosideui_version": __version__,
    }
    if API_NAME == "PySide2":
        info["notice"] = (
            "Running on PySide2 (best-effort compatibility). "
            "For best visual fidelity, consider PySide6."
        )
    return info

__all__ = [..., "qt_info"]
```

### 4.6 友好的"未装绑定"错误

`hero_side_ui/__init__.py` 顶部：

```python
try:
    from qtpy import API_NAME  # noqa: F401
except Exception as e:
    raise RuntimeError(
        "HeroSideUI 需要一个 Qt 绑定，但当前环境未安装。\n"
        "请二选一安装：\n"
        "    pip install herosideui[pyside6]    # 推荐\n"
        "    pip install herosideui[pyside2]    # DCC/Qt5 场景\n"
        "或在已有 Qt 绑定的环境（如 Maya/Houdini）中直接使用 herosideui。"
    ) from e
```

### 4.7 Phase 1 验收清单

- [ ] `pip install -e .[pyside6]` 后 `pytest tests/` 全绿
- [ ] 所有 examples 视觉**与迁移前完全一致**（基线截图作为 Phase 3 ground truth）
- [ ] `grep -r "from PySide6" hero_side_ui/` → 0 命中
- [ ] `grep -r "from PySide2" hero_side_ui/` → 0 命中
- [ ] `grep -rE "\.(AlignmentFlag|RenderHint|ColorRole|WidgetAttribute|EchoMode)\." hero_side_ui/` → 0 命中
- [ ] pre-commit 装上后 commit 一次能拦下故意写错的 import
- [ ] `hero_side_ui.qt_info()` 返回正确信息

> ⚠ **不可妥协的硬约束**：Phase 1 完成后 PySide6 路径必须 100% 等价，任何视觉退化都要在进入 Phase 2 前修掉。

---

## 五、Phase 2 — PySide2 装载与烟囱测试

**目标**：让 PySide2 venv 能装上、能起窗、不崩。**先不看像素**。

### 5.1 准备 PySide2 环境

```bash
# 单独 venv，避免污染 PySide6 venv
python3.10 -m venv .venv-pyside2
source .venv-pyside2/bin/activate          # win: .venv-pyside2\Scripts\activate
pip install -e .[pyside2,dev]
```

注意：PySide2 官方 wheel 仅支持 Python 3.5–3.10。**Python 3.11+ 必须用 PySide6**。

### 5.2 强制选择后端

```bash
# 强制 qtpy 使用 PySide2，避免歧义
export QT_API=pyside2          # win: set QT_API=pyside2
```

### 5.3 烟囱测试

```bash
# 1. 库加载
python -c "import hero_side_ui; print(hero_side_ui.qt_info())"

# 期望输出包含 "binding": "PySide2"

# 2. 起窗
python examples/button/demo.py
python examples/theme_toggle/demo.py

# 3. 单元测试
pytest tests/ -v
```

### 5.4 预期会爆的点（已知坑）

| 现象                                                          | 原因                                              | 修法                        |
| ------------------------------------------------------------- | ------------------------------------------------- | --------------------------- |
| `tests/conftest.py` 的 `sendPostedEvents(None, 0)` 报参数错误 | Qt5 签名略不同                                    | conftest 加 try/except 兼容 |
| 某 SVG 图标不显示                                             | PySide2 的 QSvg 依赖 `pyside2-tools` 单独装       | 安装文档里说明              |
| 字体加载失败                                                  | `QFontDatabase.addApplicationFont` Qt5 是实例方法 | 改用 qtpy 提供的兼容写法    |
| 启动时报 `QApplication: invalid style override`               | 主题字符串大小写差异                              | 统一小写                    |

### 5.5 Phase 2 验收清单

- [ ] PySide2 venv 下 `python -c "import hero_side_ui"` 不报错
- [ ] 至少 5 个 example 能起窗运行（先不看视觉）
- [ ] `pytest tests/` 在 PySide2 venv 下通过率 ≥ 95%（个别动画测试可能需要 Phase 3 修）
- [ ] `qt_info()` 正确返回 `PySide2` + Qt 5.15.x

---

## 六、Phase 3 — 像素级视觉回归（核心难点）

**目标**：13 个高风险 paintEvent 在 PySide6 / PySide2 下视觉差异 ≤ 阈值。

> ⚠ **这是整个迁移最贵的阶段**，预算 5–7 天。如果工时不够，只能放弃像素级对齐目标，回退到"视觉等价即可"。

### 6.1 高风险点全名单

按风险等级分级。每个组件都需要逐 example 截图比对。

#### 第 1 级 — 渲染最敏感（必测）

| 文件                     | 类/方法                              | 风险点                         | 预期适配                 |
| ------------------------ | ------------------------------------ | ------------------------------ | ------------------------ |
| `components/card.py`     | `Card.paintEvent`                    | 4–15 层 alpha 递减阴影叠加     | 阴影层数与权重按绑定切换 |
| `components/tabs.py`     | `_CursorWidget.paintEvent`           | 光标宽度依赖 QFontMetrics      | 字体度量统一抽象         |
| `components/progress.py` | `_ProgressBar` / `_CircularProgress` | 圆角 clip + drawArc 1/16° 精度 | 浮点坐标贯穿到底         |
| `components/checkbox.py` | `_CheckBox.paintEvent`               | 按压缩放坐标变换嵌套           | QRectF 全程浮点          |
| `components/popover.py`  | `Popover.paintEvent`                 | 背景 + 箭头 polygon + 多层阴影 | 同 Card                  |

#### 第 2 级 — 路径绘制（重点测）

| 文件                              | 类/方法                                            |
| --------------------------------- | -------------------------------------------------- |
| `animation/ripple.py`             | `RippleOverlay.paintEvent` — QPainterPath 圆角裁剪 |
| `components/scroll_shadow.py`     | `_ShadowOverlay.paintEvent` — QLinearGradient      |
| `components/tooltip.py`           | `Tooltip.paintEvent`                               |
| `animation/check_draw.py`         | `paint_animated_check` — RoundCap/RoundJoin        |
| `animation/pixmap_scale_proxy.py` | `_ScaleEffect.draw` — pixmap 缩放                  |

#### 第 3 级 — 辅助验证（目测）

`divider.py` / `input.py` / `switch.py` / `accordion.py` / `animation/underline_expand.py`

### 6.2 视觉回归工具

新建 `tools/visual_regression/`：

```
tools/visual_regression/
├── snapshot.py         # 对一个 example 跑 QWidget.grab() 存 PNG
├── compare.py          # PIL 逐像素 diff，输出热力图 + 数值
├── run_all.py          # 对 examples/ 全跑一遍
└── baselines/
    └── pyside6/        # PySide6 基线（在 Phase 1 验收后建立）
        ├── button.png
        ├── card.png
        └── ...
```

**关键设计**：

- 用 `widget.grab()` 而非系统截图，避开窗口装饰 / DPI 干扰
- 阈值：`max_pixel_diff ≤ 3`、`diff_ratio ≤ 0.5%` 视为通过
- 基线只保存 PySide6（ground truth），PySide2 截图实时生成对比

### 6.3 字体度量统一抽象

新建 `hero_side_ui/utils/text_metrics.py`：

```python
from qtpy.QtGui import QFont, QFontMetrics, QFontMetricsF

def text_advance(font: QFont, text: str) -> float:
    """光学一致的文本宽度。所有组件统一调用，避免 Qt5/Qt6 度量偏差。"""
    fm = QFontMetricsF(font)
    return fm.boundingRect(text).width()

def cap_height(font: QFont) -> float:
    """大写字母光学高度，用于垂直居中。"""
    fm = QFontMetricsF(font)
    return fm.capHeight()
```

把 `tabs.py` / `checkbox.py` / `text.py` 中所有直接 `QFontMetrics(...)` 改成调用这两个函数。

### 6.4 Qt 兼容层（差异封装）

新建 `hero_side_ui/utils/qt_compat.py`：

```python
from qtpy import API_NAME

IS_PYSIDE6 = API_NAME == "PySide6"
IS_PYSIDE2 = API_NAME == "PySide2"

def shadow_layers(blur: int) -> int:
    """阴影层数。PySide6 多一些更细腻，PySide2 少一些避免渲染压力。"""
    base = max(4, blur // 2)
    return base if IS_PYSIDE6 else max(6, base)

def shadow_alpha_curve(layers: int, i: int, max_alpha: float) -> float:
    """阴影 alpha 递减。两边采用不同公式以达到视觉等价。"""
    if IS_PYSIDE6:
        return max_alpha * (layers - i + 1) / (layers * layers)
    # PySide2 抗锯齿混合略不同，需要稍微提高 alpha
    return max_alpha * (layers - i + 1) / (layers * layers) * 1.15
```

> **铁律 6 — 双绑定零分支**：组件源码不允许出现 `if API_NAME == ...` 这类裸判断。所有绑定差异封装在 `utils/qt_compat.py` 等专用模块里。

### 6.5 Phase 3 验收清单

- [ ] `tools/visual_regression/run_all.py` 在 macOS 上跑通
- [ ] 第 1 级 5 个文件全部 diff ≤ 阈值
- [ ] 第 2 级 5 个文件全部 diff ≤ 阈值
- [ ] 第 3 级 5 个文件目测一致
- [ ] `tabs/login_signup.py` 完整登录页双绑定截图肉眼无法分辨

---

## 七、Phase 4 — CI、发布与文档

### 7.1 CI 矩阵扩展

`.github/workflows/ci.yml` 增加 PySide2 job：

```yaml
jobs:
  test-pyside6:
    name: Test (PySide6)
    runs-on: macos-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    # 失败 → 阻塞 PR
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra pyside6 --extra dev
      - run: uv run pytest tests/ -v

  test-pyside2:
    name: Test (PySide2, best-effort)
    runs-on: macos-latest
    continue-on-error: true # ★ 失败 → warning，不阻塞
    strategy:
      matrix:
        python-version: ["3.10"] # PySide2 仅 Python 3.10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra pyside2 --extra dev
      - env:
          QT_API: pyside2
        run: uv run pytest tests/ -v

  visual-regression:
    name: Visual Regression
    runs-on: macos-latest
    needs: [test-pyside6, test-pyside2]
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - run: uv run python tools/visual_regression/run_all.py
      - uses: actions/upload-artifact@v4
        with:
          name: visual-diff-report
          path: tools/visual_regression/reports/
```

### 7.2 发布

`publish.yml` 不动。一个 wheel `herosideui-X.Y.Z-py3-none-any.whl` 通吃，用户通过 extras 选绑定。

### 7.3 文档

- `README.md`：第一行改成"A PySide6 component library... Also compatible with PySide2..."；安装段落给两套命令；底部加"PySide2 兼容性说明"链接到本文
- `docs/migration.md`（本文）
- `docs/qt-binding-selection.md`（新增，500 行内）：写给用户的"选哪个 extras / `QT_API` 怎么用 / 怎么排查问题"
- `MEMORY.md`：把"绑定优先级铁律"和"双绑定零分支铁律 6"写进项目长期记忆

### 7.4 Phase 4 验收清单

- [ ] PR 打到 main 时 PySide6 矩阵全绿、PySide2 矩阵 warning 也无所谓
- [ ] `pip install herosideui[pyside6]` 在干净 venv 装得上
- [ ] `pip install herosideui[pyside2]` 在 Python 3.10 干净 venv 装得上
- [ ] `pip install herosideui` 不装绑定 → import 时给出友好错误指引

---

## 八、重难点清单

按"踩坑概率 × 修复成本"排序，前 3 条是真正吃工时的地方。

### 难点 1（最大）：像素级视觉对齐

**原因**：Qt5 的抗锯齿混合、字体光栅化、子像素定位与 Qt6 不完全一致，多层阴影叠加时差异会放大到肉眼可见。

**应对**：

- `utils/qt_compat.py` 把阴影层数、alpha 曲线按绑定隔离
- `utils/text_metrics.py` 统一字体度量入口，避免 `horizontalAdvance` vs `boundingRect().width()` 行为差
- 自动化截图回归 + 人工验收，两道关
- **预算 5–7 天，是单一最耗时的阶段**

### 难点 2：Qt6 强类型枚举与扁平枚举的认知切换

**原因**：扁平枚举（`Qt.AlignCenter`）失去 IDE 自动补全的命名空间引导，开发者要"记住"哪个常量在哪个类里。

**应对**：

- 一次性脚本扁平化所有现有代码（4.3）
- pre-commit lint 拦截回退（4.4）
- 团队 README 加"扁平枚举速查表"（常用 30 个）

### 难点 3：tests/conftest.py 的 Qt5/Qt6 兼容

**原因**：当前 conftest 用 `sendPostedEvents(None, 0)` 这类 API 清理 Qt 状态，PySide2 行为微调。

**应对**：

- conftest 加 `try/except`，兼容写法
- 关键 fixture 加 `@pytest.mark.skipif(API_NAME == "PySide2", reason="...")` 兜底个别测试

### 难点 4：DCC 内嵌 Python 与 pip extras 冲突

**原因**：Maya/Houdini 自带 PySide2，用户 `pip install herosideui[pyside2]` 可能让 pip 在 DCC Python 里再装一份 PySide2，覆盖原生版本。

**应对**：

- 文档单独写"DCC 用户安装指南"：推荐 `pip install herosideui --no-deps && pip install qtpy`，由 DCC 提供 PySide2
- `qt_info()` 输出能让用户看到当前用的是不是 DCC 自带版本

### 难点 5：字体加载差异

**原因**：`QFontDatabase` 在 Qt5 是实例方法（`QFontDatabase().addApplicationFont(path)`），Qt6 是静态方法。

**应对**：

- 当前项目代码扫描结果显示 **没有使用 QFontDatabase**，无影响
- 未来引入字体时直接用 qtpy 推荐的 idiom

### 难点 6：HiDPI 适配差异

**原因**：Qt6 默认开启高 DPI 缩放，Qt5 需要在 `QApplication` 创建前手动开 `AA_EnableHighDpiScaling`。

**应对**：

- 这是用户的 `main()` 责任，不是组件库责任
- 在 `docs/qt-binding-selection.md` 加 "PySide2 用户的高 DPI 启动样板"

### 难点 7：动画曲线在两边的视觉差异

**原因**：`QEasingCurve` 内部精度可能略不同，长动画（>500ms）累积差异肉眼可辨。

**应对**：

- Phase 3 视觉回归覆盖动画关键帧（首帧 / 50% / 末帧）
- 必要时在 `utils/qt_compat.py` 提供"等效曲线"（如 PySide2 用 `OutCubic` 替换 PySide6 的某些曲线）

---

## 九、代价与撤退判定

### 9.1 走 qtpy 路线必须接受的 7 个代价

| #   | 代价                      | 缓解                                   |
| --- | ------------------------- | -------------------------------------- |
| 1   | 首次迁移 8–10 天          | 分阶段验收，逐 phase 锁定              |
| 2   | 调试堆栈多一层 qtpy       | 用 `qt_info()` 快速定位                |
| 3   | IDE 强类型枚举体验下降    | 速查表 + 习惯                          |
| 4   | Qt6 新 API 受限或要写降级 | qt_compat 封装                         |
| 5   | 视觉漂移可能在长期发生    | CI 视觉回归 + 周抽查                   |
| 6   | Qt6 新特性自我审查        | 在 PySide6 上放飞，PySide2 best-effort |
| 7   | qtpy 依赖锁版本           | `qtpy>=2.4,<3`                         |

### 9.2 撤退判定（破产线）

任一触发即承认决策错误，撤回到双分支或纯 PySide6：

1. **Phase 3 单个组件需要 ≥ 50 行 `if IS_PYSIDE2` 分叉代码** → qtpy 单源破产
2. **CI 视觉回归连续 3 周拦截 5+ 个 PR** → 维护成本超过收益
3. **PySide2 用户占比 < 5%（issue 标签统计）** → 直接弃疗 PySide2，回到纯 PySide6
4. **qtpy 出 3.x 破坏性升级且无人维护** → fork 或撤回双分支

撤退路径：

- 撤到双分支：从 main 拉 `pyside2` 分支，反向跑迁移脚本（qtpy → PySide2）
- 撤到纯 PySide6：删 PySide2 extras，更新 README，下个 minor 版本生效

---

## 十、用户视角：如何选择 / 排查

### 10.1 安装

```bash
# 推荐路径（90% 用户）
pip install herosideui[pyside6]

# DCC 插件 / 老 Qt5 桌面应用
pip install herosideui[pyside2]

# DCC 内嵌 Python（环境已自带 PySide2）
pip install herosideui --no-deps
pip install qtpy
```

### 10.2 强制后端选择

`qtpy` 按以下优先级选后端：

1. 环境变量 `QT_API`（最高优先级，可选 `pyside6` / `pyside2` / `pyqt6` / `pyqt5`）
2. 已 import 的 Qt 绑定
3. 已安装的绑定（自动探测）

```python
import os
os.environ["QT_API"] = "pyside2"  # 必须写在 import herosideui 之前
import hero_side_ui
```

### 10.3 排查问题

```python
import hero_side_ui
print(hero_side_ui.qt_info())
# {
#     "binding": "PySide6",
#     "qt_version": "6.5.3",
#     "pyside_version": "6.5.3",
#     "pyqt_version": None,
#     "herosideui_version": "0.1.0",
# }
```

提 issue 时贴这段输出即可。

### 10.4 视觉差异说明

PySide6 是视觉 ground truth。PySide2 渲染与 PySide6 在以下方面可能存在 ≤ 3px 的差异：

- 阴影边缘锯齿
- 字体度量（个别字体差 1px）
- 圆弧抗锯齿混合

如果用户看到与文档截图明显不一致，请用 `qt_info()` 确认后端，并附在 issue 里。

---

## 附录 A：迁移调研数据

来源：`feature/qtpy-migration` 分支启动前的全量代码扫描。

| 维度                  | 数据                         |
| --------------------- | ---------------------------- |
| 总文件数              | 54                           |
| 总代码行数            | ~16,300                      |
| Qt6 强类型枚举命中    | 191 处 / 25 文件             |
| paintEvent 重写       | 24 处 / 13 文件 + 2 动画模块 |
| QPainter 实例化       | 37 处                        |
| QPainterPath 使用     | 26 处                        |
| QFontMetrics 使用     | 16 处（Tabs 最敏感）         |
| setStyleSheet 调用    | 100+ 处（无 Qt6-only 伪类）  |
| `from PySide6` import | 全量需替换                   |

风险评估高/中/低：

- **高**：Card 阴影、Tabs 光标对齐、Checkbox 缩放叠加、Popover 箭头
- **中**：Ripple/ScrollShadow 渐变、Tooltip 箭头、CheckDraw 路径
- **低**：Divider/Input/Switch/Accordion/UnderlineExpand

## 附录 B：关键文件清单

```
hero_side_ui/                              # 全量 qtpy 化
├── core/theme_provider.py                 # QPalette.ColorRole 等
├── components/
│   ├── tabs.py                            # 字体度量适配（最敏感）
│   ├── card.py                            # 阴影公式适配
│   ├── progress.py                        # 圆弧精度适配
│   ├── checkbox.py                        # 坐标变换适配
│   ├── popover.py                         # polygon + 阴影
│   └── ...（其余 11 个组件）
├── animation/                             # 全部枚举扁平化
└── utils/
    ├── text_metrics.py                    # ★ 新：字体度量统一抽象
    └── qt_compat.py                       # ★ 新：绑定差异封装

scripts/
├── migrate_to_qtpy.py                     # 一次性，跑完即删
├── flatten_enums.py                       # 一次性，跑完即删
└── lint_qt_compat.py                      # 长期，pre-commit 用

tools/visual_regression/                   # ★ 新：截图回归套件
├── snapshot.py
├── compare.py
├── run_all.py
└── baselines/pyside6/

pyproject.toml                             # extras + Python 范围
.github/workflows/ci.yml                   # 双绑定矩阵
.pre-commit-config.yaml                    # 加 lint hook
docs/
├── migration.md                           # 本文
└── qt-binding-selection.md                # 用户选择指南
README.md                                  # 改 + 加 PySide2 兼容性段
MEMORY.md                                  # 加 2 条铁律
```
