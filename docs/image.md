# Image 图像

> HeroUI v2 Image 组件的 PySide6 实现。

支持本地路径 / Qt 资源 / 远程 URL / `QPixmap` / `QImage` 五种图源；自带圆角裁剪、阴影、Skeleton 占位、模糊副本、hover 放大等视觉变体。

## 导入

```python
from hero_side_ui import Image
```

## 基本用法

```python
img = Image(src="path/to/image.png", width=300, height=200)
```

### 远程 URL

```python
img = Image(src="https://uapis.cn/api/v1/random/image", width=300, height=200)
```

加载期间自动展示 Skeleton 占位动画，加载完成淡入显示真实图像。

### QPixmap 直传

```python
from PySide6.QtGui import QPixmap

pm = QPixmap("a.png")
img = Image(src=pm)
```

### 圆角

```python
img = Image(src=src, radius="full", width=120, height=120)
```

可选值：`none` / `sm` / `md` / `lg` / `full`，默认 `lg`。Image 使用专属圆角映射（比全局 RADIUS 整体大一号）。

### 裁剪模式（object_fit）

```python
img = Image(src=src, width=200, height=140, object_fit="contain")
```

可选值与 CSS `object-fit` 一致：

- `cover`（默认）—— 等比放大铺满，超出裁掉
- `contain` —— 等比缩放使整图可见，周围可能留白
- `fill` —— 拉伸铺满，不保持比例
- `none` —— 原始尺寸，居中裁剪
- `scale-down` —— `none` 与 `contain` 中取较小的

### 只设一边尺寸

```python
img = Image(src=src, width=180)   # 高度加载完成后按原图比例推算
img = Image(src=src, height=120)  # 宽度加载完成后按原图比例推算
```

### 阴影

```python
img = Image(src=src, shadow="md")
```

可选值：`none` / `sm` / `md` / `lg`，底层使用 `QGraphicsDropShadowEffect`。

### Hover 放大（isZoomed）

```python
img = Image(src=src, is_zoomed=True)               # 默认 1.25
img = Image(src=src, is_zoomed=True, zoom_factor=1.5)  # 自定义倍数
```

鼠标进入时 300ms 内缩放至 `zoom_factor`（默认 1.25），离开时还原。

### 模糊副本背景（isBlurred）

```python
img = Image(src=src, is_blurred=True)                      # 默认 10px 半径
img = Image(src=src, is_blurred=True, blur_amount=0.5)      # 温和一半
img = Image(src=src, is_blurred=True, blur_amount=2.0)      # 加强一倍
```

在主图下方放一份模糊放大的副本，模拟 HeroUI 的 `blur + saturate-150 + opacity-30 + scale-105 + translate-y-1`。`blur_amount` 是倍率，默认 1.0 对应 10px 半径（比 HeroUI 原生 16px 温和一档）。

### 受控 loading（强制显示 Skeleton）

```python
img = Image(src=src, is_loading=True)
img.set_is_loading(False)  # 自行决定何时取消 loading 锁
```

### Fallback（加载失败兜底图）

```python
img = Image(src=bad_url, fallback_src="path/to/placeholder.png")
```

主图加载失败或还未到达时展示 `fallback_src`。指定 `fallback_src` 时默认会关闭 Skeleton（与 HeroUI 行为一致）。

### 去除外层 wrapper

```python
img = Image(src=src, remove_wrapper=True)
```

`remove_wrapper=True` 时无 Skeleton / Zoom / Blur / Shadow 任何效果，仅保留圆角图像。

## Props

