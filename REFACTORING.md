# HeroSideUI 重构 RFC：组件目录结构与代码体积治理

> 状态：**Phase 1 + Phase 2 + Phase 2-5 已完成（780 测试零回归，无文件 > 800 行）** · 起草 2026-05-13 · 作者：jerrylu + Claude
> 目标版本：0.1.0（alpha 收尾 → beta 准备）
> 影响面：内部代码结构，**公共 API 完全兼容**（`from hero_side_ui import X` 不变）
> 实施记录：见章节 11（Phase 1）/ 章节 12（Phase 2）/ 章节 13（Phase 2-5）

---

## 1. 问题陈述

### 1.1 现状数据

`hero_side_ui/components/` 共 18 个组件，按行数排序：

| 组件                |     行数 | 复杂度信号                                                            |
| ------------------- | -------: | --------------------------------------------------------------------- |
| **listbox.py**      | **1758** | 13 个 module-level 函数 + 3 个 class，颜色计算/状态机/渲染全在一处    |
| **textarea.py**     | **1566** | 内含 `_TextEdit`、`_ResizeGrip`、`Textarea` 三个 class                |
| **input.py**        | **1439** | 内含 `_LineEdit`、`_ClearButton`、`_InputWrapper`、`Input` 四个 class |
| **tabs.py**         | **1344** | 主组件 + TabItem + \_TabList + \_CursorWidget + 动画驱动              |
| **popover.py**      | **1250** | 弹层定位 + 主体 + 内容容器 + backdrop                                 |
| **autocomplete.py** | **1108** | Input + Popover + Listbox 组合，重抄了大量 listbox 逻辑               |
| checkbox.py         |      922 |                                                                       |
| progress.py         |      874 |                                                                       |
| tooltip.py          |      799 |                                                                       |
| card.py             |      709 |                                                                       |
| accordion.py        |      654 |                                                                       |
| scroll_shadow.py    |      626 |                                                                       |
| switch.py           |      567 |                                                                       |
| button.py           |      559 |                                                                       |
| theme_switcher.py   |      225 |                                                                       |
| divider.py          |      305 |                                                                       |
| text.py             |      178 |                                                                       |

**Top 6 巨头平均 1411 行**，最大的 listbox 1758 行；其余 12 个组件平均 562 行，符合健康区间。

### 1.2 三个真实成本

1. **贡献者门槛**。开源库的外部 PR 多数是 "改 hover 颜色 / 修一个键位 / 多加一个 prop"。要求贡献者翻 1758 行才能定位到正确入口，会直接吓走 90% 的潜在贡献。
2. **AI 协作 token 成本**。每次修 listbox/textarea/input 都要把整个文件塞进上下文，理解和修改成本随文件长度非线性增长。Autocomplete 阶段已经感受到明显压力。
3. **复用反模式**。Autocomplete 1108 行里相当一部分是 listbox 的"重抄"——同样的 selection state、键盘导航、hover 颜色推导，被复制了一份。这是 1k+ 单文件直接导致的结果：横切关注点没有出口，只能拷贝。

### 1.3 用户的额外约束（强迫症友好）

> "单文件的话 components 根目录就会出现一下 py 一下文件夹的，我有强迫症。"

这条约束**否决了"只把巨头拆成文件夹，小组件保持单文件"**的混合方案。RFC 必须给出**视觉一致**的目录结构。

---

## 2. 设计原则

1. **公共 API 零变动**。`from hero_side_ui import Button, Listbox, Autocomplete` 全部保留，外部用户感知不到重构。
2. **不为了拆而拆**。每一次拆分都必须有"复用"或"职责正交"的硬理由，否则保持原状。比 1700 行更糟的是 8 个 200 行小文件循环引用。
3. **视觉一致 > 局部最优**。`components/` 下所有子项保持**同一形态**（要么全文件夹，要么全文件）。
4. **横向抽取优先于纵向拆分**。把跨组件重复的逻辑提到 `core/` `utils/` `animation/`，比把单个组件文件拆小**更有结构红利**。横向抽取做完后，巨头组件往往会自然瘦身到合理区间，不需要硬拆。
5. **铁律不动**。重构必须不破坏 5 条铁律，尤其是"开箱即用"（铁律 5）和"组件自治主题"（铁律 1）。

