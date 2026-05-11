# ThemeProvider — 全局主题管理器

HeroSideUI 的全局主题管理器，支持 auto（跟随系统）、light、dark 三种模式，以及一键切换。

## 快速开始

```python
from hero_side_ui import ThemeProvider, Button

# 获取单例
provider = ThemeProvider.instance()

# 创建按钮（默认 theme="auto"，自动注册到 provider）
btn = Button("Click me")

# 一键切换
provider.toggle()  # btn 自动跟随变化

# 也可以直接设定模式
provider.set_mode("dark")   # 所有 auto 组件变为暗色
provider.set_mode("light")  # 所有 auto 组件变为亮色
provider.set_mode("auto")   # 跟随系统
```

## 核心概念

### 三种模式 (mode)

| 模式 | 说明 |
|------|------|
| `"auto"` | 跟随操作系统的亮暗色设置（默认） |
| `"light"` | 强制亮色 |
| `"dark"` | 强制暗色 |

### 注册策略

组件的 `theme` 参数决定注册行为：

| 组件 theme= | 行为 |
|---|---|
| `"auto"`（默认） | 自动注册到 ThemeProvider，跟随全局切换 |
| `"light"` | 硬锁亮色，不注册，不受 toggle/set_mode 影响 |
| `"dark"` | 硬锁暗色，不注册，不受 toggle/set_mode 影响 |

```python
btn_auto = Button("跟随全局")           # 跟随切换 ✓
btn_fixed = Button("固定暗色", theme="dark")  # 永远暗色，不受切换影响
```

### 系统主题实时检测

在 `auto` 模式下，ThemeProvider 会：
1. 启动时检测系统当前亮暗色（Qt 6.5+ `colorScheme()` 或 QPalette 亮度回退）
2. 监听系统主题变化信号（`styleHints().colorSchemeChanged`）
3. 系统切换时自动广播给所有已注册组件

## API 参考

### `ThemeProvider.instance() -> ThemeProvider`

获取全局单例。懒初始化。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `mode` | `str` (只读) | 当前模式：`"auto"` / `"light"` / `"dark"` |
| `current_theme` | `str` (只读) | 当前实际生效的主题：`"light"` / `"dark"` |
| `registered_count` | `int` (只读) | 已注册组件数量 |

### 方法

#### `set_mode(mode: str) -> None`

设置主题模式。

- `"auto"`: 跟随系统
- `"light"`: 强制亮色
- `"dark"`: 强制暗色

如果新模式导致实际主题变化，会广播给所有已注册组件。

#### `toggle() -> None`

一键切换。将当前主题在 light/dark 之间反转。

- 切换后模式变为 `"light"` 或 `"dark"`（不再是 auto）
- 如果当前是 auto 模式，基于当前实际主题反转

#### `register(widget) -> None`

手动注册组件到管理器。组件需有 `set_theme(theme: str)` 方法。

- 注册时会立即同步一次当前主题
- 使用 weakref，组件销毁时自动清理

#### `unregister(widget) -> None`

从管理器中移除组件。

#### `is_registered(widget) -> bool`

检查组件是否已注册。

### 信号

| 信号 | 参数 | 说明 |
|------|------|------|
| `theme_changed` | `str` ("light"/"dark") | 实际主题变化时发射 |
| `mode_changed` | `str` ("auto"/"light"/"dark") | 模式变化时发射 |

## 组件适配

所有 HeroSideUI 组件的 `theme` 参数默认值为 `"auto"`：

```python
# 以下等价 — 都会跟随全局切换
btn = Button("A")
btn = Button("A", theme="auto")

# 硬锁 — 不受全局切换影响
btn = Button("B", theme="dark")
```

### `set_theme(theme)` 方法变化

组件的 `set_theme()` 现在也接受 `"auto"`：

```python
btn = Button("Test", theme="light")  # 硬锁亮色
btn.set_theme("auto")                 # 切换为跟随全局（并注册到 provider）
btn.set_theme("dark")                 # 再次硬锁（并取消注册）
```

## 示例

完整示例见 `examples/theme_toggle/demo.py`：

```python
from hero_side_ui import ThemeProvider, Button

provider = ThemeProvider.instance()

# 创建切换按钮
toggle_btn = Button("切换主题", color="primary")
toggle_btn.clicked.connect(provider.toggle)

# 跟随切换的组件
btn1 = Button("按钮 A", color="success")
btn2 = Button("按钮 B", color="danger", variant="flat")

# 不跟随的组件
btn_fixed = Button("固定暗色", theme="dark")
```

## 向后兼容

- 传 `theme="light"` 或 `theme="dark"` 的行为与之前完全一致
- 不传 `theme` → 默认 `"auto"` → 在你不使用 ThemeProvider 的情况下，auto 会 fallback 到系统检测结果
- ThemeProvider 是按需初始化的单例，不影响不使用它的代码
