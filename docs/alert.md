# Alert

HeroUI v2 风格的 Alert 通知组件，用于提供操作或事件的临时反馈。

源码对照：
- 样式: https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/alert.ts
- 组件: https://github.com/heroui-inc/heroui/tree/main/packages/components/alert

## 导入

```python
from hero_side_ui import Alert
```

## 基本用法

```python
alert = Alert(
    title="注意",
    description="这是一条重要通知。",
    color="warning",
    variant="flat",
)
```

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `str` | `""` | 标题文本 |
| `description` | `str` | `""` | 描述文本 |
| `color` | `str` | `"default"` | 颜色变体 |
| `variant` | `str` | `"flat"` | 样式变体 |
| `radius` | `str` | `"md"` | 圆角大小 |
| `icon` | `str \| None` | `None` | 自定义图标名或 SVG 路径（None=基于 color 自动选默认图标） |
| `start_content` | `QWidget \| None` | `None` | 起始位置的自定义 widget |
| `end_content` | `QWidget \| None` | `None` | 末尾自定义 widget（如操作按钮） |
| `is_visible` | `bool` | `True` | 控制可见性 |
| `is_closable` | `bool` | `False` | 是否显示关闭按钮 |
| `hide_icon` | `bool` | `False` | 隐藏图标 |
| `hide_icon_wrapper` | `bool` | `False` | 隐藏图标容器（并移除间距） |
| `on_close` | `Callable \| None` | `None` | 关闭时的回调函数 |
| `theme` | `str` | `"auto"` | 主题模式：`"auto"` / `"light"` / `"dark"` |
| `parent` | `QWidget \| None` | `None` | 父部件 |

## 可选值

### color

`"default"` `"primary"` `"secondary"` `"success"` `"warning"` `"danger"`

### variant

`"solid"` `"bordered"` `"flat"` `"faded"`

### radius

`"none"` `"sm"` `"md"` `"lg"` `"full"`

## 默认图标映射

| color | 图标 |
|-------|------|
| `default` | information-circle （info） |
| `primary` | information-circle （info） |
| `secondary` | information-circle （info） |
| `success` | check （勾选） |
| `warning` | exclamation-triangle （警告三角） |
| `danger` | x-circle （错误叉） |

可通过 `icon` 参数传入自定义图标名覆盖。

## 信号

| 信号 | 说明 |
|------|------|
| `closed` | Alert 关闭时发射 |

## 公共方法

| 方法 | 说明 |
|------|------|
| `set_color(color)` | 切换颜色变体 |
| `set_variant(variant)` | 切换样式变体 |
| `set_radius(radius)` | 切换圆角 |
| `set_theme(theme)` | 切换主题模式 |
| `set_title(title)` | 更新标题 |
| `set_description(desc)` | 更新描述 |
| `set_icon(icon)` | 设置自定义图标，传 None 恢复默认 |
| `set_hide_icon(hide)` | 切换图标可见性 |
| `set_hide_icon_wrapper(hide)` | 切换图标容器可见性 |
| `set_visible(visible)` | 控制可见性 |
| `is_visible()` | 返回当前可见性 |
| `set_closable(closable)` | 控制关闭按钮显示 |
| `set_start_content(widget)` | 插入起始自定义 widget |
| `set_end_content(widget)` | 插入末尾自定义 widget |
| `close()` | 程序化关闭（等价于点击关闭按钮） |

## 示例

### 颜色变体

```python
for color in ["default", "primary", "secondary", "success", "warning", "danger"]:
    alert = Alert(title=color.capitalize(), description="通知内容", color=color, variant="flat")
```

### 带操作按钮

```python
btn = Button("了解详情", color="primary", variant="light", size="sm")
alert = Alert(
    title="有新版本",
    description="v2.0 已发布。",
    color="primary",
    variant="flat",
    end_content=btn,
)
```

### 可关闭

```python
alert = Alert(
    title="操作成功",
    description="数据已保存。",
    color="success",
    is_closable=True,
    on_close=lambda: print("已关闭"),
)
```

### 受控可见性

```python
alert = Alert(title="通知", is_visible=False)
# ... 某个条件触发 ...
alert.set_visible(True)
```