---

## 3. 方案对比

### 方案 A：保持现状 + 内部用 region 分块

**做法**：所有组件保持单文件，用注释块（`# region xxx / # endregion`）分隔。

- ✅ 零迁移成本
- ❌ 1700 行还是 1700 行，AI/贡献者成本无改善
- ❌ Autocomplete 的"重抄 listbox"问题不解决

**结论**：不采纳。

### 方案 B：每个组件都拆成包（统一文件夹）

**做法**：`components/listbox.py` → `components/listbox/{__init__.py, listbox.py, item.py, ...}`，所有 18 个组件统一拆。

- ✅ 视觉一致（强迫症友好）
- ✅ 给巨头组件提供拆分空间
- ❌ Button/Divider/Text 这种 200-500 行的组件被强行拆开会变成"为拆而拆"
- ❌ `__init__.py` 变成单纯的 re-export 文件，新增 18 个

**结论**：方向对，但需要解决"小组件别强拆"的问题。

### 方案 C（采纳）：**横向抽取为主 + 全员包结构 + 小组件单文件包**

**两步走**：

**Step 1（核心收益）：横向抽取共用逻辑到 `core/` `utils/` `animation/`**

把跨组件的横切关注点提到公共层，**直接砍掉巨头 30-40% 体积**。

**Step 2（结构统一）：所有组件统一改为包结构，但允许"单文件包"**

```
components/
├── button/
│   ├── __init__.py          # re-export Button
│   └── button.py            # 主实现（保持单文件，~500 行）
├── listbox/
│   ├── __init__.py          # re-export Listbox, ListboxItem, ListboxSection
│   ├── listbox.py           # 主组件
│   ├── item.py              # ListboxItem
│   ├── section.py           # ListboxSection
│   └── _palette.py          # 颜色推导函数（13 个 _bg_role_color 之类的）
└── ...
```

视觉上 `components/` 全部是文件夹，强迫症满足。小组件如 Button/Divider 内部就 `button.py` 一个文件，但**外形和巨头一致**。

- ✅ 视觉一致
- ✅ 巨头有拆分空间
- ✅ 小组件不被强行肢解（包里就一个 py 文件）
- ✅ 公共 API 零变动（`__init__.py` 内 re-export 不变）
- ⚠️ 每个组件多一个 `__init__.py`（成本可接受）

---

## 4. Step 1：横向抽取清单（核心红利）

> 这一步**不动任何组件的对外文件路径**，只是把组件内部的重复代码提到公共层。
> 预计 listbox 1758 → ~1100，textarea/input 类似比例瘦身。

### 4.1 新增 `core/state_palette.py`（最大头）

抽取 listbox.py 顶部那 13 个 `_bg_role_color / _hover_bg / _hover_border / _text_default / _text_hover / _desc_color / _selected_indicator_color / ...` 函数。

它们的本质是：**"给定 variant + color + theme + state，返回应该用什么颜色"** 的查找表。这套逻辑在 button / checkbox / autocomplete / tabs 里都各自重新写了一遍。

```python
# core/state_palette.py
class StatePalette:
    @staticmethod
    def bg(variant: str, color: str, theme: str, state: str) -> QColor: ...
    @staticmethod
    def border(variant: str, color: str, theme: str, state: str) -> QColor: ...
    @staticmethod
    def text(variant: str, color: str, theme: str, state: str) -> QColor: ...
```

**直接受益组件**：listbox / autocomplete / button / checkbox / switch / tabs（预计每个 -100~300 行）。

### 4.2 新增 `core/keyboard_nav.py`

抽取键盘导航逻辑：方向键移动光标、Home/End 跳首尾、字母键首字母跳转、Enter/Space 触发。

**直接受益**：listbox / autocomplete / tabs（每个 -50~150 行）。

### 4.3 新增 `core/selection_model.py`

抽取选择状态机：single / multiple / none 三种模式，selected_keys 维护，change 事件。

**直接受益**：listbox / autocomplete / checkbox-group / tabs（每个 -50~100 行）。

### 4.4 利用已有的 `animation/` 模块

