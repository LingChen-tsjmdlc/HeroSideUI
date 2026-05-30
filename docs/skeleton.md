# Skeleton 骨架屏

> HeroUI v2 Skeleton 组件的 PySide6 实现。

骨架屏占位组件，用于展示加载状态和预期内容形状。支持 shimmer 扫光动画。

## 导入

```python
from hero_side_ui import Skeleton
```

## 基本用法

### 包裹子组件（自动匹配形状）

```python
from hero_side_ui import Skeleton

skeleton = Skeleton(radius="lg")
skeleton.setFixedSize(200, 96)
```

### 独立使用

```python
avatar = Skeleton(radius="full")
avatar.setFixedSize(48, 48)
```

### 加载完成切换

```python
skeleton = Skeleton(radius="lg")
skeleton.set_loaded(True)   # 显示内容，停止动画
skeleton.set_loaded(False)  # 显示骨架，恢复动画
```

## Props

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `child` | `QWidget \| None` | `None` | 包裹的子组件，Skeleton 会自动匹配其形状 |
| `is_loaded` | `bool` | `False` | 加载状态。`True` 时停止骨架动画并显示子组件 |
| `disable_animation` | `bool` | `False` | 禁用 shimmer 扫光动画 |
| `radius` | `str` | `"lg"` | 圆角大小：`none` / `sm` / `md` / `lg` / `full` |
| `theme` | `str` | `"auto"` | 主题：`auto` / `light` / `dark` |
| `parent` | `QWidget \| None` | `None` | 父组件 |

## Slots（视觉层）

| Slot | 说明 |
|------|------|
| **base** | 骨架屏主容器，包含 shimmer 扫光动画 |
| **content** | 被包裹的内容区域，`is_loaded=True` 时可见 |

## Data Attributes

`base` 元素上的属性：

| 属性 | 说明 |
|------|------|
| `is_loaded` | 当前加载状态 |

## 公共方法

| 方法 | 说明 |
|------|------|
| `set_loaded(loaded: bool)` | 切换加载状态，带 300ms opacity 过渡 |
| `is_loaded() -> bool` | 获取当前加载状态 |
| `set_disable_animation(disable: bool)` | 禁用/启用动画 |
| `set_radius(radius: str)` | 设置圆角 |
| `set_child(child: QWidget)` | 替换内容区域的子组件 |
| `set_theme(theme: str)` | 设置主题 (`auto`/`light`/`dark`) |
| `set_stylesheet(qss: str)` | 自定义样式表（覆盖默认样式） |

## 动画

- **shimmer 扫光**：从左到右循环移动的渐变亮带，周期 2000ms，InOutCubic 缓动
- 加载完成时 shimmer 自动停止，骨架层和内容层带 300ms 交叉淡入淡出过渡
- `disable_animation=True` 完全禁用动画，骨架仅显示静态底色
