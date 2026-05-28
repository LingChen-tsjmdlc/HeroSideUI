# Radio

基于 HeroUI v2 [radio-group](https://v2.heroui.com/docs/components/radio-group) 复刻的单选组件。`Radio` 继承 `RadioBase → QAbstractButton`，外观全部通过 `paintEvent` 自绘；`RadioGroup` 是互斥容器，统一管理颜色/尺寸/主题并聚合 `value_changed` 信号。

## 特性

- **6 种颜色**：`default` · `primary` · `secondary` · `success` · `warning` · `danger`
- **3 种尺寸**：`sm` · `md`（默认）· `lg`
- **2 种变体**：`default`（经典圆点）· `card`（卡片选择器，对齐 v2 Custom Styles）
- **description**：每个 Radio 可附带副文本
- **isDisabled / isInvalid / disableAnimation**：状态切换
- **theme**：`auto` / `light` / `dark`，`auto` 自动跟随全局 `ThemeProvider`
- **动画**：内圆点 `scale 0→1 + opacity 0→1`（180ms OutCubic）；按压 scale-95（80ms）
- **RadioBase**：可继承的基类，状态机/互斥/动画全托管，只需自己实现 `paintEvent`

## 快速开始

```python
from hero_side_ui import Radio, RadioGroup

# 单独使用
r = Radio("Accept terms", color="primary")
r.toggled.connect(lambda ok: print("checked:", ok))

# 配合 RadioGroup
group = RadioGroup(label="Select your favorite city")
group.create_radio("Buenos Aires", value="buenos-aires")
group.create_radio("London",       value="london")
group.create_radio("Tokyo",        value="tokyo")
group.value_changed.connect(lambda v: print("selected:", v))
```

## Radio 参数

| 参数                | 类型                                                                          | 默认值      | 说明                                              |
| ------------------- | ----------------------------------------------------------------------------- | ----------- | ------------------------------------------------- |
| `text`              | `str`                                                                         | `""`        | label 文字                                        |
| `value`             | `str \| None`                                                                 | `text`      | 在 `RadioGroup` 中使用的唯一标识，未传时等于 text |
| `description`       | `str`                                                                         | `""`        | label 下方的副文本                                |
| `is_selected`       | `bool`                                                                        | `False`     | 初始选中                                          |
| `color`             | `"default" \| "primary" \| "secondary" \| "success" \| "warning" \| "danger"` | `"primary"` | 选中态颜色                                        |
| `size`              | `"sm" \| "md" \| "lg"`                                                        | `"md"`      | 组件尺寸                                          |
| `variant`           | `"default" \| "card"`                                                         | `"default"` | 视觉变体（见下方 [variant](#variant-变体) 章节）  |
| `is_disabled`       | `bool`                                                                        | `False`     | 禁用（半透明 + 不响应鼠标）                       |
| `is_invalid`        | `bool`                                                                        | `False`     | 无效态（圆环 / label 变 `danger`）                |
| `disable_animation` | `bool`                                                                        | `False`     | 关闭所有过渡动画                                  |
| `theme`             | `"auto" \| "light" \| "dark"`                                                 | `"auto"`    | `auto` 跟随全局 `ThemeProvider`                   |

## 信号

- `toggled(bool)` / `clicked(bool)` / `pressed()` / `released()`：`QAbstractButton` 原生信号。
- `selected(str)`：选中时发射 `value`（取消选中不发射）。

## 动态 API

```python
r.set_color("success")
r.set_size("lg")
r.set_variant("card")
r.set_description("副文本")
r.set_is_disabled(True)
r.set_is_invalid(True)
r.set_disable_animation(True)
r.set_theme("dark")          # 或 "light" / "auto"
r.set_value("new-value")

# 选中状态
r.setChecked(True)           # 原生
r.set_is_selected(True)      # 别名
r.is_selected()              # 别名 isChecked()
r.value()                    # 读取 value
r.variant()                  # 读取当前 variant
r.description()              # 读取 description
```

## variant 变体

### default（默认）

经典圆点 radio：圆环在左，label / description 在右。

```python
Radio("Free", value="free", color="primary")
```

### card

卡片式选择器：整体带圆角边框，label / description 在左，圆点在右。选中时边框渐变为主色，hover 时底色切换为 `bg-content2`。对齐 HeroUI v2 Custom Styles 示例。

```python
Radio("Free", value="free", description="Up to 20 items", variant="card")
```

通常配合 `RadioGroup(variant="card")` 一次性广播给所有子 radio：

```python
group = RadioGroup(label="Plans", variant="card")
group.create_radio("Free",       value="free",       description="Up to 20 items")
group.create_radio("Pro",        value="pro",        description="Unlimited items. $10 per month.")
group.create_radio("Enterprise", value="enterprise", description="24/7 support. Contact us for pricing.")
```

## 尺寸规格

| size | wrapper | control | label 字号 | description 字号 |
| ---- | ------- | ------- | ---------- | ---------------- |
| `sm` | 16×16   | 6×6     | 13px       | 11px             |
| `md` | 20×20   | 8×8     | 14px       | 13px             |
| `lg` | 24×24   | 10×10   | 16px       | 14px             |

---

## RadioGroup

互斥单选容器，统一管理颜色/尺寸/变体/主题/方向，提供 `label` / `description` / `errorMessage` / 必填标记，并聚合 `value_changed` 信号。

### 快速开始

```python
from hero_side_ui import RadioGroup

group = RadioGroup(
    label="Plans",
    description="Selected plan can be changed at any time.",
    color="primary",
    default_value="pro",
)
group.create_radio("Free",       value="free",       description="Up to 20 items")
group.create_radio("Pro",        value="pro",        description="Unlimited items. $10 per month.")
group.create_radio("Enterprise", value="enterprise", description="24/7 support. Contact us for pricing.")

group.value_changed.connect(lambda v: print("selected:", v))
print(group.value())        # "pro"
group.set_value("free")
```

### 参数

| 参数                | 类型                                                                          | 默认值       | 说明                                     |
| ------------------- | ----------------------------------------------------------------------------- | ------------ | ---------------------------------------- |
| `label`             | `str`                                                                         | `""`         | 顶部 label                               |
| `description`       | `str`                                                                         | `""`         | 帮助文字（`is_invalid` 时被 error 覆盖） |
| `error_message`     | `str`                                                                         | `""`         | `is_invalid=True` 时展示的错误文字       |
| `orientation`       | `"vertical" \| "horizontal"`                                                  | `"vertical"` | 子 radio 排布方向                        |
| `color`             | `"default" \| "primary" \| "secondary" \| "success" \| "warning" \| "danger"` | `"primary"`  | 广播到所有子 radio                       |
| `size`              | `"sm" \| "md" \| "lg"`                                                        | `"md"`       | 广播到所有子 radio                       |
| `variant`           | `"default" \| "card"`                                                         | `"default"`  | 广播到所有子 radio                       |
| `is_disabled`       | `bool`                                                                        | `False`      | 禁用整组                                 |
| `is_invalid`        | `bool`                                                                        | `False`      | 无效态（子 radio 变 danger）             |
| `is_required`       | `bool`                                                                        | `False`      | label 后显示红色 `*`                     |
| `default_value`     | `str \| None`                                                                 | `None`       | 初始选中的 radio value                   |
| `disable_animation` | `bool`                                                                        | `False`      | 广播到所有子 radio                       |
| `theme`             | `"auto" \| "light" \| "dark"`                                                 | `"auto"`     | `auto` 跟随全局 `ThemeProvider`          |

### 信号

- `value_changed(str | None)`：任一子 radio 选中时发射当前 value；无选中时为 `None`。

### 方法

```python
# 添加子 radio
group.create_radio("Free", value="free", description="...")  # 创建并加入
group.add_radio(my_radio)                                     # 加入已构造的 RadioBase 子类

# value 读写
group.value()              # 当前选中 value，无选中返回 None
group.set_value("pro")     # 程序化选中（同时取消其他）

# 动态属性（自动广播到所有子 radio）
group.set_color("success")
group.set_size("lg")
group.set_variant("card")
group.set_theme("dark")
group.set_is_disabled(True)
group.set_is_invalid(True)
group.set_is_required(True)
group.set_orientation("horizontal")
group.set_label("新标题")
group.set_description("新帮助文字")
group.set_error_message("新错误文字")
group.set_disable_animation(True)
group.variant()            # 读取当前 variant
```

### 互斥语义

- 选中一个 radio 时，其他 radio 自动取消选中。
- 已选中的 radio 再次点击**不会取消**（对齐 HeroUI 行为）。
- `set_value(None)` 可程序化清空选中。

---

## RadioBase — 自造视觉

`RadioBase` 是 `Radio` 的基类，只承载状态机、动画、互斥钩子和数据 API，**不实现 `paintEvent`**。继承它可以完全自定义视觉，同时让 `RadioGroup` 自动托管互斥逻辑。

对齐 HeroUI v2 Custom Implementation（`useRadio` hook）的 PySide 等价写法。

### 用法

```python
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from hero_side_ui import RadioBase, RadioGroup
from hero_side_ui.themes import HEROUI_COLORS

class MyRadio(RadioBase):
    """自定义卡片样式 Radio"""

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(300, 56)

    def paintEvent(self, _event):
        is_dark = self._theme == "dark"
        dc = HEROUI_COLORS["default"]
        primary = QColor(HEROUI_COLORS["primary"][500])

        bg = QColor("#ffffff" if not is_dark else dc[900])
        border = primary if self.isChecked() else QColor(dc[300] if not is_dark else dc[700])
        if self._hover and not self.isChecked():
            bg = QColor(dc[100] if not is_dark else dc[800])

        rect = self.rect()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._is_disabled:
            p.setOpacity(0.5)

        # 卡片底
        p.setPen(QPen(border, 2))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(1, 1, rect.width() - 2, rect.height() - 2), 10, 10)

        # label
        p.setPen(QPen(QColor("#11181c" if not is_dark else "#ecedee")))
        p.drawText(rect.adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignVCenter, self.text())
        p.end()


# 加入 RadioGroup，互斥 / value_changed 自动生效
group = RadioGroup(label="Plans")
group.add_radio(MyRadio("Free",       value="free"))
group.add_radio(MyRadio("Pro",        value="pro"))
group.add_radio(MyRadio("Enterprise", value="enterprise"))
group.value_changed.connect(lambda v: print("selected:", v))
```

### RadioBase 可用属性（paintEvent 内直接读取）

| 属性                     | 类型    | 说明                          |
| ------------------------ | ------- | ----------------------------- |
| `self._theme`            | `str`   | `"light"` 或 `"dark"`         |
| `self._color`            | `str`   | 当前颜色 token                |
| `self._size`             | `str`   | 当前尺寸 token                |
| `self._variant`          | `str`   | 当前 variant                  |
| `self._hover`            | `bool`  | 鼠标悬停中                    |
| `self._is_disabled`      | `bool`  | 禁用状态                      |
| `self._is_invalid`       | `bool`  | 无效状态                      |
| `self._control_progress` | `float` | 选中动画进度 0.0→1.0（180ms） |
| `self._press_progress`   | `float` | 按压动画进度 0.0→1.0（80ms）  |
| `self.isChecked()`       | `bool`  | 当前是否选中                  |
| `self.text()`            | `str`   | label 文字                    |
| `self._description`      | `str`   | 副文本                        |
| `self._value`            | `str`   | value 标识                    |

> `_control_progress` 和 `_press_progress` 是 Qt `Property` 驱动的动画属性，每帧自动触发 `update()`，在 `paintEvent` 里直接读取即可实现平滑过渡。

### 注意事项

- 必须实现 `paintEvent`，否则组件不可见。
- 建议同时覆写 `sizeHint()` 返回合理尺寸，否则 layout 可能压缩为 0。
- `RadioGroup.add_radio()` 接受任意 `RadioBase` 子类，加入后自动注入互斥守卫并监听 `toggled` 信号。
- 不要在 `paintEvent` 里调用 `self.update()`，会导致无限重绘。

---

## 与 HeroUI v2 的差异

| 特性       | HeroUI v2                                         | HeroSideUI                                         |
| ---------- | ------------------------------------------------- | -------------------------------------------------- |
| 样式定制   | `classNames={{ base: cn(...) }}` 传 Tailwind 类名 | `variant="card"` 内置变体；或继承 `RadioBase` 自绘 |
| 自造 Radio | `useRadio()` hook 返回 prop getter                | 继承 `RadioBase`，状态/互斥/动画全托管             |
| 动画曲线   | CSS `transition`                                  | `QPropertyAnimation` OutCubic 180ms                |
| 按压反馈   | `scale-95` CSS transform                          | `QPainter.translate + scale` 自绘                  |
| 已选中再点 | 不取消（radio 语义）                              | 同，由 `_toggle_guard` 钩子拦截                    |
| RTL 支持   | 有                                                | 暂无                                               |

## 相关文档

- [Checkbox](./checkbox.md) — 多选框，支持 indeterminate / lineThrough
- [Switch](./switch.md) — 胶囊开关，用于二态切换
- [ThemeProvider](./theme_provider.md) — 全局主题管理