`animation/` 目录已经做得不错（check_draw / tween / ripple / collapse / fade_scale），但 listbox 里的 hover 颜色补间、textarea 的 resize 动画**还在组件内手写**。把它们也搬过去。

**直接受益**：listbox / textarea / input / tabs（每个 -50~100 行）。

### 4.5 内部子组件抽取到 `_internal/`（评估中，可选）

`input.py` 内的 `_ClearButton`、`textarea.py` 内的 `_ResizeGrip` 这类**只服务于一个父组件的私有子组件**，保持在组件包内即可（见 Step 2），不必上移到全局。

### 4.6 预期收益（保守估计）

| 组件            | 当前 | Step 1 后 |                   削减 |
| --------------- | ---: | --------: | ---------------------: |
| listbox.py      | 1758 |     ~1050 |                   -40% |
| textarea.py     | 1566 |     ~1100 |                   -30% |
| input.py        | 1439 |     ~1000 |                   -30% |
| tabs.py         | 1344 |     ~1000 |                   -25% |
| autocomplete.py | 1108 |      ~700 | -37%（重抄部分被消除） |
| popover.py      | 1250 |     ~1100 |                   -12% |

**Step 1 完成后，没有任何组件超过 1100 行**——如果 Step 2 拆得不顺利，也是可以接受的中间态。

---

## 5. Step 2：目录结构统一为"包形态"

### 5.1 目标结构

```
hero_side_ui/
├── __init__.py                  # 顶层 re-export（已存在，不变）
├── core/
│   ├── theme_provider.py        # 已存在
│   ├── scroll_style.py          # 已存在
│   ├── smooth_scroll.py         # 已存在
│   ├── state_palette.py         # ✨ 新增
│   ├── keyboard_nav.py          # ✨ 新增
│   └── selection_model.py       # ✨ 新增
├── animation/                   # 已存在，继续扩充
├── themes/                      # 已存在
├── utils/                       # 已存在
└── components/
    ├── __init__.py              # re-export 不变
    ├── button/
    │   ├── __init__.py
    │   └── button.py
    ├── divider/
    │   ├── __init__.py
    │   └── divider.py
    ├── text/
    │   ├── __init__.py
    │   └── text.py              # Title/Subtitle/Caption/Body
    ├── theme_switcher/
    │   ├── __init__.py
    │   └── theme_switcher.py
    ├── switch/
    │   ├── __init__.py
    │   └── switch.py
    ├── accordion/
    │   ├── __init__.py
    │   ├── accordion.py         # 主组件
    │   └── item.py              # AccordionItem
    ├── card/
    │   ├── __init__.py
    │   └── card.py              # Card + Header/Body/Footer（保持单文件，<800 行）
    ├── checkbox/
    │   ├── __init__.py
    │   ├── checkbox.py
    │   └── group.py             # CheckboxGroup
    ├── progress/
    │   ├── __init__.py
    │   ├── progress.py          # Progress
    │   ├── circular.py          # CircularProgress
    │   └── spinner.py           # Spinner
    ├── tooltip/
    │   ├── __init__.py
    │   └── tooltip.py
    ├── scroll_shadow/
    │   ├── __init__.py
    │   └── scroll_shadow.py
    ├── input/
    │   ├── __init__.py
    │   ├── input.py             # Input（主组件 + 编排）
    │   ├── _line_edit.py        # 私有 _LineEdit
    │   ├── _clear_button.py     # 私有 _ClearButton
    │   └── _wrapper.py          # 私有 _InputWrapper
    ├── textarea/
    │   ├── __init__.py
    │   ├── textarea.py
    │   ├── _text_edit.py
    │   └── _resize_grip.py
    ├── tabs/
    │   ├── __init__.py
    │   ├── tabs.py              # Tabs 主组件
    │   ├── item.py              # TabItem
    │   ├── _tab_list.py         # _TabList
    │   └── _cursor.py           # _CursorWidget
    ├── popover/
    │   ├── __init__.py
    │   ├── popover.py
    │   ├── content.py           # PopoverContent
    │   └── _backdrop.py
    ├── listbox/
    │   ├── __init__.py
    │   ├── listbox.py
    │   ├── item.py              # ListboxItem
    │   └── section.py           # ListboxSection
    └── autocomplete/
        ├── __init__.py
        ├── autocomplete.py
        ├── item.py
        └── section.py
```