| Prop                | 类型                               | 默认值    | 说明                                                 |
| ------------------- | ---------------------------------- | --------- | ---------------------------------------------------- |
| `src`               | `str \| QPixmap \| QImage \| None` | `None`    | 图源；URL 走 QNetworkAccessManager 异步下载          |
| `width`             | `int \| None`                      | `None`    | 可视宽度（像素）；None 时加载完成后取原图原始宽度    |
| `height`            | `int \| None`                      | `None`    | 可视高度（像素）；None 时加载完成后取原图原始高度    |
| `radius`            | `str`                              | `"lg"`    | `none` / `sm` / `md` / `lg` / `full`                 |
| `shadow`            | `str`                              | `"none"`  | `none` / `sm` / `md` / `lg`                          |
| `object_fit`        | `str`                              | `"cover"` | `cover` / `contain` / `fill` / `none` / `scale-down` |
| `is_blurred`        | `bool`                             | `False`   | 模糊副本背景                                         |
| `blur_amount`       | `float`                            | `1.0`     | 模糊强度倍率（1.0 ≈ 10px 半径），>1 加强、<1 减弱    |
| `is_zoomed`         | `bool`                             | `False`   | hover 放大到 `zoom_factor`                           |
| `zoom_factor`       | `float`                            | `1.25`    | `is_zoomed=True` 时 hover 的放大倍数（>= 1.0）       |
| `is_loading`        | `bool`                             | `False`   | 受控 loading；`True` 时强制显示 Skeleton             |
| `disable_skeleton`  | `bool`                             | `False`   | 关闭 Skeleton（指定 `fallback_src` 时自动 `True`）   |
| `disable_animation` | `bool`                             | `False`   | 关闭所有动画（zoom hover / fade-in / shimmer）       |
| `remove_wrapper`    | `bool`                             | `False`   | 去掉 wrapper —— 等价于裸 QLabel 圆角图               |
| `fallback_src`      | `str \| QPixmap \| QImage \| None` | `None`    | 主图加载失败时的兜底图源                             |
| `parent`            | `QWidget \| None`                  | `None`    | 父组件                                               |

## 信号

| 信号       | 说明           |
| ---------- | -------------- |
| `loaded()` | 主图源加载成功 |
| `failed()` | 主图源加载失败 |

## 公共方法

| 方法                            | 说明                                        |
| ------------------------------- | ------------------------------------------- |
| `set_src(src)`                  | 设置新图源（重置 loading 状态）             |
| `set_is_loading(loading: bool)` | 切换受控 loading                            |
| `set_radius(r: str)`            | 设置圆角                                    |
| `set_shadow(s: str)`            | 设置阴影                                    |
| `set_is_zoomed(v: bool)`        | 设置 hover 放大开关                         |
| `set_zoom_factor(v: float)`     | 设置 hover 放大倍数                         |
| `set_object_fit(fit: str)`      | 设置裁剪模式                                |
| `set_is_blurred(v: bool)`       | 设置模糊副本开关                            |
| `set_blur_amount(v: float)`     | 设置模糊强度倍率                            |
| `set_disable_skeleton(v: bool)` | 设置是否禁用 Skeleton                       |
| `is_loading() -> bool`          | 当前是否处于 loading（受控 OR 真实加载中）  |
| `status() -> str`               | `pending` / `loading` / `loaded` / `failed` |
| `pixmap() -> QPixmap \| None`   | 已加载的原始图像                            |

## 视觉细节

- **圆角裁剪**：通过 `QPainterPath` clip 真正裁剪图像（QSS `border-radius` 在 Qt 不会裁剪 pixmap）。
- **object-fit**：5 种语义与 CSS 对齐；draw 时先按 fit 算出 target rect，再叠加 zoom 倍率。
- **fade-in**：data-loaded 后图像 opacity 0→1，300ms `OutCubic`。
- **isZoomed**：300ms `OutCubic` 缩放至 `zoom_factor`（默认 1.25，可配）。
- **isBlurred**：副本被缩到 200px 内做 saturate + alpha 预处理后再 `QGraphicsBlurEffect`，默认半径 10px，可通过 `blur_amount` 倍率调节。
- **shadow**：`QGraphicsDropShadowEffect`，参数表 `IMAGE_SHADOWS`（`themes.component_presets.image`）。
- **Skeleton**：完全复用项目 `Skeleton` 组件，加载完成 `set_loaded(True)` 触发 300ms 交叉淡入淡出。
- **远程 URL 节流**：进程级单例 `_UrlRequestQueue` 把所有 `http(s)` 请求串行化，相邻两次实际发起的间隔随机 1.0–1.5s。本地路径 / `QPixmap` / `QImage` 不受影响。