### 5.2 拆分原则（防止矫枉过正）

每个包**只有在满足以下任一条件时才拆出额外文件**：

1. 文件 > 800 行 且 存在独立子组件（如 `_ResizeGrip`、`TabItem`）
2. 子类型对外暴露（如 `ListboxItem` 是用户 API 的一部分）
3. 内部辅助类**真正独立**（不依赖父组件的 self.\*）

**不满足以上条件，就放在 `xxx.py` 主文件里**。Button/Divider/Switch/Tooltip 这类组件，包里就一个 py 文件，**这是有意为之**——视觉对齐 + 给未来留扩展位。

### 5.3 `__init__.py` 模板

每个组件包的 `__init__.py` 只做 re-export，**不写任何实现**：

```python
# components/listbox/__init__.py
from .listbox import Listbox
from .item import ListboxItem
from .section import ListboxSection

__all__ = ["Listbox", "ListboxItem", "ListboxSection"]
```

`components/__init__.py` 保持现在的写法不变（`from .listbox import Listbox, ...` 仍然能工作，因为子包的 `__init__.py` re-export 了）。

### 5.4 私有文件命名约定

- 对外暴露的子组件：`item.py` / `section.py` / `content.py`（无下划线前缀）
- 纯私有内部 widget：`_line_edit.py` / `_clear_button.py`（带下划线前缀）
- 调色板/工具函数：`_palette.py` / `_styles.py`

---

## 6. 测试与文档影响

### 6.1 测试

`tests/test_listbox.py` 等**完全不动**——它们 import 的是公共 API（`from hero_side_ui import Listbox`），路径不变。

新增 `core/state_palette.py` / `core/keyboard_nav.py` / `core/selection_model.py` 应配套单元测试：

- `tests/test_state_palette.py`
- `tests/test_keyboard_nav.py`
- `tests/test_selection_model.py`

### 6.2 文档

`docs/` 下每组件一份 md 路径不变。新增 `docs/state_palette.md` / `docs/keyboard_nav.md` / `docs/selection_model.md` 给贡献者参考（用户文档无需提及）。

### 6.3 examples

`examples/` 下所有 demo **完全不动**。

---

## 7. 落地节奏（强烈推荐分批，不要一次性大爆炸）

### Phase 0：准备（不动代码，~半天）

- [ ] 本 RFC 评审通过
- [ ] 当前 Autocomplete 收尾 + 合并到 main
- [ ] 跑一次完整测试 + 视觉回归基线，作为重构对照

### Phase 1：横向抽取（~2-3 天，零 API 破坏）

- [ ] 新增 `core/state_palette.py` + 单元测试
- [ ] 把 listbox 的颜色推导函数迁移过去 → 跑测试
- [ ] 把 button/checkbox/autocomplete 的颜色推导也迁过去 → 跑测试
- [ ] 新增 `core/keyboard_nav.py` → 迁 listbox/autocomplete/tabs → 跑测试
- [ ] 新增 `core/selection_model.py` → 迁 listbox/checkbox-group/tabs → 跑测试
- [ ] **检查点**：所有 plummet 之后没有组件 > 1100 行

> 这一步是**纯收益、零风险**的。即使 Phase 2 因故搁置，Phase 1 也能独立带来巨大价值。

### Phase 2：结构统一为包形态（~1-2 天）

- [ ] 从最简单的组件开始（button → divider → text → switch → tooltip → theme_switcher → scroll_shadow）：每个新建文件夹 + 移动主文件 + 加 `__init__.py` → 跑测试
- [ ] 中等组件（accordion → card → checkbox → progress）
- [ ] 巨头组件（input → textarea → popover → tabs → listbox → autocomplete），同时执行内部拆分

### Phase 3：清理与发布（~半天）

- [ ] 更新贡献者文档（CONTRIBUTING.md）说明新目录结构
- [ ] 检查所有 import 路径
- [ ] 验证 `pip install` 后能正常 import
- [ ] 打 tag 0.1.0-alpha

**总计**：约 4-6 天。**强烈不建议一次性 PR 合进去**——按 Phase 1 / Phase 2 / Phase 3 各开一个 PR，每次都能跑完整测试 + 视觉回归。

---

## 8. 风险与权衡

| 风险                                                                       | 缓解                                                                               |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Phase 1 重构时改动多个文件，可能引入回归                                   | 每次只迁一类逻辑（先 palette 再 keyboard），每次跑全量测试                         |
| `core/state_palette.py` 设计错抽象，反而限制组件                           | Phase 1 不强求完美抽象——先把 listbox/autocomplete 共用的那部分提出来即可，按需扩展 |
| 视觉回归基线被打破（颜色微调被吃了一像素）                                 | 在 Phase 0 录基线快照（如果尚无），Phase 1 每步对比                                |
| 包结构后 IDE goto 跳 2 跳才到实现                                          | `__init__.py` 只做 re-export，现代 IDE（VS Code/PyCharm）能透传 goto，实测影响很小 |
| 用户私下 `from hero_side_ui.components.listbox import _bg_role_color` 之类 | 这种用法本就是脆弱依赖；不构成正式 API，可忽略                                     |

---

## 9. 我（Claude）的最终建议

1. **现在不要重构**。当前 Autocomplete 还在收尾、Tabs 刚定型，此时大动结构会同时引入两类不稳定。
2. **Autocomplete 完成、合并到 main 后**，立刻启动 Phase 1（横向抽取）。这一步**性价比最高**——单是消除 listbox/autocomplete 的重抄就能给你立竿见影的爽感，且不动外部结构。
3. **Phase 1 跑通且稳定一周后**，再启动 Phase 2（包形态统一）。这一步主要是搬家，但搬完之后整个项目"专业感"立刻上一个台阶——这是开源库给社区看的"第一印象"。
4. **不要追求每个文件 < 300 行**。Step 1 之后 1000 行以内的组件是健康的，强行拆只会增加跳转成本。把 1758 行变 1000 行已经是质变。
5. **关于"小组件单文件包"看起来浪费**：换个角度看，`button/button.py` 比 `button.py` 多一个 `__init__.py` 而已，但换来的是 `components/` 目录一眼扫过去 18 个**形态完全一致**的子项。这正是强迫症想要的东西，也是 Material-UI / Ant Design / Radix 等成熟组件库一致采用的结构。

---

## 10. Open Questions

- [ ] **`state_palette` 命名是否合适？** 也可叫 `theme_resolver` / `color_resolver`。倾向 `state_palette`，因为它解决的是"在某个状态下该用哪种颜色"。
- [ ] **`core/` vs `internals/`？** Material-UI 用 `internals/` 表示"用户不该 import"。我们已经有 `core/`（ThemeProvider 也在），保持 `core/` 一致。
- [ ] **`__init__.py` 是否需要 type stub（`.pyi`）？** 0.1.0 前可以不做；进入 beta 后建议加上以改善 IDE 体验。
- [ ] **Tabs 的 `_TabList` / `_CursorWidget` 抽不抽？** 它们和 Tabs 强耦合，目前倾向保留在 `tabs/_tab_list.py` 单独文件，不上移。

---

**等你裁决：**

- ✅ 同意大方向（方案 C：横向抽取 + 包形态统一）？
- ⏸ 同意"现在不动，Autocomplete 完成后再启动 Phase 1"的节奏？
- 🔧 有哪些 Open Questions 你想现在就拍板？

---

## 11. 实施记录（2026-05-13）

### 11.1 已完成：StatePalette（Step 1 + Step 2）

**新增**：`hero_side_ui/core/state_palette.py` + `tests/test_state_palette.py`

API 形态（最终）：

```python
from hero_side_ui import StatePalette

StatePalette.bg(variant, color, theme, state)        # 背景
StatePalette.border(variant, color, theme, state)    # 边框
StatePalette.text(variant, color, theme, state)      # 文字
StatePalette.text_default(theme)                     # 默认字色
StatePalette.text_description(theme)                 # 次级字色
StatePalette.shortcut_border(theme)                  # 快捷键标签边框
StatePalette.divider(theme)                          # 分隔线
StatePalette.selected_indicator(variant, color, theme)  # 选中标记
```

全 ``@staticmethod``，无状态。

**State 模型**：``resting`` / ``hover`` / ``focus`` / ``selected`` / ``disabled``。``focus`` 和 ``selected`` 视觉等同 ``hover``（HeroUI 标准行为，组件可直接按此简化）。

**listbox 迁移结果**：

| 指标 | 迁移前 | 迁移后 |
|---|---:|---:|
| `listbox.py` | 1758 行 | 1623 行（**-7.7%**）|
| `tests/test_listbox.py` | 57 通过 | 57 通过（零回归）|
| 新增 `core/state_palette.py` | — | 291 行（含详尽文档注释）|
| 新增 `tests/test_state_palette.py` | — | 310 行 / 41 用例 / 8.3s |

### 11.2 已否决：Step 3（其他组件接入）

**原假设**：button / checkbox / autocomplete / tabs 都各自重抄了 listbox 的颜色矩阵。

**实测发现**（grep 验证）：

- `button.py` 走 QSS 字符串拼接路径，**没抄 QColor 矩阵**
- `checkbox.py` 只有 selected/unselected 两态，直接用 HEROUI_COLORS 索引，**没有 variant×state 矩阵**
- `autocomplete.py` **完全复用** Listbox 实例，颜色逻辑由 listbox 内部负责
- `tabs.py` 有自己的一套，**没抄**

**结论**：listbox 的 13 个颜色函数是**它独有的复杂度**，不是跨组件重抄。StatePalette 的价值在于**未来加组件想要同款颜色矩阵可一行调用**，而不是立刻给 N 个组件减肥。

### 11.3 已否决：Step 4/5（KeyboardNav / SelectionModel）

**原假设**：listbox/autocomplete/tabs 共享键盘导航逻辑和 selection 状态机。

**实测发现**：

- listbox 的 `keyPressEvent` **只有 30 行**（Up/Down/Home/End/Enter 简单分发）
- autocomplete 的键盘导航**高度依赖** `_visible_items()` filter 模型 + 外挂 listbox 实例，抽到公共 KeyboardNav 反而更复杂
- tabs **根本没写** `keyPressEvent`，QButtonGroup 自带焦点流转直接用
- selection 状态在 listbox 里 ~60 行，其他组件不共享此模型

**结论**：这些"横切关注点"是命名幻觉。抽取只会增加跳转成本而不减少代码体积。

### 11.4 判断边界（写入未来 RFC 的准则）

1. **真实考古优先于设计直觉**：任何"抽取重复逻辑"的 RFC，必须先 grep 验证至少 3 个组件有**语义相同**的重复，才能动手。
2. **行数不是重构理由**：1500 行单文件如果是**不可简化的业务复杂度**（Qt 多 subwidget 编排、paintEvent 细节、QSS 拼接），拆了也不会更好读。
3. **StatePalette 是成功的孤例，不是模板**：颜色矩阵刚好是无状态、纯函数、有清晰数学结构，才适合抽。不要套用到有状态的逻辑上。

### 11.5 Phase 2（目录包化）的新判断

原计划"所有 18 组件改包结构"的主要理由是：**给巨头组件提供拆分空间**。但 Phase 1 的实测表明：

- listbox 的 1623 行里，**没有明显可单独成文件的子类**（_Item / _Section 确实独立，但它们对外就是 `ListboxItem` / `ListboxSection`，不需要藏）
- textarea / input 的 `_ResizeGrip` / `_ClearButton` 等**确实是独立子组件**，有拆分价值
- 但拆完是否真的"更好读"，需要先拆一个巨头试点

**建议**：Phase 2 **不再执行"18 组件全员包化"**，改为"按需文件夹化"——只对 textarea / input / popover / tabs 这几个有明确独立子组件的组件做包化，其余 14 个保持单文件。用户强迫症的成本用**加一条目录分组注释**处理：

```
components/
├── __init__.py
│
├── # --- 原子组件（单文件） ---
├── button.py
├── divider.py
├── switch.py
├── ...
│
├── # --- 复合组件（包结构） ---
├── input/
├── textarea/
├── popover/
└── tabs/
```

但这个**需要你最终拍板**——是用注释分组接受混合形态，还是坚持"视觉一致 = 全员包化"继续走完 Phase 2。我建议前者，因为给 14 个小组件强加 `__init__.py` 纯粹是视觉洁癖没有实际收益，反而给贡献者多加一层跳转。

### 11.6 下一步建议

选一条路：

- **(A)** 接受 Phase 1 到此结束，当作 alpha → beta 的结构整理告一段落，回到业务开发
- **(B)** 继续做 Phase 2，但改为"按需文件夹化"（见 11.5）
- **(C)** 坚持原 RFC 的"全员包化"方案，视觉一致优先

---

## 12. Phase 2 实施记录（2026-05-13）

### 12.1 最终目录结构

17 个组件全部统一为包形态。文件分布如下（行数为切分后实际值）：

| 包 | 主文件 | 子文件 | 总行数 |
|---|---:|---|---:|
| accordion | accordion.py 209 | item.py 394 / _indicator.py 79 | 686 |
| autocomplete | autocomplete.py 936 | _selector_button.py 83 / _end_content.py 60 | 1082 |
| button | button.py 559 | — | 562 |
| card | card.py 709 | — | 712 |
| checkbox | checkbox.py 661 | group.py 285 | 950 |
| divider | divider.py 255 | — | 258 |
| input | input.py 1196 | _line_edit.py 37 / _clear_button.py 77 / _wrapper.py 162 | 1475 |
| listbox | listbox.py 724 | item.py 773 / section.py 171 | 1673 |
| popover | popover.py 1067 | content.py 36 / _backdrop.py 109 / _click_catcher.py 48 / _constants.py 26 | 1290 |
| progress | progress.py 520 | circular.py 388 | 912 |
| scroll_shadow | scroll_shadow.py 626 | — | 629 |
| switch | switch.py 567 | — | 570 |
| tabs | tabs.py 562 | item.py 525 / _cursor.py 117 / _tab_list.py 70 / _helpers.py 111 / _constants.py 8 | 1397 |
| text | text.py 195 | — | 198 |
| textarea | textarea.py 1415 | _text_edit.py 65 / _resize_grip.py 99 | 1582 |
| theme_switcher | theme_switcher.py 189 | — | 192 |
| tooltip | tooltip.py 799 | — | 802 |

### 12.2 关键减肥（巨头组件）

| 组件 | 改造前主文件 | 改造后主文件 | 减量 |
|---|---:|---:|---:|
| listbox | 1623（Phase 1 后）| **724** | -55% |
| tabs | 1344 | **562** | -58% |
| autocomplete | 1108 | **936** | -16% |
| popover | 1250 | **1067** | -15% |
| input | 1439 | **1196** | -17% |
| textarea | 1566 | **1415** | -10% |

listbox 和 tabs 收获最大，因为 `ListboxItem` / `TabItem` 本身就是逻辑独立的可独立成文件的 class。input/textarea/popover 因为私有子组件较小，主文件减肥有限——但**视觉结构已经清晰**（外部贡献者一眼就能定位"清除按钮 → input/_clear_button.py"）。

### 12.3 拆分流程沉淀（下次复用）

每个组件按以下五步：

1. **切片**：Python 脚本读原文件，按 `^class ` 找各 class 起始行，`block_top()` 回退到上方注释/空行边界，切成 N 段 body。
2. **写新文件**：每个 body 配独立 preamble（docstring + 最小 import + 关联 import）。
3. **AST 自动补 import**：扫描每个 .py 用了哪些 `Q*` / `Optional` / `List` 等顶级名字，对照 `KNOWN_IMPORTS` 字典自动追加 import 行（工具脚本在 `.workbuddy/fix_imports.py`，本次用完已删，下次需要可复刻）。
4. **拯救"夹层"**：popover / tabs 顶部 `VALID_PLACEMENTS / _resolve_*()` 等在 imports 和第一个 class 之间的常量/helper，必须额外抽到 `_constants.py` / `_helpers.py`，否则切 class body 时丢失。
5. **跑组件测试**：每个组件独立验证后才进入下一个。

### 12.4 输出

- **780 测试全绿，零回归**
- 所有公共 import 路径不变
- 文件夹形态视觉一致（强迫症友好）
- 真正的拆分（不是单纯 mv）

### 12.5 待办

- [ ] Phase 2 应该 commit（建议 commit message：`♻️ refactor: 全组件包化 + 巨头按职责拆分`）
- [ ] `docs/` 下的引用路径如果出现 `from hero_side_ui.components.listbox import ListboxItem` 这种私有路径，需要更新（公共 import 不受影响）
- [ ] 0.1.0 发布前，可考虑给 `tools/` 加入 `split_component.py` 通用工具（本次 inline 脚本可固化）

---

## 13. Phase 2-5 深拆记录（2026-05-13，铁律 8 引入）

Phase 2 第一轮"包化"被用户当面指出"input.py 1196 / autocomplete.py 936 还是太大，拆了个寂寞"。立刻引入**铁律 8（单文件 ≤ 800 行硬指标）**写入 MEMORY.md，回头深拆四大巨头。

### 13.1 拆分手法：mixin 模式（继承 + 委托）

```python
class Input(_InputStylingMixin, _InputLayoutMixin, QWidget):
    ...
```

- mixin 文件只 import Qt/typing/themes，**不 import 主组件本身**（避免循环）
- mixin 里的方法直接 `self._color` / `self._wrapper` 用宿主类属性，**零参数迁移**
- MRO 顺序：`Input → MixinA → MixinB → QWidget → object`，不与 Qt 元类冲突
- 主组件文件改动量为零（除了基类列表）

### 13.2 四大巨头最终行数

| 组件 | 改造前主文件 | Phase 2-5 后主文件 | 减量 | mixin 文件 |
|---|---:|---:|---:|---|
| input | 1196 | **525** | -56% | _styling.py 552 / _layout.py 163 |
| autocomplete | 936 | **615** | -34% | _styling.py 90 / _callbacks.py 149 / _keyboard.py 145 |
| textarea | 1415 | **670** | -53% | _styling.py 544 / _autosize.py 96 / _layout.py 170 |
| popover | 1067 | **610** | -43% | _trigger.py 143 / _geometry.py 153 / _paint.py 221 |

### 13.3 拆分准则（落地为铁律 8）

每个 mixin 必须代表**一个清晰职责**：

- `_styling.py` —— "如何根据 variant×color×size×theme×state 推导每个子部件的颜色/QSS"
- `_layout.py` —— 几何同步（label 浮起、wrapper 重排、绝对定位槽）
- `_autosize.py` —— textarea 特有，多行高度计算
- `_keyboard.py` —— 方向键/Home/End/Enter 导航
- `_callbacks.py` —— 内部 `_on_*` 槽函数集中处
- `_trigger.py` —— popover 特有，触发器附着与悬停/点击
- `_geometry.py` —— popover 特有，弹层定位算法（12 种 placement）
- `_paint.py` —— popover 特有，paintEvent + 颜色推导

### 13.4 终态健康度

```
没有任何文件 > 800 行（铁律 8 合规）。
9 个文件在 600-800 黄色警戒区，全部是"主组件协调 + setter API surface"
（合理职责，不需要再拆）。
```

### 13.5 关键技术细节

1. **AST 自动补 import 工具**：`.workbuddy/fix_imports.py`（用完已删，下次拆需要时复刻）。`KNOWN_IMPORTS` 字典覆盖 PySide6.QtCore/QtGui/QtWidgets/QtSvg + typing + 项目层 themes/utils/core 名字。每次拆完跑一次能消除 90% 的 NameError。

2. **Heredoc 陷阱**：bash `<<'PY' ... PY` 里嵌 Python 多行字符串包含 `# === / # 圆角` 等组合时偶尔会破坏 heredoc 结束识别，把脚本写到 `.workbuddy/split_xxx.py` 单独执行最稳。

3. **textarea 复用 input 的私有 widget**：`from ..input._wrapper import _InputWrapper; from ..input._clear_button import _ClearButton`。**显式指到模块文件，不走 `..input` 包级 import**——保持私有性（input 包的公共 `__init__.py` 不 re-export 它们）。

### 13.6 Phase 2 全部完成

不再有遗留巨头。后续如果有新组件加入，按本 RFC §13 的 mixin 模板设计，主文件天然 < 600 行。
